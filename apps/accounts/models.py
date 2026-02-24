from django.contrib.auth.models import User
from django.contrib.auth.signals import user_logged_in, user_login_failed
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey


class UserProfile(models.Model):
    """ユーザーごとの追加情報（OTP、役割、プロフィールなど）"""

    class Role(models.TextChoices):
        ADMIN = 'admin', '管理者'
        EDITOR = 'editor', '編集者'
        GENERAL = 'general', '一般'
        VIEWER = 'viewer', '閲覧者'

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.GENERAL, verbose_name='役割')

    # LINE WORKS から取得・同期する情報
    family_name = models.CharField(max_length=100, blank=True, default='', verbose_name='姓')
    given_name = models.CharField(max_length=100, blank=True, default='', verbose_name='名')
    phonetic_family_name = models.CharField(max_length=100, blank=True, default='', verbose_name='姓(ふりがな)')
    phonetic_given_name = models.CharField(max_length=100, blank=True, default='', verbose_name='名(ふりがな)')
    phone_number = models.CharField(max_length=20, blank=True, default='', verbose_name='電話番号')
    email = models.EmailField(blank=True, default='', verbose_name='メールアドレス')

    # OTP関連
    otp_code = models.CharField(max_length=255, blank=True, default='', verbose_name='OTPコード(ハッシュ)')
    otp_expires_at = models.DateTimeField(blank=True, null=True, verbose_name='OTP有効期限')
    otp_attempts = models.IntegerField(default=0, verbose_name='試行回数')
    otp_locked_until = models.DateTimeField(blank=True, null=True, verbose_name='ロック解除日時')

    class Meta:
        verbose_name = 'ユーザープロフィール'
        verbose_name_plural = 'ユーザープロフィール'

    def __str__(self):
        return f"{self.user.username} ({self.get_role_display()})"

    @property
    def full_name(self):
        return f"{self.family_name} {self.given_name}".strip() or self.user.first_name

    @property
    def full_kana(self):
        return f"{self.phonetic_family_name} {self.phonetic_given_name}".strip()

    def save(self, *args, **kwargs):
        # ロールに基づいて User の権限を同期
        if self.role == self.Role.ADMIN:
            if not self.user.is_staff or not self.user.is_superuser:
                self.user.is_staff = True
                self.user.is_superuser = True
                self.user.save(update_fields=['is_staff', 'is_superuser'])
        elif self.role in [self.Role.EDITOR, self.Role.GENERAL, self.Role.VIEWER]:
            # 管理者以外に変更された場合、スタッフ権限を外す（必要に応じて）
            if self.user.is_staff or self.user.is_superuser:
                self.user.is_staff = False
                self.user.is_superuser = False
                self.user.save(update_fields=['is_staff', 'is_superuser'])
        
        super().save(*args, **kwargs)

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.get_or_create(user=instance)


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    if hasattr(instance, 'profile'):
        instance.profile.save()


class Member(models.Model):
    member_id_1 = models.CharField(max_length=3, verbose_name='会員番号')
    member_id_2 = models.CharField(max_length=4, verbose_name='会員番号2')
    name = models.CharField(max_length=255, verbose_name='会員名')
    department = models.CharField(max_length=255, blank=True, default='', verbose_name='部署')
    manager_name = models.CharField(max_length=255, verbose_name='運用担当者')
    phone = models.CharField(max_length=20, verbose_name='Tel')
    email = models.EmailField(verbose_name='E-mail')

    class Meta:
        verbose_name = '会員情報'
        verbose_name_plural = '会員情報'

    def __str__(self):
        return self.name


class EmailTemplate(models.Model):
    to_address = models.EmailField(verbose_name='送信先アドレス')
    cc_address = models.CharField(max_length=255, blank=True, default='', verbose_name='CC', help_text='カンマ区切りで複数指定可能。{ユーザーEメールアドレス} も使用できます。')
    subject = models.CharField(max_length=255, verbose_name='件名')
    body = models.TextField(verbose_name='本文')

    class Meta:
        verbose_name = 'メールテンプレート'
        verbose_name_plural = 'メールテンプレート'

    def __str__(self):
        return self.subject


class AuditLog(models.Model):
    """システムの監査ログ（操作履歴）"""
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='ユーザー')
    action = models.CharField(max_length=50, verbose_name='操作種別')
    description = models.TextField(verbose_name='操作詳細')
    ip_address = models.GenericIPAddressField(null=True, blank=True, verbose_name='IPアドレス')
    timestamp = models.DateTimeField(auto_now_add=True, verbose_name='日時')

    # 関連オブジェクト (ContentTypeを使用して汎用的にリンク)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, null=True, blank=True)
    object_id = models.PositiveIntegerField(null=True, blank=True)
    content_object = GenericForeignKey('content_type', 'object_id')

    class Meta:
        verbose_name = '監査ログ'
        verbose_name_plural = '監査ログ'
        ordering = ['-timestamp']

    def __str__(self):
        user_str = self.user.username if self.user else "System"
        return f"{self.timestamp} - {user_str} - {self.action}"


@receiver(user_logged_in)
def log_user_login(sender, request, user, **kwargs):
    from .utils import log_action
    log_action(user=user, action='LOGIN', description='ログイン成功', request=request)


@receiver(user_login_failed)
def log_user_login_failed(sender, credentials, request, **kwargs):
    from .utils import log_action
    username = credentials.get('username', 'unknown')
    log_action(user=None, action='LOGIN_FAILED', description=f'ログイン失敗 (ユーザー名: {username})', request=request)
