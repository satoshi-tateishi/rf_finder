# LINE WORKS SSO

> **このアプリは独自の SSO/OTP を持ちません。**
>
> SSO（LINE WORKS OIDC）および OTP（2段階認証）は **shin•on Portal の責務** です。
> RF Finder は Portal が発行する `portal_jwt` クッキーを検証するだけで認証を完了します。

## 認証フロー

```
① ユーザーが http://localhost:8084/ にアクセス（未認証）
       ↓ login_required → login_view
② http://localhost:8000/login/?next=http://localhost:8084/
       ↓ Portal で LINE WORKS SSO + OTP 認証
③ http://localhost:8084/  ← 元の URL に戻る
       ↓ PortalJWTMiddleware が portal_jwt クッキーを検証
④ Django セッション確立 → アプリ表示
```

## RF Finder 側の実装

| ファイル | 役割 |
|---------|------|
| `apps/accounts/middleware.py` | `PortalJWTMiddleware`：JWT検証・自動ログイン |
| `apps/accounts/views.py` | `login_view`：Portal ログインへリダイレクト |

## 関連ドキュメント

- **SSO/OTP の実装詳細** → `shin-on_portal/docs/07_LINE_WORKS_SSO.md`
- **連携アプリへの統合手順** → `shin-on_portal/docs/06_APP_INTEGRATION_GUIDE.md`
- **LINE WORKS Bot API**（通知送信） → `LINE_WORKS_API.md`（このディレクトリ）
