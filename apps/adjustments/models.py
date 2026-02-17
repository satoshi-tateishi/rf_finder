from django.db import models
from apps.facilities.models import Facility

class OperationAdjustment(models.Model):
    """運用調整届データ（PDF生成用）"""
    facility = models.ForeignKey(Facility, on_delete=models.PROTECT, verbose_name="対象施設")
    user_name = models.CharField(max_length=100, verbose_name="申請者名")
    event_name = models.CharField(max_length=255, verbose_name="催事名", blank=True)
    event_date = models.DateField(verbose_name="使用日")
    # 実際に使用する周波数リスト（例: [{"freq": 806.125, "ch": "A11"}, ...]）
    used_frequencies = models.JSONField(verbose_name="使用周波数リスト")
    
    # LINE WORKS連携用
    line_works_user_id = models.CharField(max_length=100, verbose_name="LINE WORKSユーザーID", blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="作成日時")

    class Meta:
        verbose_name = "運用調整届"
        verbose_name_plural = "運用調整届一覧"

    def __str__(self):
        return f"{self.event_date} - {self.facility.name} ({self.user_name})"
