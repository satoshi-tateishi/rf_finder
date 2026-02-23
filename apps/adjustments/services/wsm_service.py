import csv
import io
from typing import List

from apps.facilities.models import Facility, TVChannelStatus


class WSMService:
    """Sennheiser WSM用のCSV (セミコロン区切り) を生成するサービス"""

    @staticmethod
    def generate_csv(facility: Facility, selected_channels: List[int]) -> str:
        """
        指定された施設と選択されたチャンネルに基づき、WSM用CSV文字列を生成する。
        """
        output = io.StringIO()
        # WSMはセミコロン区切りを期待する
        writer = csv.writer(output, lineterminator='\n', delimiter=';')

        # ヘッダー
        writer.writerow([
            "name", "type", "frequency", "tolerance", "minfrequency",
            "maxfrequency", "priority", "squelchlevel"
        ])

        # チャンネル状態を全取得 (13-53)
        channels_status = {
            cs.channel_number: cs.is_available
            for cs in TVChannelStatus.objects.filter(facility=facility)
        }

        # 13CHから53CHまでループ
        for ch in range(13, 54):
            is_available = channels_status.get(ch, False)
            is_selected = ch in selected_channels

            # 基本の周波数範囲
            min_f = 470000 + (ch - 13) * 6000
            max_f = min_f + (4000 if ch == 53 else 6000)

            # ガードバンド (GB) 適用ロジック
            # 前のチャンネルとの境界
            if ch > 13:
                prev_available = channels_status.get(ch - 1, False)
                if is_available != prev_available:
                    if is_available:
                        min_f += 1000
                    else:
                        min_f -= 1000

            # 次のチャンネルとの境界
            if ch < 53:
                next_available = channels_status.get(ch + 1, False)
                if is_available != next_available:
                    if is_available:
                        max_f -= 1000
                    else:
                        max_f += 1000

            # WSMフィールドの決定
            # type: 2 (Included/許可), 3 (Excluded/除外)
            # priority: 2 (Selected), 4 (Normal)
            row_type = 2 if is_selected else 3
            priority = 2 if is_selected else 4

            writer.writerow([
                f"TV {ch}",
                row_type,
                0,  # frequency
                0,  # tolerance
                min_f,
                max_f,
                priority,
                5   # squelchlevel (固定)
            ])

        # Blocked (A帯域外の除外)
        writer.writerow(["Blocked", 3, 0, 0, 714000, 798000, 4, 5])

        return output.getvalue()
