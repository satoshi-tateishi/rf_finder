import logging

from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpResponse
from django.utils import timezone

from apps.accounts.models import Member
from apps.accounts.utils import is_admin, log_action

from .constants import STATUS_DRAFT, STATUS_SUBMITTED
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

logger = logging.getLogger(__name__)


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
        logger.warning('[Validation Error] %s', all_errors)
        return False, all_errors

    return True, None


@json_api_view(validate=False)
def save_adjustment(request, data):
    """手動保存（下書き）"""
    try:
        adjustment = OperationAdjustment.save_from_json(data, user=request.user, status='draft')
        return api_success({'id': adjustment.id, 'message': 'Saved as draft'})
    except Exception as e:
        logger.exception('調整届の保存に失敗しました: %s', e)
        return api_error(str(e), status=500)


@login_required(login_url='accounts:login')
def list_adjustments(request):
    """保存済み一覧の取得"""
    event_name = request.GET.get('event_name')
    facility_name = request.GET.get('facility_name')
    user_name = request.GET.get('user_name')
    status = request.GET.get('status')  # 'draft' or 'submitted'

    # 最終更新日時（updated_at）の降順で取得（N+1クエリ防止）
    queryset = OperationAdjustment.objects.select_related('user__profile').prefetch_related('facilities').order_by('-updated_at')

    if event_name:
        queryset = queryset.filter(event_name__icontains=event_name)
    if facility_name:
        queryset = queryset.filter(facilities__name__icontains=facility_name).distinct()
    if user_name:
        queryset = queryset.filter(user_name__icontains=user_name)
    if status in (STATUS_DRAFT, STATUS_SUBMITTED):
        queryset = queryset.filter(status=status)

    results = []
    for adj in queryset[:20]:
        results.append(
            {
                'id': adj.id,
                'parent_id': adj.parent_id,
                'event_name': adj.event_name,
                'user_name': adj.user_name,  # 現地使用者
                'sender_name': adj.user.profile.full_name
                if (adj.user and hasattr(adj.user, 'profile'))
                else (adj.user.get_full_name() if adj.user else 'システム'),  # 実際に操作した申請者
                'app_type': adj.get_app_type_display(),
                'status': adj.get_status_display(),
                'created_at': timezone.localtime(adj.created_at).strftime('%Y/%m/%d %H:%M'),
                'updated_at': timezone.localtime(adj.updated_at).strftime('%Y/%m/%d %H:%M'),
                'facility_names': [f.name for f in adj.facilities.all()],
            }
        )

    return api_success(results)


@login_required(login_url='accounts:login')
def get_adjustment(request, pk):
    """単一データの取得"""
    try:
        adj = OperationAdjustment.objects.get(pk=pk)

        # 認可チェック: 作成者本人または管理者のみ許可
        if adj.user and adj.user != request.user and not is_admin(request.user):
            return api_error('Permission denied', status=403)

        data = {
            'id': adj.id,
            'parent_id': adj.parent_id,
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
            'status': adj.status,
        }
        return api_success(data)
    except OperationAdjustment.DoesNotExist:
        return api_error('Not found', status=404)


@json_api_view(validate=True)
def preview_excel(request, data):
    member = Member.objects.first()
    buffer = generate_adjustment_excel(data, member)
    filename = get_adjustment_filename(data, 'xlsx')

    log_action(user=request.user, action='EXCEL_EXPORT', description=f'Excel出力: {filename}', request=request)

    from django.utils.encoding import escape_uri_path

    content = buffer.getvalue()
    response = HttpResponse(content, content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Length'] = len(content)
    # 日本語ファイル名対策: RFC 5987形式
    response['Content-Disposition'] = f"attachment; filename*=UTF-8''{escape_uri_path(filename)}"
    return response


@json_api_view(validate=True)
def preview_pdf(request, data):
    logger.debug('preview_pdf called')
    member = Member.objects.first()
    try:
        buffer = generate_adjustment_pdf(data, member)
        filename = get_adjustment_filename(data, 'pdf')

        log_action(user=request.user, action='PDF_EXPORT', description=f'PDF出力: {filename}', request=request)

        from django.utils.encoding import escape_uri_path

        content = buffer.getvalue()
        response = HttpResponse(content, content_type='application/pdf')
        response['Content-Length'] = len(content)

        # クエリパラメータで強制ダウンロード指定があるか確認（フロントからは未対応だが拡張性のため）
        disposition = request.GET.get('disposition', 'inline')

        # デフォルトはインラインだが、ファイル名も指定する
        response['Content-Disposition'] = f"{disposition}; filename*=UTF-8''{escape_uri_path(filename)}"
        return response
    except Exception as e:
        return api_error(str(e), status=500)


@json_api_view(validate=True)
def send_email(request, data):
    member = Member.objects.first()
    try:
        with transaction.atomic():
            # 0. データを保存 (status='submitted')
            adjustment = OperationAdjustment.save_from_json(data, user=request.user, status='submitted')
            data['id'] = adjustment.id

            # 1. PDFを生成
            pdf_buffer = generate_adjustment_pdf(data, member)

            # 2. メール送信
            send_adjustment_email(data, member, pdf_buffer)

            # 監査ログの記録
            log_action(
                user=request.user,
                action='EMAIL_SEND',
                description=f'メール送信: {adjustment.event_name} (ID: {adjustment.id})',
                request=request,
                obj=adjustment,
            )

        # 3. LINE Bot連携 (外部サービス呼び出しはトランザクション外が望ましい)
        bot_service = LineBotService()

        # 通知用データに実際に送信したユーザー名を追加
        if hasattr(request.user, 'profile'):
            data['sender_name'] = request.user.profile.full_name
        else:
            data['sender_name'] = request.user.get_full_name() or request.user.username

        filename = get_adjustment_filename(data, 'pdf')
        pdf_content = pdf_buffer.getvalue()

        # 3.1 依頼元の個別トークルームへ送信 (channelIdがあれば)
        channel_id = data.get('channelId')
        if channel_id:
            try:
                bot_service.send_pdf(channel_id, pdf_content, file_name=filename)
            except Exception as bot_err:
                logger.warning('依頼元トークルームへのPDF送信に失敗しました: %s', bot_err, exc_info=True)

        # 3.2 指定の通知グループへ送信 (設定があれば)
        from django.conf import settings

        notify_channel_id = getattr(settings, 'LINE_WORKS_NOTIFICATION_CHANNEL_ID', None)
        if notify_channel_id:
            try:
                # サービス層で構築されたメッセージを使用
                msg = bot_service.build_submission_notification_message(data)
                # テキストメッセージとPDFを送信
                bot_service.send_text_message(notify_channel_id, msg)
                bot_service.send_pdf(notify_channel_id, pdf_content, file_name=filename)
            except Exception as notify_err:
                logger.warning('通知グループへの送信に失敗しました: %s', notify_err, exc_info=True)

        return api_success({'message': 'Email sent successfully', 'id': adjustment.id})
    except Exception as e:
        logger.exception('メール送信処理に失敗しました: %s', e)
        return api_error(str(e), status=500)


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
        filename = f'wsm_{facility.name}_{date_str}.csv'

        log_action(
            user=request.user,
            action='WSM_EXPORT',
            description=f'WSM CSV出力: {facility.name}',
            request=request,
            obj=facility,
        )

        from django.utils.encoding import escape_uri_path

        response = HttpResponse(csv_content, content_type='text/csv')
        response['Content-Disposition'] = f"attachment; filename*=UTF-8''{escape_uri_path(filename)}"
        return response
    except Facility.DoesNotExist:
        return api_error('Facility not found', status=404)
    except Exception as e:
        return api_error(str(e), status=500)
