import os
import subprocess
import gzip
import shutil
import logging
import tempfile
from datetime import datetime, timedelta
from django.conf import settings
from django.utils import timezone
from apps.accounts.models import DropboxToken
import dropbox
from dropbox.exceptions import ApiError

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

    class DictWrapper(object):
        def __init__(self, data):
            self._data = data

        def __getitem__(self, key):
            return self._data[key]

        def __setitem__(self, key, value):
            self._data[key] = value

        def pop(self, key):
            return self._data.pop(key)

        def __contains__(self, key):
            return key in self._data

        def __delitem__(self, key):
            del self._data[key]

    def get_token_model(self):
        return DropboxToken.objects.filter(service_name='backup').first()

    def is_authenticated(self):
        token = self.get_token_model()
        return token is not None and (token.access_token or token.refresh_token)

    def get_client(self):
        token = self.get_token_model()
        if not token:
            raise Exception('Dropbox token not found. Please authenticate first.')

        # トークンの期限切れチェックとリフレッシュ
        if token.is_access_token_expired():
            if token.has_valid_refresh_token():
                self.refresh_access_token(token)
            else:
                raise Exception('Access token expired and no refresh token available.')

        return dropbox.Dropbox(token.access_token)

    def refresh_access_token(self, token_model):
        """リフレッシュトークンを使用してアクセストークンを更新する"""
        try:
            dbx = dropbox.Dropbox(
                oauth2_refresh_token=token_model.refresh_token, app_key=self.app_key, app_secret=self.app_secret
            )
            res = dbx.refresh_access_token()

            token_model.access_token = res.access_token
            # 有効期限を更新 (秒を時間に変換)
            expires_in = getattr(res, 'expires_in', 14400)
            token_model.expires_at = timezone.now() + timedelta(seconds=expires_in)
            token_model.save()

            logger.info('Successfully refreshed Dropbox access token.')
            return True
        except Exception as e:
            logger.error(f'Failed to refresh Dropbox token: {e}')
            raise e

    def upload_file(self, local_path, remote_path):
        """ファイルをDropboxにアップロードする"""
        client = self.get_client()
        with open(local_path, 'rb') as f:
            try:
                client.files_upload(f.read(), remote_path, mode=dropbox.files.WriteMode.overwrite)
                logger.info(f'Uploaded {local_path} to Dropbox: {remote_path}')
                return True
            except ApiError as e:
                logger.error(f'Dropbox API Error during upload: {e}')
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

        # 一時ディレクトリを使い、一時的な my.cnf を作成してパスワード露出を避ける
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                # 一時 my.cnf
                cnf_path = os.path.join(tmpdir, 'my.cnf')
                with open(cnf_path, 'w') as cnf:
                    cnf.write('[client]\n')
                    if db_user:
                        cnf.write(f'user={db_user}\n')
                    if db_pass:
                        cnf.write(f'password={db_pass}\n')
                    if db_host:
                        cnf.write(f'host={db_host}\n')
                    if db_port:
                        cnf.write(f'port={db_port}\n')

                # 一時 SQL ファイル
                with tempfile.NamedTemporaryFile(delete=False, suffix='.sql') as sqlf:
                    sql_file = sqlf.name
                gz_file = f'{sql_file}.gz'

                # mysqldump 実行（--defaults-file を使用して認証情報を渡す）
                cmd = ['mysqldump', f'--defaults-file={cnf_path}', db_name]
                with open(sql_file, 'w') as f:
                    subprocess.run(cmd, stdout=f, check=True)

                # gzip 圧縮
                with open(sql_file, 'rb') as f_in:
                    with gzip.open(gz_file, 'wb') as f_out:
                        shutil.copyfileobj(f_in, f_out)

                # Dropboxへアップロード
                remote_dir = datetime.now().strftime('/backups/%Y/%m/%d')
                remote_path = f'{remote_dir}/db_backup_{timestamp}.sql.gz'

                self.upload_file(gz_file, remote_path)

                # 監査ログ記録
                log_action(action='DB_BACKUP', description=f'データベースバックアップ成功: {remote_path}')

                return {'success': True, 'path': remote_path, 'timestamp': timestamp}

        except Exception as e:
            logger.error(f'Database backup failed: {e}')
            log_action(action='DB_BACKUP_FAILED', description=f'データベースバックアップ失敗: {str(e)}')
            raise e
        finally:
            # 一時ファイルの削除（存在チェックして削除）
            try:
                if 'sql_file' in locals() and os.path.exists(sql_file):
                    os.remove(sql_file)
                if 'gz_file' in locals() and os.path.exists(gz_file):
                    os.remove(gz_file)
            except Exception:
                pass

    def get_auth_url(self, redirect_uri, session):
        """OAuth認証用のURLを生成する"""
        flow = dropbox.DropboxOAuth2Flow(
            consumer_key=self.app_key,
            consumer_secret=self.app_secret,
            redirect_uri=redirect_uri,
            session=self.DictWrapper(session),
            csrf_token_session_key='dropbox-auth-csrf-token',
            token_access_type='offline',
        )
        return flow.start()

    def finish_auth(self, query_params, session, redirect_uri):
        """認可コードからトークンを取得して保存する"""
        flow = dropbox.DropboxOAuth2Flow(
            consumer_key=self.app_key,
            consumer_secret=self.app_secret,
            redirect_uri=redirect_uri,
            session=self.DictWrapper(session),
            csrf_token_session_key='dropbox-auth-csrf-token',
                        token_access_type='offline',
                    )
        try:
                        result = flow.finish(query_params)
                        
                        # トークン情報を保存
                        token_model, created = DropboxToken.objects.get_or_create(service_name='backup')
                        token_model.access_token = result.access_token
                        token_model.refresh_token = result.refresh_token
                        token_model.token_type = 'Bearer'
                        token_model.account_id = result.account_id
                        # 有効期限の設定
                        expires_in = getattr(result, 'expires_in', 14400)
                        token_model.expires_at = timezone.now() + timedelta(seconds=expires_in)
            
                        # アカウント情報を取得
                        dbx = dropbox.Dropbox(result.access_token)
                        acc = dbx.users_get_current_account()
                        token_model.account_name = acc.name.display_name
            
                        token_model.save()
                        
                        from apps.accounts.utils import log_action
            
                        log_action(action='DROPBOX_AUTH', description=f'Dropbox連携成功: {token_model.account_name}')
                        
                        return token_model
        except Exception as e:
            logger.error(f'Dropbox auth failed: {e}', exc_info=True) # exc_info=True を追加してスタックトレースも出力
            raise e
