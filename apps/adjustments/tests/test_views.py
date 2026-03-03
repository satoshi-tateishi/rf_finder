import json

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
