import logging
import time

import jwt
import requests
from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)


class LineBotService:
    """
    LINE WORKS Bot API Service for sending files to talk rooms.
    """

    CACHE_KEY = 'line_works_access_token_v2'
    TOKEN_EXPIRY = 86400 - 300  # 24 hours - 5 minutes buffer

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        # Prevent re-initialization if the instance already exists
        if hasattr(self, '_initialized') and self._initialized:
            return

        self.client_id = settings.LINE_WORKS_CLIENT_ID
        self.client_secret = settings.LINE_WORKS_CLIENT_SECRET
        self.service_account = settings.LINE_WORKS_SERVICE_ACCOUNT
        self.private_key = settings.LINE_WORKS_PRIVATE_KEY
        self.bot_id = settings.LINE_WORKS_BOT_ID
        self._initialized = True

    def _generate_jwt(self):
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

    def _get_access_token(self):
        """
        Get access token using JWT or from cache.
        """
        token = cache.get(self.CACHE_KEY)
        if token:
            return token

        assertion = self._generate_jwt()
        url = 'https://auth.worksmobile.com/oauth2/v2.0/token'
        data = {
            'assertion': assertion,
            'grant_type': 'urn:ietf:params:oauth:grant-type:jwt-bearer',
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'scope': 'bot,user.read',
        }
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}

        try:
            response = requests.post(url, data=data, headers=headers, timeout=10)
            if response.status_code == 200:
                res_data = response.json()
                token = res_data.get('access_token')
                # Store in cache
                try:
                    expires_in = int(res_data.get('expires_in', self.TOKEN_EXPIRY))
                except (ValueError, TypeError):
                    expires_in = self.TOKEN_EXPIRY

                # Ensure we don't cache for longer than the actual expiry
                cache_time = min(expires_in - 60, self.TOKEN_EXPIRY)
                cache.set(self.CACHE_KEY, token, cache_time)
                return token
            else:
                logger.error(f'[LineBotService] Failed to get access token: {response.text}')
                return None
        except Exception as e:
            logger.error(f'[LineBotService] Error getting access token: {e}')
            return None

    def _get_upload_url(self, file_name):
        """
        Get upload URL and file ID for the bot.
        """
        access_token = self._get_access_token()
        if not access_token:
            return None, None

        url = f'https://www.worksapis.com/v1.0/bots/{self.bot_id}/attachments'
        headers = {'Authorization': f'Bearer {access_token}', 'Content-Type': 'application/json'}
        data = {'fileName': file_name}

        try:
            response = requests.post(url, json=data, headers=headers, timeout=10)
            if response.status_code == 200:
                res_data = response.json()
                return res_data.get('uploadUrl'), res_data.get('fileId')
            else:
                logger.error(f'[LineBotService] Failed to get upload URL: {response.text}')
                return None, None
        except Exception as e:
            logger.error(f'[LineBotService] Error getting upload URL: {e}')
            return None, None

    def _upload_file(self, upload_url, file_content, file_name):
        """
        Upload file binary to the given upload URL.
        """
        access_token = self._get_access_token()
        if not access_token:
            return False

        headers = {'Authorization': f'Bearer {access_token}'}
        files = {'FileData': (file_name, file_content, 'application/pdf')}

        try:
            response = requests.post(upload_url, headers=headers, files=files, timeout=30)
            if response.status_code in [200, 201]:
                return True
            else:
                logger.error(f'[LineBotService] Failed to upload file content: {response.text}')
                return False
        except Exception as e:
            logger.error(f'[LineBotService] Error uploading file: {e}')
            return False

    def send_pdf(self, channel_id, file_content, file_name='adjustment_request.pdf'):
        """
        Public method to send a PDF file to a talk room.
        """
        if not self.bot_id or not channel_id:
            logger.warning('[LineBotService] Bot ID or Channel ID is missing.')
            return False

        # 1. Get Access Token
        access_token = self._get_access_token()
        if not access_token:
            return False

        # 2. Get Upload URL
        upload_url, file_id = self._get_upload_url(file_name)
        if not upload_url or not file_id:
            return False

        # 3. Upload File
        if not self._upload_file(upload_url, file_content, file_name):
            return False

        # 4. Send Message
        url = f'https://www.worksapis.com/v1.0/bots/{self.bot_id}/channels/{channel_id}/messages'
        headers = {'Authorization': f'Bearer {access_token}', 'Content-Type': 'application/json'}
        data = {'content': {'type': 'file', 'fileId': file_id}}

        try:
            response = requests.post(url, json=data, headers=headers, timeout=10)
            if response.status_code == 201:
                logger.info(f'[LineBotService] Successfully sent PDF to channel {channel_id}')
                return True
            else:
                logger.error(f'[LineBotService] Failed to send file message: {response.text}')
                return False
        except Exception as e:
            logger.error(f'[LineBotService] Error sending PDF message: {e}')
            return False

    def send_flex_message(self, channel_id, flex_content, alt_text='Flex Message'):
        """
        Send Flex Message to talk room.
        """
        if not self.bot_id or not channel_id:
            logger.warning('[LineBotService] Bot ID or Channel ID is missing.')
            return False

        access_token = self._get_access_token()
        if not access_token:
            return False

        url = f'https://www.worksapis.com/v1.0/bots/{self.bot_id}/channels/{channel_id}/messages'
        headers = {'Authorization': f'Bearer {access_token}', 'Content-Type': 'application/json'}
        data = {'content': {'type': 'flex', 'altText': alt_text, 'contents': flex_content}}

        try:
            response = requests.post(url, json=data, headers=headers, timeout=10)
            if response.status_code == 201:
                logger.info(f'[LineBotService] Successfully sent Flex Message to channel {channel_id}')
                return True
            else:
                logger.error(f'[LineBotService] Failed to send Flex Message: {response.text}')
                return False
        except Exception as e:
            logger.error(f'[LineBotService] Error sending Flex Message: {e}')
            return False

    def send_text_message(self, channel_id, text):
        """
        Send simple text message to a talk room (group/channel).
        """
        if not self.bot_id or not channel_id:
            logger.warning('[LineBotService] Bot ID or Channel ID is missing.')
            return False

        access_token = self._get_access_token()
        if not access_token:
            return False

        url = f'https://www.worksapis.com/v1.0/bots/{self.bot_id}/channels/{channel_id}/messages'
        headers = {'Authorization': f'Bearer {access_token}', 'Content-Type': 'application/json'}
        data = {'content': {'type': 'text', 'text': text}}

        try:
            response = requests.post(url, json=data, headers=headers, timeout=10)
            if response.status_code == 201:
                logger.info(f'[LineBotService] Successfully sent text message to channel {channel_id}')
                return True
            else:
                logger.error(f'[LineBotService] Failed to send text message: {response.text}')
                return False
        except Exception as e:
            logger.error(f'[LineBotService] Error sending text message: {e}')
            return False

    def send_user_message(self, user_id, text):
        """
        Send simple text message to a specific user (1-on-1).
        """
        if not self.bot_id or not user_id:
            logger.warning('[LineBotService] Bot ID or User ID is missing.')
            return False

        access_token = self._get_access_token()
        if not access_token:
            return False

        url = f'https://www.worksapis.com/v1.0/bots/{self.bot_id}/users/{user_id}/messages'
        headers = {'Authorization': f'Bearer {access_token}', 'Content-Type': 'application/json'}
        data = {'content': {'type': 'text', 'text': text}}

        try:
            response = requests.post(url, json=data, headers=headers, timeout=10)
            if response.status_code == 201:
                logger.info(f'[LineBotService] Successfully sent text message to user {user_id}')
                return True
            else:
                logger.error(f'[LineBotService] Failed to send user message: {response.text}')
                return False
        except Exception as e:
            logger.error(f'[LineBotService] Error sending user message: {e}')
            return False

    def get_user_info(self, user_id):
        """
        Fetch user details from LINE WORKS Users API.
        """
        access_token = self._get_access_token()
        if not access_token:
            return None

        url = f'https://www.worksapis.com/v1.0/users/{user_id}'
        headers = {'Authorization': f'Bearer {access_token}'}

        try:
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f'[LineBotService] Failed to fetch user info for {user_id}: {response.text}')
                return None
        except Exception as e:
            logger.error(f'[LineBotService] Error fetching user info: {e}')
            return None

    def set_persistent_menu(self, woff_id):
        """
        トークルーム下部の固定メニュー（Persistent Menu）を設定する
        """
        if not self.bot_id:
            logger.warning('[LineBotService] Bot ID is missing.')
            return False

        access_token = self._get_access_token()
        if not access_token:
            return False

        url = f'https://www.worksapis.com/v1.0/bots/{self.bot_id}/persistentmenu'
        headers = {'Authorization': f'Bearer {access_token}', 'Content-Type': 'application/json'}
        # WOFFアプリのURLスキーム
        woff_url = f'https://woff.worksmobile.com/woff/{woff_id}'

        data = {'content': {'actions': [{'type': 'uri', 'label': 'RF Finder を開く', 'uri': woff_url}]}}

        try:
            response = requests.post(url, json=data, headers=headers, timeout=10)
            if response.status_code in [200, 201]:
                logger.info(f'[LineBotService] Successfully set persistent menu for bot {self.bot_id}')
                return True
            else:
                logger.error(f'[LineBotService] Failed to set persistent menu: {response.text}')
                return False
        except Exception as e:
            logger.error(f'[LineBotService] Error setting persistent menu: {e}')
            return False

    def delete_persistent_menu(self):
        """
        トークルーム下部の固定メニュー（Persistent Menu）を削除する
        """
        if not self.bot_id:
            logger.warning('[LineBotService] Bot ID is missing.')
            return False

        access_token = self._get_access_token()
        if not access_token:
            return False

        url = f'https://www.worksapis.com/v1.0/bots/{self.bot_id}/persistentmenu'
        headers = {'Authorization': f'Bearer {access_token}'}

        try:
            response = requests.delete(url, headers=headers, timeout=10)
            if response.status_code in [200, 201, 204]:
                logger.info(f'[LineBotService] Successfully deleted persistent menu for bot {self.bot_id}')
                return True
            else:
                logger.error(f'[LineBotService] Failed to delete persistent menu: {response.text}')
                return False
        except Exception as e:
            logger.error(f'[LineBotService] Error deleting persistent menu: {e}')
            return False

    def create_rich_menu(self, woff_id, label='RF Finder を起動'):
        """
        リッチメニューを登録し、richmenuId を返す
        """
        access_token = self._get_access_token()
        if not access_token:
            return None

        url = f'https://www.worksapis.com/v1.0/bots/{self.bot_id}/richmenus'
        headers = {'Authorization': f'Bearer {access_token}', 'Content-Type': 'application/json'}
        woff_url = f'https://woff.worksmobile.com/woff/{woff_id}'

        data = {
            'richmenuName': 'RF Finder Default Menu',
            'size': {'width': 2500, 'height': 843},
            'areas': [
                {
                    'bounds': {'x': 0, 'y': 0, 'width': 2500, 'height': 843},
                    'action': {'type': 'uri', 'label': label, 'uri': woff_url},
                }
            ],
        }

        try:
            response = requests.post(url, json=data, headers=headers, timeout=10)
            if response.status_code in [200, 201]:
                richmenu_id = response.json().get('richmenuId')
                logger.info(f'[LineBotService] Created rich menu: {richmenu_id}')
                return richmenu_id
            else:
                logger.error(f'[LineBotService] Failed to create rich menu: {response.text}')
                return None
        except Exception as e:
            logger.error(f'[LineBotService] Error creating rich menu: {e}')
            return None

    def upload_rich_menu_image(self, richmenu_id, file_id):
        """
        リッチメニューに画像を登録する（fileIdを指定）
        """
        access_token = self._get_access_token()
        if not access_token:
            return False

        url = f'https://www.worksapis.com/v1.0/bots/{self.bot_id}/richmenus/{richmenu_id}/image'
        headers = {'Authorization': f'Bearer {access_token}', 'Content-Type': 'application/json'}
        data = {'fileId': file_id}

        try:
            response = requests.post(url, json=data, headers=headers, timeout=10)
            if response.status_code in [200, 201, 204]:
                logger.info(f'[LineBotService] Registered rich menu image for {richmenu_id}')
                return True
            else:
                logger.error(f'[LineBotService] Failed to register rich menu image: {response.text}')
                return False
        except Exception as e:
            logger.error(f'[LineBotService] Error registering rich menu image: {e}')
            return False

    def set_default_rich_menu(self, richmenu_id):
        """
        リッチメニューをBotのデフォルトに設定する
        """
        access_token = self._get_access_token()
        if not access_token:
            return False

        url = f'https://www.worksapis.com/v1.0/bots/{self.bot_id}/richmenus/{richmenu_id}/set-default'
        headers = {'Authorization': f'Bearer {access_token}'}

        try:
            response = requests.post(url, headers=headers, timeout=10)
            if response.status_code in [200, 201, 204]:
                logger.info(f'[LineBotService] Set default rich menu to {richmenu_id}')
                return True
            else:
                logger.error(f'[LineBotService] Failed to set default rich menu: {response.text}')
                return False
        except Exception as e:
            logger.error(f'[LineBotService] Error setting default rich menu: {e}')
            return False

    def list_rich_menus(self):
        """
        登録されているリッチメニューの一覧を取得
        """
        access_token = self._get_access_token()
        if not access_token:
            return []

        url = f'https://www.worksapis.com/v1.0/bots/{self.bot_id}/richmenus'
        headers = {'Authorization': f'Bearer {access_token}'}

        try:
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                return response.json().get('richmenus', [])
            return []
        except Exception:
            return []

    def delete_rich_menu(self, richmenu_id):
        """
        リッチメニューを削除
        """
        access_token = self._get_access_token()
        if not access_token:
            return False

        url = f'https://www.worksapis.com/v1.0/bots/{self.bot_id}/richmenus/{richmenu_id}'
        headers = {'Authorization': f'Bearer {access_token}'}

        try:
            response = requests.delete(url, headers=headers, timeout=10)
            return response.status_code in [200, 201, 204]
        except Exception:
            return False

    def build_submission_notification_message(self, data):
        """
        運用調整届の送信通知メッセージ（テキスト）を構築する。
        """
        from apps.adjustments.constants import APP_TYPE_MAP

        app_type_jp = APP_TYPE_MAP.get(data.get('app_type'), '新規')
        event_name = data.get('event', {}).get('name', '無題の催事')
        user_name = data.get('user', {}).get('name', '不明')

        # 施設情報の整形
        facilities = data.get('facilities', [])
        facility_lines = []
        for i, f in enumerate(facilities):
            name = f.get('name', '不明')
            start = f.get('start_date', '').replace('-', '/')
            end = f.get('end_date', '').replace('-', '/')
            facility_lines.append(f'{i + 1}.{name}\n{start} - {end}')

        facility_text = '\n\n'.join(facility_lines)

        msg = (
            f'【運用調整届 送信通知】\n'
            f'区分: {app_type_jp}\n'
            f'催事名: {event_name}\n'
            f'申請者: {user_name}\n\n'
            f'施設:\n{facility_text}\n\n'
            f'上記内容で特ラ機構へメール送信しました。添付のPDFをご確認ください。'
        )
        return msg
