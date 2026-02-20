import io
import json
import traceback
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from apps.accounts.models import Member
from .services import generate_adjustment_excel, generate_adjustment_pdf, send_adjustment_email

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

@csrf_exempt
def send_email(request):
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Method not allowed'}, status=405)
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'message': 'Invalid JSON'}, status=400)

    member = Member.objects.first()
    try:
        # 1. PDFを生成
        pdf_buffer = generate_adjustment_pdf(data, member)
        
        # 2. メール送信
        send_adjustment_email(data, member, pdf_buffer)
        
        return JsonResponse({'status': 'success', 'message': 'Email sent successfully'})
    except Exception as e:
        print(f"Error sending email: {e}")
        traceback.print_exc()
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
