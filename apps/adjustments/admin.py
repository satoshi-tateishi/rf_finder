from django.contrib import admin
from .models import OperationAdjustment

@admin.register(OperationAdjustment)
class OperationAdjustmentAdmin(admin.ModelAdmin):
    list_display = ('event_date', 'facility', 'user_name', 'created_at')
    list_filter = ('event_date', 'created_at')
    search_fields = ('facility__name', 'user_name', 'event_name')
