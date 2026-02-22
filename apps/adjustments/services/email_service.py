from datetime import datetime

from django.conf import settings
from django.core.mail import EmailMessage

from apps.accounts.models import EmailTemplate
from ..utils import get_adjustment_filename


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
            pass

    # テンプレートの取得
    template = EmailTemplate.objects.first()
    if not template:
        raise RuntimeError('メールテンプレートが設定されていません。管理画面から作成してください。')

    # 区分（タイプ）の取得
    app_type_map = {'new': '新規', 'change': '変更', 'delete': '削除'}
    app_type_jp = app_type_map.get(data.get('app_type'), '新規')

    subject = template.subject
    body = template.body
    cc_raw = template.cc_address
    
    # プレースホルダーの置換
    replacements = {
        '{ユーザー名}': user_name,
        '{ユーザーEメールアドレス}': user_email,
        '{催事名}': event_name,
        '{運用日}': start_date_formatted,
        '{タイプ}': app_type_jp,
    }
    for placeholder, value in replacements.items():
        subject = subject.replace(placeholder, value or '')
        body = body.replace(placeholder, value or '')
        cc_raw = cc_raw.replace(placeholder, value or '')

    # CCのリスト化
    cc_list = [addr.strip() for addr in cc_raw.split(',') if addr.strip()]

    # 本文の最後に改行を追加（添付ファイルとの隙間用）
    body = body.rstrip() + '\n\n'

    # 送信先: 管理画面の設定を使用
    recipient = template.to_address

    email = EmailMessage(
        subject,
        body,
        settings.DEFAULT_FROM_EMAIL,
        [recipient],
        cc=cc_list,
    )

    # PDFを添付
    pdf_buffer.seek(0)
    filename = get_adjustment_filename(data, 'pdf')
    email.attach(filename, pdf_buffer.getvalue(), 'application/pdf')

    # 送信
    return email.send(fail_silently=False)
