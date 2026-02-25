import logging
from datetime import datetime

from django.conf import settings
from django.core.mail import EmailMessage

from apps.accounts.models import EmailTemplate

from ..utils import get_adjustment_filename

logger = logging.getLogger(__name__)


def send_adjustment_email(data, member, pdf_buffer):
    """
    運用調整届のPDFを添付してメール送信を行う。
    DBに保存されたメールテンプレート（EmailTemplate）を参照し、プレースホルダーを置換する。
    """
    event_name = data.get('event', {}).get('name', '無題の催事')
    user_name = data.get('user', {}).get('name', '未設定')
    user_email = data.get('user', {}).get('email', '')

    # 運用日（最初の施設の開始日）を取得してフォーマット
    facilities = data.get('facilities', [])
    start_date_raw = facilities[0].get('start_date', '') if facilities else ''
    start_date_formatted = start_date_raw
    if start_date_raw:
        try:
            # YYYY-MM-DD を解析
            dt = datetime.strptime(start_date_raw, '%Y-%m-%d')
            # YYYY年M月D日 に変換 (月・日ともに0埋めなし)
            start_date_formatted = f'{dt.year}年{dt.month}月{dt.day}日'
        except ValueError:
            logger.warning(f"Invalid date format: {start_date_raw}")
            pass

    # テンプレートの取得 (name='adjustment' を優先取得し、なければ最初の一件)
    try:
        template = EmailTemplate.objects.filter(name='adjustment').first()
        if not template:
            template = EmailTemplate.objects.first()
            
        if not template:
            raise RuntimeError('メールテンプレートが登録されていません。管理画面から "adjustment" という名前で作成してください。')
            
        recipient = template.to_address
        if not recipient:
            raise RuntimeError('送信先メールアドレス(to_address)が設定されていません。')

    except Exception as e:
        logger.error(f"Failed to retrieve email template: {e}")
        raise

    # 区分（タイプ）の取得
    from ..constants import APP_TYPE_MAP
    app_type_jp = APP_TYPE_MAP.get(data.get('app_type'), '新規')

    subject = template.subject
    body = template.body
    cc_raw = template.cc_address or ''

    # プレースホルダーの置換
    replacements = {
        '{ユーザー名}': user_name,
        '{ユーザーEメールアドレス}': user_email,
        '{催事名}': event_name,
        '{運用日}': start_date_formatted,
        '{タイプ}': app_type_jp,
    }
    
    # 文字列の長い順にソートして置換（部分一致による誤置換防止）
    # 今回の例では {ユーザー名} と {ユーザー} があっても {ユーザー名} から先に置換される
    for placeholder in sorted(replacements.keys(), key=len, reverse=True):
        value = replacements[placeholder] or ''
        subject = subject.replace(placeholder, value)
        body = body.replace(placeholder, value)
        cc_raw = cc_raw.replace(placeholder, value)

    # CCのリスト化
    cc_list = [addr.strip() for addr in cc_raw.split(',') if addr.strip()]

    # メールオブジェクトの作成
    email = EmailMessage(
        subject,
        body,
        settings.DEFAULT_FROM_EMAIL,
        [recipient],
        cc=cc_list,
    )

    # PDFを添付 (Gmail文字化け対策: MIMEApplicationを直接操作)
    from email.mime.application import MIMEApplication

    pdf_buffer.seek(0)
    filename = get_adjustment_filename(data, 'pdf')

    # メモリ効率のため getvalue() ではなく読み込みを使用
    attachment = MIMEApplication(pdf_buffer.read(), _subtype='pdf')
    # add_headerで直接RFC 2231形式のパラメータを指定する
    # Python 3.x の email モジュールは、日本語を渡すと自動的に RFC 2231 (filename*) 形式でエンコードします
    attachment.add_header('Content-Disposition', 'attachment', filename=filename)

    # DjangoのEmailMessageにMIMEパートを直接追加
    email.attach(attachment)

    # 送信
    try:
        sent_count = email.send(fail_silently=False)
        logger.info(f"Email sent successfully: {subject} to {recipient}")
        return sent_count
    except Exception as e:
        logger.error(f"Failed to send email: {e}")
        raise
