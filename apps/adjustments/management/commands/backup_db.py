import logging

from django.core.management.base import BaseCommand

from apps.adjustments.services.dropbox_service import DropboxError, DropboxService

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'データベースのバックアップを作成し、Dropboxへアップロードします（保持ポリシーを自動適用）。'

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE('データベースバックアップ処理を開始します...'))

        service = DropboxService()

        # 認証済みか確認
        if not service.is_authenticated():
            self.stdout.write(self.style.ERROR('Dropboxが認証されていません。Web画面から連携設定を行ってください。'))
            return

        try:
            result = service.create_db_backup()

            if result.get('success'):
                self.stdout.write(self.style.SUCCESS(
                    f'バックアップ成功: {result["path"]} (日時: {result["timestamp"]})'
                ))
            else:
                self.stdout.write(self.style.ERROR('バックアップ処理に失敗しました。'))

        except DropboxError as e:
            self.stdout.write(self.style.ERROR(f'Dropboxエラーが発生しました: {str(e)}'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'予期しないエラーが発生しました: {str(e)}'))
            logger.exception('Backup command failed')
