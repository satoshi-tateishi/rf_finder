from unittest.mock import MagicMock, patch

from django.core.cache import cache
from django.test import TestCase

from apps.adjustments.services import LineBotService


class LineBotServiceTest(TestCase):
    def setUp(self):
        cache.clear()
        # Singleton instance reset for testing (though __new__ makes it tricky)
        LineBotService._instance = None

    @patch('apps.adjustments.services.line_bot_service.requests.post')
    def test_get_access_token_caching(self, mock_post):
        """アクセストークンがキャッシュされ、2回目以降はリクエストが発生しないこと"""
        # 1回目のレスポンス設定
        mock_post.return_value = MagicMock(
            status_code=200,
            json=lambda: {'access_token': 'test_token_123', 'expires_in': 3600}
        )

        service = LineBotService()

        # 1回目：リクエストが発生する
        token1 = service._get_access_token()
        self.assertEqual(token1, 'test_token_123')
        self.assertEqual(mock_post.call_count, 1)

        # 2回目：キャッシュから取得され、リクエストが発生しない
        token2 = service._get_access_token()
        self.assertEqual(token2, 'test_token_123')
        self.assertEqual(mock_post.call_count, 1)

    @patch('apps.adjustments.services.line_bot_service.requests.post')
    def test_send_pdf_flow(self, mock_post):
        """PDF送信の一連のフロー（トークン取得 -> アップロードURL取得 -> アップロード -> 送信）が正しく実行されること"""
        # 順次レスポンスを設定
        mock_post.side_effect = [
            # 1. _get_access_token
            MagicMock(status_code=200, json=lambda: {'access_token': 'fake_token'}),
            # 2. _get_upload_url
            MagicMock(status_code=200, json=lambda: {'uploadUrl': 'https://upload.com', 'fileId': 'file_id_999'}),
            # 3. _upload_file
            MagicMock(status_code=200),
            # 4. send_pdf (final message)
            MagicMock(status_code=201)
        ]

        with self.settings(LINE_WORKS_BOT_ID='test_bot'):
            service = LineBotService()
            success = service.send_pdf(channel_id='ch_001', file_content=b'dummy_pdf_data', file_name='test.pdf')

            self.assertTrue(success)
            self.assertEqual(mock_post.call_count, 4)

            # 最後のメッセージ送信の引数チェック
            last_call_args = mock_post.call_args_list[-1]
            self.assertIn('/bots/test_bot/channels/ch_001/messages', last_call_args[0][0])
            self.assertEqual(last_call_args[1]['json']['content']['fileId'], 'file_id_999')

    @patch('apps.adjustments.services.line_bot_service.requests.post')
    def test_send_flex_message(self, mock_post):
        """Flex Messageが正しく送信されること"""
        mock_post.side_effect = [
            # 1. _get_access_token
            MagicMock(status_code=200, json=lambda: {'access_token': 'fake_token'}),
            # 2. send_flex_message
            MagicMock(status_code=201)
        ]

        service = LineBotService()
        flex_content = {"type": "bubble", "body": {"type": "box", "layout": "vertical", "contents": []}}
        success = service.send_flex_message(channel_id='ch_001', flex_content=flex_content)

        self.assertTrue(success)
        self.assertEqual(mock_post.call_count, 2)

        # 引数チェック
        last_call_args = mock_post.call_args_list[-1]
        self.assertEqual(last_call_args[1]['json']['content']['type'], 'flex')
        self.assertEqual(last_call_args[1]['json']['content']['contents'], flex_content)

    @patch('apps.adjustments.services.line_bot_service.requests.post')
    def test_token_refresh_on_error(self, mock_post):
        """トークン取得に失敗した場合に適切にエラーハンドリングされること"""
        mock_post.return_value = MagicMock(status_code=401, text='Unauthorized')

        service = LineBotService()
        token = service._get_access_token()

        self.assertIsNone(token)
        self.assertEqual(mock_post.call_count, 1)

    @patch('apps.adjustments.services.line_bot_service.requests.post')
    def test_set_persistent_menu(self, mock_post):
        """固定メニューの設定が正しく行われること"""
        mock_post.side_effect = [
            # 1. _get_access_token
            MagicMock(status_code=200, json=lambda: {'access_token': 'fake_token'}),
            # 2. set_persistent_menu
            MagicMock(status_code=200)
        ]

        with self.settings(LINE_WORKS_BOT_ID='test_bot'):
            service = LineBotService()
            success = service.set_persistent_menu(woff_id='woff_123')

            self.assertTrue(success)
            self.assertEqual(mock_post.call_count, 2)

            # リクエスト内容の確認
            last_call_args = mock_post.call_args_list[-1]
            self.assertIn('/bots/test_bot/persistentmenu', last_call_args[0][0])
            self.assertEqual(last_call_args[1]['json']['content']['actions'][0]['label'], 'RF Finder を開く')
            self.assertIn('woff/woff_123', last_call_args[1]['json']['content']['actions'][0]['uri'])
