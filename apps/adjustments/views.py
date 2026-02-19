import io
import json
from datetime import datetime
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib import colors
from django.conf import settings
from apps.accounts.models import Member
from .services import format_channels, generate_adjustment_excel, generate_adjustment_pdf
import os

@csrf_exempt
def preview_excel(request):
    if request.method != 'POST':
        return HttpResponse("Method not allowed", status=405)
    
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return HttpResponse("Invalid JSON", status=400)

    member = Member.objects.first()
    buffer = generate_adjustment_excel(data, member)

    response = HttpResponse(
        buffer, 
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = 'attachment; filename="adjustment.xlsx"'
    return response

@csrf_exempt
def preview_pdf(request):
    if request.method != 'POST':
        return HttpResponse("Method not allowed", status=405)
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return HttpResponse("Invalid JSON", status=400)

    member = Member.objects.first()
    buffer = generate_adjustment_pdf(data, member)

    response = HttpResponse(buffer, content_type='application/pdf')
    response['Content-Disposition'] = 'inline; filename="preview.pdf"'
    return response
