# CLAUDE.md

## 言語設定

**必ず日本語で回答してください。** コード内のコメント、コミットメッセージ、説明文など、すべてのコミュニケーションは日本語で行うこと。

## プロジェクト概要

**RF Finder** — 特定ラジオマイク（A帯）の施設別空きチャンネル検索・運用調整届の自動生成・送信を行う Web アプリケーション。

- **フレームワーク**: Django 4.2 / MySQL 8.0
- **認証**: shin•on Portal JWT (`portal_jwt` クッキー検証)
- **コンテナ**: Docker (web + db), Apache リバースプロキシ
- **静的解析**: Ruff (`pyproject.toml` 参照)

## デプロイ

このプロジェクトは GitHub Actions による CI/CD デプロイ自動化を行っています。

### ワークフロー概要 (`.github/workflows/deploy.yml`)

**トリガー**: `release` ブランチへの push

#### ジョブ構成

| ジョブ | 内容 |
|--------|------|
| `lint-python` | Ruff による Python 静的解析 |
| `test-python` | MySQL 8.0 を使った Django ユニットテスト |
| `deploy` | 上記2ジョブ成功後、SSH で自宅サーバーへ本番デプロイ |

#### デプロイ手順（サーバー側で自動実行）

1. `git reset --hard origin/release` で最新コードを取得
2. `docker compose -f docker-compose.prod.yml up -d --build` でコンテナ再構築
3. `manage.py migrate` でDBマイグレーション
4. `manage.py collectstatic` で静的ファイルを `static_root/` に集約
5. `static_root/` の所有権を `www-data` に変更（Apache が読み取れるよう設定）
6. 秘密鍵・`.env` のパーミッションをセキュアに設定 (`600`)

#### 必要な GitHub Secrets

| Secret | 内容 |
|--------|------|
| `DEPLOY_HOST` | デプロイ先サーバーのホスト名/IP |
| `DEPLOY_USER` | SSH ユーザー名 |
| `DEPLOY_KEY` | SSH 秘密鍵 |
| `DEPLOY_PATH` | サーバー上のプロジェクトパス |

## テスト実行

**開発環境でのテストは Docker コンテナ上で実行すること。** ホスト環境には Django や MySQL クライアントが入っていないため、`manage.py test` をホストから直接実行しても動作しない。

```bash
docker exec rf_finder_web python manage.py test
```

詳細な出力が必要な場合：

```bash
docker exec rf_finder_web python manage.py test --verbosity=2
```

## コード品質ルール

**git push 前に必ず Ruff チェックを実行すること。**

```bash
ruff check .
```

エラーがある場合は修正してから push する。自動修正できるものは `ruff check --fix .` で対応可。
設定は `pyproject.toml` を参照。

## ドキュメント一覧

### アーキテクチャ・機能仕様

| ドキュメント | 内容 |
|------------|------|
| [docs/PHASES.md](docs/PHASES.md) | 開発進捗・フェーズ別完了状況 |
| [docs/REFACTORING.md](docs/REFACTORING.md) | リファクタリング実績と残課題 |
| [docs/LINE_WORKS_SSO.md](docs/LINE_WORKS_SSO.md) | 認証フロー（Portal JWT 連携の概要） |
| [docs/06_APP_INTEGRATION_GUIDE.md](docs/06_APP_INTEGRATION_GUIDE.md) | shin•on Portal JWT 統合実装ガイド |
| [docs/LINE_WORKS_API.md](docs/LINE_WORKS_API.md) | LINE WORKS Bot API 技術リファレンス |
| [docs/PDF_MAPPING.md](docs/PDF_MAPPING.md) | 運用調整届 PDF/Excel フィールドマッピング |
| [docs/WSM_CSV_EXPORT.md](docs/WSM_CSV_EXPORT.md) | Sennheiser WSM 用 CSV フォーマット仕様 |
| [docs/LOG_AUDIT.md](docs/LOG_AUDIT.md) | 監査ログ (AuditLog) 実装仕様 |

### インフラ・運用

| ドキュメント | 内容 |
|------------|------|
| [docs/DEPLOYMENT_HOME_SERVER.md](docs/DEPLOYMENT_HOME_SERVER.md) | 自宅サーバーへの本番デプロイ手順 |
| [docs/BACKUP_PLAN.md](docs/BACKUP_PLAN.md) | Dropbox バックアップ・復元機能仕様 |
| [docs/DATA_IMPORT.md](docs/DATA_IMPORT.md) | 施設データ（郵便番号付与・CSV インポート）手順 |

### テスト・品質

| ドキュメント | 内容 |
|------------|------|
| [docs/TESTING.md](docs/TESTING.md) | テスト実行方法・デバッグ手法 |
