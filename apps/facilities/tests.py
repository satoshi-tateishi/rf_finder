from django.test import TestCase
from django.urls import reverse

from .models import Facility, TVChannelStatus
from .services import calculate_available_frequencies


class FrequencyCalculationTest(TestCase):
    def setUp(self):
        self.facility = Facility.objects.create(
            name='テスト施設', prefecture='東京都', address='渋谷区', category='屋内'
        )
        # ch13-ch15を作成
        for ch in range(13, 16):
            TVChannelStatus.objects.create(facility=self.facility, channel_number=ch, is_available=True)

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

        self.assertEqual(ch13['gb_lower'], 0)  # 下限は0
        self.assertEqual(ch13['gb_upper'], 1000)  # 次のch14が不可なので上限は1000

    def test_gb_calculation_continuous_channels(self):
        """連続した空きチャンネルの場合、中間の境界にはGBが適用されないこと"""
        # ch13, ch14, ch15 すべて空き
        results = calculate_available_frequencies(self.facility)

        ch14 = next(r for r in results if r['channel'] == 14)
        self.assertEqual(ch14['gb_lower'], 0)
        self.assertEqual(ch14['gb_upper'], 0)


class FacilityAPITest(TestCase):
    def setUp(self):
        from django.contrib.auth.models import User

        self.user = User.objects.create_user(username='facilitytest', password='password')
        self.client.force_login(self.user)

        self.f1 = Facility.objects.create(name='東京ドーム', prefecture='東京都', address='文京区')
        self.f2 = Facility.objects.create(name='明治座', prefecture='東京都', address='中央区')
        TVChannelStatus.objects.create(facility=self.f1, channel_number=13, is_available=True)

    def test_facility_search_api(self):
        """名称による施設検索が正しく機能すること"""
        # 2文字以上のクエリ
        response = self.client.get(reverse('facilities:search'), {'q': 'ドーム'})
        self.assertEqual(response.status_code, 200)
        data = response.json()['data']
        self.assertEqual(len(data['results']), 1)
        self.assertEqual(data['results'][0]['name'], '東京ドーム')

        # 短すぎるクエリ（2文字未満）は空結果を返す仕様
        response = self.client.get(reverse('facilities:search'), {'q': '東'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()['data']['results']), 0)

    def test_facility_detail_api(self):
        """施設詳細APIが計算済みチャンネルを含む正しいデータを返すこと"""
        response = self.client.get(reverse('facilities:detail', args=[self.f1.id]))
        self.assertEqual(response.status_code, 200)
        data = response.json()['data']
        self.assertEqual(data['facility']['name'], '東京ドーム')
        self.assertTrue('available_channels' in data)
        self.assertEqual(data['available_channels'][0]['channel'], 13)

    def test_facility_detail_not_found(self):
        """存在しない施設IDの場合は404を返すこと"""
        response = self.client.get(reverse('facilities:detail', args=[99999]))
        self.assertEqual(response.status_code, 404)


class TVChannelStatusFrequencyTest(TestCase):
    def setUp(self):
        self.facility = Facility.objects.create(
            name='周波数テスト施設', prefecture='東京都', address='千代田区'
        )

    def _make_ch(self, ch):
        return TVChannelStatus.objects.create(facility=self.facility, channel_number=ch, is_available=True)

    def test_ch13_start_frequency(self):
        """ch13 の開始周波数は 470,000 kHz であること"""
        ch = self._make_ch(13)
        self.assertEqual(ch.frequency_start_khz, 470000)

    def test_ch14_start_frequency(self):
        """ch14 の開始周波数は 476,000 kHz（6MHz幅）であること"""
        ch = self._make_ch(14)
        self.assertEqual(ch.frequency_start_khz, 476000)

    def test_ch53_start_frequency(self):
        """ch53 の開始周波数は 710,000 kHz であること"""
        ch = self._make_ch(53)
        self.assertEqual(ch.frequency_start_khz, 470000 + (53 - 13) * 6000)
        self.assertEqual(ch.frequency_start_khz, 710000)

    def test_normal_channel_end_frequency(self):
        """通常チャンネルの終了周波数は開始 + 6,000 kHz であること"""
        ch = self._make_ch(30)
        self.assertEqual(ch.frequency_end_khz, ch.frequency_start_khz + 6000)

    def test_ch53_end_frequency_is_4mhz_wide(self):
        """ch53 の終了周波数は開始 + 4,000 kHz（A帯特殊）であること"""
        ch = self._make_ch(53)
        self.assertEqual(ch.frequency_end_khz, ch.frequency_start_khz + 4000)
        self.assertEqual(ch.frequency_end_khz, 714000)


class FacilitySearchEdgeCaseTest(TestCase):
    def setUp(self):
        from django.contrib.auth.models import User

        self.user = User.objects.create_user(username='searchedgeuser', password='password')
        self.client.force_login(self.user)
        Facility.objects.create(name='横浜アリーナ', prefecture='神奈川県', address='横浜市')

    def test_empty_query_returns_empty(self):
        """クエリが空の場合は空結果を返すこと"""
        response = self.client.get(reverse('facilities:search'), {'q': ''})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()['data']['results']), 0)

    def test_no_match_returns_empty(self):
        """一致する施設がない場合は空結果を返すこと"""
        response = self.client.get(reverse('facilities:search'), {'q': '存在しない施設名XYZ'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()['data']['results']), 0)
