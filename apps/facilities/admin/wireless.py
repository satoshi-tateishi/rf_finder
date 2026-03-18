from django.contrib import admin
from import_export.admin import ImportExportModelAdmin

from ..models import WirelessEquipment
from ..resources import WirelessEquipmentResource


@admin.register(WirelessEquipment)
class WirelessEquipmentAdmin(ImportExportModelAdmin):
    resource_class = WirelessEquipmentResource
    list_display = ('model_name', 'manufacturer', 'min_frequency', 'max_frequency')
    search_fields = ('model_name', 'manufacturer')
