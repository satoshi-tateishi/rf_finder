from unittest.mock import patch

from django.core.cache import cache
from django.test import TestCase, override_settings

from apps.adjustments.services import LineBotService


class LineBotServiceTest(TestCase):
    def setUp(self):
        cache.clear()
        # 2048bit RSA private key (dummy for testing)
        self.dummy_private_key = (
            '-----BEGIN RSA PRIVATE KEY-----\n'
            'MIIEpQIBAAKCAQEAp7prKNIj28EWIGNIOWPQNTfCwCZPKEjyseE6BRnvKPONPrre\n'
            'TYXEsziudSt7OdgUv60jWK66BoXf4YsOXjTZ4kKRx5ZHLTGenMlQ+X4YQt5Xn7i5\n'
            'vrj5Fw9+807kz/T+DO24BdHRVF6WICAp52q36FpEMinWfc/mN5OC/sdR9GRxACfV\n'
            'R8EUDwrkzX7TZwBqiLo89tQ9SMZppr4yKyJeWoynrda9O3E8ugoHgLv+++y8ku6u\n'
            'Ck8q4BFgohZD8Ktn3eVRgAGTDSxOyPVSI2p+5iozPD8iraC98FWQ8CrrvCWe8rAe\n'
            'vG5e50utroo/GAFDdtyIFmVGhqzJThJr3IlPpwIDAQABAoIBAQCY5QFcE7rmTqv5\n'
            '2Cb1UbxxVqQr/n/37A94ASSfk9WEUge2YCfXKRJ2gTveyUUqJIQ9efmXlKc03QKJ\n'
            'mfX+AFWBwEcdVisJ0oqQx58N31kEU6Qyj/SaHAnMcK674nYH739Kj8RJYctdCl/1\n'
            'Zvxr3MdKgkZaJ/NDeqmUjd5Cm7VkflSKI29O35QCM9LrDDg9N4XmxBEVv5i9vveq\n'
            '0XKd1oyc/2+JBrEU1xO8zQ6kwK5WQ/HniIk7yLnMK9BnQxNaKJgUOCpdmNZK/EGr\n'
            'BsPIlwBRgf2hIb+wiSjeaDMhWfaSkaOzGZFDkXS5L1329bmmi6rCjYgp5hrk2xVS\n'
            'XdCrYVshAoGBANpad87/l7J5wat3U1M1Z5aRJAIU6FpLIIcCjpyWngI5wBf25FhM\n'
            'tfeENTmmoQTndLE03OZ4MueKzYexABpeqNqbp50XHsc5cUcnIi9HbXK0TO8zmte3\n'
            '9NweSq5MBdWDQSRrjmZ0M02o8fObIeTOQYNQfm2TkRfyLDb5D8EfokOXAoGBAMSl\n'
            'fZcswRSuuk8WsXVCqnK1tg1iKAXH1PTBcuKeG0TBJlMhBm5lbPTdLSdaTIjPeOet\n'
            'ti02peVN3KdnqMfrRSnlKXRu59yasDuRLefD8Oh9FbNmfmrBHVE3Fh5kIxCFS8rz\n'
            '88tP3jt4mkYNt9/IW2zNb7McyyvP4cEMCJJeCZZxAoGBAMVqqAniMtAtnzmc0Bxa\n'
            'G4cZQLoVFyKT7BvE5xWSY9fVSOUh1sAy0w6vXMP78HcToQCar+I76KJJb5vwHwy4\n'
            'augDdV7lSXGMcOuI6TJf3QepFinquWOyMVNWm+TMXTX2zs3T5NKi2sOrLN44c0OA\n'
            'a+ECxNvjYHqK/QjS1Diilj2PAoGBALIePE4Mia+UPMmago72HbHdidNBj4L86JXy\n'
            'C3/dOlHiqjYt+cdRM4nwNRAqKJzbYGZp4FO/5jB3gGBZ8nVzU6iJHC2Mr5QQwYST\n'
            'EgOWZcYQVvGy6tsDpOyFexF4HpK+SlLA+Zi09VTk/shpcJ3Qu48n3f9dG2LJ33Ce\n'
            '17zMVN7hAoGAVhRYkBz+NwU6hG7OZomR3UPcUl1ZBstNVMQKX8fetSTCkUriMkQc\n'
            'JNbHExAVlkJQcbDAF+gZPTSh9mMs/DXK0ybLH/sChyiO7tub5qY4I/fZnG6keEPt\n'
            'hJq8A4O5iojNrjXVCJkJbg8hVdvztZR+musxUKVeGo6VGuIJD3kt80M=\n'
            '-----END RSA PRIVATE KEY-----'
        )
        self.settings_override = {
            'LINE_WORKS_CLIENT_ID': 'test_client_id',
            'LINE_WORKS_CLIENT_SECRET': 'test_client_secret',
            'LINE_WORKS_SERVICE_ACCOUNT': 'test_sa',
            'LINE_WORKS_PRIVATE_KEY': self.dummy_private_key,
            'LINE_WORKS_BOT_ID': 'test_bot_id',
            'LINE_WORKS_MOCK_MODE': True,
        }

    def test_get_access_token_mock_mode(self):
        """テストモード時は常に固定のモックトークンを返すこと"""
        with override_settings(**self.settings_override):
            service = LineBotService()
            token = service._get_access_token()
            self.assertEqual(token, 'mock_access_token')

    @patch('requests.Session.post')
    def test_get_access_token_api_call(self, mock_post):
        """モックモード無効時、APIを呼び出してトークンを取得しキャッシュすること"""
        mock_post.return_value.ok = True
        mock_post.return_value.json.return_value = {'access_token': 'fresh_token_123', 'expires_in': 3600}

        with override_settings(**{**self.settings_override, 'LINE_WORKS_MOCK_MODE': False}):
            service = LineBotService()
            # 内部フラグを一時的に騙して API 呼び出しをシミュレート
            with patch('os.sys.argv', []):
                token = service._get_access_token()
                self.assertEqual(token, 'fresh_token_123')
                self.assertTrue(mock_post.called)

    def test_send_text_message_mock(self):
        """モックモードでテキストメッセージ送信が「成功(True)」を返すこと"""
        with override_settings(**self.settings_override):
            service = LineBotService()
            success = service.send_text_message('channel_123', 'Hello Test')
            self.assertTrue(success)

    def test_send_pdf_mock(self):
        """モックモードでPDF送信が「成功(True)」を返すこと"""
        with override_settings(**self.settings_override):
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
            'facilities': [{'name': '施設A', 'start_date': '2026-03-01', 'end_date': '2026-03-01'}],
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
