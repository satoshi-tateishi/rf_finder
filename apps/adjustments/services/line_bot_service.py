import io
import logging
import os
import time
from typing import Any, Dict, List, Optional, Tuple, Union

import jwt
import requests
from django.conf import settings
from django.core.cache import cache
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)


class LineBotService:
    """
    LINE WORKS Bot API Service for sending files to talk rooms.
    """

    CACHE_KEY = 'line_works_access_token_v2'
    TOKEN_EXPIRY = 86400 - 300  # 24 hours - 5 minutes buffer
    
    # API Base URLs
    AUTH_BASE_URL = getattr(settings, 'LINE_WORKS_AUTH_BASE_URL', 'https://auth.worksmobile.com')
    API_BASE_URL = getattr(settings, 'LINE_WORKS_API_BASE_URL', 'https://www.worksapis.com')

    def __init__(self):
        self.client_id = settings.LINE_WORKS_CLIENT_ID
        self.client_secret = settings.LINE_WORKS_CLIENT_SECRET
        self.service_account = settings.LINE_WORKS_SERVICE_ACCOUNT
        self.private_key = settings.LINE_WORKS_PRIVATE_KEY
        self.bot_id = settings.LINE_WORKS_BOT_ID
        
        # Session configuration with retry logic
        self.session = requests.Session()
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)

    def _generate_jwt(self) -> str:
        """
        Generate JWT for Service Account authentication.
        """
        now = int(time.time())
        payload = {
            'iss': self.client_id,
            'sub': self.service_account,
            'iat': now,
            'exp': now + 3600,  # 1 hour (for JWT itself)
        }
        headers = {'alg': 'RS256', 'typ': 'JWT'}
        return jwt.encode(payload, self.private_key, algorithm='RS256', headers=headers)

    def _get_access_token(self) -> Optional[str]:
        """
        Get access token using JWT or from cache.
        """
        # 安全装置: テストモード時のモックトークン
        if getattr(settings, 'LINE_WORKS_MOCK_MODE', False) or 'test' in os.sys.argv:
            return 'mock_access_token'

        token = cache.get(self.CACHE_KEY)
        if token:
            return token

        # レースコンディション対策（簡易ロック）
        lock_key = f"{self.CACHE_KEY}_lock"
        if not cache.add(lock_key, "locked", 10):
            # 他のプロセスが取得中の場合は少し待ってからキャッシュを確認
            time.sleep(1)
            return cache.get(self.CACHE_KEY)

        try:
            assertion = self._generate_jwt()
            url = f'{self.AUTH_BASE_URL}/oauth2/v2.0/token'
            data = {
                'assertion': assertion,
                'grant_type': 'urn:ietf:params:oauth:grant-type:jwt-bearer',
                'client_id': self.client_id,
                'client_secret': self.client_secret,
                'scope': 'bot,user.read',
            }
            
            response = self.session.post(url, data=data, timeout=10)
            if response.ok:
                res_data = response.json()
                token = res_data.get('access_token')
                
                try:
                    expires_in = int(res_data.get('expires_in', self.TOKEN_EXPIRY))
                except (ValueError, TypeError):
                    expires_in = self.TOKEN_EXPIRY

                # キャッシュ時間は最小60秒、最大 TOKEN_EXPIRY に制限
                cache_time = max(60, min(expires_in - 60, self.TOKEN_EXPIRY))
                cache.set(self.CACHE_KEY, token, cache_time)
                return token
            else:
                logger.error(f'[LineBotService] Failed to get access token: {response.status_code}')
                return None
        except Exception as e:
            logger.error(f'[LineBotService] Error getting access token: {e}')
            return None
        finally:
            cache.delete(lock_key)

    def _request(self, method: str, path: str, access_token: str, **kwargs) -> requests.Response:
        """
        共通リクエストメソッド
        """
        url = f'{self.API_BASE_URL}/v1.0{path}'
        headers = kwargs.pop('headers', {})
        headers['Authorization'] = f'Bearer {access_token}'
        
        return self.session.request(method, url, headers=headers, **kwargs)

    def _get_upload_url(self, access_token: str, file_name: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Get upload URL and file ID for the bot.
        """
        path = f'/bots/{self.bot_id}/attachments'
        data = {'fileName': file_name}

        try:
            response = self._request('POST', path, access_token, json=data, timeout=10)
            if response.ok:
                res_data = response.json()
                return res_data.get('uploadUrl'), res_data.get('fileId')
            else:
                logger.error(f'[LineBotService] Failed to get upload URL: {response.status_code}')
                return None, None
        except Exception as e:
            logger.error(f'[LineBotService] Error getting upload URL: {e}')
            return None, None

    def _upload_file(self, upload_url: str, access_token: str, file_content: bytes, file_name: str) -> bool:
        """
        Upload file binary to the given upload URL.
        """
        headers = {'Authorization': f'Bearer {access_token}'}
        # requests の files パラメータには bytes を直接渡すのが最も確実です
        files = {'FileData': (file_name, file_content, 'application/pdf')}

        try:
            response = self.session.post(upload_url, headers=headers, files=files, timeout=30)
            if response.ok:
                return True
            else:
                logger.error(f'[LineBotService] Failed to upload file content: {response.status_code}')
                return False
        except Exception as e:
            logger.error(f'[LineBotService] Error uploading file: {e}')
            return False

    def send_pdf(self, channel_id: str, file_content: bytes, file_name: str = 'adjustment_request.pdf') -> bool:
        """
        Public method to send a PDF file to a talk room.
        """
        if not self.bot_id or not channel_id:
            logger.warning('[LineBotService] Bot ID or Channel ID is missing.')
            return False

        # 安全装置: テストモードまたはデバッグモードでの誤送信防止
        if getattr(settings, 'LINE_WORKS_MOCK_MODE', False) or 'test' in os.sys.argv:
            logger.info(f'[LineBotService][MOCK] Sending PDF to {channel_id}: {file_name} ({len(file_content)} bytes)')
            return True

        access_token = self._get_access_token()
        if not access_token:
            return False

        # 1. Get Upload URL
        upload_url, file_id = self._get_upload_url(access_token, file_name)
        if not upload_url or not file_id:
            return False

        # 2. Upload File (トークンを渡すように修正)
        if not self._upload_file(upload_url, access_token, file_content, file_name):
            return False

        # 3. Send Message
        path = f'/bots/{self.bot_id}/channels/{channel_id}/messages'
        data = {'content': {'type': 'file', 'fileId': file_id}}

        try:
            response = self._request('POST', path, access_token, json=data, timeout=10)
            if response.status_code == 201:
                logger.info(f'[LineBotService] Successfully sent PDF to channel {channel_id}')
                return True
            else:
                logger.error(f'[LineBotService] Failed to send file message: {response.status_code}')
                return False
        except Exception as e:
            logger.error(f'[LineBotService] Error sending PDF message: {e}')
            return False

    def send_flex_message(self, channel_id: str, flex_content: Dict[str, Any], alt_text: str = 'Flex Message') -> bool:
        """
        Send Flex Message to talk room.
        """
        if not self.bot_id or not channel_id:
            return False

        if getattr(settings, 'LINE_WORKS_MOCK_MODE', False) or 'test' in os.sys.argv:
            logger.info(f'[LineBotService][MOCK] Sending Flex Message to {channel_id}: {alt_text}')
            return True

        access_token = self._get_access_token()
        if not access_token:
            return False

        path = f'/bots/{self.bot_id}/channels/{channel_id}/messages'
        data = {'content': {'type': 'flex', 'altText': alt_text, 'contents': flex_content}}

        try:
            response = self._request('POST', path, access_token, json=data, timeout=10)
            if response.ok:
                return True
            else:
                logger.error(f'[LineBotService] Failed to send Flex Message: {response.status_code}')
                return False
        except Exception as e:
            logger.error(f'[LineBotService] Error sending Flex Message: {e}')
            return False

    def send_text_message(self, channel_id: str, text: str) -> bool:
        """
        Send simple text message to a talk room (group/channel).
        """
        if not self.bot_id or not channel_id:
            return False

        if getattr(settings, 'LINE_WORKS_MOCK_MODE', False) or 'test' in os.sys.argv:
            logger.info(f'[LineBotService][MOCK] Sending Text to {channel_id}: {text[:50]}...')
            return True

        access_token = self._get_access_token()
        if not access_token:
            return False

        path = f'/bots/{self.bot_id}/channels/{channel_id}/messages'
        data = {'content': {'type': 'text', 'text': text}}

        try:
            response = self._request('POST', path, access_token, json=data, timeout=10)
            if response.ok:
                return True
            else:
                logger.error(f'[LineBotService] Failed to send text message: {response.status_code}')
                return False
        except Exception as e:
            logger.error(f'[LineBotService] Error sending text message: {e}')
            return False

    def send_user_message(self, user_id: str, text: str) -> bool:
        """
        Send simple text message to a specific user (1-on-1).
        """
        if not self.bot_id or not user_id:
            return False

        if getattr(settings, 'LINE_WORKS_MOCK_MODE', False) or 'test' in os.sys.argv:
            logger.info(f'[LineBotService][MOCK] Sending User Message to {user_id}: {text[:50]}...')
            return True

        access_token = self._get_access_token()
        if not access_token:
            return False

        path = f'/bots/{self.bot_id}/users/{user_id}/messages'
        data = {'content': {'type': 'text', 'text': text}}

        try:
            response = self._request('POST', path, access_token, json=data, timeout=10)
            if response.ok:
                return True
            else:
                logger.error(f'[LineBotService] Failed to send user message: {response.status_code}')
                return False
        except Exception as e:
            logger.error(f'[LineBotService] Error sending user message: {e}')
            return False

    def get_user_info(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Fetch user details from LINE WORKS Users API.
        """
        access_token = self._get_access_token()
        if not access_token:
            return None

        path = f'/users/{user_id}'

        try:
            response = self._request('GET', path, access_token, timeout=10)
            if response.ok:
                return response.json()
            else:
                logger.error(f'[LineBotService] Failed to fetch user info for {user_id}: {response.status_code}')
                return None
        except Exception as e:
            logger.error(f'[LineBotService] Error fetching user info: {e}')
            return None

    def build_submission_notification_message(self, data: Dict[str, Any]) -> str:
        """
        運用調整届の送信通知メッセージ（テキスト）を構築する。
        """
        from apps.adjustments.constants import APP_TYPE_MAP

        app_type_jp = APP_TYPE_MAP.get(data.get('app_type'), '新規')
        event_name = data.get('event', {}).get('name', '無題の催事')
        user_name = data.get('user', {}).get('name', '不明')

        facilities = data.get('facilities', [])
        facility_lines = []
        for i, f in enumerate(facilities):
            name = f.get('name', '不明')
            start = f.get('start_date', '').replace('-', '/')
            end = f.get('end_date', '').replace('-', '/')
            facility_lines.append(f'{i + 1}.{name}\n{start} - {end}')

        facility_text = '\n\n'.join(facility_lines)

        return (
            f'【運用調整届 送信通知】\n'
            f'区分: {app_type_jp}\n'
            f'催事名: {event_name}\n'
            f'申請者: {user_name}\n\n'
            f'施設:\n{facility_text}\n\n'
            f'上記内容で特ラ機構へメール送信しました。添付のPDFをご確認ください。'
        )
