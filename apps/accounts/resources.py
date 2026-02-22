from import_export import resources

from .models import EmailTemplate, Member


class MemberResource(resources.ModelResource):
    class Meta:
        model = Member


class EmailTemplateResource(resources.ModelResource):
    class Meta:
        model = EmailTemplate
