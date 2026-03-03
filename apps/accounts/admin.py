from django import forms
from django.contrib import admin
from django.db import models
from django.utils.html import format_html
from import_export.admin import ImportExportModelAdmin

from .models import AuditLog, DropboxToken, EmailTemplate, Member, UserProfile
from .resources import EmailTemplateResource, MemberResource


class AuditLogUserFilter(admin.SimpleListFilter):
    title = 'ユーザー'
    parameter_name = 'user'

    def lookups(self, request, model_admin):
        # ログに存在するユーザーのみ、氏名で一覧表示
        user_ids = AuditLog.objects.exclude(user=None).values_list('user_id', flat=True).distinct()
        profiles = (
            UserProfile.objects.filter(user_id__in=user_ids)
            .select_related('user')
            .order_by('family_name', 'given_name')
        )
        result = []
        for profile in profiles:
            name = profile.full_name or profile.user.username
            result.append((profile.user_id, name))
        return result

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(user_id=self.value())
        return queryset


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


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('timestamp', 'get_user_display', 'action', 'description', 'ip_address')
    list_filter = ('action', 'timestamp', AuditLogUserFilter)
    search_fields = ('description', 'user__profile__family_name', 'user__profile__given_name', 'ip_address')
    readonly_fields = (
        'get_user_display',
        'action',
        'description',
        'ip_address',
        'timestamp',
        'content_type',
        'object_id',
        'content_object',
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    @admin.display(description='ユーザー', ordering='user__profile__family_name')
    def get_user_display(self, obj):
        if not obj.user:
            return '—'
        if hasattr(obj.user, 'profile'):
            name = obj.user.profile.full_name
            if name:
                return name
        return obj.user.username


class UserProfileAdminForm(forms.ModelForm):
    is_active = forms.BooleanField(
        label='アカウント有効',
        required=False,
        help_text='無効にするとログインできなくなります。削除の代わりにこのフラグで管理してください。',
    )

    class Meta:
        model = UserProfile
        fields = ('user', 'role', 'portal_uuid', 'family_name', 'given_name',
                  'phonetic_family_name', 'phonetic_given_name', 'phone_number', 'email')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.fields['is_active'].initial = self.instance.user.is_active


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    form = UserProfileAdminForm
    list_display = ('get_lw_uuid', 'role', 'full_name', 'phone_number', 'email', 'get_is_active')
    list_filter = ('role', 'user__is_active')
    search_fields = ('user__username', 'family_name', 'given_name', 'email')
    fieldsets = (
        (
            '基本情報',
            {
                'description': 'Portal 同期情報は shin•on Portal JWT から自動同期されます。このアプリからは編集できません。',
                'fields': (
                    ('family_name', 'given_name'),
                    ('phonetic_family_name', 'phonetic_given_name'),
                    'get_user_uuid',
                    'portal_uuid',
                    'email',
                    'phone_number',
                    'is_active',
                ),
            },
        ),
        (
            'RF Finder 設定',
            {
                'fields': ('role',),
            },
        ),
    )

    # JWT で同期されるフィールド（role・is_active・get_user_uuid は除く）
    _JWT_SYNC_FIELDS = (
        'portal_uuid',
        'family_name',
        'given_name',
        'phonetic_family_name',
        'phonetic_given_name',
        'phone_number',
        'email',
    )

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def get_readonly_fields(self, request, obj=None):
        return ('get_user_uuid',) + self._JWT_SYNC_FIELDS

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        obj.user.is_active = form.cleaned_data.get('is_active', True)
        obj.user.save(update_fields=['is_active'])

    @admin.display(description='LINE WORKS UUID')
    def get_user_uuid(self, obj):
        return obj.user.username if obj.user else '—'

    @admin.display(description='LW_UUID', ordering='user__username')
    def get_lw_uuid(self, obj):
        return obj.user.username

    @admin.display(description='有効', boolean=True, ordering='user__is_active')
    def get_is_active(self, obj):
        return obj.user.is_active


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


class MemberAdminForm(forms.ModelForm):
    class Meta:
        model = Member
        fields = ('member_id_1', 'member_id_2', 'name', 'department', 'manager_name', 'phone', 'email')
        widgets = {
            'member_id_1': forms.TextInput(attrs={'maxlength': '3'}),
            'member_id_2': forms.TextInput(attrs={'maxlength': '4'}),
        }


@admin.register(Member)
class MemberAdmin(ImportExportModelAdmin):
    form = MemberAdminForm
    resource_class = MemberResource
    list_display = ('get_member_card',)
    list_display_links = ('get_member_card',)
    search_fields = ('name', 'member_id_1', 'member_id_2', 'manager_name')
    fieldsets = (
        (None, {'fields': (('member_id_1', 'member_id_2'), 'name', 'department', 'manager_name', 'phone', 'email')}),
    )

    class Media:
        css = {'all': ('css/member_admin.css',)}
        js = ('js/admin_row_click.js',)

    @admin.display(description='会員情報')
    def get_member_card(self, obj):
        css = format_html(
            '<style>'
            '.field-get_member_card a {{ text-decoration: none !important; color: inherit !important; display: block; padding: 8px; margin: -8px; }}'
            '.field-get_member_card:hover {{ background-color: #eff6ff !important; cursor: pointer; }}'
            '</style>'
        )

        return format_html(
            '{}'
            '<div style="padding: 4px;">'
            '<span style="font-weight: bold; color: #1f2937; font-size: 16px;">{}</span>'
            '</div>',
            css,
            obj.name,
        )


@admin.register(EmailTemplate)
class EmailTemplateAdmin(ImportExportModelAdmin):
    resource_class = EmailTemplateResource
    list_display = ('name', 'subject', 'to_address', 'cc_address')
    fieldsets = (
        (None, {'fields': ('name', 'to_address', 'cc_address', 'subject', 'body')}),
        (
            '利用可能な変数 (プレースホルダー)',
            {
                'description': format_html(
                    '<style>'
                    '.placeholder-guide {{'
                    '  background-color: var(--darkened-bg, #f8fafc);'
                    '  padding: 12px;'
                    '  border: 1px solid var(--border-color, #e2e8f0);'
                    '  border-radius: 4px;'
                    '  color: var(--body-fg, #333);'
                    '  margin-bottom: 10px;'
                    '}}'
                    '.placeholder-guide ul {{'
                    '  margin: 10px 0 0 20px;'
                    '  padding: 0;'
                    '}}'
                    '.placeholder-guide b {{'
                    '  color: var(--primary-fg, #2563eb);'
                    '  background-color: var(--selected-bg, rgba(0,0,0,0.05));'
                    '  padding: 2px 4px;'
                    '  border-radius: 3px;'
                    '}}'
                    '</style>'
                    '<div class="placeholder-guide">'
                    '<p style="margin: 0;">以下の記号を入力すると、送信時に実際の値に置き換わります：</p>'
                    '<ul>'
                    '<li><b>{{ユーザー名}}</b> : 現地使用者の氏名</li>'
                    '<li><b>{{ユーザーEメールアドレス}}</b> : 現地使用者のメールアドレス</li>'
                    '<li><b>{{催事名}}</b> : 催事名</li>'
                    '<li><b>{{運用日}}</b> : 最初の施設の開始日</li>'
                    '<li><b>{{タイプ}}</b> : 申請区分（新規 / 変更 / 削除）</li>'
                    '</ul>'
                    '</div>'
                ),
                'fields': [],
            },
        ),
    )
