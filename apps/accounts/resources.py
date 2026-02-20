from import_export import resources

from .models import EmailTemplate, Member, WoffUser


class MemberResource(resources.ModelResource):
    class Meta:
        model = Member


class EmailTemplateResource(resources.ModelResource):
    class Meta:
        model = EmailTemplate


class WoffUserResource(resources.ModelResource):
    class Meta:
        model = WoffUser
