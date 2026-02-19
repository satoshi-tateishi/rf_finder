from import_export import resources
from .models import Company, EmailTemplate, WoffUser

class CompanyResource(resources.ModelResource):
    class Meta:
        model = Company

class EmailTemplateResource(resources.ModelResource):
    class Meta:
        model = EmailTemplate

class WoffUserResource(resources.ModelResource):
    class Meta:
        model = WoffUser
