# リファクタリング計画・残課題

## 残課題

現時点ですべての計画済みリファクタリング課題は完了済み。

---

## 対応しないと判断した項目

| 内容 | 理由 |
|------|------|
| docstring・型アノテーションの全面補充 | 動作に影響なし。現状のコードは十分に可読 |
| Excel セル座標のテンプレートファイル化 | `Cells` クラスで管理されており現状でも保守可能 |
| `except Exception` の全廃 | 外部サービス連携（LINE WORKS・Dropbox）では意図的に `Exception` を catch して `DropboxError` 等でラップする設計。不必要な絞り込みは保守コストを上げる |
| Playwright E2E テスト | 現状の 118 件ユニットテストで十分にカバーされており、UI テストの追加は費用対効果が低い |

---

## アーキテクチャメモ（経緯が重要なもの）

- **認証**: shin•on Portal JWT（`portal_jwt` クッキー）に一本化。旧 LINE WORKS OIDC + OTP は全廃。
- **権限チェック**: `require_admin`（JSON 403 返し）/ `require_admin_redirect(url)`（リダイレクト）デコレータで統一。`is_admin(user)` ヘルパーを `accounts/utils.py` に集約。
- **Dropbox**: `DropboxTokenManager`（OAuth・トークン管理）と `DropboxService`（バックアップ・リストア）に分離。`services/dropbox_token.py` が前者を担当。
- **ロギング**: `logger.xxx('%s', var)` 遅延評価スタイルに統一（Ruff `G` ルール準拠）。`exc_info=True` の代わりに `logger.exception()` を使用。
- **テストランナー**: `manage.py test`（Django 標準）→ `pytest` + `pytest-django` + `pytest-cov` に移行。テスト間キャッシュ汚染のバグ修正（`AdjustmentAPITest` で `LineBotService` をモック化、`LineBotServiceTest` で setUp に `cache.clear()` を追加）。
- **URL 設計**: `apps.facilities.urls` の二重マウントを解消。`index` ビューは `config/urls.py` に直接登録（`path('', facility_views.index, name='index')`）。施設 API は `/api/facilities/` 配下のみ。`namespace='api-facilities'` ハックを廃止し `app_name = 'facilities'` を自然に使用。
- **定数管理**: `adjustments/constants.py` に `STATUS_DRAFT`, `STATUS_SUBMITTED`, `APP_TYPE_NEW/CHANGE/DELETE`, `APP_TYPE_CHOICES`, `STATUS_CHOICES`, `APP_TYPE_MAP` を集約。`models.py` でインポートして使用。
- **admin 構成**: `facilities/admin/` および `accounts/admin/` パッケージに分割。機能別ファイル（filters.py, facility.py, wireless.py / audit_log.py, dropbox.py, user_profile.py, member.py, email_template.py）で管理。
- **Docker セキュリティ**: 本番コンテナは非 root ユーザー（`appuser` UID 1000）で実行。開発環境はボリュームマウントの都合上 `user: root` を明示指定。
