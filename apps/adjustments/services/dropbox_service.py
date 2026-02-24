import os
import subprocess
import gzip
import shutil
import logging
from datetime import datetime
from django.conf import settings
from django.utils import timezone
from apps.accounts.models import DropboxToken
import dropbox
from dropbox.exceptions import AuthError, ApiError

logger = logging.getLogger(__name__)

class DropboxService:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(DropboxService, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self.app_key = getattr(settings, 'DROPBOX_APP_KEY', '')
        self.app_secret = getattr(settings, 'DROPBOX_APP_SECRET', '')
        self._initialized = True

    def get_token_model(self):
        return DropboxToken.objects.filter(service_name='backup').first()

    def is_authenticated(self):
        token = self.get_token_model()
        return token is not None and (token.access_token or token.refresh_token)

    def get_client(self):
        token = self.get_token_model()
        if not token:
            raise Exception("Dropbox token not found. Please authenticate first.")

        # トークンの期限切れチェックとリフレッシュ
        if token.is_access_token_expired():
            if token.has_valid_refresh_token():
                self.refresh_access_token(token)
            else:
                raise Exception("Access token expired and no refresh token available.")

        return dropbox.Dropbox(token.access_token)

    def refresh_access_token(self, token_model):
        """リフレッシュトークンを使用してアクセストークンを更新する"""
        try:
            dbx = dropbox.Dropbox(
                oauth2_refresh_token=token_model.refresh_token,
                app_key=self.app_key,
                app_secret=self.app_secret
            )
            res = dbx.refresh_access_token()
            
            token_model.access_token = res.access_token
            # 有効期限を更新 (秒を時間に変換)
            expires_in = getattr(res, 'expires_in', 14400)
            token_model.expires_at = timezone.now() + timezone.timedelta(seconds=expires_in)
            token_model.save()
            
            logger.info("Successfully refreshed Dropbox access token.")
            return True
        except Exception as e:
            logger.error(f"Failed to refresh Dropbox token: {e}")
            raise e

    def upload_file(self, local_path, remote_path):
        """ファイルをDropboxにアップロードする"""
        client = self.get_client()
        with open(local_path, "rb") as f:
            try:
                client.files_upload(f.read(), remote_path, mode=dropbox.files.WriteMode.overwrite)
                logger.info(f"Uploaded {local_path} to Dropbox: {remote_path}")
                return True
            except ApiError as e:
                logger.error(f"Dropbox API Error during upload: {e}")
                raise e

    def create_db_backup(self):
        """MySQLのバックアップを作成し、Dropboxにアップロードする"""
        from apps.accounts.utils import log_action
        
        # データベース設定の取得 (DATABASES['default'])
        db_config = settings.DATABASES['default']
        db_name = db_config['NAME']
        db_user = db_config['USER']
        db_pass = db_config['PASSWORD']
        db_host = db_config['HOST']
        db_port = db_config.get('PORT', '3306')

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        sql_file = f"/tmp/db_backup_{timestamp}.sql"
        gz_file = f"{sql_file}.gz"

        try:
            # 1. mysqldump実行
            cmd = [
                'mysqldump',
                f'--host={db_host}',
                f'--port={db_port}',
                f'--user={db_user}',
                f'--password={db_pass}',
                db_name
            ]
            
            with open(sql_file, 'w') as f:
                subprocess.run(cmd, stdout=f, check=True)

            # 2. gzip圧縮
            with open(sql_file, 'rb') as f_in:
                with gzip.open(gz_file, 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)

            # 3. Dropboxへアップロード
            remote_dir = datetime.now().strftime('/backups/%Y/%m/%d')
            remote_path = f"{remote_dir}/db_backup_{timestamp}.sql.gz"
            
            self.upload_file(gz_file, remote_path)

            # 4. 監査ログ記録
            log_action(action='DB_BACKUP', description=f'データベースバックアップ成功: {remote_path}')
            
            return {
                'success': True,
                'path': remote_path,
                'timestamp': timestamp
            }

        except Exception as e:
            logger.error(f"Database backup failed: {e}")
            log_action(action='DB_BACKUP_FAILED', description=f'データベースバックアップ失敗: {str(e)}')
            raise e
        finally:
            # 一時ファイルの削除
            if os.path.exists(sql_file):
                os.remove(sql_file)
            if os.path.exists(gz_file):
                os.remove(gz_file)

    def get_auth_url(self, redirect_uri):
        """OAuth認証用のURLを生成する"""
        # PKCEなどは使用せず、標準的なフロー（リフレッシュトークン要求あり）
        flow = dropbox.DropboxOAuth2FlowNoImplicit(
            self.app_key,
            self.app_secret,
            redirect_uri,
            'dropbox-auth-csrf-token', # セッションで管理すべきだが簡易化
            token_access_type='offline' # リフレッシュトークンを取得するために必須
        )
        return flow.start()

    def finish_auth(self, code, redirect_uri):
        """認可コードからトークンを取得して保存する"""
        flow = dropbox.DropboxOAuth2FlowNoImplicit(
            self.app_key,
            self.app_secret,
            redirect_uri,
            'dropbox-auth-csrf-token',
            token_access_type='offline'
        )
        try:
            result = flow.finish(code)
            
            # トークン情報を保存
            token_model, created = DropboxToken.objects.get_or_create(service_name='backup')
            token_model.access_token = result.access_token
            token_model.refresh_token = result.refresh_token
            token_model.token_type = 'Bearer'
            token_model.account_id = result.account_id
            # 有効期限の設定
            expires_in = getattr(result, 'expires_in', 14400)
            token_model.expires_at = timezone.now() + timezone.timedelta(seconds=expires_in)
            
            # アカウント情報を取得
            dbx = dropbox.Dropbox(result.access_token)
            acc = dbx.users_get_current_account()
            token_model.account_name = acc.name.display_name
            
            token_model.save()
            
            from apps.accounts.utils import log_action
            log_action(action='DROPBOX_AUTH', description=f'Dropbox連携成功: {token_model.account_name}')
            
            return token_model
        except Exception as e:
            logger.error(f"Dropbox auth failed: {e}")
            raise e
