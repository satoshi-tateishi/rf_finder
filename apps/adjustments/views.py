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

        # 3. LINE Bot連携
        bot_service = LineBotService()
        filename = get_adjustment_filename(data, 'pdf')
        pdf_content = pdf_buffer.getvalue()

        # 3.1 依頼元の個別トークルームへ送信 (channelIdがあれば)
        channel_id = data.get('channelId')
        if channel_id:
            try:
                bot_service.send_pdf(channel_id, pdf_content, file_name=filename)
            except Exception as bot_err:
                print(f'Error sending PDF to requester: {bot_err}')

        # 3.2 指定の通知グループへ送信 (設定があれば)
        from django.conf import settings
        notify_channel_id = getattr(settings, 'LINE_WORKS_NOTIFICATION_CHANNEL_ID', None)
        if notify_channel_id:
            try:
                # メッセージの作成
                app_type_map = {'new': '新規', 'change': '変更', 'delete': '削除'}
                app_type_jp = app_type_map.get(data.get('app_type'), '新規')
                event_name = data.get('event', {}).get('name', '無題の催事')
                user_name = data.get('user', {}).get('name', '不明')

                # 施設情報の整形
                facilities = data.get('facilities', [])
                facility_lines = []
                for i, f in enumerate(facilities):
                    name = f.get('name', '不明')
                    start = f.get('start_date', '').replace('-', '/')
                    end = f.get('end_date', '').replace('-', '/')
                    facility_lines.append(f"{i + 1}.{name}\n{start} - {end}")

                facility_text = "\n\n".join(facility_lines)

                msg = (
                    f"【運用調整届 送信通知】\n"
                    f"区分: {app_type_jp}\n"
                    f"催事名: {event_name}\n"
                    f"申請者: {user_name}\n\n"
                    f"施設:\n{facility_text}\n\n"
                    f"上記内容で特ラ機構へメール送信しました。添付のPDFをご確認ください。"
                )

                # テキストメッセージとPDFを送信
                bot_service.send_text_message(notify_channel_id, msg)
                bot_service.send_pdf(notify_channel_id, pdf_content, file_name=filename)
            except Exception as notify_err:
                print(f'Error sending notification to LW group: {notify_err}')

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
