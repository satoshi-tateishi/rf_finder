import csv
import os

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.facilities.models import Facility, TVChannelStatus, WirelessEquipment


class Command(BaseCommand):
    help = 'Import facility and device data from CSV files (Replaces existing data)'

    def handle(self, *args, **options):
        # BASE_DIR から相対的に csv ディレクトリを取得するように修正
        from django.conf import settings

        csv_dir = os.path.join(settings.BASE_DIR, 'csv')

        with transaction.atomic():
            # 既存データの全削除 (TRUNCATE 相当)
            self.stdout.write('Clearing existing data...')
            WirelessEquipment.objects.all().delete()
            Facility.objects.all().delete()  # TVChannelStatusもCASCADEで削除される

            # 1. Import Devices
            self.import_devices(os.path.join(csv_dir, 'devices.csv'))

            # 2. Import Locations (郵便番号入りを使用)
            self.import_locations(os.path.join(csv_dir, 'locations_with_zip.csv'))

        self.stdout.write(self.style.SUCCESS('Successfully imported all data'))

    def import_devices(self, file_path):
        self.stdout.write(f'Importing devices from {file_path}...')
        with open(file_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                WirelessEquipment.objects.create(
                    model_name=row['name'],
                    manufacturer='Other',
                    min_frequency=int(row['minfrequency']),
                    max_frequency=int(row['maxfrequency']),
                )

    def import_locations(self, file_path):
        self.stdout.write(f'Importing locations from {file_path}...')
        with open(file_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # 施設情報の作成
                facility = Facility.objects.create(
                    name=row['施設名'],
                    address=row['住所'],
                    prefecture=row['都道府県名'],
                    category=row['屋内外'],
                    applied_area=row.get('適用エリア'),
                    postal_code=row.get('郵便番号'),
                )

                # チャンネルステータスの作成 (ch13 - ch53)
                for ch in range(13, 54):
                    ch_key = f'{ch}CH'
                    is_available = False

                    if ch == 53:
                        is_available = True
                    else:
                        val = row.get(ch_key, '').strip()
                        if val in ['○', '1']:
                            is_available = True

                    TVChannelStatus.objects.create(facility=facility, channel_number=ch, is_available=is_available)
