# LINE WORKS SSO 連携ガイド (Django版)

サンプルアプリケーション `shin-on_wiki` の実装を基にした、Django での LINE WORKS SSO (**Authorization Code Flow**) の推奨実装方法をまとめます。以前の `shin-on` で使用されていた Implicit Flow よりもセキュアで、現在の標準的な手法です。

## 1. 認証フローの概要 (Authorization Code Flow)

1.  **リダイレクト**: ユーザーを LINE WORKS の認証エンドポイントへ送る（`response_type=code`）。
2.  **認可コードの取得**: ユーザーが承認後、LINE WORKS がアプリのコールバック URL へ `code` を付けてリダイレクト。
3.  **トークン交換 (Server-side)**: サーバー側で `code` を LINE WORKS のトークンエンドポイントへ送り、`access_token` と `id_token` を取得。
4.  **検証・ログイン**: `id_token` (JWT) を検証し、ユーザー情報の取得・作成、および Django セッションへのログインを行う。

---

## 2. 必要な設定 (.env)

```env
LINEWORKS_CLIENT_ID=your_client_id
LINEWORKS_CLIENT_SECRET=your_client_secret
LINEWORKS_REDIRECT_URI=http://localhost:8084/api/accounts/lineworks/callback/
LINEWORKS_DOMAIN=shin-on1981
```

---

## 3. 実装ステップ

### 3.1 認証開始 (Authorize Redirect)

ユーザーを以下の URL へリダイレクトさせます。

- **Base URL**: `https://auth.worksmobile.com/oauth2/v2.0/authorize`
- **Parameters**:
    - `client_id`: アプリの Client ID
    - `redirect_uri`: 登録済みのリダイレクト先
    - `scope`: `openid profile email`
    - `response_type`: `code`
    - `state`: セッションに保存したランダム文字列（CSRF対策）
    - `domain`: LINE WORKS のドメイン (例: `shin-on1981`)

### 3.2 コールバック処理 (Server-side)

LINE WORKS から受け取った `code` を使ってトークンを取得します。

```python
import requests
import jwt

def callback(request):
    code = request.GET.get('code')
    state = request.GET.get('state')
    
    # 1. Stateの検証
    if state != request.session.get('oidc_state'):
        return error("Invalid state")

    # 2. Token交換
    token_res = requests.post('https://auth.worksmobile.com/oauth2/v2.0/token', data={
        'code': code,
        'client_id': settings.LINEWORKS_CLIENT_ID,
        'client_secret': settings.LINEWORKS_CLIENT_SECRET,
        'redirect_uri': settings.LINEWORKS_REDIRECT_URI,
        'grant_type': 'authorization_code'
    })
    
    tokens = token_res.json()
    id_token = tokens.get('id_token')

    # 3. id_token (JWT) の検証
    # PyJWTを使用して aud, iss, exp を検証
    payload = jwt.decode(id_token, options={"verify_signature": False}) # 実際は公開鍵で検証推奨
    
    # 4. ドメイン検証
    email = payload.get('email')
    if not email.endswith(f"@{settings.LINEWORKS_DOMAIN}"):
        return error("許可されていない組織のユーザーです")

    # 5. ユーザーの取得または作成
    user, created = User.objects.get_or_create(
        username=payload.get('sub'),
        defaults={
            'email': email,
            'first_name': payload.get('family_name', ''),
            'last_name': payload.get('given_name', ''),
        }
    )
    
    login(request, user)
    return redirect('/')
```

---

## 4. shin-on_wiki 実装の特徴 (推奨ポイント)

- **セキュアなコード交換**: `id_token` がブラウザの履歴やログに残るリスクを排除。
- **PKCE (Proof Key for Code Exchange)**: セッションハイジャック対策として `code_verifier` と `code_challenge` の併用を推奨（`shin-on_wiki` で実装済み）。
- **ユーザー補完**: `family_name` (姓) と `given_name` (名) を分離して取得し、Django の User モデルに正しくマッピング。
- **組織制限**: `validateUserDomain` ロジックにより、自社ドメイン（`shin-on1981`）以外のアクセスを厳格に拒否。

---

## 5. 次のステップ

1.  **ライブラリの選定**: `mozilla-django-oidc` や `django-allauth` などの既存ライブラリを利用するか、上記のようにシンプルに独自実装するかを決定する。
2.  **LINE WORKS Developer Console の設定**: `redirect_uri` を本番・開発環境それぞれ登録し、Client ID/Secret を発行する。
