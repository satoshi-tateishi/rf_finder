from django.contrib import admin

from ..models import AuditLog, UserProfile


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
