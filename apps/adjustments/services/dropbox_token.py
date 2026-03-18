import logging
from datetime import timedelta

import dropbox
from django.conf import settings
from django.utils import timezone

from apps.accounts.models import DropboxToken

logger = logging.getLogger(__name__)


class DropboxError(Exception):
    """Dropboxサービスに関連する基底例外"""

    pass


class DropboxAuthError(DropboxError):
    """認証に関連する例外"""

    pass


class DropboxBackupError(DropboxError):
    """バックアップ実行に関連する例外"""

    pass


class DropboxTokenManager:
    """Dropbox OAuth トークンの取得・更新・認証フローを担当するクラス。"""

    def __init__(self):
        self.app_key = getattr(settings, 'DROPBOX_APP_KEY', '')
        self.app_secret = getattr(settings, 'DROPBOX_APP_SECRET', '')
        if not self.app_key or not self.app_secret:
            logger.warning('Dropbox APIキーが正しく設定されていません。')

    class DictWrapper(object):
        """DropboxOAuth2Flow が要求するセッション互換オブジェクト。"""

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
        """DBからDropboxトークンを取得する。存在しない場合は None を返す。"""
        try:
            return DropboxToken.objects.get(service_name='backup')
        except DropboxToken.DoesNotExist:
            return None

    def is_authenticated(self) -> bool:
        """有効なトークンが存在するか確認する。"""
        token = self.get_token_model()
        return token is not None and bool(token.access_token or token.refresh_token)

    def get_client(self) -> dropbox.Dropbox:
        """有効な Dropbox クライアントを返す。必要に応じてトークンをリフレッシュする。"""
        token_model = self.get_token_model()
        if not token_model:
            raise DropboxAuthError('Dropboxのトークンが見つかりません。先に認証を行ってください。')

        logger.debug('[DropboxTokenManager] Check token - Now: %s, Expires: %s', timezone.now(), token_model.expires_at)

        if token_model.is_access_token_expired():
            if token_model.has_valid_refresh_token():
                try:
                    logger.info('アクセストークンの期限が近いため、リフレッシュを実行します。')
                    temp_dbx = dropbox.Dropbox(
                        oauth2_refresh_token=token_model.refresh_token,
                        app_key=self.app_key,
                        app_secret=self.app_secret,
                    )
                    res = temp_dbx.refresh_access_token()
                    token_model.access_token = res.access_token
                    expires_in = getattr(res, 'expires_in', 14400)
                    token_model.expires_at = timezone.now() + timedelta(seconds=expires_in)
                    token_model.save()
                    logger.info('Dropboxのアクセストークンを正常に更新して保存しました。')
                except Exception as e:
                    logger.error('Dropboxトークンのリフレッシュに失敗しました: %s', e)
                    raise DropboxAuthError(f'Dropboxの再連携が必要です: {str(e)}') from e
            else:
                logger.warning('アクセストークンが期限切れですが、リフレッシュトークンがありません。')
                raise DropboxAuthError('Dropboxの再連携が必要です。')

        return dropbox.Dropbox(
            oauth2_access_token=token_model.access_token,
            oauth2_refresh_token=token_model.refresh_token,
            app_key=self.app_key,
            app_secret=self.app_secret,
        )

    def get_auth_url(self, redirect_uri: str, session) -> str:
        """OAuth認証用のURLを生成する。"""
        flow = dropbox.DropboxOAuth2Flow(
            consumer_key=self.app_key,
            consumer_secret=self.app_secret,
            redirect_uri=redirect_uri,
            session=self.DictWrapper(session),
            csrf_token_session_key='dropbox-auth-csrf-token',
            token_access_type='offline',
        )
        return flow.start()

    def finish_auth(self, query_params, session, redirect_uri: str):
        """認可コードからトークンを取得して保存する。"""
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

            token_model, _ = DropboxToken.objects.get_or_create(service_name='backup')
            token_model.access_token = result.access_token
            token_model.refresh_token = result.refresh_token
            token_model.token_type = 'Bearer'
            token_model.account_id = result.account_id
            expires_in = getattr(result, 'expires_in', 14400)
            token_model.expires_at = timezone.now() + timedelta(seconds=expires_in)

            dbx = dropbox.Dropbox(result.access_token)
            acc = dbx.users_get_current_account()
            token_model.account_name = acc.name.display_name
            token_model.save()

            from apps.accounts.utils import log_action

            log_action(action='DROPBOX_AUTH', description=f'Dropbox連携成功: {token_model.account_name}')
            logger.info('Dropboxの認証が完了しました: %s', token_model.account_name)
            return token_model
        except Exception as e:
            logger.exception('Dropboxの認証に失敗しました: %s', e)
            raise DropboxAuthError(f'Dropboxの認証に失敗しました: {str(e)}') from e
