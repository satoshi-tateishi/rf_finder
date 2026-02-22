import io
import os

from django.conf import settings
from django.core.management.base import BaseCommand
from PIL import Image, ImageDraw, ImageFont

from apps.adjustments.services import LineBotService


class Command(BaseCommand):
    help = 'LINE WORKS Bot の固定メニューまたはリッチメニューを設定し、RF Finder WOFFへのリンクを表示します。'

    def add_arguments(self, parser):
        parser.add_argument(
            '--rich-menu',
            action='store_true',
            help='リッチメニュー（画像メニュー）を設定します。',
        )
        parser.add_argument(
            '--clean',
            action='store_true',
            help='既存のリッチメニューをすべて削除してから設定します。',
        )
        parser.add_argument(
            '--delete',
            action='store_true',
            help='既存のメニュー（リッチメニューおよび固定メニュー）をすべて削除します。',
        )

    def handle(self, *args, **options):
        bot_service = LineBotService()

        if options['delete']:
            self.stdout.write('メニューの削除を実行中...')
            # リッチメニューの削除
            menus = bot_service.list_rich_menus()
            for m in menus:
                bot_service.delete_rich_menu(m['richmenu_id'] if 'richmenu_id' in m else m.get('richmenuId'))
                self.stdout.write(f'Deleted rich menu: {m.get("richmenuId")}')
            
            # 固定メニューの削除
            if bot_service.delete_persistent_menu():
                self.stdout.write(self.style.SUCCESS('固定メニューを削除しました。'))
            else:
                self.stderr.write(self.style.ERROR('固定メニューの削除に失敗しました。'))
            return

        woff_id = settings.WOFF_ID

        if options['rich_menu']:
            self.stdout.write('リッチメニュー（画像メニュー）を設定中...')
            
            # 1. 既存メニューの削除（オプション）
            if options['clean']:
                menus = bot_service.list_rich_menus()
                for m in menus:
                    bot_service.delete_rich_menu(m['richmenuId'])
                    self.stdout.write(f'Deleted old menu: {m["richmenuId"]}')

            # 2. メニュー画像の生成
            image_content = self.generate_menu_image()
            if not image_content:
                self.stderr.write(self.style.ERROR('画像の生成に失敗しました。'))
                return

            # 3. リッチメニューの登録
            richmenu_id = bot_service.create_rich_menu(woff_id)
            if not richmenu_id:
                self.stderr.write(self.style.ERROR('リッチメニューの登録に失敗しました。'))
                return

            # 4. 画像のアップロード (2段階プロセス)
            self.stdout.write('メニュー画像をアップロード中...')
            upload_url, file_id = bot_service._get_upload_url("menu.png")
            if not upload_url or not file_id:
                self.stderr.write(self.style.ERROR('アップロードURLの取得に失敗しました。'))
                return

            if not bot_service._upload_file(upload_url, image_content, "menu.png"):
                self.stderr.write(self.style.ERROR('画像のバイナリアップロードに失敗しました。'))
                return

            if not bot_service.upload_rich_menu_image(richmenu_id, file_id):
                self.stderr.write(self.style.ERROR('リッチメニューへの画像登録に失敗しました。'))
                return

            # 5. デフォルトメニューの設定
            if not bot_service.set_default_rich_menu(richmenu_id):
                self.stderr.write(self.style.ERROR('デフォルトメニューの設定に失敗しました。'))
                return

            self.stdout.write(self.style.SUCCESS(f'リッチメニューの設定が完了しました。ID: {richmenu_id}'))

        else:
            self.stdout.write(f'WOFF ID: {woff_id} を使用して固定メニューを設定中...')
            
            # リッチメニューが存在すると固定メニューを設定できないため、まず削除を試みる
            menus = bot_service.list_rich_menus()
            if menus:
                self.stdout.write(f'{len(menus)} 個の既存リッチメニューを削除します...')
                for m in menus:
                    bot_service.delete_rich_menu(m['richmenu_id'] if 'richmenu_id' in m else m.get('richmenuId'))
            
            success = bot_service.set_persistent_menu(woff_id)

            if success:
                self.stdout.write(self.style.SUCCESS('固定メニュー（RF Finder を開く）の設定に成功しました。トークルームの入力エリア横の「三」アイコンから確認してください。'))
            else:
                self.stderr.write(self.style.ERROR('固定メニューの設定に失敗しました。'))

    def generate_menu_image(self):
        """
        リッチメニュー用の画像を生成してバイナリを返す
        """
        width, height = 2500, 843
        background_color = (0, 195, 0)  # LINE WORKS Green
        text = "RF Finder を起動"
        
        # 画像作成
        img = Image.new('RGB', (width, height), color=background_color)
        draw = ImageDraw.Draw(img)
        
        # フォント設定
        font_path = os.path.join(settings.BASE_DIR, 'static/fonts/NotoSansJP-Regular.ttf')
        try:
            # 大きめのフォントサイズ
            font = ImageFont.truetype(font_path, 160)
        except Exception:
            self.stdout.write('Font not found, using default font.')
            font = ImageFont.load_default()

        # テキストを中央に配置
        left, top, right, bottom = draw.textbbox((0, 0), text, font=font)
        text_width = right - left
        text_height = bottom - top
        position = ((width - text_width) // 2, (height - text_height) // 2 - 40)
        
        draw.text(position, text, fill=(255, 255, 255), font=font)
        
        # アイコン（簡易）
        draw.rectangle([width // 2 - 400, height - 120, width // 2 + 400, height - 110], fill=(255, 255, 255))

        # バイナリに変換
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        return buffer.getvalue()
