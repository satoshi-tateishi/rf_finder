import unicodedata
from django.conf import settings

def log_action(user=None, action="", description="", request=None, obj=None):
    """
    操作ログを記録する。
    
    :param user: 操作を行ったユーザー。None の場合は request.user を試行。
    :param action: 操作種別（LOGIN, PDF_EXPORT等）
    :param description: 操作の詳細説明
    :param request: IPアドレス取得用のHttpRequestオブジェクト
    :param obj: 関連するモデルオブジェクト（任意）
    """
    from .models import AuditLog
    from django.contrib.contenttypes.models import ContentType
    
    if user is None and request and request.user.is_authenticated:
        user = request.user
        
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
        return ""

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

    return "".join(result)

def normalize_phonetic(text):
    """
    ふりがなをひらがなに正規化し、余分な空白を除去する。
    """
    if not text:
        return ""
    # NFKC正規化 (全角英数を半角にするなど)
    text = unicodedata.normalize('NFKC', text)
    return katakana_to_hiragana(text).strip()
