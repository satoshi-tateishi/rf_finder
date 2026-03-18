from django.contrib.auth.models import User
from django.db import models

from apps.facilities.models import Facility

from .constants import APP_TYPE_CHOICES, APP_TYPE_NEW, STATUS_CHOICES, STATUS_DRAFT, STATUS_SUBMITTED


class OperationAdjustment(models.Model):
    """運用調整届データ（永続化・再編集用）"""

    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='作成者')
    app_type = models.CharField(max_length=10, choices=APP_TYPE_CHOICES, default=APP_TYPE_NEW, verbose_name='申請区分')

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
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_DRAFT, verbose_name='ステータス')

    parent = models.ForeignKey(
        'self', null=True, blank=True, on_delete=models.SET_NULL, related_name='children', verbose_name='元申請'
    )

    created_at = models.DateTimeField(auto_now_add=True, verbose_name='作成日時')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新日時')

    class Meta:
        verbose_name = '運用調整届'
        verbose_name_plural = '運用調整届一覧'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.event_name} ({self.user_name})'

    @classmethod
    def save_from_json(cls, data, user=None, status='draft'):
        """
        JSONデータ（辞書形式）を受け取り、モデルインスタンスを保存・更新する。
        """
        from django.db import transaction

        with transaction.atomic():
            adjustment_id = data.get('id')
            parent_id = data.get('parent_id')

            if adjustment_id:
                try:
                    # 更新時は、IDだけでなくユーザーの一致も確認する (セキュリティ強化)
                    if user and user.is_authenticated:
                        # 既に送信済みの場合は、一切の変更を拒否する (既存のIDを指定しての再送信も不可)
                        instance = cls.objects.select_for_update().get(pk=adjustment_id)
                        if instance.status == STATUS_SUBMITTED:
                            raise ValueError('既に送信済みのデータは変更できません。')

                        # 作成者本人でない場合の下書き上書きを制限
                        if instance.user and instance.user != user:
                            raise PermissionError('他のユーザーの下書きを編集する権限がありません。')
                    else:
                        raise PermissionError('ログインが必要です。')
                except cls.DoesNotExist as e:
                    raise ValueError('対象のデータが見つかりません。') from e
            else:
                instance = cls()

            if user and user.is_authenticated:
                instance.user = user

            # 親申請の紐付け (永続化)
            if parent_id:
                try:
                    instance.parent = cls.objects.get(pk=parent_id)
                except cls.DoesNotExist:
                    pass

            # ステータス遷移の制限: draft または submitted のみを許可
            if status not in [STATUS_DRAFT, STATUS_SUBMITTED]:
                raise ValueError('不正なステータス指定です。')
            instance.status = status

            instance.app_type = data.get('app_type', APP_TYPE_NEW)

            user_data = data.get('user', {})
            instance.user_name = user_data.get('name', '')
            instance.user_kana = user_data.get('kana', '')
            instance.user_tel = user_data.get('tel', '')
            instance.user_email = user_data.get('email', '')

            event_data = data.get('event', {})
            instance.event_name = event_data.get('name', '')
            instance.event_comment = event_data.get('comment', '')

            instance.facilities_json = data.get('facilities', [])
            instance.mic_counts_json = data.get('mic_counts', {})
            instance.selected_channels_json = data.get('selected_channels', [])
            instance.extra_53ch = data.get('extra_53ch') == '○'

            instance.save()

            # M2M 施設の紐付け (IDの妥当性チェック)
            facility_ids = [f.get('id') for f in data.get('facilities', []) if f.get('id')]
            if facility_ids:
                valid_facilities = Facility.objects.filter(id__in=facility_ids)
                if valid_facilities.count() != len(set(facility_ids)):
                    raise ValueError('不正または存在しない施設IDが含まれています。')
                instance.facilities.set(valid_facilities)

            return instance

        return instance
