import io
from django.test import TestCase
from django.core import mail
from apps.accounts.models import Member, EmailTemplate
from .utils import format_channels
from .services import generate_adjustment_excel, generate_adjustment_pdf, send_adjustment_email

class AdjustmentLogicTest(TestCase):
    def test_format_channels(self):
        """チャンネル番号リストが正しいハイフン連結文字列になること"""
        self.assertEqual(format_channels([13, 14, 15]), "13-15")
        self.assertEqual(format_channels([13, 14, 16, 17, 18]), "13, 14, 16-18")
        self.assertEqual(format_channels([13, 15, 17]), "13, 15, 17")
        self.assertEqual(format_channels([]), "")

    def test_generate_excel_and_pdf_smoke(self):
        """ExcelとPDFの生成がエラーなく完了し、BytesIOを返すこと"""
        member = Member.objects.create(
            member_id_1="123", member_id_2="4567", name="テスト会員", 
            manager_name="担当者", phone="03-1234-5678", email="test@example.com"
        )
        data = {
            "app_type": "new",
            "user": {"name": "使用者", "kana": "しようしゃ", "tel": "090", "email": "u@ex.com"},
            "event": {"name": "催事", "comment": "コメント"},
            "facilities": [
                {"name": "施設1", "start_date": "2026-02-20", "selectedChannels": [13, 14]}
            ]
        }
        
        # Excel生成テスト
        excel_buffer = generate_adjustment_excel(data, member)
        self.assertIsInstance(excel_buffer, io.BytesIO)
        self.assertTrue(len(excel_buffer.getvalue()) > 0)

        # PDF生成テスト (LibreOfficeが必要なため、環境によってはスキップされる可能性があるが、コンテナ内なら動くはず)
        try:
            pdf_buffer = generate_adjustment_pdf(data, member)
            self.assertIsInstance(pdf_buffer, io.BytesIO)
            self.assertTrue(len(pdf_buffer.getvalue()) > 0)
        except Exception as e:
            self.fail(f"PDF generation failed: {e}")

    def test_send_adjustment_email(self):
        """メール送信がテンプレートに基づいて正しく行われること"""
        member = Member.objects.create(name="テスト会社")
        EmailTemplate.objects.create(
            subject="【{運用日}】テスト",
            body="こんにちは {ユーザー名} 様",
            to_address="recipient@example.com",
            from_address="sender@example.com"
        )
        data = {
            "user": {"name": "太郎", "email": "taro@ex.com"},
            "facilities": [{"start_date": "2026-02-20"}]
        }
        pdf_buffer = io.BytesIO(b"dummy pdf content")
        
        send_adjustment_email(data, member, pdf_buffer)
        
        # 送信済みメールの検証
        self.assertEqual(len(mail.outbox), 1)
        sent = mail.outbox[0]
        self.assertEqual(sent.subject, "【2026年2月20日】テスト")
        self.assertIn("こんにちは 太郎 様", sent.body)
        self.assertEqual(len(sent.attachments), 1)
        self.assertEqual(sent.attachments[0][0], "adjustment_form.pdf")
