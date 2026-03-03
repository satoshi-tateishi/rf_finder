from datetime import timedelta

from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.db import IntegrityError
from django.test import RequestFactory, TestCase
from django.urls import reverse
from django.utils import timezone

from .models import AuditLog, DropboxToken, UserProfile
from .utils import katakana_to_hiragana, log_action, normalize_phonetic


class AuditLogTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='password')
        self.factory = RequestFactory()

    def test_log_action_with_user(self):
        log = log_action(user=self.user, action='TEST_ACTION', description='Test Description')
        self.assertEqual(AuditLog.objects.count(), 1)
        self.assertEqual(log.user, self.user)
        self.assertEqual(log.action, 'TEST_ACTION')
        self.assertEqual(log.description, 'Test Description')

    def test_log_action_with_request(self):
        request = self.factory.get('/')
        request.user = self.user
        log = log_action(action='REQUEST_ACTION', description='Request Description', request=request)
        self.assertEqual(AuditLog.objects.count(), 1)
        self.assertEqual(log.user, self.user)
        self.assertEqual(log.action, 'REQUEST_ACTION')
        # Check IP address (default for RequestFactory is 127.0.0.1)
        self.assertEqual(log.ip_address, '127.0.0.1')


class UserProfileTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='profileuser', password='password')

    def test_full_name_property(self):
        """姓名が正しく結合されること"""
        self.user.profile.family_name = '山田'
        self.user.profile.given_name = '太郎'
        self.user.profile.save()
        self.assertEqual(self.user.profile.full_name, '山田 太郎')

    def test_full_name_empty_falls_back_to_first_name(self):
        """姓名が空の場合、User.first_name にフォールバックすること"""
        self.user.first_name = '太郎'
        self.user.save()
        self.user.profile.family_name = ''
        self.user.profile.given_name = ''
        self.user.profile.save()
        self.assertEqual(self.user.profile.full_name, '太郎')

    def test_full_kana_property(self):
        """ふりがなが正しく結合されること"""
        self.user.profile.phonetic_family_name = 'やまだ'
        self.user.profile.phonetic_given_name = 'たろう'
        self.user.profile.save()
        self.assertEqual(self.user.profile.full_kana, 'やまだ たろう')

    def test_admin_role_syncs_is_staff_and_superuser(self):
        """admin ロールを設定すると is_staff と is_superuser が True になること"""
        self.user.profile.role = UserProfile.Role.ADMIN
        self.user.profile.save()
        self.user.refresh_from_db()
        self.assertTrue(self.user.is_staff)
        self.assertTrue(self.user.is_superuser)

    def test_non_admin_role_removes_staff_permissions(self):
        """admin から editor に変更すると is_staff と is_superuser が False になること"""
        # まず admin にする
        self.user.is_staff = True
        self.user.is_superuser = True
        self.user.save()
        # editor に変更
        self.user.profile.role = UserProfile.Role.EDITOR
        self.user.profile.save()
        self.user.refresh_from_db()
        self.assertFalse(self.user.is_staff)
        self.assertFalse(self.user.is_superuser)

    def test_portal_uuid_unique_constraint(self):
        """portal_uuid はユニーク制約があること"""
        self.user.profile.portal_uuid = 'unique-uuid-001'
        self.user.profile.save()

        other_user = User.objects.create_user(username='other', password='password')
        other_user.profile.portal_uuid = 'unique-uuid-001'
        with self.assertRaises(IntegrityError):
            other_user.profile.save()


class DropboxTokenTest(TestCase):
    def _make_token(self, expires_at=None, refresh_token=''):
        return DropboxToken.objects.create(
            access_token='dummy_access',
            refresh_token=refresh_token,
            expires_at=expires_at,
        )

    def test_expired_when_no_expires_at(self):
        """`expires_at` が None の場合は期限切れと判定すること"""
        token = self._make_token(expires_at=None)
        self.assertTrue(token.is_access_token_expired())

    def test_not_expired_when_valid(self):
        """十分な有効期限がある場合は期限切れと判定しないこと"""
        token = self._make_token(expires_at=timezone.now() + timedelta(hours=1))
        self.assertFalse(token.is_access_token_expired())

    def test_expired_within_buffer(self):
        """有効期限まで5分未満の場合は期限切れと判定すること（5分バッファ）"""
        token = self._make_token(expires_at=timezone.now() + timedelta(minutes=3))
        self.assertTrue(token.is_access_token_expired())

    def test_has_valid_refresh_token(self):
        """リフレッシュトークンがある場合は True を返すこと"""
        token = self._make_token(refresh_token='valid_refresh_token')
        self.assertTrue(token.has_valid_refresh_token())

    def test_no_refresh_token(self):
        """リフレッシュトークンが空の場合は False を返すこと"""
        token = self._make_token(refresh_token='')
        self.assertFalse(token.has_valid_refresh_token())


class AccountUtilityTest(TestCase):
    def test_katakana_to_hiragana(self):
        """カタカナがひらがなに変換されること"""
        self.assertEqual(katakana_to_hiragana('アイウエオ'), 'あいうえお')

    def test_katakana_to_hiragana_keeps_hiragana(self):
        """ひらがなはそのまま返ること"""
        self.assertEqual(katakana_to_hiragana('あいうえお'), 'あいうえお')

    def test_katakana_to_hiragana_empty(self):
        """空文字列を渡した場合は空文字列を返すこと"""
        self.assertEqual(katakana_to_hiragana(''), '')

    def test_normalize_phonetic_nfkc_and_katakana(self):
        """全角カタカナが NFKC 正規化後にひらがなに変換されること"""
        # NFKC 正規化により全角スペース(U+3000)→半角スペース(U+0020)、全角カタカナ→ひらがな
        self.assertEqual(normalize_phonetic('ヤマダ　タロウ'), 'やまだ たろう')

    def test_normalize_phonetic_empty(self):
        """空文字列を渡した場合は空文字列を返すこと"""
        self.assertEqual(normalize_phonetic(''), '')


class AuditLogWithObjectTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='loguser', password='password')
        self.factory = RequestFactory()

    def test_log_action_with_obj(self):
        """obj を渡した場合、GenericForeignKey が正しくセットされること"""
        log = log_action(user=self.user, action='TEST', description='with obj', obj=self.user)
        expected_ct = ContentType.objects.get_for_model(self.user)
        self.assertEqual(log.content_type, expected_ct)
        self.assertEqual(log.object_id, self.user.pk)

    def test_log_action_x_forwarded_for(self):
        """X-Forwarded-For ヘッダーがある場合、その IP が記録されること"""
        request = self.factory.get('/', HTTP_X_FORWARDED_FOR='203.0.113.1, 10.0.0.1')
        request.user = self.user
        log = log_action(action='FWD_TEST', description='forwarded ip', request=request)
        self.assertEqual(log.ip_address, '203.0.113.1')


class AccountsViewTest(TestCase):
    def setUp(self):
        self.admin_user = User.objects.create_user(username='admin', password='password')
        self.admin_user.profile.role = UserProfile.Role.ADMIN
        self.admin_user.profile.family_name = '管理'
        self.admin_user.profile.given_name = '者'
        self.admin_user.profile.save()

        self.general_user = User.objects.create_user(username='general', password='password')
        self.general_user.profile.role = UserProfile.Role.GENERAL
        self.general_user.profile.save()

    def test_get_my_profile_authenticated(self):
        """認証済みユーザーがプロフィールを取得できること"""
        self.client.force_login(self.admin_user)
        response = self.client.get(reverse('accounts:me'))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'success')
        self.assertEqual(data['data']['family_name'], '管理')
        self.assertEqual(data['data']['role'], 'admin')

    def test_get_my_profile_unauthenticated(self):
        """未認証の場合はログインページにリダイレクトされること"""
        response = self.client.get(reverse('accounts:me'))
        self.assertEqual(response.status_code, 302)

    def test_list_audit_logs_admin(self):
        """admin ユーザーは監査ログを取得できること"""
        log_action(user=self.admin_user, action='LOGIN', description='管理者ログイン')
        self.client.force_login(self.admin_user)
        response = self.client.get(reverse('accounts:list_audit_logs'))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'success')
        self.assertGreaterEqual(len(data['data']), 1)

    def test_list_audit_logs_non_admin_forbidden(self):
        """非 admin ユーザーは監査ログにアクセスできず 403 になること"""
        self.client.force_login(self.general_user)
        response = self.client.get(reverse('accounts:list_audit_logs'))
        self.assertEqual(response.status_code, 403)

    def test_list_audit_logs_filter_by_action(self):
        """`action` パラメータで監査ログをフィルタリングできること"""
        log_action(user=self.admin_user, action='LOGIN', description='ログイン')
        log_action(user=self.admin_user, action='PDF_EXPORT', description='PDF出力')
        self.client.force_login(self.admin_user)
        response = self.client.get(reverse('accounts:list_audit_logs'), {'action': 'LOGIN'})
        self.assertEqual(response.status_code, 200)
        data = response.json()['data']
        self.assertTrue(all(entry['action'] == 'LOGIN' for entry in data))
