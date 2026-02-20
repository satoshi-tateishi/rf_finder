from typing import Dict, List

from .models import Facility


def calculate_available_frequencies(facility: Facility) -> List[Dict]:
    """
    指定された施設のチャンネルごとの利用可能周波数範囲を計算する。
    ガードバンド(GB)ルールを適用する。
    """
    # 施設の全チャンネル情報を取得 (ch13-ch53)
    channels = list(facility.channels.all().order_by('channel_number'))
    status_map = {c.channel_number: c.is_available for c in channels}

    results = []

    for ch_status in channels:
        ch_num = ch_status.channel_number

        # そもそもそのチャンネルが使用不可ならスキップ
        if not ch_status.is_available:
            continue

        start_khz = ch_status.frequency_start_khz
        end_khz = ch_status.frequency_end_khz

        gb_lower = 0
        gb_upper = 0

        # 下限側のGB判定
        if ch_num == 13:
            gb_lower = 0
        else:
            prev_available = status_map.get(ch_num - 1, False)
            if not prev_available:
                gb_lower = 1000  # 1MHz

        # 上限側のGB判定
        if ch_num == 53:
            gb_upper = 0
        else:
            next_available = status_map.get(ch_num + 1, False)
            if not next_available:
                gb_upper = 1000  # 1MHz

        # 実効範囲の算出
        effective_start = start_khz + gb_lower
        effective_end = end_khz - gb_upper

        # もしGBで範囲が消滅する場合はスキップ（通常は6MHzあるので1+1=2MHz引いても残る）
        if effective_start < effective_end:
            results.append(
                {
                    'channel': ch_num,
                    'base_start': start_khz,
                    'base_end': end_khz,
                    'effective_start': effective_start,
                    'effective_end': effective_end,
                    'gb_lower': gb_lower,
                    'gb_upper': gb_upper,
                }
            )

    return results
