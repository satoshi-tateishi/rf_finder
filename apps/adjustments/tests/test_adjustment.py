import io
import json

from django.core import mail
from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import EmailTemplate, Member
from apps.adjustments.services import (
    generate_adjustment_excel,
    generate_adjustment_pdf,
    send_adjustment_email,
)
from apps.adjustments.utils import format_channels


class AdjustmentLogicTest(TestCase):
    def test_format_channels(self):
        """チャンネル番号リストが正しいハイフン連結文字列になること"""
        self.assertEqual(format_channels([13, 14, 15]), '13-15')
        self.assertEqual(format_channels([13, 14, 16, 17, 18]), '13, 14, 16-18')
        self.assertEqual(format_channels([13, 15, 17]), '13, 15, 17')
        self.assertEqual(format_channels([]), '')

    def test_generate_excel_and_pdf_smoke(self):
        """ExcelとPDFの生成がエラーなく完了し、BytesIOを返すこと"""
        member = Member.objects.create(
            member_id_1='123',
            member_id_2='4567',
            name='テスト会員',
            manager_name='担当者',
            phone='03-1234-5678',
            email='test@example.com',
        )
        data = {
            'app_type': 'new',
            'user': {'name': '使用者', 'kana': 'しようしゃ', 'tel': '090', 'email': 'u@ex.com'},
            'event': {'name': '催事', 'comment': 'コメント'},
            'facilities': [
                {'name': '施設1', 'start_date': '2026-02-20', 'start_time': '09:00', 'selectedChannels': [13, 14]}
            ],
            'mic_counts': {'analog_rm': {'10mw': 1}},
        }

        # Excel生成テスト
        excel_buffer = generate_adjustment_excel(data, member)
        self.assertIsInstance(excel_buffer, io.BytesIO)
        self.assertTrue(len(excel_buffer.getvalue()) > 0)

        # PDF生成テスト
        try:
            pdf_buffer = generate_adjustment_pdf(data, member)
            self.assertIsInstance(pdf_buffer, io.BytesIO)
            self.assertTrue(len(pdf_buffer.getvalue()) > 0)
        except Exception as e:
            self.fail(f'PDF generation failed: {e}')

    def test_send_adjustment_email(self):
        """メール送信がテンプレートに基づいて正しく行われること"""
        member = Member.objects.create(name='テスト会社')
        EmailTemplate.objects.create(
            subject='【{運用日}】テスト',
            body='こんにちは {ユーザー名} 様。区分は {タイプ} です。',
            to_address='recipient@example.com',
            cc_address='{ユーザーEメールアドレス}, boss@example.com',
        )
        data = {
            'app_type': 'change',
            'user': {'name': '太郎', 'email': 'taro@ex.com'},
            'facilities': [{'start_date': '2026-02-20'}]
        }
        pdf_buffer = io.BytesIO(b'dummy pdf content')

        send_adjustment_email(data, member, pdf_buffer)

        # 送信済みメールの検証
        self.assertEqual(len(mail.outbox), 1)
        sent = mail.outbox[0]
        self.assertEqual(sent.subject, '【2026年2月20日】テスト')
        self.assertIn('こんにちは 太郎 様。区分は 変更 です。', sent.body)
        # CCの検証
        self.assertIn('taro@ex.com', sent.cc)
        self.assertIn('boss@example.com', sent.cc)
        self.assertEqual(len(sent.attachments), 1)
        # ファイル名が正しく生成されているか（運用連絡票_新規_無題の催事_20260220.pdf）
        self.assertIn('運用連絡票', sent.attachments[0][0])
        self.assertIn('20260220', sent.attachments[0][0])


class AdjustmentAPITest(TestCase):
    def setUp(self):
        Member.objects.create(name='テスト会員')
        EmailTemplate.objects.create(
            subject='テスト件名',
            body='テスト本文',
            to_address='test@example.com'
        )
        self.valid_data = {
            'app_type': 'new',
            'user': {'name': '使用者', 'kana': 'しようしゃ', 'tel': '090-1234-5678', 'email': 'u@ex.com'},
            'event': {'name': '催事'},
            'facilities': [
                {
                    'name': '施設1',
                    'start_date': '2026-02-20',
                    'end_date': '2026-02-20',
                    'start_time': '09:00',
                    'end_time': '22:00',
                }
            ],
            'mic_counts': {'analog_rm': {'10mw': 1}},
        }

    def test_preview_pdf_api(self):
        """PDFプレビューAPIが正常にPDFを返すこと"""
        response = self.client.post(
            reverse('adjustments:preview_pdf'), data=json.dumps(self.valid_data), content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/pdf')

    def test_preview_excel_api(self):
        """ExcelプレビューAPIが正常にExcelファイルを返すこと"""
        response = self.client.post(
            reverse('adjustments:preview_excel'), data=json.dumps(self.valid_data), content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

    def test_send_email_api(self):
        """メール送信APIが正常に受理されること"""
        response = self.client.post(
            reverse('adjustments:send_email'), data=json.dumps(self.valid_data), content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['status'], 'success')
        self.assertEqual(len(mail.outbox), 1)

    def test_api_invalid_json(self):
        """不正なJSONを送った場合に400エラーになること"""
        response = self.client.post(
            reverse('adjustments:preview_pdf'), data='invalid json', content_type='application/json'
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['status'], 'error')

    def test_missing_member(self):
        """会員情報（Member）がDBに存在しない場合でも生成処理が継続されること"""
        Member.objects.all().delete()
        response = self.client.post(
            reverse('adjustments:preview_pdf'), data=json.dumps(self.valid_data), content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/pdf')

    def test_validation_error_empty_payload(self):
        """空のJSONオブジェクトを送った場合にバリデーションエラーになること"""
        response = self.client.post(
            reverse('adjustments:preview_pdf'), data=json.dumps({}), content_type='application/json'
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['status'], 'error')
        self.assertIn('errors', response.json())

    def test_validation_error_missing_event_name(self):
        """必須項目（催事名）が欠落している場合にエラーになること"""
        incomplete_data = self.valid_data.copy()
        incomplete_data['event'] = {}  # 催事名がない

        response = self.client.post(
            reverse('adjustments:preview_pdf'), data=json.dumps(incomplete_data), content_type='application/json'
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['status'], 'error')
        # エラーキーが event_name になっていることを確認 (UserInfoForm/EventInfoFormの接頭辞)
        self.assertIn('event_name', response.json()['errors'])

    def test_validation_error_missing_user_fields(self):
        """現地使用者の必須項目が欠落している場合にエラーになること"""
        incomplete_data = self.valid_data.copy()
        incomplete_data['user'] = {'name': '名前のみ'}  # 他が足りない

        response = self.client.post(
            reverse('adjustments:preview_pdf'), data=json.dumps(incomplete_data), content_type='application/json'
        )
        self.assertEqual(response.status_code, 400)
        errors = response.json()['errors']
        self.assertIn('user_kana', errors)
        self.assertIn('user_tel', errors)
        self.assertIn('user_email', errors)

    def test_validation_error_no_mic_counts(self):
        """マイク数が1つも入力されていない場合にエラーになること"""
        incomplete_data = self.valid_data.copy()
        incomplete_data['mic_counts'] = {}  # 空

        response = self.client.post(
            reverse('adjustments:preview_pdf'), data=json.dumps(incomplete_data), content_type='application/json'
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn('mic_counts', response.json()['errors'])

    def test_validation_error_incomplete_facility(self):
        """施設の時間情報が不足している場合にエラーになること"""
        incomplete_data = self.valid_data.copy()
        incomplete_data['facilities'] = [{'name': '施設1', 'start_date': '2026-02-20'}]  # 時間がない

        response = self.client.post(
            reverse('adjustments:preview_pdf'), data=json.dumps(incomplete_data), content_type='application/json'
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn('facilities', response.json()['errors'])

    def test_validation_error_zero_mics(self):
        """マイク数がすべて0の場合にエラーになること"""
        invalid_data = self.valid_data.copy()
        invalid_data['mic_counts'] = {
            'analog_rm': {'10mw': 0},
            'digital_rm': {'10mw': '0', '20mw': 0}
        }
        response = self.client.post(
            reverse('adjustments:preview_pdf'), data=json.dumps(invalid_data), content_type='application/json'
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn('mic_counts', response.json()['errors'])

class AdjustmentUtilityTest(TestCase):
    def test_get_adjustment_filename_sanitization(self):
        """ファイル名に使用できない文字がサニタイズされること"""
        from apps.adjustments.utils import get_adjustment_filename
        data = {
            'app_type': 'change',
            'event': {'name': '催事 / ハムレット : "復讐" *'},
            'facilities': [{'start_date': '2026-02-22'}]
        }
        filename = get_adjustment_filename(data, 'pdf')
        # 禁止文字 / : " * が除外され、ファイル名が妥当であることを確認
        self.assertNotIn('/', filename)
        self.assertNotIn(':', filename)
        self.assertNotIn('"', filename)
        self.assertNotIn('*', filename)
        self.assertIn('運用連絡票_変更_', filename)
        self.assertIn('20260222.pdf', filename)

    def test_get_adjustment_filename_app_types(self):
        """各申請区分が正しく日本語に変換されること"""
        from apps.adjustments.utils import get_adjustment_filename
        base_data = {'event': {'name': 'テスト'}, 'facilities': []}

        self.assertIn('新規', get_adjustment_filename({**base_data, 'app_type': 'new'}))
        self.assertIn('変更', get_adjustment_filename({**base_data, 'app_type': 'change'}))
        self.assertIn('削除', get_adjustment_filename({**base_data, 'app_type': 'delete'}))

class EmailServiceDetailTest(TestCase):
    def test_template_full_replacement(self):
        """すべてのプレースホルダーが正しく置換されること"""
        from apps.adjustments.services import send_adjustment_email
        member = Member.objects.create(name='テスト会員')
        EmailTemplate.objects.create(
            subject='{タイプ}:{催事名}',
            body='{ユーザー名} 様 ({ユーザーEメールアドレス})\n運用日: {運用日}',
            to_address='to@ex.com'
        )
        data = {
            'app_type': 'new',
            'user': {'name': '太郎', 'email': 'taro@ex.com'},
            'event': {'name': 'ハムレット'},
            'facilities': [{'start_date': '2026-05-10'}]
        }
        pdf_buffer = io.BytesIO(b'dummy')

        send_adjustment_email(data, member, pdf_buffer)

        sent = mail.outbox[0]
        self.assertEqual(sent.subject, '新規:ハムレット')
        self.assertIn('太郎 様 (taro@ex.com)', sent.body)
        self.assertIn('運用日: 2026年5月10日', sent.body)

