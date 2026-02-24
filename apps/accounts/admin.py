from django import forms
from django.contrib import admin
from django.utils.html import format_html
from import_export.admin import ImportExportModelAdmin

from .models import EmailTemplate, Member, UserProfile
from .resources import EmailTemplateResource, MemberResource


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'role', 'full_name', 'phone_number', 'email')
    list_filter = ('role',)
    search_fields = ('user__username', 'family_name', 'given_name', 'email')
    readonly_fields = ('otp_code', 'otp_expires_at', 'otp_locked_until')
    fieldsets = (
        ('基本情報', {'fields': ('user', 'role')}),
        ('LINE WORKS同期情報', {'fields': (
            ('family_name', 'given_name'),
            ('phonetic_family_name', 'phonetic_given_name'),
            'phone_number', 'email'
        )}),
        ('セキュリティ (OTP)', {
            'fields': ('otp_code', 'otp_expires_at', 'otp_attempts', 'otp_locked_until'),
            'classes': ('collapse',)
        }),
    )


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
    list_display = ('subject', 'to_address', 'cc_address')
    fieldsets = (
        (None, {'fields': ('to_address', 'cc_address', 'subject', 'body')}),
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
