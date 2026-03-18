from django import forms
from django.contrib import admin
from django.utils.html import format_html
from import_export.admin import ImportExportModelAdmin

from ..models import Member
from ..resources import MemberResource


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
