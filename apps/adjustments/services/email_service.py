import logging
from datetime import datetime
from email.mime.application import MIMEApplication

from django.conf import settings
from django.core.mail import EmailMessage
from django.core.validators import validate_email
from django.core.exceptions import ValidationError

from apps.accounts.models import EmailTemplate
from ..constants import APP_TYPE_MAP
from ..utils import get_adjustment_filename

logger = logging.getLogger(__name__)


def _apply_replacements(text: str, replacements: dict) -> str:
    """
    プレースホルダーを置換する内部ユーティリティ関数。
    長いプレースホルダーから順に置換することで誤置換を防ぐ。
    """
    if not text:
        return ""
    # 文字列の長い順にソートして置換（部分一致による誤置換防止）
    for placeholder in sorted(replacements.keys(), key=len, reverse=True):
        value = replacements[placeholder] or ''
        text = text.replace(placeholder, str(value))
    return text


def send_adjustment_email(data, member, pdf_buffer):
    """
    運用調整届のPDFを添付してメール送信を行う。
    DBに保存されたメールテンプレート（EmailTemplate）を参照し、プレースホルダーを置換する。
    """
    event_name = data.get('event', {}).get('name', '無題の催事')
    user_name = data.get('user', {}).get('name', '未設定')
    user_email = data.get('user', {}).get('email', '')

    # 運用日（最初の施設の開始日）を取得してフォーマット
    # 安全性の向上: 入力データの構造チェックを厳密化
    facilities = data.get('facilities', [])
    start_date_raw = ''
    if isinstance(facilities, list) and facilities:
        first_facility = facilities[0]
        if isinstance(first_facility, dict):
            start_date_raw = first_facility.get('start_date', '')

    start_date_formatted = start_date_raw
    if start_date_raw:
        try:
            # YYYY-MM-DD を解析
            dt = datetime.strptime(start_date_raw, '%Y-%m-%d')
            # YYYY年M月D日 に変換
            start_date_formatted = f'{dt.year}年{dt.month}月{dt.day}日'
        except ValueError:
            logger.warning(f"Invalid date format: {start_date_raw}")
            pass

    # 1. テンプレートの取得 (name='adjustment' を優先取得し、なければ最初の一件)
    template = EmailTemplate.objects.filter(name='adjustment').first()
    if not template:
        template = EmailTemplate.objects.first()
        
    if not template:
        msg = 'メールテンプレートが登録されていません。管理画面から "adjustment" という名前で作成してください。'
        logger.error(msg)
        raise RuntimeError(msg)
        
    recipient = template.to_address
    if not recipient:
        msg = '送信先メールアドレス(to_address)が設定されていません。'
        logger.error(msg)
        raise RuntimeError(msg)

    # 送信先アドレスのバリデーション
    try:
        validate_email(recipient)
    except ValidationError:
        msg = f"不正なメールアドレス形式です: {recipient}"
        logger.error(msg)
        raise RuntimeError(msg)

    # 2. 置換データの準備
    app_type_jp = APP_TYPE_MAP.get(data.get('app_type'), '新規')
    
    # 会員情報の取得（引数 member を活用）
    member_name = member.name if member else ''
    manager_name = member.manager_name if member else ''

    # 安全性の向上: None の場合に空文字にする
    subject_template = template.subject or ''
    body_template = template.body or ''
    cc_raw_template = template.cc_address or ''

    replacements = {
        '{ユーザー名}': user_name,
        '{ユーザーEメールアドレス}': user_email,
        '{催事名}': event_name,
        '{運用日}': start_date_formatted,
        '{タイプ}': app_type_jp,
        '{会員名}': member_name,
        '{運用担当者}': manager_name,
    }
    
    # 置換の実行（共通関数化）
    subject = _apply_replacements(subject_template, replacements)
    body = _apply_replacements(body_template, replacements)
    cc_raw = _apply_replacements(cc_raw_template, replacements)

    # CCのリスト化
    cc_list = [addr.strip() for addr in cc_raw.split(',') if addr.strip()]

    # 本文の最後に改行を追加（余白用）
    body = body.rstrip() + '\n\n'

    # 3. メールオブジェクトの作成
    email = EmailMessage(
        subject,
        body,
        settings.DEFAULT_FROM_EMAIL,
        [recipient],
        cc=cc_list,
    )

    # 4. PDFを添付 (Gmail文字化け対策)
    pdf_buffer.seek(0)
    filename = get_adjustment_filename(data, 'pdf')

    # メモリ効率のため getvalue() ではなく読み込みを使用
    attachment = MIMEApplication(pdf_buffer.read(), _subtype='pdf')
    attachment.add_header('Content-Disposition', 'attachment', filename=filename)
    email.attach(attachment)

    # 5. 送信
    try:
        sent_count = email.send(fail_silently=False)
        if sent_count != 1:
            logger.warning(f"Unexpected sent_count: {sent_count} (expected 1) for {subject}")
        else:
            logger.info(f"Email sent successfully: {subject} to {recipient}")
        return sent_count
    except Exception:
        # exc_info=True でスタックトレースをログに出力
        logger.error("Failed to send email", exc_info=True)
        raise
