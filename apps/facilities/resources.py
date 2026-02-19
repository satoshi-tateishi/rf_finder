import csv
import unicodedata
import re
from pathlib import Path
from django.conf import settings
from import_export import resources, fields
from .models import Facility, TVChannelStatus, WirelessEquipment

def normalize_address(text):
    if not isinstance(text, str): return ""
    text = unicodedata.normalize('NFKC', text)
    kanji_map = str.maketrans('一二三四五六七八九〇', '1234567890')
    text = text.translate(kanji_map)
    text = re.sub(r'([0-9]+)丁目', r'\1-', text)
    text = re.sub(r'([0-9]+)番[地丁]?', r'\1-', text)
    text = re.sub(r'([0-9]+)号', r'\1', text)
    text = text.replace(' ', '').replace('　', '')
    text = re.sub(r'-+', '-', text).strip('-')
    return text

_zip_lookup = None

def get_zip_lookup():
    global _zip_lookup
    if _zip_lookup is not None:
        return _zip_lookup
    
    zip_csv_path = Path(settings.BASE_DIR) / "csv" / "utf_ken_all.csv"
    if not zip_csv_path.exists():
        return []
        
    lookup = []
    try:
        with open(zip_csv_path, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            for row in reader:
                if len(row) < 9: continue
                zip_code = row[2]
                pref = row[6]
                city = row[7]
                town = row[8]
                if town == '以下に掲載がない場合':
                    town = ''
                
                full_addr = normalize_address(pref + city + town)
                if full_addr:
                    lookup.append((full_addr, zip_code))
    except Exception:
        return []
                
    lookup.sort(key=lambda x: len(x[0]), reverse=True)
    _zip_lookup = lookup
    return _zip_lookup

def find_zip_code(prefecture, address):
    norm_target = normalize_address(prefecture + address)
    if not norm_target: return ""
    
    lookup = get_zip_lookup()
    for addr_key, zip_code in lookup:
        if addr_key in norm_target:
            return f"{zip_code[:3]}-{zip_code[3:]}" if len(zip_code) == 7 else zip_code
    return ""

class FacilityResource(resources.ModelResource):
    # インポート用CSVのヘッダー名に合わせる
    postal_code = fields.Field(attribute='postal_code', column_name='郵便番号')
    prefecture = fields.Field(attribute='prefecture', column_name='都道府県名')
    address = fields.Field(attribute='address', column_name='住所')
    name = fields.Field(attribute='name', column_name='施設名')
    category = fields.Field(attribute='category', column_name='屋内外')
    applied_area = fields.Field(attribute='applied_area', column_name='適用エリア')

    class Meta:
        model = Facility
        fields = ('postal_code', 'prefecture', 'address', 'name', 'category', 'applied_area')
        export_order = ('postal_code', 'prefecture', 'address', 'name', 'category', 'applied_area') + tuple(f'{ch}CH' for ch in range(13, 54))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # 動的にCHカラムをフィールドとして追加
        for ch in range(13, 54):
            field_name = f'{ch}CH'
            self.fields[field_name] = fields.Field(column_name=field_name, attribute=None)

    def export(self, queryset=None, *args, **kwargs):
        if queryset is not None:
            queryset = queryset.prefetch_related('channels')
        return super().export(queryset, *args, **kwargs)

    def export_resource(self, obj, **kwargs):
        self._current_obj_channels = {c.channel_number: c.is_available for c in obj.channels.all()}
        return super().export_resource(obj, **kwargs)

    def export_field(self, field, obj, **kwargs):
        if hasattr(field, 'column_name') and str(field.column_name).endswith('CH'):
            try:
                ch_num = int(str(field.column_name).replace('CH', ''))
                if getattr(self, '_current_obj_channels', {}).get(ch_num):
                    return '○'
            except (ValueError, AttributeError):
                pass
            return ''
        return super().export_field(field, obj, **kwargs)

    def before_save_instance(self, instance, using_transactions, dry_run):
        if not instance.postal_code or instance.postal_code == "":
            instance.postal_code = find_zip_code(instance.prefecture, instance.address)

    def after_save_instance(self, instance, using_transactions, dry_run):
        if dry_run:
            return
        if hasattr(self, 'current_row'):
            row = self.current_row
            for ch in range(13, 54):
                ch_key = f'{ch}CH'
                is_available = False
                if ch == 53:
                    is_available = True
                elif ch_key in row:
                    val = str(row[ch_key]).strip()
                    if val in ['○', '1', 'available']:
                        is_available = True
                TVChannelStatus.objects.update_or_create(
                    facility=instance,
                    channel_number=ch,
                    defaults={'is_available': is_available}
                )

    def before_import_row(self, row, **kwargs):
        self.current_row = row

class WirelessEquipmentResource(resources.ModelResource):
    class Meta:
        model = WirelessEquipment

class TVChannelStatusResource(resources.ModelResource):
    class Meta:
        model = TVChannelStatus
