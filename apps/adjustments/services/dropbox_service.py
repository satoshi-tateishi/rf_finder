import fcntl
import gzip
import logging
import os
import shutil
import subprocess
import tempfile
from datetime import datetime, timedelta

import dropbox
from django.conf import settings
from django.utils import timezone
from dropbox.exceptions import ApiError

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


class DropboxService:
    def __init__(self):
        self.app_key = getattr(settings, 'DROPBOX_APP_KEY', '')
        self.app_secret = getattr(settings, 'DROPBOX_APP_SECRET', '')
        if not self.app_key or not self.app_secret:
            logger.warning('Dropbox APIキーが正しく設定されていません。')

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
        try:
            return DropboxToken.objects.get(service_name='backup')
        except DropboxToken.DoesNotExist:
            return None

    def is_authenticated(self):
        token = self.get_token_model()
        return token is not None and (token.access_token or token.refresh_token)

    def get_client(self):
        token = self.get_token_model()
        if not token:
            raise DropboxAuthError('Dropboxのトークンが見つかりません。先に認証を行ってください。')

        # トークンの期限切れチェックとリフレッシュ
        if token.is_access_token_expired():
            if token.has_valid_refresh_token():
                self.refresh_access_token(token)
            else:
                raise DropboxAuthError('アクセストークンが期限切れで、リフレッシュトークンも利用できません。')

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

            logger.info('Dropboxのアクセストークンを正常に更新しました。')
            return True
        except Exception as e:
            logger.error(f'Dropboxトークンの更新に失敗しました: {e}')
            raise DropboxAuthError(f'Dropboxトークンの更新に失敗しました: {str(e)}') from e

    def ensure_folder_exists(self, client, folder_path):
        """フォルダが存在することを確認し、なければ作成する"""
        if folder_path == '/' or not folder_path:
            return

        try:
            client.files_get_metadata(folder_path)
        except ApiError as e:
            # フォルダが見つからない場合のエラーをチェック
            if e.error.is_path() and e.error.get_path().is_not_found():
                try:
                    client.files_create_folder_v2(folder_path)
                    logger.info(f'Dropboxにフォルダを作成しました: {folder_path}')
                except ApiError as create_e:
                    # 同時実行などで既に作成されている場合は無視
                    logger.warning(f'フォルダ {folder_path} の作成に失敗しました (既に存在している可能性があります): {create_e}')
            else:
                raise e

    def upload_file(self, local_path, remote_path):
        """ファイルをDropboxにアップロードする (チャンクアップロード統一)"""
        client = self.get_client()
        file_size = os.path.getsize(local_path)

        # 親フォルダの存在確認
        remote_dir = os.path.dirname(remote_path)
        self.ensure_folder_exists(client, remote_dir)

        # メモリ使用量を抑えるため、サイズに関わらずチャンクアップロードを使用
        CHUNK_SIZE = 4 * 1024 * 1024  # 4MB 単位 (Dropbox推奨の最小単位に近い値)

        with open(local_path, 'rb') as f:
            try:
                if file_size <= CHUNK_SIZE:
                    # 小さいファイルは一括でアップロード
                    client.files_upload(f.read(), remote_path, mode=dropbox.files.WriteMode.overwrite)
                else:
                    # チャンクアップロード
                    logger.info(f'アップロードを開始します: {local_path} ({file_size} バイト)')
                    upload_session_start_result = client.files_upload_session_start(f.read(CHUNK_SIZE))
                    cursor = dropbox.files.UploadSessionCursor(
                        session_id=upload_session_start_result.session_id,
                        offset=f.tell()
                    )
                    commit = dropbox.files.CommitInfo(path=remote_path, mode=dropbox.files.WriteMode.overwrite)

                    while f.tell() < file_size:
                        if (file_size - f.tell()) <= CHUNK_SIZE:
                            client.files_upload_session_finish(f.read(CHUNK_SIZE), cursor, commit)
                        else:
                            client.files_upload_session_append_v2(f.read(CHUNK_SIZE), cursor)
                            cursor.offset = f.tell()

                logger.info(f'Dropboxにファイルをアップロードしました: {remote_path} ({file_size} バイト)')
                return True
            except ApiError as e:
                logger.error(f'アップロード中にDropbox APIエラーが発生しました: {e}')
                raise DropboxBackupError(f'アップロード中にDropbox APIエラーが発生しました: {str(e)}') from e
            except Exception as e:
                logger.error(f'アップロード中に予期しないエラーが発生しました: {e}')
                raise DropboxBackupError(f'アップロード中に予期しないエラーが発生しました: {str(e)}') from e

    def create_db_backup(self):
        """MySQLのバックアップを作成し、Dropboxにアップロードする"""
        from apps.accounts.utils import log_action

        # 二重起動防止のロックファイル
        lock_file_path = os.path.join(tempfile.gettempdir(), 'rf_finder_backup.lock')
        lock_file = open(lock_file_path, 'w')
        try:
            fcntl.flock(lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            logger.warning('バックアップ処理が既に実行中のため、スキップします。')
            return {'success': False, 'message': 'Already running'}

        try:
            # データベース設定の取得 (DATABASES['default'])
            db_config = settings.DATABASES['default']
            db_name = db_config['NAME']
            db_user = db_config['USER']
            db_pass = db_config['PASSWORD']
            db_host = db_config['HOST']
            db_port = db_config.get('PORT', '3306')

            # 日本時間 (Asia/Tokyo) に変換
            now = timezone.localtime(timezone.now())
            timestamp = now.strftime('%Y%m%d_%H%M%S')

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

                    # パーミッションを 600 (所有者のみ読み書き可能) に設定
                    os.chmod(cnf_path, 0o600)

                    # 一時 SQL ファイル
                    with tempfile.NamedTemporaryFile(delete=False, suffix='.sql') as sqlf:
                        sql_file = sqlf.name
                    gz_file = f'{sql_file}.gz'

                    # mysqldump 実行（--defaults-file を使用して認証情報を渡す）
                    # 注意: --skip-ssl はDockerコンテナ間通信の証明書エラー回避用
                    cmd = [
                        'mysqldump',
                        f'--defaults-file={cnf_path}',
                        '--single-transaction',
                        '--quick',
                        '--routines',
                        '--events',
                        '--triggers',
                        '--skip-ssl',
                        db_name
                    ]

                    try:
                        with open(sql_file, 'w') as f:
                            subprocess.run(cmd, stdout=f, check=True, stderr=subprocess.PIPE)
                    except subprocess.CalledProcessError as e:
                        # stderr から機密情報をマスクする
                        err_msg = e.stderr.decode('utf-8', errors='ignore')
                        if db_pass:
                            err_msg = err_msg.replace(db_pass, '********')
                        logger.error(f'mysqldump実行エラー: {err_msg}')
                        raise DropboxBackupError(f'データベースのダンプ作成に失敗しました: {err_msg}') from e

                    # gzip 圧縮
                    with open(sql_file, 'rb') as f_in:
                        with gzip.open(gz_file, 'wb') as f_out:
                            shutil.copyfileobj(f_in, f_out)

                    # Dropboxへアップロード
                    remote_dir = now.strftime('/backups/%Y/%m/%d')
                    remote_path = f'{remote_dir}/db_backup_{timestamp}.sql.gz'

                    self.upload_file(gz_file, remote_path)

                    # 監査ログ記録
                    log_action(action='DB_BACKUP', description=f'データベースバックアップ成功: {remote_path}')

                    # 古いバックアップの削除 (保持ポリシー: 最新5件, 過去3ヶ月の月次アーカイブを保持)
                    try:
                        self.clean_old_backups()
                    except Exception as ce:
                        logger.warning(f'古いバックアップの削除中にエラーが発生しました (バックアップ自体は成功しています): {ce}')

                    return {'success': True, 'path': remote_path, 'timestamp': timestamp}

            except Exception as e:
                # エラーメッセージから機密情報をマスク
                error_str = str(e)
                if db_pass:
                    error_str = error_str.replace(db_pass, '********')

                logger.error(f'データベースバックアップ失敗: {error_str}')
                log_action(action='DB_BACKUP_FAILED', description=f'データベースバックアップ失敗: {error_str}')
                raise DropboxBackupError(f'データベースバックアップ失敗: {error_str}') from e
            finally:
                # 一時ファイルの削除
                try:
                    if 'sql_file' in locals() and os.path.exists(sql_file):
                        os.remove(sql_file)
                    if 'gz_file' in locals() and os.path.exists(gz_file):
                        os.remove(gz_file)
                except Exception:
                    pass
        finally:
            fcntl.flock(lock_file, fcntl.LOCK_UN)
            lock_file.close()

    def list_backups(self, limit=30):
        """Dropbox上のバックアップファイル一覧を取得する"""
        client = self.get_client()
        backups = []

        try:
            # /backups 以下の .sql.gz ファイルを探す
            result = client.files_search_v2(
                query='.sql.gz',
                options=dropbox.files.SearchOptions(
                    path='/backups',
                    max_results=limit,
                    file_extensions=['gz']
                )
            )

            for match in result.matches:
                metadata = match.metadata.get_metadata()
                if isinstance(metadata, dropbox.files.FileMetadata):
                    # server_modified が naive の場合は UTC として aware に変換
                    server_modified = metadata.server_modified
                    if timezone.is_naive(server_modified):
                        server_modified = timezone.make_aware(server_modified, timezone.utc)

                    dt_local = timezone.localtime(server_modified)
                    backups.append({
                        'name': metadata.name,
                        'path': metadata.path_display,
                        'size': metadata.size,
                        'server_modified': dt_local.strftime('%Y-%m-%d %H:%M:%S')
                    })

            # 日付の新しい順にソート
            backups.sort(key=lambda x: x['server_modified'], reverse=True)
            return backups
        except ApiError as e:
            logger.error(f'バックアップ一覧の取得に失敗しました: {e}')
            return []

    def download_file(self, remote_path, local_path):
        """Dropboxからファイルをダウンロードする"""
        client = self.get_client()
        try:
            client.files_download_to_file(local_path, remote_path)
            logger.info(f'Dropboxからファイルをダウンロードしました: {remote_path}')
            return True
        except ApiError as e:
            logger.error(f'ダウンロード中にDropbox APIエラーが発生しました: {e}')
            raise DropboxBackupError(f'ファイルのダウンロードに失敗しました: {str(e)}') from e

    def restore_db_from_backup(self, remote_path, confirm=False):
        """指定されたバックアップファイルからデータベースを復元する"""
        if not confirm:
            raise DropboxBackupError('復元を実行するには明示的な確認が必要です。')

        from apps.accounts.utils import log_action

        # 二重起動防止
        lock_file_path = os.path.join(tempfile.gettempdir(), 'rf_finder_restore.lock')
        lock_file = open(lock_file_path, 'w')
        try:
            fcntl.flock(lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as e:
            raise DropboxBackupError('復元処理またはバックアップ処理が既に実行中です。') from e

        # データベース設定の取得
        db_config = settings.DATABASES['default']
        db_name = db_config['NAME']
        db_user = db_config['USER']
        db_pass = db_config['PASSWORD']
        db_host = db_config['HOST']
        db_port = db_config.get('PORT', '3306')

        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                # 1. ファイルをダウンロード
                gz_file = os.path.join(tmpdir, 'backup.sql.gz')
                sql_file = os.path.join(tmpdir, 'backup.sql')
                self.download_file(remote_path, gz_file)

                # 2. 解凍 (gzip)
                logger.info(f'バックアップファイルを解凍しています: {gz_file}')
                with gzip.open(gz_file, 'rb') as f_in:
                    with open(sql_file, 'wb') as f_out:
                        shutil.copyfileobj(f_in, f_out)

                # 3. MySQL設定ファイルの作成 (認証用)
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
                os.chmod(cnf_path, 0o600)

                # 4. mysql コマンドでインポート (バイナリモードで読み込み)
                cmd = [
                    'mysql',
                    f'--defaults-file={cnf_path}',
                    '--skip-ssl',
                    db_name
                ]

                logger.info(f'データベースのリストアを実行しています: {db_name}')
                try:
                    with open(sql_file, 'rb') as f:
                        subprocess.run(cmd, stdin=f, check=True, stderr=subprocess.PIPE)
                except subprocess.CalledProcessError as e:
                    err_msg = e.stderr.decode('utf-8', errors='ignore')
                    if db_pass:
                        err_msg = err_msg.replace(db_pass, '********')
                    logger.error(f'mysql実行エラー: {err_msg}')
                    raise DropboxBackupError(f'データベースのリストアに失敗しました: {err_msg}') from e

                # 5. マイグレーションの実行 (スキーマ不整合の解消)
                logger.info('スキーマを最新の状態に更新するためにマイグレーションを実行しています...')
                try:
                    subprocess.run(['python', 'manage.py', 'migrate', '--noinput'], check=True, stderr=subprocess.PIPE)
                except subprocess.CalledProcessError as e:
                    err_msg = e.stderr.decode('utf-8', errors='ignore')
                    logger.error(f'リストア後のマイグレーションに失敗しました: {err_msg}')
                    # マイグレーション失敗は重大だが、データ自体は入っている可能性があるため警告に留めるか検討
                    # ここではエラーとして扱い、ログに記録する
                    raise DropboxBackupError(f'リストア後のマイグレーションに失敗しました: {err_msg}') from e

                # 監査ログ記録
                log_action(action='DB_RESTORE', description=f'データベース復元成功: {remote_path}')
                logger.info(f'データベースの復元とマイグレーションが完了しました: {remote_path}')

                return {'success': True, 'path': remote_path}

        except Exception as e:
            error_str = str(e)
            if db_pass:
                error_str = error_str.replace(db_pass, '********')
            logger.error(f'復元処理に失敗しました: {error_str}')
            log_action(action='DB_RESTORE_FAILED', description=f'データベース復元失敗: {error_str}')
            raise DropboxBackupError(f'復元処理に失敗しました: {error_str}') from e
        finally:
            fcntl.flock(lock_file, fcntl.LOCK_UN)
            lock_file.close()
    def clean_old_backups(self, keep_latest=5, keep_monthly_months=3):
        """保持ポリシーに基づき、古いバックアップを削除する"""
        client = self.get_client()
        logger.info(f'保持ポリシーの適用を開始します (最新{keep_latest}件, 月次アーカイブ{keep_monthly_months}ヶ月)。')

        try:
            # 1. 全てのバックアップファイルを再帰的に取得
            files = []

            # /backups ディレクトリ以下の全ファイルをリストアップ
            res = client.files_list_folder('/backups', recursive=True)

            def process_entries(entries):
                for entry in entries:
                    if isinstance(entry, dropbox.files.FileMetadata) and entry.name.endswith('.sql.gz'):
                        try:
                            # ファイル名から日時を抽出
                            date_str = entry.name.replace('db_backup_', '').replace('.sql.gz', '')
                            # naive datetime としてパースした後、timezone-aware (JST) に変換
                            naive_dt = datetime.strptime(date_str, '%Y%m%d_%H%M%S')
                            dt = timezone.make_aware(naive_dt, timezone.get_current_timezone())

                            files.append({
                                'path': entry.path_lower,
                                'name': entry.name,
                                'datetime': dt,
                                'month_key': dt.strftime('%Y-%m') # 月次判定用
                            })
                        except (ValueError, IndexError):
                            continue

            process_entries(res.entries)
            while res.has_more:
                res = client.files_list_folder_continue(res.cursor)
                process_entries(res.entries)

            if not files:
                logger.info('削除対象のバックアップファイルは見つかりませんでした。')
                return 0

            # 2. 日時で降順ソート
            files.sort(key=lambda x: x['datetime'], reverse=True)

            # 3. 保護対象の選定
            keep_paths = set()

            # (A) 最新の N 件を保護
            for i in range(min(len(files), keep_latest)):
                keep_paths.add(files[i]['path'])

            # (B) 月次アーカイブ（過去 M ヶ月の各月の最終バックアップ）を保護
            now = timezone.localtime(timezone.now())
            monthly_archives = {}

            for file in files:
                m_key = file['month_key']
                if m_key not in monthly_archives:
                    monthly_archives[m_key] = file

            # 現在の月を除外した月次アーカイブから、過去 N ヶ月分を特定
            current_month = now.strftime('%Y-%m')
            sorted_months = sorted([m for m in monthly_archives.keys() if m != current_month], reverse=True)

            added_months = 0
            for m_key in sorted_months:
                keep_paths.add(monthly_archives[m_key]['path'])
                added_months += 1
                if added_months >= keep_monthly_months:
                    break

            # 4. 削除の実行
            delete_count = 0
            for file in files:
                if file['path'] not in keep_paths:
                    try:
                        client.files_delete_v2(file['path'])
                        logger.info(f'古いバックアップを削除しました: {file["name"]}')
                        delete_count += 1
                    except ApiError as e:
                        logger.error(f'ファイルの削除に失敗しました ({file["path"]}): {e}')

            logger.info(f'保持ポリシーの適用を完了しました。保護: {len(keep_paths)}件, 削除: {delete_count}件。')
            return delete_count

        except ApiError as e:
            if e.error.is_path() and e.error.get_path().is_not_found():
                logger.info('バックアップフォルダが存在しないため、削除処理をスキップします。')
                return 0
            raise DropboxBackupError(f'保持ポリシー適用中にDropboxエラーが発生しました: {str(e)}') from e
        except Exception as e:
            logger.error(f'保持ポリシー適用中に予期しないエラーが発生しました: {e}')
            raise DropboxBackupError(f'保持ポリシー適用中にエラーが発生しました: {str(e)}') from e

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

            logger.info(f'Dropboxの認証が完了しました: {token_model.account_name}')
            return token_model
        except Exception as e:
            logger.error(f'Dropboxの認証に失敗しました: {e}', exc_info=True)
            raise DropboxAuthError(f'Dropboxの認証に失敗しました: {str(e)}') from e
