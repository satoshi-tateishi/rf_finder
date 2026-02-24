from django.contrib.auth.models import User
from django.db import models

from apps.facilities.models import Facility


class OperationAdjustment(models.Model):
    """運用調整届データ（永続化・再編集用）"""

    APP_TYPE_CHOICES = [
        ('new', '新規'),
        ('change', '変更'),
        ('delete', '削除'),
    ]
    STATUS_CHOICES = [
        ('draft', '下書き'),
        ('submitted', '送信済み'),
    ]

    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='作成者')
    app_type = models.CharField(max_length=10, choices=APP_TYPE_CHOICES, default='new', verbose_name='申請区分')

    # 申請者情報（申請時の値を保持）
    user_name = models.CharField(max_length=100, verbose_name='氏名')
    user_kana = models.CharField(max_length=100, verbose_name='ふりがな', blank=True)
    user_tel = models.CharField(max_length=20, verbose_name='電話番号', blank=True)
    user_email = models.EmailField(verbose_name='メールアドレス', blank=True)

    # 催事情報
    event_name = models.CharField(max_length=50, verbose_name='催事名')
    event_comment = models.TextField(max_length=165, verbose_name='コメント', blank=True)

    # 検索用：関連施設
    facilities = models.ManyToManyField(Facility, verbose_name='対象施設', related_name='adjustments')

    # 詳細データ（JSON）
    # 施設別の日程・時間情報
    facilities_json = models.JSONField(default=list, verbose_name='施設別日程データ')
    # 使用マイク数（行列データ）
    mic_counts_json = models.JSONField(default=dict, verbose_name='使用マイク数データ')
    # 選択された周波数/チャンネル情報
    selected_channels_json = models.JSONField(default=list, verbose_name='選択周波数データ')

    extra_53ch = models.BooleanField(default=False, verbose_name='53ch併用')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft', verbose_name='ステータス')

    created_at = models.DateTimeField(auto_now_add=True, verbose_name='作成日時')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新日時')

    class Meta:
        verbose_name = '運用調整届'
        verbose_name_plural = '運用調整届一覧'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.event_name} ({self.user_name})'
