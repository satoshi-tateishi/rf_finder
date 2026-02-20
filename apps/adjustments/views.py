import io
import json
import traceback
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from apps.accounts.models import Member
from .services import generate_adjustment_excel, generate_adjustment_pdf, send_adjustment_email
from .forms import AdjustmentRequestForm, UserInfoForm, EventInfoForm
from .utils import api_success, api_error

def validate_adjustment_data(data):
    """
    調整届データのバリデーションを行う。
    """
    form = AdjustmentRequestForm(data)
    if not form.is_valid():
        return False, form.errors

    user_form = UserInfoForm(data.get('user', {}))
    if not user_form.is_valid():
        return False, user_form.errors

    event_form = EventInfoForm(data.get('event', {}))
    if not event_form.is_valid():
        return False, event_form.errors

    return True, None

@csrf_exempt
def preview_excel(request):
    if request.method != 'POST':
        return api_error("Method not allowed", status=405)
    
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return api_error("Invalid JSON", status=400)

    # バリデーション (リファクタリング: Phase 3)
    is_valid, errors = validate_adjustment_data(data)
    if not is_valid:
        return api_error("Validation failed", errors=errors)

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
        return api_error("Method not allowed", status=405)
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return api_error("Invalid JSON", status=400)

    # バリデーション
    is_valid, errors = validate_adjustment_data(data)
    if not is_valid:
        return api_error("Validation failed", errors=errors)

    member = Member.objects.first()
    try:
        buffer = generate_adjustment_pdf(data, member)
        response = HttpResponse(buffer, content_type='application/pdf')
        response['Content-Disposition'] = 'inline; filename="preview.pdf"'
        return response
    except Exception as e:
        return api_error(str(e), status=500)

@csrf_exempt
def send_email(request):
    if request.method != 'POST':
        return api_error("Method not allowed", status=405)
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return api_error("Invalid JSON", status=400)

    # バリデーション
    is_valid, errors = validate_adjustment_data(data)
    if not is_valid:
        return api_error("Validation failed", errors=errors)

    member = Member.objects.first()
    try:
        # 1. PDFを生成
        pdf_buffer = generate_adjustment_pdf(data, member)
        
        # 2. メール送信
        send_adjustment_email(data, member, pdf_buffer)
        
        return api_success({'message': 'Email sent successfully'})
    except Exception as e:
        print(f"Error sending email: {e}")
        traceback.print_exc()
        return api_error(str(e), status=500)
