import json
import logging
from urllib.parse import urlencode, urlparse

from django.conf import settings
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import redirect, render

from apps.adjustments.services import DropboxService
from apps.adjustments.services.dropbox_token import DropboxAuthError

from .models import AuditLog, UserProfile
from .utils import require_admin, require_admin_redirect

logger = logging.getLogger(__name__)


@login_required
@require_admin
def list_audit_logs(request):
    """管理者用：監査ログの一覧を取得する"""

    action = request.GET.get('action')
    description = request.GET.get('description')

    queryset = AuditLog.objects.all().select_related('user')

    if action:
        queryset = queryset.filter(action=action)
    if description:
        queryset = queryset.filter(description__icontains=description)

    results = []
    for log in queryset[:100]:  # 直近100件
        results.append(
            {
                'id': log.id,
                'user': log.user.username if log.user else 'System',
                'user_display': log.user.first_name if log.user else 'System',
                'action': log.action,
                'description': log.description,
                'ip_address': log.ip_address,
                'timestamp': log.timestamp.strftime('%Y/%m/%d %H:%M:%S'),
            }
        )

    return JsonResponse({'status': 'success', 'data': results})


def login_view(request):
    if request.user.is_authenticated:
        return redirect('index')
    # login_required が ?next=/path/ をセットするのでフルURLに変換してポータルへ渡す
    # ポータルは OTP完了後にこのURLへリダイレクトしてくれる
    next_path = request.GET.get('next', '/')
    # Open Redirect 対策: 外部URLを拒否し、相対パスのみ許可する
    parsed = urlparse(next_path)
    if parsed.scheme or parsed.netloc:
        next_path = '/'
    next_url = request.build_absolute_uri(next_path)
    portal_url = f'{settings.PORTAL_LOGIN_URL}?{urlencode({"next": next_url})}'
    return redirect(portal_url)


@login_required
def get_my_profile(request):
    """ログインユーザーのプロフィール情報を返すAPI"""
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    data = {
        'family_name': profile.family_name,
        'given_name': profile.given_name,
        'phonetic_family_name': profile.phonetic_family_name,
        'phonetic_given_name': profile.phonetic_given_name,
        'full_name': profile.full_name,
        'full_kana': profile.full_kana,
        'phone_number': profile.phone_number,
        'email': profile.email,
        'role': profile.role,
    }
    return JsonResponse({'status': 'success', 'data': data})


def logout_view(request):
    if request.method != 'POST':
        return redirect('index')
    logout(request)
    return redirect('accounts:login')


@login_required
@require_admin_redirect('index')
def dropbox_login(request):
    """Dropbox連携を開始する (管理者のみ)"""
    service = DropboxService()
    redirect_uri = settings.DROPBOX_REDIRECT_URI
    # セッションを渡す
    auth_url = service.get_auth_url(redirect_uri, request.session)
    return redirect(auth_url)


@login_required
def dropbox_callback(request):
    """Dropbox認証のコールバック"""
    code = request.GET.get('code')
    if not code:
        return render(request, 'index.html', {'error': 'Dropbox認証がキャンセルされました。'})

    service = DropboxService()
    redirect_uri = settings.DROPBOX_REDIRECT_URI
    try:
        # クエリパラメータ全体とセッションを渡す
        service.finish_auth(request.GET, request.session, redirect_uri)
        return redirect('/admin/accounts/dropboxtoken/')
    except DropboxAuthError as e:
        logger.error('Dropbox認証コールバックでエラーが発生しました: %s', e)
        return render(request, 'index.html', {'error': f'Dropbox認証に失敗しました: {str(e)}'})


@login_required
@require_admin
def run_db_backup(request):
    """手動でデータベースバックアップを実行する"""

    service = DropboxService()
    try:
        result = service.create_db_backup()
        return JsonResponse({'status': 'success', 'data': result})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


@login_required
@require_admin
def list_backups(request):
    """Dropbox上のバックアップ一覧を取得する"""

    service = DropboxService()
    try:
        backups = service.list_backups()
        return JsonResponse({'status': 'success', 'data': backups})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


@login_required
@require_admin
def restore_db(request):
    """指定されたバックアップからデータベースを復元する"""

    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'POST request required'}, status=405)

    try:
        data = json.loads(request.body)
        remote_path = data.get('path')
        if not remote_path:
            return JsonResponse({'status': 'error', 'message': 'Path is required'}, status=400)

        service = DropboxService()
        result = service.restore_db_from_backup(remote_path, confirm=True)
        return JsonResponse({'status': 'success', 'data': result})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
