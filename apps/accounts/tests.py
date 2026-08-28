from datetime import timedelta
from unittest.mock import MagicMock, patch

import jwt as pyjwt
from django.contrib.auth.models import AnonymousUser, User
from django.contrib.contenttypes.models import ContentType
from django.contrib.sessions.middleware import SessionMiddleware
from django.db import IntegrityError
from django.test import RequestFactory, TestCase
from django.urls import reverse
from django.utils import timezone

from .middleware import PortalJWTMiddleware
from .models import AuditLog, DropboxToken, UserProfile
from .utils import is_admin, katakana_to_hiragana, log_action, normalize_phonetic


class HealthcheckTest(TestCase):
    def test_healthcheckは認証なしで空の204を返す(self):
        response = self.client.get(reverse('healthcheck'))

        self.assertEqual(response.status_code, 204)
        self.assertEqual(response.content, b'')


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


class PortalJWTMiddlewareTest(TestCase):
    """PortalJWTMiddleware の動作テスト"""

    PORTAL_UUID = 'test-portal-uuid-001'
    EMAIL = 'testuser@example.com'
    PAYLOAD = {
        'sub': PORTAL_UUID,
        'email': EMAIL,
        'family_name': '山田',
        'given_name': '太郎',
        'phonetic_family_name': 'やまだ',
        'phonetic_given_name': 'たろう',
    }

    def setUp(self):
        self.factory = RequestFactory()
        self.mock_jwks_client = MagicMock()
        # ネットワーク呼び出しをしないようクラス変数にモックを注入
        PortalJWTMiddleware._jwks_client = self.mock_jwks_client
        self.middleware = PortalJWTMiddleware(lambda req: None)

    def tearDown(self):
        PortalJWTMiddleware._jwks_client = None

    def _make_request(self, with_jwt=True):
        """セッション付きリクエストを生成する"""
        request = self.factory.get('/')
        request.COOKIES = {'portal_jwt': 'fake.jwt.token'} if with_jwt else {}
        request.user = AnonymousUser()
        # login() が必要とするセッションをセットアップ
        SessionMiddleware(lambda req: None).process_request(request)
        request.session.save()
        return request

    def _run_with_payload(self, payload=None):
        """指定ペイロードを返すモックJWTでミドルウェアを実行する"""
        if payload is None:
            payload = self.PAYLOAD
        request = self._make_request()
        mock_key = MagicMock()
        self.mock_jwks_client.get_signing_key_from_jwt.return_value = mock_key
        with patch('apps.accounts.middleware.jwt.decode', return_value=payload):
            self.middleware(request)
        return request

    # ── スキップ系 ──────────────────────────────────────────────

    def test_no_cookie_skips_auth(self):
        """portal_jwt クッキーがない場合は認証を試みないこと"""
        request = self._make_request(with_jwt=False)
        self.middleware(request)
        self.assertFalse(request.user.is_authenticated)
        self.assertEqual(User.objects.count(), 0)

    def test_expired_jwt_skips_auth(self):
        """期限切れ JWT の場合は認証をスキップすること"""
        request = self._make_request()
        self.mock_jwks_client.get_signing_key_from_jwt.side_effect = pyjwt.ExpiredSignatureError
        self.middleware(request)
        self.assertFalse(request.user.is_authenticated)

    def test_invalid_jwt_skips_auth(self):
        """不正な JWT の場合は認証をスキップすること"""
        request = self._make_request()
        self.mock_jwks_client.get_signing_key_from_jwt.side_effect = pyjwt.InvalidTokenError('bad token')
        self.middleware(request)
        self.assertFalse(request.user.is_authenticated)

    def test_missing_sub_claim_skips_auth(self):
        """JWT に sub クレームがない場合は認証をスキップすること"""
        self._run_with_payload({'email': self.EMAIL})  # sub なし
        self.assertEqual(User.objects.count(), 0)

    def test_already_authenticated_skips_jwt(self):
        """認証済みユーザーのリクエストは JWT 処理をスキップすること"""
        existing = User.objects.create_user(username='already', password='x')
        request = self._make_request()
        request.user = existing
        self.middleware(request)
        # JWKS クライアントが呼ばれていないことを確認
        self.mock_jwks_client.get_signing_key_from_jwt.assert_not_called()

    def test_inactive_user_is_rejected(self):
        """is_active=False のユーザーはログインを拒否すること"""
        user = User.objects.create_user(username='inactive', email=self.EMAIL, password=None, is_active=False)
        user.profile.portal_uuid = self.PORTAL_UUID
        user.profile.save()
        request = self._run_with_payload()
        self.assertFalse(request.user.is_authenticated)

    # ── ユーザー照合・作成 ────────────────────────────────────────

    def test_existing_user_found_by_portal_uuid(self):
        """portal_uuid が一致する既存ユーザーで認証されること"""
        user = User.objects.create_user(username='byuuid', email=self.EMAIL, password=None)
        user.profile.portal_uuid = self.PORTAL_UUID
        user.profile.save()
        request = self._run_with_payload()
        self.assertEqual(request.user, user)

    def test_existing_user_found_by_email_links_portal_uuid(self):
        """portal_uuid 未設定のユーザーが email で見つかり、portal_uuid が紐付けられること"""
        user = User.objects.create_user(username='byemail', email=self.EMAIL, password=None)
        request = self._run_with_payload()
        self.assertEqual(request.user, user)
        user.profile.refresh_from_db()
        self.assertEqual(user.profile.portal_uuid, self.PORTAL_UUID)

    def test_new_user_created_when_email_not_found(self):
        """DB にメールが存在しない場合、新規ユーザーが自動作成されること"""
        self.assertEqual(User.objects.count(), 0)
        request = self._run_with_payload()
        self.assertEqual(User.objects.count(), 1)
        user = User.objects.get(email=self.EMAIL)
        self.assertTrue(request.user.is_authenticated)
        self.assertEqual(request.user, user)

    def test_new_user_has_unusable_password(self):
        """自動作成されたユーザーはパスワードなし（JWT 認証専用）であること"""
        self._run_with_payload()
        user = User.objects.get(email=self.EMAIL)
        self.assertFalse(user.has_usable_password())

    def test_new_user_profile_fields_saved_correctly(self):
        """自動作成されたユーザーのプロフィールに JWT ペイロードの情報が正しく保存されること"""
        self._run_with_payload()
        profile = UserProfile.objects.get(user__email=self.EMAIL)
        self.assertEqual(profile.portal_uuid, self.PORTAL_UUID)
        self.assertEqual(profile.family_name, '山田')
        self.assertEqual(profile.given_name, '太郎')
        self.assertEqual(profile.phonetic_family_name, 'やまだ')
        self.assertEqual(profile.phonetic_given_name, 'たろう')
        self.assertEqual(profile.email, self.EMAIL)

    def test_profile_fields_not_overwritten_after_login(self):
        """
        【リグレッション】login() が update_last_login を発火し
        user.save() → post_save → save_user_profile シグナルが連鎖しても
        portal_uuid やプロフィールが古いキャッシュで上書きされないこと。
        """
        self._run_with_payload()
        # DB から直接再取得して確認（キャッシュを使わない）
        profile = UserProfile.objects.get(user__email=self.EMAIL)
        self.assertEqual(profile.portal_uuid, self.PORTAL_UUID)
        self.assertEqual(profile.family_name, '山田')
        self.assertEqual(profile.given_name, '太郎')


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


class IsAdminHelperTest(TestCase):
    """is_admin() ヘルパー関数の動作テスト"""

    def setUp(self):
        self.admin = User.objects.create_user(username='isadmin_admin', password='password')
        self.admin.profile.role = UserProfile.Role.ADMIN
        self.admin.profile.save()

        self.general = User.objects.create_user(username='isadmin_general', password='password')
        self.general.profile.role = UserProfile.Role.GENERAL
        self.general.profile.save()

        self.editor = User.objects.create_user(username='isadmin_editor', password='password')
        self.editor.profile.role = UserProfile.Role.EDITOR
        self.editor.profile.save()

    def test_returns_true_for_admin(self):
        """admin ロールは True を返すこと"""
        self.assertTrue(is_admin(self.admin))

    def test_returns_false_for_general(self):
        """general ロールは False を返すこと"""
        self.assertFalse(is_admin(self.general))

    def test_returns_false_for_editor(self):
        """editor ロールは False を返すこと"""
        self.assertFalse(is_admin(self.editor))

    def test_returns_false_for_user_without_profile(self):
        """profile を持たないユーザーは False を返すこと（クラッシュしないこと）"""
        user = User.objects.create_user(username='noprofile', password='password')
        user.profile.delete()
        user.refresh_from_db()
        self.assertFalse(is_admin(user))


class AdminRequiredEndpointsTest(TestCase):
    """管理者専用エンドポイントへの非管理者アクセスが 403 になること"""

    def setUp(self):
        self.non_admin = User.objects.create_user(username='notadmin_req', password='password')
        self.non_admin.profile.role = UserProfile.Role.GENERAL
        self.non_admin.profile.save()
        self.client.force_login(self.non_admin)

    def test_run_db_backup_non_admin_forbidden(self):
        response = self.client.post(reverse('accounts:run_db_backup'))
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()['status'], 'error')

    def test_list_backups_non_admin_forbidden(self):
        response = self.client.get(reverse('accounts:list_backups'))
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()['status'], 'error')

    def test_restore_db_non_admin_forbidden(self):
        import json as json_mod
        response = self.client.post(
            reverse('accounts:restore_db'),
            data=json_mod.dumps({'path': '/backups/test.sql.gz'}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()['status'], 'error')


class DropboxTokenManagerTest(TestCase):
    """DropboxTokenManager の単体テスト（OAuth・トークン管理）"""

    def setUp(self):
        from apps.adjustments.services.dropbox_token import DropboxTokenManager
        self.manager = DropboxTokenManager()

    def test_get_token_model_returns_none_when_no_token(self):
        """トークンが存在しない場合は None を返すこと"""
        self.assertIsNone(self.manager.get_token_model())

    def test_is_authenticated_false_when_no_token(self):
        """トークンが存在しない場合は認証されていないこと"""
        self.assertFalse(self.manager.is_authenticated())

    def test_is_authenticated_true_when_token_exists(self):
        """アクセストークンが存在する場合は認証済みと判定されること"""
        DropboxToken.objects.create(
            access_token='test_access',
            refresh_token='test_refresh',
            expires_at=timezone.now() + timedelta(hours=1),
        )
        self.assertTrue(self.manager.is_authenticated())

    def test_get_token_model_returns_token(self):
        """保存済みトークンが正しく取得されること"""
        token = DropboxToken.objects.create(
            service_name='backup',
            access_token='abc',
            refresh_token='xyz',
        )
        result = self.manager.get_token_model()
        self.assertEqual(result.pk, token.pk)

    def test_get_client_raises_auth_error_when_no_token(self):
        """トークンなしで get_client() を呼ぶと DropboxAuthError が発生すること"""
        from apps.adjustments.services.dropbox_token import DropboxAuthError
        with self.assertRaises(DropboxAuthError):
            self.manager.get_client()


class DropboxLoginPermissionTest(TestCase):
    """dropbox_login ビューの権限チェックテスト（#1）"""

    def setUp(self):
        self.admin = User.objects.create_user(username='dbx_admin', password='password')
        self.admin.profile.role = UserProfile.Role.ADMIN
        self.admin.profile.save()

        self.non_admin = User.objects.create_user(username='dbx_general', password='password')
        self.non_admin.profile.role = UserProfile.Role.GENERAL
        self.non_admin.profile.save()

    def test_non_admin_redirected_to_index(self):
        """非管理者が dropbox_login にアクセスすると facilities:index にリダイレクトされること"""
        self.client.force_login(self.non_admin)
        response = self.client.get(reverse('accounts:dropbox_login'))
        self.assertRedirects(response, '/', fetch_redirect_response=False)

    def test_admin_proceeds_to_dropbox(self):
        """管理者は dropbox_login にアクセスすると Dropbox の OAuth URL にリダイレクトされること"""
        from unittest.mock import patch
        self.client.force_login(self.admin)
        with patch('apps.accounts.views.DropboxService') as MockService:
            MockService.return_value.get_auth_url.return_value = 'https://dropbox.com/oauth/authorize?state=x'
            response = self.client.get(reverse('accounts:dropbox_login'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('dropbox.com', response['Location'])


class DropboxCallbackExceptionTest(TestCase):
    """dropbox_callback の例外ハンドリングテスト（#3）"""

    def setUp(self):
        self.user = User.objects.create_user(username='dbx_cb_user', password='password')
        self.client.force_login(self.user)

    def test_auth_error_renders_error_page(self):
        """DropboxAuthError 発生時にエラーページが返されること（500 ではなく 200）"""
        from unittest.mock import patch

        from apps.adjustments.services.dropbox_token import DropboxAuthError
        with patch('apps.accounts.views.DropboxService') as MockService:
            MockService.return_value.finish_auth.side_effect = DropboxAuthError('テスト認証エラー')
            response = self.client.get(
                reverse('accounts:dropbox_callback'),
                {'code': 'dummy_code', 'state': 'dummy_state'},
            )
        self.assertEqual(response.status_code, 200)
        self.assertIn('Dropbox認証に失敗しました', response.context['error'])

    def test_no_code_renders_cancel_message(self):
        """code パラメータなしでアクセスするとキャンセルメッセージが返されること"""
        response = self.client.get(reverse('accounts:dropbox_callback'))
        self.assertEqual(response.status_code, 200)
        self.assertIn('キャンセル', response.context['error'])
