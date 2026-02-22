import json
import traceback

from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt

from apps.accounts.models import Member

from .forms import AdjustmentRequestForm, EventInfoForm, UserInfoForm
from .services import (
    generate_adjustment_excel,
    generate_adjustment_pdf,
    send_adjustment_email,
    LineBotService,
)
from .utils import api_error, api_success


def validate_adjustment_data(data):
    """
    調整届データのバリデーションを行う。
    """
    all_errors = {}

    # 1. 基本フォーム (独自クリーン含む)
    form = AdjustmentRequestForm(data)
    if not form.is_valid():
        all_errors.update(form.errors)

    # 2. 現地使用者フォーム
    user_form = UserInfoForm(data.get('user', {}))
    if not user_form.is_valid():
        all_errors.update({f'user_{k}': v for k, v in user_form.errors.items()})

    # 3. 催事フォーム
    event_form = EventInfoForm(data.get('event', {}))
    if not event_form.is_valid():
        all_errors.update({f'event_{k}': v for k, v in event_form.errors.items()})

    if all_errors:
        return False, all_errors

    return True, None


@csrf_exempt
def preview_excel(request):
    if request.method != 'POST':
        return api_error('Method not allowed', status=405)

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return api_error('Invalid JSON', status=400)

    # バリデーション (リファクタリング: Phase 3)
    is_valid, errors = validate_adjustment_data(data)
    if not is_valid:
        return api_error('Validation failed', errors=errors)

    member = Member.objects.first()
    buffer = generate_adjustment_excel(data, member)

    response = HttpResponse(buffer, content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename="adjustment.xlsx"'
    return response


@csrf_exempt
def preview_pdf(request):
    if request.method != 'POST':
        return api_error('Method not allowed', status=405)
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return api_error('Invalid JSON', status=400)

    # バリデーション
    is_valid, errors = validate_adjustment_data(data)
    if not is_valid:
        return api_error('Validation failed', errors=errors)

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
        return api_error('Method not allowed', status=405)
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return api_error('Invalid JSON', status=400)

    # バリデーション
    is_valid, errors = validate_adjustment_data(data)
    if not is_valid:
        return api_error('Validation failed', errors=errors)

    member = Member.objects.first()
    try:
        # 1. PDFを生成
        pdf_buffer = generate_adjustment_pdf(data, member)

        # 2. メール送信
        send_adjustment_email(data, member, pdf_buffer)

        # 3. LINE Bot連携 (WOFF経由の場合、トークルームへPDFを送信)
        channel_id = data.get('channelId')
        if channel_id:
            try:
                bot_service = LineBotService()
                # pdf_buffer.getvalue() でバイナリを取得
                bot_service.send_pdf(channel_id, pdf_buffer.getvalue(), file_name=f"運用調整届_{data['event'].get('name', 'request')}.pdf")
            except Exception as bot_err:
                # Bot送信失敗はメインの処理を止めないようログのみ
                print(f'Error sending PDF via LINE Bot: {bot_err}')

        return api_success({'message': 'Email sent successfully'})
    except Exception as e:
        print(f'Error sending email: {e}')
        traceback.print_exc()
        return api_error(str(e), status=500)


@csrf_exempt
def test_send_text_message(request):
    if request.method != 'POST':
        return api_error('Method not allowed', status=405)
    try:
        data = json.loads(request.body)
        channel_id = data.get('channelId')
        message = data.get('message')

        if not channel_id or not message:
            return api_error('Channel ID and message are required.', status=400)

        bot_service = LineBotService()
        # テキストメッセージ送信は send_pdf メソッドを流用できないため、LineBotService に新規メソッド追加が必要
        # 今は簡易的に Flex Message を使ってテストメッセージを送る
        flex_message = {
            "type": "bubble",
            "body": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {"type": "text", "text": "テストテキストメッセージ受信", "weight": "bold"},
                    {"type": "text", "text": message, "wrap": True},
                ]
            }
        }
        success = bot_service.send_flex_message(channel_id, flex_message, alt_text="テストテキストメッセージ")
        
        if success:
            return api_success({'message': 'Test text message sent successfully'})
        else:
            return api_error('Failed to send test text message', status=500)

    except Exception as e:
        traceback.print_exc()
        return api_error(str(e), status=500)


@csrf_exempt
def test_send_pdf_message(request):
    if request.method != 'POST':
        return api_error('Method not allowed', status=405)
    try:
        data = json.loads(request.body)
        channel_id = data.get('channelId')

        if not channel_id:
            return api_error('Channel ID is required.', status=400)

        # ダミーPDFを生成
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import A4
        from io import BytesIO

        buffer = BytesIO()
        p = canvas.Canvas(buffer, pagesize=A4)
        p.drawString(100, 750, "LINE WORKS Test PDF")
        p.drawString(100, 730, "This is a dummy PDF for testing purposes.")
        p.save()
        pdf_content = buffer.getvalue()

        bot_service = LineBotService()
        success = bot_service.send_pdf(channel_id, pdf_content, file_name="test_document.pdf")
        
        if success:
            return api_success({'message': 'Test PDF message sent successfully'})
        else:
            return api_error('Failed to send test PDF message', status=500)

    except Exception as e:
        traceback.print_exc()
        return api_error(str(e), status=500)


@csrf_exempt
def log_woff_channel_id_result(request):
    if request.method != 'POST':
        return api_error('Method not allowed', status=405)
    try:
        data = json.loads(request.body)
        result = data.get('result')
        
        # サーバーログに出力
        print(f"[WOFF-DEBUG-SERVER] Received getChannelId() result from frontend: {result}")
        
        return api_success({'message': 'Logged successfully'})
    except json.JSONDecodeError:
        return api_error('Invalid JSON', status=400)
    except Exception as e:
        traceback.print_exc()
        return api_error(str(e), status=500)
