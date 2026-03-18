from django import forms
from django.contrib import admin

from ..models import UserProfile


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
