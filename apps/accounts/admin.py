from django.contrib import admin
from .models import Company, EmailTemplate, WoffUser

@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ('name', 'member_id_1', 'member_id_2', 'manager_name')

@admin.register(EmailTemplate)
class EmailTemplateAdmin(admin.ModelAdmin):
    list_display = ('subject', 'to_address', 'from_address')

@admin.register(WoffUser)
class WoffUserAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'user_id', 'phone')
    search_fields = ('name', 'email', 'user_id')
