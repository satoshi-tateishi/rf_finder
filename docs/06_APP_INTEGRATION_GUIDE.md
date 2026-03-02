# 06_APP_INTEGRATION_GUIDE.md
# shin•on Portal — 連携アプリ JWT 統合ガイド

## 概要

このドキュメントは、独自の LINE WORKS SSO + OTP を持つ既存アプリを
shin•on Portal の JWT 認証に移行するための手順書です。

Django アプリ（rf_finder）を題材として、必要な変更と AI への作業プロンプトをまとめています。
Laravel 等の他フレームワークへの応用時も、設計思想は共通です。

---

## アーキテクチャ

### 移行前
```
User → 各アプリ（LINE WORKS SSO + OTP）→ アプリ固有セッション
```

### 移行後
```
User → Portal（LINE WORKS SSO + OTP）→ portal_jwt クッキー（RS256署名・24時間有効）
                                              ↓ .shin-on1981.com ドメイン全体に付与
     → 各アプリ（portal_jwt クッキーを検証）→ ローカルセッション確立
```

### JWT の流れ

1. ユーザーがポータルで SSO + OTP 認証を完了
2. ポータルが `portal_jwt`（RS256署名 JWT）を `.shin-on1981.com` ドメインのクッキーに発行
3. 連携アプリはリクエスト毎に `portal_jwt` クッキーを受け取る
4. 連携アプリの JWT ミドルウェアが署名を検証してユーザーを識別
5. Django セッションを確立（以降はセッションで継続）

### クッキー一覧（ポータルが発行）

| クッキー名 | 用途 | 有効期限 |
|---|---|---|
| `otp_verified=true` | Apache ゲートウェイのアクセス制御 | 24時間 |
| `portal_jwt=<JWT>` | 連携アプリのユーザー識別 | 24時間（`PORTAL_JWT_COOKIE_EXPIRY`） |

---

## Portal 側の実装（完了済み）

以下は shin•on Portal に既に実装済みの機能です。

### 発行エンドポイント

| エンドポイント | 認証 | 用途 |
|---|---|---|
| `GET /api/token/` | Djangoセッション + OTPクッキー | API用JWT発行（5分有効） |
| `GET /api/jwks/` | 不要（公開） | 連携アプリの署名検証用公開鍵 |

### JWT クレーム設計

```json
{
  "iss": "https://portal.shin-on1981.com",
  "sub": "<portal_uuid>",
  "aud": "shin-on-apps",
  "iat": 1234567890,
  "exp": 1234654290,
  "jti": "<uuid4>",
  "email": "user@shin-on1981.com",
  "name": "山田太郎",
  "given_name": "太郎",
  "family_name": "山田",
  "phonetic_given_name": "たろう",
  "phonetic_family_name": "やまだ",
  "is_active": true
}
```

**重要**: `sub` クレームの値は `portal_uuid`（`User.username`）です。
不変の識別子として、ユーザーの一生変わらない主キーとして使用します。

### 鍵ペアの生成（初回のみ）

```bash
docker compose exec portal-app python manage.py generate_jwt_keys
```

---

## Django アプリへの統合手順

### 前提条件

- [ ] ポータルと同じ Cookie ドメイン（`.shin-on1981.com`）配下にあること
- [ ] `PyJWT >= 2.8.0` および `cryptography` がインストール済みであること
- [ ] ポータルの `/api/jwks/` エンドポイントにネットワーク疎通があること

### Step 1: `portal_uuid` フィールドの追加

**対象ファイル**: `apps/accounts/models.py`

`UserProfile` モデルに以下のフィールドを追加する：

```python
portal_uuid = models.CharField(
    max_length=100,
    blank=True,
    null=True,
    unique=True,
    db_index=True,
    verbose_name='ポータルUUID',
    help_text='shin•on Portal の portal_uuid（不変ID）。JWT 連携時に自動設定される。',
)
```

**マイグレーション作成・適用**:

```bash
docker compose exec web python manage.py makemigrations accounts
docker compose exec web python manage.py migrate
```

### Step 2: JWT ミドルウェアの作成

**新規ファイル**: `apps/accounts/middleware.py`

```python
"""
PortalJWTMiddleware

shin•on Portal が発行した portal_jwt クッキー（RS256署名）を検証し、
認証済みユーザーを Django セッションに紐付けるミドルウェア。
"""

import logging

import jwt
from django.conf import settings
from django.contrib.auth import login
from django.contrib.auth.models import User
from jwt import PyJWKClient

logger = logging.getLogger(__name__)


class PortalJWTMiddleware:
    _jwks_client: PyJWKClient | None = None

    def __init__(self, get_response):
        self.get_response = get_response
        if PortalJWTMiddleware._jwks_client is None:
            PortalJWTMiddleware._jwks_client = PyJWKClient(
                settings.PORTAL_JWKS_URL, cache_keys=True
            )

    def __call__(self, request):
        if not request.user.is_authenticated:
            self._authenticate_with_jwt(request)
        return self.get_response(request)

    def _authenticate_with_jwt(self, request):
        portal_jwt_token = request.COOKIES.get('portal_jwt')
        if not portal_jwt_token:
            return
        try:
            signing_key = self._jwks_client.get_signing_key_from_jwt(portal_jwt_token)
            payload = jwt.decode(
                portal_jwt_token,
                signing_key.key,
                algorithms=['RS256'],
                audience=settings.PORTAL_JWT_AUDIENCE,
                issuer=settings.PORTAL_JWT_ISSUER,
            )
        except jwt.ExpiredSignatureError:
            logger.info('portal_jwt が期限切れです。再認証が必要です。')
            return
        except jwt.InvalidTokenError as e:
            logger.warning(f'portal_jwt の検証に失敗しました: {e}')
            return
        except Exception as e:
            logger.error(f'portal_jwt 処理中に予期しないエラー: {e}', exc_info=True)
            return

        portal_uuid = payload.get('sub')
        email = payload.get('email', '')
        if not portal_uuid:
            return

        user = self._get_or_link_user(portal_uuid, email, payload)
        if user and user.is_active:
            login(request, user, backend='django.contrib.auth.backends.ModelBackend')

    def _get_or_link_user(self, portal_uuid, email, payload):
        from .models import UserProfile

        # 1. portal_uuid で検索
        try:
            profile = UserProfile.objects.select_related('user').get(portal_uuid=portal_uuid)
            return profile.user
        except UserProfile.DoesNotExist:
            pass

        # 2. email で既存ユーザーを検索して自動リンク（初回のみ）
        if not email:
            return None
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return None
        except User.MultipleObjectsReturned:
            user = User.objects.filter(email=email).order_by('id').first()

        profile, _ = UserProfile.objects.get_or_create(user=user)
        profile.portal_uuid = portal_uuid
        if not profile.family_name:
            profile.family_name = payload.get('family_name', '')
        if not profile.given_name:
            profile.given_name = payload.get('given_name', '')
        if not profile.email:
            profile.email = email
        profile.save()

        logger.info(f'portal_uuid を自動リンクしました: {user.email} -> {portal_uuid}')
        return user
```

> **注意**: `UserProfile` の `related_name` や `family_name` 等のフィールド名は
> アプリ毎に異なります。実際のモデルに合わせて調整してください。

### Step 3: settings.py の変更

**MIDDLEWARE** に `PortalJWTMiddleware` を追加する（`AuthenticationMiddleware` の直後）：

```python
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'apps.accounts.middleware.PortalJWTMiddleware',  # ← ここに追加
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]
```

**JWT 設定**を追記する：

```python
# shin•on Portal JWT 連携設定
PORTAL_JWKS_URL = env('PORTAL_JWKS_URL', default='https://portal.shin-on1981.com/api/jwks/')
PORTAL_JWT_ISSUER = env('PORTAL_JWT_ISSUER', default='https://portal.shin-on1981.com')
PORTAL_JWT_AUDIENCE = env('PORTAL_JWT_AUDIENCE', default='shin-on-apps')
```

### Step 4: .env への設定追加

```env
# shin•on Portal JWT 連携
PORTAL_JWKS_URL=https://portal.shin-on1981.com/api/jwks/
PORTAL_JWT_ISSUER=https://portal.shin-on1981.com
PORTAL_JWT_AUDIENCE=shin-on-apps
```

開発環境でポータルが `localhost` で動作している場合：

```env
PORTAL_JWKS_URL=http://localhost/api/jwks/
```

---

## 動作確認

### 1. マイグレーション確認

```bash
docker compose exec web python manage.py showmigrations accounts
```

`0012_userprofile_portal_uuid` に `[X]` が付いていることを確認。

### 2. エンドツーエンドの確認手順

1. ポータルで SSO + OTP 認証を完了する
2. ブラウザの DevTools > Application > Cookies で `portal_jwt` クッキーが発行されていることを確認
3. 連携アプリにアクセスする
4. ログイン不要でアプリのコンテンツが表示されることを確認

### 3. 初回マッピングの確認

```bash
# Django shell でマッピング状況を確認
docker compose exec web python manage.py shell
>>> from apps.accounts.models import UserProfile
>>> UserProfile.objects.filter(portal_uuid__isnull=False).values('user__email', 'portal_uuid')
```

### 4. ログ確認

```bash
docker compose logs -f web | grep portal_uuid
```

初回アクセス時に以下のログが出ることを確認：

```
portal_uuid を自動リンクしました: user@shin-on1981.com -> portal_uuid=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
```

---

## AI 作業プロンプト集

以下のプロンプトを Claude Code（または同等の AI）に与えることで、
各アプリへの統合作業を効率よく進められます。

---

### プロンプト 1：アプリ調査（最初に実行）

```
以下のDjangoアプリを調査してください：
<アプリのパス>

調査してほしい内容：
1. ディレクトリ構造全体
2. requirements.txt（PyJWT、cryptography の有無）
3. apps/accounts/models.py の UserProfile モデルの構造
   - related_name の値
   - フィールド一覧（portal_uuid フィールドがあるか）
4. config/settings.py（または settings.py）
   - MIDDLEWARE の現在の構成
   - 認証関連の設定
5. 現在の認証フロー（LINE WORKS SSO + OTP の有無）
6. 最新のマイグレーションファイル名

特に UserProfile の OneToOneField の related_name と
最新マイグレーションの番号を必ず教えてください。
```

---

### プロンプト 2：統合実装（調査結果を踏まえて実行）

```
shin•on Portal との JWT 連携を実装してください。

【このアプリの情報】（調査結果を記入）
- アプリパス: <パス>
- UserProfile の related_name: <例: profile>
- UserProfile のフィールド（姓・名・メール等の実際の名前）: <例: family_name, given_name, email>
- 最新マイグレーション番号: <例: 0011>
- settings.py のパス: <例: config/settings.py>

【実装してほしいこと】
1. apps/accounts/models.py の UserProfile に portal_uuid フィールドを追加
   （CharField, max_length=100, null=True, blank=True, unique=True, db_index=True）

2. マイグレーションファイルを手動作成
   （ファイル名: <最新番号+1>_userprofile_portal_uuid.py）

3. apps/accounts/middleware.py を新規作成（PortalJWTMiddleware）
   - portal_jwt クッキーを検証（JWKS 経由）
   - portal_uuid でユーザー検索、なければ email で自動リンク
   - UserProfile のフィールド名はこのアプリの実際の名前に合わせること

4. settings.py を変更
   - MIDDLEWARE の AuthenticationMiddleware の直後に PortalJWTMiddleware を挿入
   - PORTAL_JWKS_URL, PORTAL_JWT_ISSUER, PORTAL_JWT_AUDIENCE を追記

5. .env.sample に Portal JWT 設定を追記

【Portal の仕様】
- JWKS エンドポイント: /api/jwks/
- JWT の sub クレーム: portal_uuid（User.username の値）
- JWT の aud: shin-on-apps
- JWT の iss: https://portal.shin-on1981.com

実装後、Ruff チェックを必ず実行してください。
```

---

### プロンプト 3：テスト確認（実装後に実行）

```
<アプリパス>/apps/accounts/ の middleware.py のユニットテストを作成してください。

テストケース：
1. portal_jwt クッキーがない場合はスキップ（AnonymousUser のまま）
2. 不正な JWT の場合はスキップ
3. 期限切れ JWT の場合はスキップ
4. 有効な JWT で portal_uuid が既存ユーザーと一致する場合は認証成功
5. 有効な JWT で portal_uuid 未登録・email 一致で自動リンクして認証成功
6. 有効な JWT で email もマッチしない場合は認証されない（AnonymousUser のまま）

テスト用 RSA 鍵ペアは tempfile でテスト内で生成すること。
テスト後、Ruff チェックを実行してください。
```

---

### プロンプト 4：既存認証フローの削除（全ユーザー移行完了後）

```
<アプリパス> の LINE WORKS SSO + OTP 認証フローを削除してください。

削除対象：
- apps/accounts/urls.py の以下のパス
  - lineworks/login/
  - lineworks/callback/
  - otp/verify/
  - otp/resend/
- apps/accounts/views.py の対応するビュー関数
- UserProfile モデルの OTP 関連フィールド（otp_code, otp_expires_at, otp_attempts, otp_locked_until）
  ※ マイグレーションも作成すること

削除前に以下を確認してください：
- 全ユーザーの UserProfile.portal_uuid が埋まっていること
  （SELECT COUNT(*) FROM accounts_userprofile WHERE portal_uuid IS NULL;）
- 該当フィールドが他の箇所で参照されていないこと

実装後、Ruff チェックを実行してください。
```

---

## トラブルシューティング

### portal_jwt クッキーが届かない

- ポータルが正しく `portal_jwt` クッキーを発行しているか確認する
  ```bash
  # ポータルで portal_jwt_keys が生成されているか確認
  docker compose exec portal-app ls /keys/portal_jwt.*
  ```
- クッキーのドメインが一致しているか確認する（`.shin-on1981.com`）

### JWT 検証エラー（`InvalidTokenError`）

- `PORTAL_JWT_AUDIENCE` と `PORTAL_JWT_ISSUER` がポータルの設定と一致しているか確認する
- ポータルで鍵ペアを再生成した場合、JWKS キャッシュが古い可能性がある（アプリを再起動する）

### email マッピングが動作しない

- 連携アプリのユーザーの `email` フィールドとポータルの `user.email` が一致しているか確認する
- ログに `email=... に対応するローカルユーザーが存在しません` と出ていればユーザーを手動で作成する

### マイグレーションの競合

最新マイグレーション番号が `0011` でない場合は、プロンプト 2 の番号を実際の番号に合わせて指定する。

---

## Laravel / 他フレームワークへの応用

Django 以外のフレームワークでも基本設計は同じです。

1. **JWT 検証**: `firebase/php-jwt`（PHP）等のライブラリで RS256 を検証
2. **JWKS 取得**: `GET https://portal.shin-on1981.com/api/jwks/` から公開鍵を取得（キャッシュ推奨）
3. **ユーザー識別**: `sub` クレーム（portal_uuid）をローカル DB の外部キーとして使用
4. **自動リンク**: 初回は `email` クレームでローカルユーザーを検索して portal_uuid を保存

Laravel 用の実装プロンプトは別途作成予定。
