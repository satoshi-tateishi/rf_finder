from django.contrib import admin
from django.utils.html import format_html
from import_export.admin import ImportExportModelAdmin

from ..models import EmailTemplate
from ..resources import EmailTemplateResource


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
