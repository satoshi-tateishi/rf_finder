from django.contrib import admin
from .models import Facility, TVChannelStatus, WirelessEquipment

class TVChannelStatusInline(admin.TabularInline):
    model = TVChannelStatus
    extra = 0
    can_delete = False

@admin.register(Facility)
class FacilityAdmin(admin.ModelAdmin):
    list_display = ('name', 'prefecture', 'category', 'external_id')
    search_fields = ('name', 'address', 'external_id')
    list_filter = ('prefecture', 'category')
    inlines = [TVChannelStatusInline]

@admin.register(WirelessEquipment)
class WirelessEquipmentAdmin(admin.ModelAdmin):
    list_display = ('model_name', 'manufacturer', 'min_frequency', 'max_frequency')
    search_fields = ('model_name', 'manufacturer')

@admin.register(TVChannelStatus)
class TVChannelStatusAdmin(admin.ModelAdmin):
    list_display = ('facility', 'channel_number', 'is_available')
    list_filter = ('channel_number', 'is_available')
    search_fields = ('facility__name',)
