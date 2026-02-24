import traceback

from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt

from apps.accounts.models import Member
from apps.accounts.utils import log_action
from apps.facilities.models import Facility

from .forms import AdjustmentRequestForm, EventInfoForm, UserInfoForm
from .models import OperationAdjustment
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


def _save_adjustment_internal(request, data, status='draft'):
    """内部用：データをモデルに保存する"""
    adjustment_id = data.get('id')
    if adjustment_id:
        try:
            adjustment = OperationAdjustment.objects.get(pk=adjustment_id)
        except OperationAdjustment.DoesNotExist:
            adjustment = OperationAdjustment()
    else:
        adjustment = OperationAdjustment()

    if request.user.is_authenticated:
        adjustment.user = request.user

    adjustment.app_type = data.get('app_type', 'new')

    user_data = data.get('user', {})
    adjustment.user_name = user_data.get('name', '')
    adjustment.user_kana = user_data.get('kana', '')
    adjustment.user_tel = user_data.get('tel', '')
    adjustment.user_email = user_data.get('email', '')

    event_data = data.get('event', {})
    adjustment.event_name = event_data.get('name', '')
    adjustment.event_comment = event_data.get('comment', '')

    adjustment.facilities_json = data.get('facilities', [])
    adjustment.mic_counts_json = data.get('mic_counts', {})
    adjustment.selected_channels_json = data.get('selected_channels', [])
    adjustment.extra_53ch = data.get('extra_53ch') == '○'

    adjustment.status = status
    adjustment.save()

    # M2M 施設の紐付け
    facility_ids = [f.get('id') for f in data.get('facilities', []) if f.get('id')]
    if facility_ids:
        adjustment.facilities.set(Facility.objects.filter(id__in=facility_ids))

    return adjustment


@csrf_exempt
@json_api_view(validate=False)
def save_adjustment(request, data):
    """手動保存（下書き）"""
    try:
        adjustment = _save_adjustment_internal(request, data, status='draft')
        return api_success({'id': adjustment.id, 'message': 'Saved as draft'})
    except Exception as e:
        traceback.print_exc()
        return api_error(str(e), status=500)


def list_adjustments(request):
    """保存済み一覧の取得"""
    event_name = request.GET.get('event_name')
    facility_name = request.GET.get('facility_name')
    user_name = request.GET.get('user_name')

    queryset = OperationAdjustment.objects.all()

    if event_name:
        queryset = queryset.filter(event_name__icontains=event_name)
    if facility_name:
        queryset = queryset.filter(facilities__name__icontains=facility_name).distinct()
    if user_name:
        queryset = queryset.filter(user_name__icontains=user_name)

    results = []
    for adj in queryset[:20]:
        results.append({
            'id': adj.id,
            'event_name': adj.event_name,
            'user_name': adj.user_name,
            'app_type': adj.get_app_type_display(),
            'status': adj.get_status_display(),
            'created_at': adj.created_at.strftime('%Y/%m/%d %H:%M'),
            'facility_names': [f.name for f in adj.facilities.all()]
        })

    return api_success(results)


def get_adjustment(request, pk):
    """単一データの取得"""
    try:
        adj = OperationAdjustment.objects.get(pk=pk)
        data = {
            'id': adj.id,
            'app_type': adj.app_type,
            'user': {
                'name': adj.user_name,
                'kana': adj.user_kana,
                'tel': adj.user_tel,
                'email': adj.user_email,
            },
            'event': {
                'name': adj.event_name,
                'comment': adj.event_comment,
            },
            'facilities': adj.facilities_json,
            'mic_counts': adj.mic_counts_json,
            'selected_channels': adj.selected_channels_json,
            'extra_53ch': '○' if adj.extra_53ch else '',
            'status': adj.status
        }
        return api_success(data)
    except OperationAdjustment.DoesNotExist:
        return api_error('Not found', status=404)


@csrf_exempt
@json_api_view(validate=True)
def preview_excel(request, data):
    member = Member.objects.first()
    buffer = generate_adjustment_excel(data, member)
    filename = get_adjustment_filename(data, 'xlsx')

    log_action(user=request.user, action='EXCEL_EXPORT', description=f'Excel出力: {filename}', request=request)

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

        log_action(user=request.user, action='PDF_EXPORT', description=f'PDF出力: {filename}', request=request)

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
        # 0. データを保存 (status='submitted')
        adjustment = _save_adjustment_internal(request, data, status='submitted')
        # IDを返却データに含めるためにdataを更新（必要なら）
        data['id'] = adjustment.id

        # 1. PDFを生成
        pdf_buffer = generate_adjustment_pdf(data, member)

        # 2. メール送信
        send_adjustment_email(data, member, pdf_buffer)

        # 監査ログの記録
        log_action(user=request.user, action='EMAIL_SEND', description=f'メール送信: {adjustment.event_name} (ID: {adjustment.id})', request=request, obj=adjustment)

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

        log_action(user=request.user, action='WSM_EXPORT', description=f'WSM CSV出力: {facility.name}', request=request, obj=facility)

        response = HttpResponse(csv_content, content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response
    except Facility.DoesNotExist:
        return api_error('Facility not found', status=404)
    except Exception as e:
        return api_error(str(e), status=500)
