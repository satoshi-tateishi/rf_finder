from django.contrib import admin
from django.db import models
from django.utils.html import format_html

from ..models import DropboxToken


@admin.register(DropboxToken)
class DropboxTokenAdmin(admin.ModelAdmin):
    list_display = ('account_name', 'service_name', 'updated_at', 'status_display', 'action_buttons')
    readonly_fields = ('access_token', 'refresh_token', 'expires_at', 'account_id', 'account_name')

    @admin.display(description='ステータス')
    def status_display(self, obj):
        if obj.is_access_token_expired():
            if obj.has_valid_refresh_token():
                return format_html('<span style="color: orange;">有効期限切れ (リフレッシュ可)</span>')
            return format_html('<span style="color: red;">認証切れ</span>')
        return format_html('<span style="color: green;">有効</span>')

    @admin.display(description='操作')
    def action_buttons(self, obj):
        return format_html(
            '<a class="button" href="/auth/dropbox/login/">再連携</a>&nbsp;'
            '<a class="button" href="/auth/dropbox/backup/" target="_blank">手動バックアップ実行</a>'
        )

    def has_add_permission(self, request):
        return False


# Dropbox連携開始用のダミー
class DropboxAuthHelper(models.Model):
    class Meta:
        verbose_name = '1. Dropbox連携を開始する'
        verbose_name_plural = '1. Dropbox連携を開始する'
        managed = False

    def __str__(self):
        return str(self._meta.verbose_name)


@admin.register(DropboxAuthHelper)
class DropboxAuthAdmin(admin.ModelAdmin):
    def has_module_permission(self, request):
        if not hasattr(request.user, 'profile'):
            return False
        return request.user.profile.role == 'admin'

    def changelist_view(self, request, extra_context=None):
        from django.shortcuts import redirect

        return redirect('/auth/dropbox/login/')
