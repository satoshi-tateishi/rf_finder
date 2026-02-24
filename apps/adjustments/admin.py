from django.contrib import admin

from .models import OperationAdjustment


@admin.register(OperationAdjustment)
class OperationAdjustmentAdmin(admin.ModelAdmin):
    list_display = ('event_name', 'user_name', 'app_type', 'status', 'created_at')
    list_filter = ('app_type', 'status', 'created_at')
    search_fields = ('event_name', 'user_name', 'facilities__name')
    filter_horizontal = ('facilities',)
