from django.contrib import admin
from import_export.admin import ImportExportModelAdmin
from .models import Company, EmailTemplate, WoffUser
from .resources import CompanyResource, EmailTemplateResource, WoffUserResource

@admin.register(Company)
class CompanyAdmin(ImportExportModelAdmin):
    resource_class = CompanyResource
    list_display = ('name', 'member_id_1', 'member_id_2', 'manager_name')

@admin.register(EmailTemplate)
class EmailTemplateAdmin(ImportExportModelAdmin):
    resource_class = EmailTemplateResource
    list_display = ('subject', 'to_address', 'from_address')

@admin.register(WoffUser)
class WoffUserAdmin(ImportExportModelAdmin):
    resource_class = WoffUserResource
    list_display = ('name', 'email', 'user_id', 'phone')
    search_fields = ('name', 'email', 'user_id')
