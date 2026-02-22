import time
import jwt
import requests
from django.conf import settings
import logging

logger = console_logger = logging.getLogger(__name__)

class LineBotService:
    """
    LINE WORKS Bot API Service for sending files to talk rooms.
    """
    
    def __init__(self):
        self.client_id = settings.LINE_WORKS_CLIENT_ID
        self.client_secret = settings.LINE_WORKS_CLIENT_SECRET
        self.service_account = settings.LINE_WORKS_SERVICE_ACCOUNT
        self.private_key = settings.LINE_WORKS_PRIVATE_KEY
        self.bot_id = settings.LINE_WORKS_BOT_ID
        self.access_token = None

    def _generate_jwt(self):
        """
        Generate JWT for Service Account authentication.
        """
        now = int(time.time())
        payload = {
            "iss": self.client_id,
            "sub": self.service_account,
            "iat": now,
            "exp": now + 3600  # 1 hour
        }
        headers = {
            "alg": "RS256",
            "typ": "JWT"
        }
        return jwt.encode(payload, self.private_key, algorithm="RS256", headers=headers)

    def _get_access_token(self):
        """
        Get access token using JWT.
        """
        assertion = self._generate_jwt()
        url = "https://auth.worksmobile.com/oauth2/v2.0/token"
        data = {
            "assertion": assertion,
            "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "scope": "bot"
        }
        headers = {
            "Content-Type": "application/x-www-form-urlencoded"
        }
        
        response = requests.post(url, data=data, headers=headers)
        if response.status_code == 200:
            self.access_token = response.json().get("access_token")
            return self.access_token
        else:
            logger.error(f"[LineBotService] Failed to get access token: {response.text}")
            return None

    def _get_upload_url(self, file_name):
        """
        Get upload URL and file ID for the bot.
        """
        if not self.access_token:
            if not self._get_access_token():
                return None, None

        url = f"https://www.worksapis.com/v1.0/bots/{self.bot_id}/attachments"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
        data = {
            "fileName": file_name
        }
        
        response = requests.post(url, json=data, headers=headers)
        if response.status_code == 200:
            res_data = response.json()
            return res_data.get("uploadUrl"), res_data.get("fileId")
        else:
            logger.error(f"[LineBotService] Failed to get upload URL: {response.text}")
            return None, None

    def _upload_file(self, upload_url, file_content, file_name):
        """
        Upload file binary to the given upload URL.
        """
        headers = {
            "Authorization": f"Bearer {self.access_token}"
        }
        files = {
            "FileData": (file_name, file_content, "application/pdf")
        }
        
        response = requests.post(upload_url, headers=headers, files=files)
        if response.status_code in [200, 201]:
            return True
        else:
            logger.error(f"[LineBotService] Failed to upload file content: {response.text}")
            return False

    def send_pdf(self, channel_id, file_content, file_name="adjustment_request.pdf"):
        """
        Public method to send a PDF file to a talk room.
        """
        if not self.bot_id or not channel_id:
            logger.warning("[LineBotService] Bot ID or Channel ID is missing.")
            return False

        # 1. Get Access Token (handled inside if needed)
        
        # 2. Get Upload URL
        upload_url, file_id = self._get_upload_url(file_name)
        if not upload_url or not file_id:
            return False

        # 3. Upload File
        if not self._upload_file(upload_url, file_content, file_name):
            return False

        # 4. Send Message
        url = f"https://www.worksapis.com/v1.0/bots/{self.bot_id}/channels/{channel_id}/messages"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
        data = {
            "content": {
                "type": "file",
                "fileId": file_id
            }
        }
        
        response = requests.post(url, json=data, headers=headers)
        if response.status_code == 201:
            logger.info(f"[LineBotService] Successfully sent PDF to channel {channel_id}")
            return True
        else:
            logger.error(f"[LineBotService] Failed to send file message: {response.text}")
            return False

    def send_flex_message(self, channel_id, flex_content, alt_text="Flex Message"):
        """
        Flex Messageをトークルームに送信する
        """
        if not self.bot_id or not channel_id:
            logger.warning("[LineBotService] Bot ID or Channel ID is missing.")
            return False
        
        if not self.access_token:
            if not self._get_access_token():
                return False

        url = f"https://www.worksapis.com/v1.0/bots/{self.bot_id}/channels/{channel_id}/messages"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
        data = {
            "content": {
                "type": "flex",
                "altText": alt_text,
                "contents": flex_content
            }
        }
        
        response = requests.post(url, json=data, headers=headers)
        if response.status_code == 201:
            logger.info(f"[LineBotService] Successfully sent Flex Message to channel {channel_id}")
            return True
        else:
            logger.error(f"[LineBotService] Failed to send Flex Message: {response.text}")
            return False
