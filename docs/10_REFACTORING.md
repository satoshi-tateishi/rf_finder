# リファクタリング計画・残課題

## 残課題

### Content Security Policy (CSP) の完全対応 — 優先度：中

**現状スコア: 9.0 / 10。CSP が完成すれば 9.5〜9.8 に到達できる。**

#### 問題
`templates/index.html` にインライン `<script>` ブロックと `<style>` ブロックが存在するため、
`Content-Security-Policy: script-src 'self'` を有効化すると AppState.init 等の初期化処理がブロックされる。

#### 必要な作業
1. **インラインスクリプトの外部化**
   - `index.html` 内の `<script>AppState.init({...})</script>` を
     Django テンプレートタグで JS 変数として出力する方式に変更
     例: `<script>window.RF_FINDER_CONFIG = {{ config_json|safe }};</script>` を
     `static/js/app-init.js` で読み込む形に分離

2. **インラインスタイルの外部化**
   - `<style>` ブロック（`.ch-grid`, `.ch-btn` 等）を `static/css/style.css` に移動

3. **settings.py に CSP ヘッダを追加**
   ```python
   # django-csp パッケージ導入、または SecurityMiddleware の SECURE_* 設定で対応
   SECURE_CONTENT_SECURITY_POLICY = (
       "default-src 'self'; "
       "script-src 'self' https://cdn.jsdelivr.net; "
       "style-src 'self' https://cdnjs.cloudflare.com; "
       "font-src 'self' https://cdnjs.cloudflare.com data:; "
       "img-src 'self' data: blob:; "
       "connect-src 'self'; "
       "frame-src blob:;"
   )
   ```

#### 参考: 現在適用済みのセキュリティヘッダ（`config/settings.py`）
| ヘッダ | 設定値 | 状態 |
|--------|--------|------|
| `X-Content-Type-Options` | `nosniff` | ✅ 適用済み |
| `Referrer-Policy` | `same-origin` | ✅ 適用済み |
| `X-Frame-Options` | `DENY` | ✅ 適用済み |
| `Content-Security-Policy` | 未設定 | ❌ **要対応** |

---

### Dropbox 分散ロック — 優先度：低

`services/dropbox_service.py` のバックアップ排他制御が `/tmp/` ファイルロックのため、
複数サーバー構成では無効。現状はシングルサーバー運用のため実害なし。
スケールアウト時に Redis または DB ベースの分散ロックへ移行する。

---

## 品質保証方針

### 「テストが通れば本番でも動く」を成立させる前提条件

CI パイプライン（GitHub Actions）は以下の順で実行される。
**`test-python` が green = 本番デプロイしても基本動作に問題ない** ことを意味する。

```
push to release
  └─ lint-python (ruff check)
  └─ test-python (pytest + MySQL 8.4)
       └─ 成功時のみ → deploy (migrate → gunicorn 再起動)
```

この保証が成立するための条件と現状：

| 条件 | 現状 |
|------|------|
| テスト DB と本番 DB のエンジンが同じ（MySQL 8.4） | ✅ CI サービスに `mysql:8.4` を指定 |
| 全マイグレーションがテスト時にも適用される | ✅ `pytest-django` が `--no-migrations` なしで動作 |
| 外部サービス（LINE Works・Dropbox）はモック化 | ✅ `LINE_WORKS_MOCK_MODE=True`（`TESTING=True` 時に自動設定） |
| メール送信はインメモリバックエンド | ✅ `locmem.EmailBackend`（`TESTING=True` 時に自動設定） |
| テストカバレッジ対象 | ✅ `apps/` 配下（migrations・admin・tests を除く） |

#### 注意事項
- **LibreOffice（PDF変換）** は CI 環境に未インストール。
  `convert_excel_to_pdf` は `subprocess.run` をモック化してテストしており、
  実際の変換品質は手動確認が必要。
- **本番固有の設定値**（`SECRET_KEY`・`ALLOWED_HOSTS`・`CSRF_TRUSTED_ORIGINS` 等）は
  `.env` で管理。CI には GitHub Secrets 経由で注入。

---

## 次回作業再開プロンプト

```
前回のコードレビューで以下が対応済みです（コミット 0484bf7）。

【対応済み】
- XSS修正（ui-renderers.js / ui-controller.js の escapeHtml 導入）
- line_bot_service.py の os.sys.argv バグ修正
- User.email ユニーク制約（MySQL関数インデックス、migration 0014）
- 外部CDN（FontAwesome / SortableJS）SRI ハッシュ追加
- SECRET_KEY デフォルト値廃止、ALLOWED_HOSTS を ['localhost','127.0.0.1'] に変更
- セキュリティヘッダ追加（X-Content-Type-Options / Referrer-Policy / X-Frame-Options）
- 一覧上限をハードコードから設定変数化（FACILITY_SEARCH_LIMIT 等）
- サービス層テスト追加（EmailServiceEdgeCaseTest / ExcelServiceCellTest 等）

【残課題（docs/10_REFACTORING.md に詳細あり）】
- CSP（Content-Security-Policy）未対応：インライン script/style の外部化が必要
- Dropbox 分散ロック：シングルサーバーなら実害なし。スケールアウト時に対応

現在のコード品質スコアは 9.0 / 10。
CSP 対応が完了すれば 9.5〜9.8 に到達できます。
次のタスクを指示してください。
```

---

## 対応しないと判断した項目

| 内容 | 理由 |
|------|------|
| docstring・型アノテーションの全面補充 | 動作に影響なし。現状のコードは十分に可読 |
| Excel セル座標のテンプレートファイル化 | `Cells` クラスで管理されており現状でも保守可能 |
| `except Exception` の全廃 | 外部サービス連携（LINE WORKS・Dropbox）では意図的に `Exception` を catch して `DropboxError` 等でラップする設計。不必要な絞り込みは保守コストを上げる |
| Playwright E2E テスト | ユニットテストで十分にカバーされており、UI テストの追加は費用対効果が低い |

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
- **セキュリティ**: XSS 対策として JS 側に `UIRenderer.escapeHtml()` を導入。外部 CDN には SRI ハッシュを付与。Django `SecurityMiddleware` 経由で `X-Content-Type-Options` / `Referrer-Policy` / `X-Frame-Options` を送出。CSP は インライン script/style の外部化後に導入予定。
