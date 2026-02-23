import traceback

from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt

from apps.accounts.models import Member

from .forms import AdjustmentRequestForm, EventInfoForm, UserInfoForm
from .services import (
    LineBotService,
    WSMService,
    generate_adjustment_excel,
    generate_adjustment_pdf,
    send_adjustment_email,
)
from .utils import api_error, api_success, get_adjustment_filename, json_api_view


def validate_adjustment_data(data):
    """
    調整届データのバリデーションを行う。
    """
    all_errors = {}

    # 1. 基本フォーム
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
        print(f"[Validation Error] {all_errors}")
        return False, all_errors

    return True, None


@csrf_exempt
@json_api_view(validate=True)
def preview_excel(request, data):
    member = Member.objects.first()
    buffer = generate_adjustment_excel(data, member)
    filename = get_adjustment_filename(data, 'xlsx')

    response = HttpResponse(buffer, content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


@csrf_exempt
@json_api_view(validate=True)
def preview_pdf(request, data):
    print(">>> preview_pdf called")
    member = Member.objects.first()
    try:
        buffer = generate_adjustment_pdf(data, member)
        filename = get_adjustment_filename(data, 'pdf')
        response = HttpResponse(buffer, content_type='application/pdf')
        response['Content-Disposition'] = f'inline; filename="{filename}"'
        return response
    except Exception as e:
        return api_error(str(e), status=500)


@csrf_exempt
@json_api_view(validate=True)
def send_email(request, data):
    member = Member.objects.first()
    try:
        # 1. PDFを生成
        pdf_buffer = generate_adjustment_pdf(data, member)

        # 2. メール送信
        send_adjustment_email(data, member, pdf_buffer)

        # 3. LINE Bot連携 (将来用: channelIdがあれば送信)
        channel_id = data.get('channelId')
        if channel_id:
            try:
                bot_service = LineBotService()
                filename = get_adjustment_filename(data, 'pdf')
                bot_service.send_pdf(channel_id, pdf_buffer.getvalue(), file_name=filename)
            except Exception as bot_err:
                print(f'Error sending PDF via LINE Bot: {bot_err}')

        return api_success({'message': 'Email sent successfully'})
    except Exception as e:
        print(f'Error sending email: {e}')
        traceback.print_exc()
        return api_error(str(e), status=500)


@csrf_exempt
@json_api_view(validate=False)
def export_wsm(request, data):
    """
    指定された施設とチャンネル選択に基づき、WSM用CSVを生成して返却する。
    """
    facility_id = data.get('facility_id')
    selected_channels = data.get('selected_channels', [])

    try:
        from apps.facilities.models import Facility
        facility = Facility.objects.get(pk=facility_id)
        csv_content = WSMService.generate_csv(facility, selected_channels)

        # ファイル名を生成
        import datetime
        date_str = datetime.datetime.now().strftime('%Y%m%d')
        filename = f"wsm_{facility.name}_{date_str}.csv"

        response = HttpResponse(csv_content, content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response
    except Facility.DoesNotExist:
        return api_error('Facility not found', status=404)
    except Exception as e:
        return api_error(str(e), status=500)
