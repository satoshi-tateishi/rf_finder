import unicodedata
from functools import wraps

from django.http import JsonResponse


def is_admin(user) -> bool:
    """ユーザーが管理者ロールを持つか判定する。"""
    try:
        return user.profile.role == 'admin'
    except Exception:
        return False


def require_admin(view_func):
    """管理者ロール（admin）のみアクセスを許可するデコレータ。
    非管理者には 403 JSON レスポンスを返す。API ビュー向け。
    """

    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        if not is_admin(request.user):
            return JsonResponse({'status': 'error', 'message': 'Permission denied'}, status=403)
        return view_func(request, *args, **kwargs)

    return _wrapped


def require_admin_redirect(redirect_to: str = 'facilities:index'):
    """管理者ロール（admin）のみアクセスを許可するデコレータ。
    非管理者は指定 URL にリダイレクトする。Web ビュー向け。
    """

    def decorator(view_func):
        @wraps(view_func)
        def _wrapped(request, *args, **kwargs):
            if not is_admin(request.user):
                from django.shortcuts import redirect

                return redirect(redirect_to)
            return view_func(request, *args, **kwargs)

        return _wrapped

    return decorator


def log_action(user=None, action='', description='', request=None, obj=None):
    """
    操作ログを記録する。

    :param user: 操作を行ったユーザー。None の場合は request.user を試行。
    :param action: 操作種別（LOGIN, PDF_EXPORT等）
    :param description: 操作の詳細説明
    :param request: IPアドレス取得用のHttpRequestオブジェクト
    :param obj: 関連するモデルオブジェクト（任意）
    """
    from django.contrib.contenttypes.models import ContentType

    from .models import AuditLog

    if user is None and request and getattr(request.user, 'is_authenticated', False):
        user = request.user

    # user が渡された場合でも AnonymousUser（または認証されていないオブジェクト）の
    # 可能性があるため、認証済みでない場合は None にして AuditLog の作成で失敗しない
    if user is not None:
        is_auth = getattr(user, 'is_authenticated', None)
        if callable(is_auth):
            try:
                is_auth = is_auth()
            except Exception:
                is_auth = False
        if not is_auth:
            user = None

    ip_address = None
    if request:
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip_address = x_forwarded_for.split(',')[0].strip()
        else:
            ip_address = request.META.get('REMOTE_ADDR')

    log_data = {
        'user': user,
        'action': action,
        'description': description,
        'ip_address': ip_address,
    }

    if obj:
        log_data['content_type'] = ContentType.objects.get_for_model(obj)
        log_data['object_id'] = obj.pk

    return AuditLog.objects.create(**log_data)


def katakana_to_hiragana(text):
    """
    カタカナをひらがなに変換する。
    """
    if not text:
        return ''

    # 全角カタカナをひらがなに変換 (Unicode の差分 0x60 を引く)
    # カタカナ: 0x30A1 - 0x30F6
    # ひらがな: 0x3041 - 0x3096
    result = []
    for char in text:
        code = ord(char)
        if 0x30A1 <= code <= 0x30F6:
            result.append(chr(code - 0x60))
        else:
            result.append(char)

    return ''.join(result)


def normalize_phonetic(text):
    """
    ふりがなをひらがなに正規化し、余分な空白を除去する。
    """
    if not text:
        return ''
    # NFKC正規化 (全角英数を半角にするなど)
    text = unicodedata.normalize('NFKC', text)
    return katakana_to_hiragana(text).strip()
