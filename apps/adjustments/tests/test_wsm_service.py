from django.test import TestCase

from apps.adjustments.services.wsm_service import WSMService
from apps.facilities.models import Facility, TVChannelStatus


class WSMServiceTest(TestCase):
    def setUp(self):
        self.facility = Facility.objects.create(
            name='テスト施設', prefecture='東京都', address='渋谷区', category='屋内'
        )
        # 13CHから53CHまでの基本データを作成 (デフォルトはすべて運用不可)
        for ch in range(13, 54):
            TVChannelStatus.objects.create(
                facility=self.facility,
                channel_number=ch,
                is_available=False
            )

    def test_wsm_csv_generation_basic(self):
        """基本的なCSV生成と、選択されたチャンネルの反映をテスト"""
        # 13CHと53CHを「空き」にし、13CHを「選択」する
        TVChannelStatus.objects.filter(
            facility=self.facility,
            channel_number__in=[13, 53]
        ).update(is_available=True)

        selected_channels = [13]
        csv_content = WSMService.generate_csv(self.facility, selected_channels)

        lines = csv_content.strip().split('\n')
        # ヘッダー + 41チャンネル(13-53) + Blocked = 43行
        self.assertEqual(len(lines), 43)

        # ヘッダー確認
        self.assertEqual(lines[0], "name;type;frequency;tolerance;minfrequency;maxfrequency;priority;squelchlevel")

        # 13CH (Selected, Available, Next is Unavailable)
        # 470000 - (476000 - 1000) = 470000 - 475000
        # Type: 2 (Selected), Priority: 2
        self.assertEqual(lines[1], "TV 13;2;0;0;470000;475000;2;5")

        # 14CH (Not Selected, Unavailable, Prev is Available)
        # (476000 - 1000) - 482000 = 475000 - 482000?
        # Wait, if 14 is Unavailable and 13 is Available.
        # ch14: is_available=False, prev_available=True.
        # is_available != prev_available is True.
        # is_available is False, so min_f -= 1000. 476000 -> 475000. Correct.
        self.assertEqual(lines[2], "TV 14;3;0;0;475000;482000;4;5")

        # 53CH (Not Selected, Available, Prev is Unavailable)
        # 710000 + 1000 = 711000. Max is 714000.
        self.assertEqual(lines[41], "TV 53;3;0;0;711000;714000;4;5")

        # Blocked
        self.assertEqual(lines[42], "Blocked;3;0;0;714000;798000;4;5")

    def test_wsm_csv_continuous_channels(self):
        """連続した空きチャンネルでのGB不適用をテスト"""
        # 13CH, 14CH を「空き」にする
        TVChannelStatus.objects.filter(
            facility=self.facility,
            channel_number__in=[13, 14]
        ).update(is_available=True)

        csv_content = WSMService.generate_csv(self.facility, [])
        lines = csv_content.strip().split('\n')

        # TV 13: 470000 - 476000 (Next is Available, so no GB at upper)
        self.assertEqual(lines[1], "TV 13;3;0;0;470000;476000;4;5")
        # TV 14: 476000 - 481000 (Prev is Available, so no GB at lower. Next is Unavailable, so GB at upper)
        self.assertEqual(lines[2], "TV 14;3;0;0;476000;481000;4;5")
