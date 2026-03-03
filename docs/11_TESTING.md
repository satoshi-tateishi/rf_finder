# テスト・デバッグ手法

プロジェクトのテストおよびデバッグに関するドキュメントです。

## ユニットテスト

### テスト実行コマンド

```bash
# 全テスト実行
docker exec rf_finder_web python manage.py test

# 特定アプリのみ
docker exec rf_finder_web python manage.py test apps.adjustments.tests

# 特定テストクラスのみ
docker exec rf_finder_web python manage.py test apps.adjustments.tests.test_wsm_service

# ローカル（Docker なし）の場合
python manage.py test
```

### テストファイル一覧

| ファイル | 対象 | 主なテスト内容 |
|---------|------|--------------|
| `apps/adjustments/tests/test_adjustment.py` | `OperationAdjustment` モデル | 保存・更新・取得ロジック、JSON からの永続化 (`save_from_json`) |
| `apps/adjustments/tests/test_wsm_service.py` | `WsmService` | ガードバンド計算、CSV 生成フォーマット検証 |
| `apps/adjustments/tests/test_line_bot.py` | `LineBotService` | LINE WORKS Bot API の呼び出し（モック使用） |
| `apps/adjustments/tests/test_lw_notification.py` | メール送信 + LINE 通知連携 | メール送信成功時の LINE WORKS 通知フロー |

### テスト対象外（未実装）

- `apps/accounts/tests.py` — 空ファイル。認証・ミドルウェアのテストは未実装。
- `apps/facilities/tests.py` — 空ファイル。施設検索 API・GB 計算のテストは未実装。

---

## 静的解析 (Ruff)

```bash
# コードチェック
docker exec rf_finder_web ruff check .

# 自動修正
docker exec rf_finder_web ruff check --fix .

# フォーマット
docker exec rf_finder_web ruff format .
```

設定は `pyproject.toml` に記載。マイグレーションファイルはチェック対象外 (`exclude = ["**/migrations/*"]`)。

---

## デバッグ手法

### ログ確認

```bash
# Web コンテナのログ
docker logs rf_finder_web

# DB コンテナのログ
docker logs rf_finder_db

# リアルタイム追跡
docker logs -f rf_finder_web
```

### 監査ログ (AuditLog)

管理画面 (`/admin/accounts/auditlog/`) でユーザー操作ログを確認できる。
ログ種別: `LOGIN`, `PDF_EXPORT`, `EXCEL_EXPORT`, `CSV_EXPORT`, `EMAIL_SEND`, `DROPBOX_BACKUP`, `DROPBOX_RESTORE`, `DB_BACKUP` など。

### Django シェル

```bash
docker exec -it rf_finder_web python manage.py shell
```

---

## 自動テスト (Playwright)

UI の動作確認には Playwright を使用する予定です。

> 現在 E2E テストは未実装。今後、フォーム入力・PDF 生成・メール送信フローの自動テストを追加予定。
