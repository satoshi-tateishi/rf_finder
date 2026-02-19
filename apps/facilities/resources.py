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
    # CH状態をエクスポートに含めるための設定
    class Meta:
        model = Facility
        fields = ('id', 'name', 'prefecture', 'address', 'category', 'applied_area', 'external_id')
        export_order = ('id', 'name', 'prefecture', 'address', 'category', 'applied_area', 'external_id') + tuple(f'{ch}CH' for ch in range(13, 54))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # 動的にCHカラムをフィールドとして追加
        for ch in range(13, 54):
            field_name = f'{ch}CH'
            self.fields[field_name] = fields.Field(column_name=field_name, attribute=None)

    def export_field(self, field, obj):
        if field.column_name.endswith('CH'):
            ch_num = int(field.column_name.replace('CH', ''))
            status = obj.channels.filter(channel_number=ch_num).first()
            if status:
                return '○' if status.is_available else ''
            return ''
        return super().export_field(field, obj)

    def before_save_instance(self, instance, using_transactions, dry_run):
        # 郵便番号が空の場合、住所から自動計算
        if not instance.external_id or instance.external_id == "":
            instance.external_id = find_zip_code(instance.prefecture, instance.address)

    def after_save_instance(self, instance, using_transactions, dry_run):
        if dry_run:
            return
            
        # インポート行データからCH状態を抽出して保存
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
