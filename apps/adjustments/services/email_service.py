from datetime import datetime

from django.conf import settings
from django.core.mail import EmailMessage

from apps.accounts.models import EmailTemplate


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

    if template:
        subject = template.subject
        body = template.body
        # プレースホルダーの置換
        replacements = {
            '{ユーザー名}': user_name,
            '{ユーザーEメールアドレス}': user_email,
            '{催事名}': event_name,
            '{運用日}': start_date_formatted,
        }
        for placeholder, value in replacements.items():
            subject = subject.replace(placeholder, value or '')
            body = body.replace(placeholder, value or '')

        # 本文の最後に改行を追加（添付ファイルとの隙間用）
        body = body.rstrip() + '\n\n'

        # 送信先: .env の設定がある場合はそれを優先（テスト用）、なければテンプレートの設定を使用
        recipient = getattr(settings, 'ADJUSTMENT_EMAIL_TO', template.to_address)
    else:
        # テンプレートがない場合のデフォルト
        subject = f'【運用調整届】{event_name} - {user_name}'
        body = f"""特定ラジオマイク運用調整届（自動送信）

催事名: {event_name}
申請者: {member.name if member else '未設定'}
現地使用者: {user_name}

詳細は添付のPDFをご確認ください。

"""
        recipient = getattr(settings, 'ADJUSTMENT_EMAIL_TO', 'rm-unyo@radiomic.org')

    email = EmailMessage(
        subject,
        body,
        settings.DEFAULT_FROM_EMAIL,
        [recipient],
    )

    # PDFを添付
    pdf_buffer.seek(0)
    email.attach('adjustment_form.pdf', pdf_buffer.getvalue(), 'application/pdf')

    # 送信
    return email.send(fail_silently=False)
