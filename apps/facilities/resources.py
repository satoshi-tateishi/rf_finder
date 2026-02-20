import csv
import unicodedata

from django.db import transaction
from import_export import fields, resources

from .models import Facility, TVChannelStatus, WirelessEquipment


def normalize_address(text):
    if not isinstance(text, str):
        return ''
    text = unicodedata.normalize('NFKC', text)
    kanji_map = str.maketrans('一二三四五六七八九〇', '1234567890')
    text = text.translate(kanji_map)
    return text.replace(' ', '').replace('　', '')


_zip_lookup_cache = None


def get_zip_lookup():
    global _zip_lookup_cache
    if _zip_lookup_cache is not None:
        return _zip_lookup_cache

    _zip_lookup_cache = {}
    import os

    from django.conf import settings

    csv_path = os.path.join(settings.BASE_DIR, 'csv', 'x-ken-all.csv')
    if os.path.exists(csv_path):
        with open(csv_path, 'r', encoding='shift_jis') as f:
            reader = csv.reader(f)
            for row in reader:
                if len(row) < 9:
                    continue
                zip_code = row[2]
                pref = row[6]
                addr = row[7] + row[8]
                if addr == '以下に掲載がない場合':
                    addr = ''
                key = normalize_address(pref + addr)
                if key not in _zip_lookup_cache:
                    _zip_lookup_cache[key] = zip_code
    return _zip_lookup_cache


def find_zip_code(prefecture, address):
    norm_target = normalize_address(prefecture + address)
    if not norm_target:
        return ''

    lookup = get_zip_lookup()
    if norm_target in lookup:
        return lookup[norm_target]

    for key, val in lookup.items():
        if norm_target.startswith(key):
            return val
    return ''


class FacilityResource(resources.ModelResource):
    class Meta:
        model = Facility
        fields = ('postal_code', 'prefecture', 'address', 'name', 'category', 'applied_area')
        export_order = ('postal_code', 'prefecture', 'address', 'name', 'category', 'applied_area') + tuple(
            f'{ch}CH' for ch in range(13, 54)
        )

    def __init__(self):
        super().__init__()
        for ch in range(13, 54):
            field_name = f'{ch}CH'
            self.fields[field_name] = fields.Field(column_name=field_name, attribute=None)

    def export(self, queryset=None, *args, **kwargs):
        return super().export(queryset, *args, **kwargs)

    def export_resource(self, obj, **kwargs):
        self._current_obj_channels = {c.channel_number: c.is_available for c in obj.channels.all()}
        return super().export_resource(obj, **kwargs)

    def dehydrate_postal_code(self, obj):
        if obj.postal_code:
            return obj.postal_code
        return find_zip_code(obj.prefecture, obj.address)

    def get_export_value(self, field, obj):
        if field.column_name.endswith('CH'):
            ch_num = int(field.column_name.replace('CH', ''))
            is_avail = self._current_obj_channels.get(ch_num, True)
            return '○' if is_avail else '×'
        return super().get_export_value(field, obj)

    def before_import(self, dataset, using_transactions, dry_run, **kwargs):
        dataset.insert_col(0, lambda row: None, header='id')

    def before_import_row(self, row, **row_kwargs):
        row['postal_code'] = find_zip_code(row['prefecture'], row['address'])

    def after_import(self, dataset, result, using_transactions, dry_run, **kwargs):
        if not dry_run:
            for row_result in result.rows:
                if (
                    row_result.import_type == result.IMPORT_TYPE_NEW
                    or row_result.import_type == result.IMPORT_TYPE_UPDATE
                ):
                    facility = Facility.objects.get(pk=row_result.object_id)
                    row_data = dataset.dict[row_result.object_index]

                    with transaction.atomic():
                        for ch in range(13, 54):
                            val = row_data.get(f'{ch}CH')
                            if val:
                                is_avail = val == '○'
                                TVChannelStatus.objects.update_or_create(
                                    facility=facility, channel_number=ch, defaults={'is_available': is_avail}
                                )


class WirelessEquipmentResource(resources.ModelResource):
    class Meta:
        model = WirelessEquipment
        import_id_fields = ('model_name',)
        fields = ('manufacturer', 'model_name', 'min_frequency', 'max_frequency')
