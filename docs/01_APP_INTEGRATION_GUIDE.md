# shin•on Portal — 連携アプリ JWT 統合ガイド

## 概要

shin•on Portal の JWT 認証を他の Web アプリと連携させるための実装ガイド。
RF Finder での実装・デバッグ経験を元に、**ハマりポイントと正しい対処法**を含めてまとめる。

---

## 認証フロー全体像

```
[ユーザー]
  │
  ├─① 未認証で連携アプリへアクセス
  │
[連携アプリ]
  │  login_required → /auth/login/?next=/path/
  │
  ├─② ポータルログイン画面へリダイレクト
  │   http://localhost/login/?next=http://localhost:8084/path/
  │
[shin•on Portal]
  │  LINE WORKS SSO → OTP 検証
  │  set_otp_cookie() → portal_jwt クッキー発行 → next_url へリダイレクト
  │
[連携アプリ]
  │  PortalJWTMiddleware が portal_jwt を検証
  │  → ユーザー照合 or 自動作成 → Django セッション確立
  │
  └─③ アプリのコンテンツを表示
```

---

## ポータルが発行するクッキー

| クッキー名 | 用途 | 有効期限 | SameSite | HttpOnly | Secure |
|-----------|------|---------|----------|---------|--------|
| `otp_verified=true` | Apache ゲートウェイのアクセス制御 | 24時間 | Lax | ✓ | 本番のみ |
| `portal_jwt=<JWT>` | 連携アプリのユーザー識別 | 24時間 | Lax | ✓ | 本番のみ |

### クッキードメインの動作

```python
# portal-app/apps/accounts/services/otp_service.py
domain = settings.LINE_WORKS_DOMAIN if not settings.DEBUG else None
```

| 環境 | domain 設定 | 到達範囲 |
|------|------------|---------|
| 本番（DEBUG=False） | `.shin-on1981.com` | サブドメイン全体 |
| 開発（DEBUG=True） | `None`（ホスト限定） | `localhost`（ポート不問） |

**ポイント**: ブラウザはポートを無視してクッキーを送信するため、
`localhost:80` でセットされたクッキーは `localhost:8084` にも送られる。

---

## JWT ペイロード（クッキー用）

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
  "phone_number": "09012345678",
  "is_active": true
}
```

**重要**: `sub` は `portal_uuid`（= `User.username`）。不変の識別子として使う。

新しいクレームを追加する場合は `portal-app/apps/accounts/services/jwt_service.py` の
`issue_token()` と `issue_cookie_token()` 両方を修正すること。

---

## リダイレクト URL バリデーション

ポータルは OTP 完了後に `next_url` へリダイレクトするが、
**オープンリダイレクト対策**として許可ドメインをチェックする。

```python
# portal-app/apps/accounts/views.py
def _get_safe_redirect_url(next_url):
    parsed = urlparse(next_url)
    allowed_domain = settings.LINE_WORKS_DOMAIN.lstrip('.')  # 'shin-on1981.com'
    netloc = parsed.netloc.split(':')[0]  # ポート番号を除去して比較

    # 1. 本番ドメイン（サブドメイン含む）は許可
    if parsed.scheme in ('http', 'https') and (
        netloc == allowed_domain or netloc.endswith('.' + allowed_domain)
    ):
        return next_url

    # 2. 追加許可ホスト（開発環境の localhost 等）
    if netloc in getattr(settings, 'PORTAL_ALLOWED_REDIRECT_HOSTS', []):
        return next_url

    # 許可外 → ポータルトップに飛ばす（next_url が無視される）
    return reverse('accounts:portal_index')
```

### 開発環境での設定

連携アプリが `localhost:8084` 等で動く場合は `.env` に追加が必要：

```env
# portal-app/.env
PORTAL_ALLOWED_REDIRECT_HOSTS=["localhost"]
```

ポート番号は除去して比較されるため `localhost` だけでよい。
設定漏れの症状：OTP 完了後に連携アプリへ戻らず、ポータルトップに飛ぶ。

---

## 連携アプリ側の実装（PortalJWTMiddleware）

### ミドルウェアの配置

```python
# settings.py
MIDDLEWARE = [
    ...
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'apps.accounts.middleware.PortalJWTMiddleware',  # AuthenticationMiddleware の直後
    ...
]
```

### ユーザー照合ロジック（3段階）

```
portal_jwt 受信
    │
    ├─[1] portal_uuid でプロフィール検索 → 見つかれば即返す
    │      ＋ JWT の phone_number が変化していれば更新（常時同期）
    │
    ├─[2] email で既存ユーザー検索 → 見つかれば portal_uuid を紐付け
    │      ＋ 各プロフィールフィールドを空の場合のみ補完
    │
    └─[3] どちらも見つからない → JWT ペイロードで新規ユーザーを自動作成
```

### 実装上の重要な注意点

#### ⚠️ Django post_save シグナルとの干渉バグ

新規ユーザーを `create_user()` で作成すると以下のシグナル連鎖が起きる：

```
create_user()
  → user.save()
    → post_save: create_user_profile  # UserProfile 作成（portal_uuid=None でキャッシュ）
    → post_save: save_user_profile    # user.profile をキャッシュ（portal_uuid=None）
  → 返却
→ 我々のコードで profile.portal_uuid = uuid; profile.save()  # DB更新 ✓
→ login(request, user)
  → update_last_login → user.save()
    → post_save: save_user_profile
      → user.profile.save()  # キャッシュされた古いオブジェクト（portal_uuid=None）で上書き ✗
```

**間違い（portal_uuid が None になる）**:
```python
profile, _ = UserProfile.objects.get_or_create(user=user)  # キャッシュを更新しない
profile.portal_uuid = portal_uuid
profile.save()
```

**正しい実装（user.profile 経由でキャッシュを更新する）**:
```python
profile = user.profile  # user オブジェクトのキャッシュを更新する
profile.portal_uuid = portal_uuid
profile.save()
# → login() 後の save_user_profile が user.profile を再び呼んでも
#   キャッシュ済みの更新済みオブジェクトが使われる ✓
```

#### JWT クレームの同期タイミング

| フィールド | パス1（uuid照合） | パス2（email照合） | パス3（新規作成） |
|-----------|----------------|----------------|----------------|
| `portal_uuid` | （既に設定済み） | 紐付け | 設定 |
| `phone_number` | **常に最新値へ更新** | 空の場合のみ補完 | 設定 |
| `family_name` 等 | 更新しない | 空の場合のみ補完 | 設定 |

`phone_number` をパス1でも更新する理由：ポータルで電話番号が変更された際に
連携アプリ側に自動反映させるため。

```python
# パス1での phone_number 同期
jwt_phone = payload.get('phone_number', '')
if jwt_phone and profile.phone_number != jwt_phone:
    profile.phone_number = jwt_phone
    profile.save(update_fields=['phone_number'])
```

---

## 必要な設定値一覧

### 連携アプリ側（.env）

```env
# JWKS エンドポイント（Docker 内からポータルコンテナへ直接アクセス）
PORTAL_JWKS_URL=http://portal-app:8000/api/jwks/

# JWT 検証パラメータ（ポータルの設定と完全一致させること）
PORTAL_JWT_ISSUER=https://portal.shin-on1981.com
PORTAL_JWT_AUDIENCE=shin-on-apps

# ポータルのログインページ URL（連携アプリが未認証時にリダイレクトする先）
PORTAL_LOGIN_URL=http://localhost/login/
```

### ポータル側（.env）

```env
# 開発環境で localhost の連携アプリを許可する場合
PORTAL_ALLOWED_REDIRECT_HOSTS=["localhost"]
```

---

## Docker ネットワーク設計

### コンテナ間の通信

```
[browser] ──── localhost:80 ──── [apache-gateway]
                                       │
                              shin-on-internal ネットワーク
                                  ┌────┴────┐
                              [portal-app]  [rf_finder_web]
                                             │
                                         rf_network
                                             │
                                       [rf_finder_db]
```

JWKS 取得（`http://portal-app:8000/api/jwks/`）は
`shin-on-internal` ネットワーク経由でコンテナ間通信する。

### コンテナ起動順の保証

`depends_on: - db` だけではコンテナが「起動した」ことしか保証されない。
MySQL が接続受付可能になる前に web が起動すると接続エラーが発生する。

**正しい設定**（`healthcheck` + `condition: service_healthy`）：

```yaml
services:
  db:
    image: mysql:8.4
    ...
    healthcheck:
      test: ["CMD", "mysqladmin", "ping", "-h", "127.0.0.1", "-u", "root", "-proot_password"]
      interval: 5s
      timeout: 3s
      retries: 10
      start_period: 30s  # MySQL の初期化完了まで待つ

  web:
    ...
    depends_on:
      db:
        condition: service_healthy  # ← ここが重要
```

---

## 動作確認チェックリスト

```
□ ポータルの PORTAL_ALLOWED_REDIRECT_HOSTS に連携アプリのホストが含まれている
□ 連携アプリの PORTAL_JWKS_URL がポータルコンテナに疎通できる
□ PORTAL_JWT_ISSUER / PORTAL_JWT_AUDIENCE がポータルの設定と一致している
□ docker-compose に healthcheck と condition: service_healthy が設定されている
□ DB マイグレーションが完了している（portal_uuid フィールドを含む）
```

---

## トラブルシューティング

### OTP 完了後にポータルトップに飛んでしまう

**原因**: `_get_safe_redirect_url` が `next_url` を弾いている。

**確認方法**: ポータルの `.env` で `PORTAL_ALLOWED_REDIRECT_HOSTS` を確認する。
`localhost` が含まれていなければ追加してコンテナを再起動する。

### `portal_jwt` クッキーは届いているが認証されない

**確認手順**:
1. DB にユーザーが存在するか確認
2. Django ログで `portal_jwt 処理中に予期しないエラー` が出ていないか確認
3. `PORTAL_JWT_ISSUER` / `PORTAL_JWT_AUDIENCE` がポータル設定と一致しているか確認

```bash
# ユーザー存在確認
docker exec <web_container> python manage.py shell -c "
from django.contrib.auth.models import User
print(User.objects.values('email', 'profile__portal_uuid'))
"
```

### JWT は有効だがプロフィールフィールド（portal_uuid 等）が None になる

**原因**: `User.objects.create_user()` 後に `get_or_create` でプロフィールを取得すると
`login()` が発火する `save_user_profile` シグナルによって上書きされる。

**対処**: `user.profile`（キャッシュ経由）でアクセスする。詳細は上記「Django post_save シグナルとの干渉バグ」を参照。

### `Can't connect to server on 'db'` エラー

**原因**: `depends_on: - db` だけでは MySQL の起動完了を保証しない。

**対処**: `healthcheck` を db サービスに追加し、web サービスの `depends_on` を
`condition: service_healthy` に変更する（上記 Docker 設定参照）。

### 電話番号などの新クレームが反映されない

portal_jwt クッキーは 24時間キャッシュされる。
ポータル側でクレームを追加しても、既存クッキーが有効な間は古い JWT が使われ続ける。

**強制更新方法**: ブラウザの `portal_jwt` クッキーを削除して再ログインする。

---

## 新しい連携アプリを追加する際のチェックリスト

```
□ ポータル: PORTAL_ALLOWED_REDIRECT_HOSTS に新アプリのホストを追加
□ 連携アプリ: PORTAL_JWKS_URL / PORTAL_JWT_ISSUER / PORTAL_JWT_AUDIENCE を設定
□ 連携アプリ: portal_uuid フィールドを UserProfile に追加・マイグレーション実施
□ 連携アプリ: PortalJWTMiddleware を実装（AuthenticationMiddleware の直後に配置）
□ 連携アプリ: docker-compose に healthcheck を設定
□ 連携アプリ: shin-on-internal ネットワークに接続（JWKS 疎通のため）
□ テスト: PortalJWTMiddleware のユニットテストを追加（シグナル干渉の回帰テスト含む）
```
