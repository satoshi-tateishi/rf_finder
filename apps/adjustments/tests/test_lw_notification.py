import io
from unittest.mock import ANY, patch

from django.test import TestCase, override_settings
from django.urls import reverse

from apps.accounts.models import EmailTemplate, Member
from apps.facilities.models import Facility, TVChannelStatus


class LWNotificationTest(TestCase):
    def setUp(self):
        from django.contrib.auth.models import User

        from apps.accounts.models import UserProfile

        # テスト用ユーザーの作成とログイン
        self.user = User.objects.create_user(username='testnotif', password='password')
        if not hasattr(self.user, 'profile'):
            UserProfile.objects.create(user=self.user)
        self.user.profile.family_name = '通知'
        self.user.profile.given_name = 'テスト'
        self.user.profile.save()
        self.client.force_login(self.user)

        self.member = Member.objects.create(name='テスト会員', member_id_1='123', member_id_2='456')
        EmailTemplate.objects.create(to_address='dest@example.com', subject='{タイプ}:{催事名}', body='{ユーザー名} 様')
        self.facility = Facility.objects.create(name='テスト施設', prefecture='東京都', address='渋谷区')
        TVChannelStatus.objects.create(facility=self.facility, channel_number=13, is_available=True)

    @patch('apps.adjustments.views.LineBotService')
    @patch('apps.adjustments.views.send_adjustment_email')
    @patch('apps.adjustments.views.generate_adjustment_pdf')
    @override_settings(LINE_WORKS_NOTIFICATION_CHANNEL_ID='group_123')
    def test_send_email_triggers_lw_notification(self, mock_gen_pdf, mock_send_email, mock_bot_class):
        """メール送信時にLW通知（メッセージとPDF）がグループに送信されること"""
        # Mocking
        mock_pdf_buffer = io.BytesIO(b'dummy pdf')
        mock_gen_pdf.return_value = mock_pdf_buffer

        mock_bot_instance = mock_bot_class.return_value
        mock_bot_instance.send_text_message.return_value = True
        mock_bot_instance.send_pdf.return_value = True

        data = {
            'app_type': 'new',
            'user': {'name': '太郎', 'kana': 'たろう', 'tel': '090', 'email': 'taro@ex.com'},
            'event': {'name': 'テスト催事', 'comment': 'メモ'},
            'facilities': [
                {
                    'id': self.facility.id,
                    'start_date': '2026-03-01',
                    'end_date': '2026-03-01',
                    'start_time': '10:00',
                    'end_time': '12:00',
                    'selectedChannels': [13],
                }
            ],
            'mic_counts': {'analog_rm': {'10mw': '1'}},
            'extra_53ch': '',
            'channelId': 'user_456',  # 依頼元
        }

        response = self.client.post(reverse('adjustments:send_email'), data=data, content_type='application/json')

        self.assertEqual(response.status_code, 200)

        # 依頼元へのPDF送信
        mock_bot_instance.send_pdf.assert_any_call('user_456', b'dummy pdf', file_name=ANY)

        # グループへの通知メッセージ送信
        mock_bot_instance.send_text_message.assert_called_with('group_123', ANY)
        # グループへのPDF送信
        mock_bot_instance.send_pdf.assert_any_call('group_123', b'dummy pdf', file_name=ANY)

        self.assertEqual(mock_bot_instance.send_pdf.call_count, 2)
        self.assertEqual(mock_bot_instance.send_text_message.call_count, 1)
