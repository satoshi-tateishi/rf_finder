from unittest.mock import patch

from django.test import TestCase, override_settings

from apps.adjustments.services import LineBotService


class LineBotServiceTest(TestCase):
    def setUp(self):
        # 必要な設定をオーバーライド
        self.settings_override = {
            'LINE_WORKS_CLIENT_ID': 'test_client_id',
            'LINE_WORKS_CLIENT_SECRET': 'test_client_secret',
            'LINE_WORKS_SERVICE_ACCOUNT': 'test_sa',
            'LINE_WORKS_PRIVATE_KEY': 'test_key',
            'LINE_WORKS_BOT_ID': 'test_bot_id',
            'LINE_WORKS_MOCK_MODE': True,
        }

    @override_settings(LINE_WORKS_MOCK_MODE=True)
    def test_get_access_token_mock_mode(self):
        """テストモード時は常に固定のモックトークンを返すこと"""
        service = LineBotService()
        token = service._get_access_token()
        self.assertEqual(token, 'mock_access_token')

    @patch('requests.Session.post')
    @override_settings(LINE_WORKS_MOCK_MODE=False)
    def test_get_access_token_api_call(self, mock_post):
        """モックモード無効時、APIを呼び出してトークンを取得しキャッシュすること"""
        # Note: 実際には 'test' in sys.argv が優先されるため、
        # このテストを厳密に実行するには内部フラグを操作する必要があるが、
        # ここでは実装の意図を確認するに留める
        mock_post.return_value.ok = True
        mock_post.return_value.json.return_value = {
            'access_token': 'fresh_token_123',
            'expires_in': 3600
        }

        service = LineBotService()
        # 内部フラグを一時的に騙して API 呼び出しをシミュレート
        with patch('os.sys.argv', []):
            token = service._get_access_token()
            self.assertEqual(token, 'fresh_token_123')
            self.assertTrue(mock_post.called)

    @override_settings(LINE_WORKS_MOCK_MODE=True)
    def test_send_text_message_mock(self):
        """モックモードでテキストメッセージ送信が「成功(True)」を返すこと"""
        service = LineBotService()
        success = service.send_text_message('channel_123', 'Hello Test')
        self.assertTrue(success)

    @override_settings(LINE_WORKS_MOCK_MODE=True)
    def test_send_pdf_mock(self):
        """モックモードでPDF送信が「成功(True)」を返すこと"""
        service = LineBotService()
        success = service.send_pdf('channel_123', b'dummy content', 'test.pdf')
        self.assertTrue(success)

    def test_build_submission_notification_message(self):
        """送信通知メッセージが正しく構築されること"""
        service = LineBotService()
        data = {
            'app_type': 'new',
            'event': {'name': 'テスト催事'},
            'user': {'name': '現地太郎'},
            'sender_name': '操作次郎',
            'facilities': [
                {'name': '施設A', 'start_date': '2026-03-01', 'end_date': '2026-03-01'}
            ]
        }
        msg = service.build_submission_notification_message(data)

        self.assertIn('【運用調整届 送信通知】', msg)
        self.assertIn('区分: 新規', msg)
        self.assertIn('催事名: テスト催事', msg)
        self.assertIn('現地使用者: 現地太郎', msg)
        self.assertIn('申請者: 操作次郎', msg)
        self.assertIn('施設:\n1.施設A\n2026/03/01 - 2026/03/01', msg)

    @patch('apps.adjustments.services.line_bot_service.LineBotService._request')
    @override_settings(LINE_WORKS_MOCK_MODE=False)
    def test_get_user_info(self, mock_request):
        """ユーザー情報取得APIが正しく呼び出されること"""
        mock_request.return_value.ok = True
        mock_request.return_value.json.return_value = {'userName': 'テストユーザー'}

        service = LineBotService()
        with patch('apps.adjustments.services.line_bot_service.LineBotService._get_access_token', return_value='token'):
            info = service.get_user_info('user_123')
            self.assertEqual(info['userName'], 'テストユーザー')
            mock_request.assert_called_with('GET', '/users/user_123', 'token', timeout=10)
