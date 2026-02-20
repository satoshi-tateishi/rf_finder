from django.test import TestCase
from .models import Facility, TVChannelStatus
from .services import calculate_available_frequencies

class FrequencyCalculationTest(TestCase):
    def setUp(self):
        self.facility = Facility.objects.create(
            name="テスト施設",
            prefecture="東京都",
            address="渋谷区",
            category="屋内"
        )
        # ch13-ch15を作成
        for ch in range(13, 16):
            TVChannelStatus.objects.create(
                facility=self.facility,
                channel_number=ch,
                is_available=True
            )

    def test_gb_calculation_isolated_channel(self):
        """孤立した空きチャンネル（両隣が不可）の場合、上下に1MHzのGBが適用されること"""
        # ch14のみ空き、ch13とch15を不可にする
        TVChannelStatus.objects.filter(facility=self.facility, channel_number__in=[13, 15]).update(is_available=False)
        
        results = calculate_available_frequencies(self.facility)
        self.assertEqual(len(results), 1)
        ch14 = results[0]
        
        # ch14: 476MHz - 482MHz
        # GB適用後: 477MHz - 481MHz
        self.assertEqual(ch14['channel'], 14)
        self.assertEqual(ch14['gb_lower'], 1000)
        self.assertEqual(ch14['gb_upper'], 1000)
        self.assertEqual(ch14['effective_start'], 476000 + 1000)
        self.assertEqual(ch14['effective_end'], 482000 - 1000)

    def test_gb_calculation_ch13_edge(self):
        """ch13の下限にはGBが適用されないこと"""
        # ch13が空き、ch14が不可
        TVChannelStatus.objects.filter(facility=self.facility, channel_number=14).update(is_available=False)
        
        results = calculate_available_frequencies(self.facility)
        ch13 = next(r for r in results if r['channel'] == 13)
        
        self.assertEqual(ch13['gb_lower'], 0) # 下限は0
        self.assertEqual(ch13['gb_upper'], 1000) # 次のch14が不可なので上限は1000

    def test_gb_calculation_continuous_channels(self):
        """連続した空きチャンネルの場合、中間の境界にはGBが適用されないこと"""
        # ch13, ch14, ch15 すべて空き
        results = calculate_available_frequencies(self.facility)
        
        ch14 = next(r for r in results if r['channel'] == 14)
        self.assertEqual(ch14['gb_lower'], 0)
        self.assertEqual(ch14['gb_upper'], 0)
