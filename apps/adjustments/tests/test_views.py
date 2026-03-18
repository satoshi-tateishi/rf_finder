import json
from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import UserProfile

from ..models import OperationAdjustment


class ListAdjustmentsTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='listuser', password='password')
        self.client.force_login(self.user)

        self.adj1 = OperationAdjustment.objects.create(
            user=self.user,
            app_type='new',
            user_name='山田太郎',
            event_name='春の公演',
            status='draft',
        )
        self.adj2 = OperationAdjustment.objects.create(
            user=self.user,
            app_type='change',
            user_name='鈴木花子',
            event_name='夏のイベント',
            status='submitted',
        )

    def test_unauthenticated_redirects(self):
        """未認証でアクセスするとログインページにリダイレクトされること"""
        self.client.logout()
        response = self.client.get(reverse('adjustments:list_adjustments'))
        self.assertEqual(response.status_code, 302)

    def test_authenticated_returns_list(self):
        """ログイン済みで調整届一覧が取得できること"""
        response = self.client.get(reverse('adjustments:list_adjustments'))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'success')
        self.assertEqual(len(data['data']), 2)

    def test_filter_by_event_name(self):
        """`event_name` パラメータで絞り込めること"""
        response = self.client.get(reverse('adjustments:list_adjustments'), {'event_name': '春'})
        self.assertEqual(response.status_code, 200)
        results = response.json()['data']
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['event_name'], '春の公演')

    def test_filter_by_user_name(self):
        """`user_name` パラメータで絞り込めること"""
        response = self.client.get(reverse('adjustments:list_adjustments'), {'user_name': '鈴木'})
        self.assertEqual(response.status_code, 200)
        results = response.json()['data']
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['event_name'], '夏のイベント')

    def test_filter_by_status_draft(self):
        """`status=draft` で下書きのみ絞り込めること"""
        response = self.client.get(reverse('adjustments:list_adjustments'), {'status': 'draft'})
        self.assertEqual(response.status_code, 200)
        results = response.json()['data']
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['status'], '下書き')

    def test_filter_by_status_submitted(self):
        """`status=submitted` で送信済みのみ絞り込めること"""
        response = self.client.get(reverse('adjustments:list_adjustments'), {'status': 'submitted'})
        self.assertEqual(response.status_code, 200)
        results = response.json()['data']
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['status'], '送信済み')

    def test_filter_by_invalid_status_returns_all(self):
        """不正な `status` 値は無視されて全件返ること"""
        response = self.client.get(reverse('adjustments:list_adjustments'), {'status': 'invalid'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()['data']), 2)

    def test_response_includes_parent_id(self):
        """一覧レスポンスに `parent_id` フィールドが含まれること"""
        child = OperationAdjustment.objects.create(
            user=self.user,
            app_type='change',
            user_name='子申請者',
            event_name='子申請',
            status='draft',
            parent=self.adj1,
        )
        response = self.client.get(reverse('adjustments:list_adjustments'), {'event_name': '子申請'})
        results = response.json()['data']
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['parent_id'], self.adj1.id)
        child.delete()

    def test_limit_respected_via_setting(self):
        """ADJUSTMENT_LIST_LIMIT 設定が一覧件数の上限として機能すること"""
        # 既存2件に加え3件追加して合計5件
        for i in range(3):
            OperationAdjustment.objects.create(
                user=self.user, app_type='new', user_name=f'追加{i}', event_name=f'追加催事{i}', status='draft'
            )

        with self.settings(ADJUSTMENT_LIST_LIMIT=3):
            response = self.client.get(reverse('adjustments:list_adjustments'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()['data']), 3)


class GetAdjustmentTest(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username='owner', password='password')
        self.other = User.objects.create_user(username='other', password='password')

        self.admin = User.objects.create_user(username='adminuser', password='password')
        self.admin.profile.role = UserProfile.Role.ADMIN
        self.admin.profile.save()

        self.adj = OperationAdjustment.objects.create(
            user=self.owner,
            app_type='new',
            user_name='所有者',
            event_name='オーナー催事',
            status='draft',
        )

    def test_owner_can_access(self):
        """作成者本人は調整届にアクセスできること"""
        self.client.force_login(self.owner)
        response = self.client.get(reverse('adjustments:get_adjustment', args=[self.adj.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['data']['event']['name'], 'オーナー催事')

    def test_other_user_gets_forbidden(self):
        """他ユーザーが別人の調整届にアクセスすると 403 になること"""
        self.client.force_login(self.other)
        response = self.client.get(reverse('adjustments:get_adjustment', args=[self.adj.pk]))
        self.assertEqual(response.status_code, 403)

    def test_admin_can_access_any(self):
        """admin ユーザーは他人の調整届にもアクセスできること"""
        self.client.force_login(self.admin)
        response = self.client.get(reverse('adjustments:get_adjustment', args=[self.adj.pk]))
        self.assertEqual(response.status_code, 200)

    def test_not_found(self):
        """存在しない ID にアクセスすると 404 になること"""
        self.client.force_login(self.owner)
        response = self.client.get(reverse('adjustments:get_adjustment', args=[99999]))
        self.assertEqual(response.status_code, 404)

    def test_response_includes_parent_id(self):
        """詳細レスポンスに `parent_id` フィールドが含まれること"""
        child = OperationAdjustment.objects.create(
            user=self.owner,
            app_type='change',
            user_name='子申請者',
            event_name='子催事',
            status='draft',
            parent=self.adj,
        )
        self.client.force_login(self.owner)
        response = self.client.get(reverse('adjustments:get_adjustment', args=[child.pk]))
        self.assertEqual(response.status_code, 200)
        data = response.json()['data']
        self.assertEqual(data['parent_id'], self.adj.id)
        child.delete()


class JsonApiViewDecoratorTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='decoratoruser', password='password')

    def test_unauthenticated_redirects(self):
        """未認証で @json_api_view エンドポイントにアクセスするとリダイレクトされること"""
        response = self.client.post(
            reverse('adjustments:save_adjustment'),
            data=json.dumps({}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 302)

    def test_get_method_rejected(self):
        """GET メソッドで @json_api_view エンドポイントにアクセスすると 405 になること"""
        self.client.force_login(self.user)
        response = self.client.get(reverse('adjustments:save_adjustment'))
        self.assertEqual(response.status_code, 405)


class ValidateAdjustmentLoggingTest(TestCase):
    """バリデーションエラーが print でなく logger で記録されること"""

    def setUp(self):
        self.user = User.objects.create_user(username='logtest', password='password')
        self.client.force_login(self.user)

    def test_validation_error_uses_logger_not_print(self):
        """バリデーションエラー発生時に logger.warning が呼ばれ、print は呼ばれないこと。
        validate=True のエンドポイント(preview_pdf)に不正データを送信して確認する。"""
        # facilities・mic_counts が空なのでバリデーション失敗する
        invalid_data = json.dumps({
            'app_type': 'new',
            'user': {'name': '使用者', 'kana': 'しようしゃ', 'tel': '090-0000-0000', 'email': 'u@example.com'},
            'event': {'name': '催事', 'comment': ''},
            'facilities': [],
            'mic_counts': {},
            'selected_channels': [],
        })
        with self.assertLogs('apps.adjustments.views', level='WARNING') as log_ctx:
            with patch('builtins.print') as mock_print:
                self.client.post(
                    reverse('adjustments:preview_pdf'),
                    data=invalid_data,
                    content_type='application/json',
                )
                mock_print.assert_not_called()
        self.assertTrue(any('Validation Error' in msg for msg in log_ctx.output))

    def test_preview_pdf_entry_uses_logger_not_print(self):
        """preview_pdf 呼び出し時に print が呼ばれないこと"""
        valid_data = json.dumps({
            'app_type': 'new',
            'user': {'name': '使用者', 'kana': 'しようしゃ', 'tel': '090-0000-0000', 'email': 'u@example.com'},
            'event': {'name': '催事', 'comment': ''},
            'facilities': [],
            'mic_counts': {},
            'selected_channels': [],
        })
        with patch('apps.adjustments.views.generate_adjustment_pdf') as mock_pdf:
            import io
            mock_pdf.return_value = io.BytesIO(b'%PDF-dummy')
            with patch('builtins.print') as mock_print:
                self.client.post(
                    reverse('adjustments:preview_pdf'),
                    data=valid_data,
                    content_type='application/json',
                )
                mock_print.assert_not_called()


class ListAdjustmentsQueryCountTest(TestCase):
    """list_adjustments のクエリ数が件数に比例して増加しないこと（N+1対策）"""

    def setUp(self):
        self.user = User.objects.create_user(username='querytest', password='password')
        self.client.force_login(self.user)

    def _create_adjustments(self, count):
        for i in range(count):
            OperationAdjustment.objects.create(
                user=self.user,
                app_type='new',
                user_name=f'ユーザー{i}',
                event_name=f'催事{i}',
                status='draft',
            )

    def test_query_count_does_not_grow_with_records(self):
        """2件と5件でクエリ数が同じであること（N+1クエリがないこと）"""
        from django.db import connection
        from django.test.utils import CaptureQueriesContext

        self._create_adjustments(2)
        url = reverse('adjustments:list_adjustments')

        with CaptureQueriesContext(connection) as ctx_2:
            self.client.get(url)
        count_2 = len(ctx_2.captured_queries)

        OperationAdjustment.objects.all().delete()
        self._create_adjustments(5)

        with CaptureQueriesContext(connection) as ctx_5:
            self.client.get(url)
        count_5 = len(ctx_5.captured_queries)

        self.assertEqual(
            count_2,
            count_5,
            f'N+1クエリの疑い: 2件={count_2}クエリ, 5件={count_5}クエリ',
        )
