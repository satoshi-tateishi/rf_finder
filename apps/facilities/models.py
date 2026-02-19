from django.db import models

class Facility(models.Model):
    """施設情報（総務省CSVベース）"""
    name = models.CharField(max_length=255, verbose_name="施設名")
    prefecture = models.CharField(max_length=50, verbose_name="都道府県")
    address = models.TextField(verbose_name="住所")
    category = models.CharField(max_length=100, verbose_name="施設カテゴリ")
    applied_area = models.CharField(max_length=255, verbose_name="適用エリア", null=True, blank=True)
    # 郵便番号 (住所から自動算出またはCSVインポート)
    postal_code = models.CharField(max_length=100, null=True, blank=True, verbose_name="郵便番号")

    class Meta:
        verbose_name = "施設"
        verbose_name_plural = "施設一覧"

    def __str__(self):
        return self.name

class TVChannelStatus(models.Model):
    """TVチャンネルの状態（ch13-ch53）"""
    facility = models.ForeignKey(Facility, on_delete=models.CASCADE, related_name='channels')
    channel_number = models.IntegerField(verbose_name="チャンネル番号") # 13 to 53
    # 放送波や既存運用などで「空いていない」場合はFalse
    is_available = models.BooleanField(default=True, verbose_name="空き状況")
    
    class Meta:
        verbose_name = "TVチャンネル状態"
        verbose_name_plural = "TVチャンネル状態一覧"
        unique_together = ('facility', 'channel_number')
        ordering = ['channel_number']

    @property
    def frequency_start_khz(self):
        """チャンネルの開始周波数 (kHz) (例: ch13 = 470000kHz)"""
        return 470000 + (self.channel_number - 13) * 6000

    @property
    def frequency_end_khz(self):
        """チャンネルの終了周波数 (kHz)"""
        # ch53は710-714MHz (A帯) のため、4MHz幅とする
        if self.channel_number == 53:
            return self.frequency_start_khz + 4000
        return self.frequency_start_khz + 6000

class WirelessEquipment(models.Model):
    """ワイヤレスマイク機器のマスタ (kHz単位)"""
    manufacturer = models.CharField(max_length=100, verbose_name="メーカー")
    model_name = models.CharField(max_length=100, verbose_name="型番")
    min_frequency = models.PositiveIntegerField(verbose_name="最小周波数(kHz)")
    max_frequency = models.PositiveIntegerField(verbose_name="最大周波数(kHz)")

    class Meta:
        verbose_name = "ワイヤレス機器"
        verbose_name_plural = "ワイヤレス機器一覧"

    def __str__(self):
        return f"{self.manufacturer} {self.model_name}"
