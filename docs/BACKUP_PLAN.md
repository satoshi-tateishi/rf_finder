# データベースバックアップ (Dropbox API) 実装計画

## 1. 目的
システムの継続性を確保するため、Dropbox API を使用してデータベースのバックアップを外部クラウドストレージに自動・手動で保存する機能を実装する。

## 2. 実装概要
`sample_app/shin-on_wiki` での実装実績に基づき、Django 環境に最適化した形で実装する。OAuth 2.0 (Refresh Token 対応) を使用し、長期的な無人バックアップを可能にする。

## 3. 技術仕様

### 3.1 使用ライブラリ
- `dropbox`: Python 用公式 SDK。
- `mysqldump`: MySQL データベースのダンプ作成用（Docker コンテナ内にインストール済みであること）。

### 3.2 データモデル (`apps/accounts/models.py`)
`DropboxToken` モデルを作成し、認証情報を永続化する。

| フィールド名 | 型 | 説明 |
| :--- | :--- | :--- |
| `service_name` | CharField | サービス名（デフォルト: 'backup'） |
| `access_token` | TextField | 現在のアクセストークン |
| `refresh_token` | TextField | リフレッシュトークン（長期利用に必須） |
| `token_type` | CharField | Bearer 等 |
| `account_id` | CharField | Dropbox アカウントID |
| `account_name` | CharField | 表示名（確認用） |
| `expires_at` | DateTimeField | アクセストークンの有効期限 |
| `created_at` | DateTimeField | 作成日時 |
| `updated_at` | DateTimeField | 更新日時 |

### 3.3 サービス層 (`apps/adjustments/services/dropbox_service.py`)
シングルトンパターンを採用し、以下の機能を提供する。
- **認証管理**: トークンの有効性確認、自動リフレッシュ。
- **ファイル操作**: バックアップファイルのアップロード、一覧取得、削除。
- **バックアップ実行**: `mysqldump` を実行し、生成された SQL ファイル（または圧縮ファイル）をアップロード。

### 3.4 認証フロー
1. 管理者が管理画面から「Dropbox 連携」を開始。
2. Dropbox の認証ページへリダイレクト。
3. コールバック URL で認可コードを受け取り、アクセストークンとリフレッシュトークンを取得・保存。

## 4. 機能要件

### 4.1 バックアップ対象
- MySQL データベースの全テーブル (`mysqldump`)。
- 必要に応じて `media/` フォルダの静的ファイル（画像等）も含めることを検討。

### 4.2 保存ルール
- ファイル名: `db_backup_yyyyMMdd_HHmmss.sql.gz`
- 保存先: `/{DROPBOX_FOLDER_PATH}/YYYY/MM/DD/`
- 保持期間: 直近 30 日分など、古いバックアップを自動削除する機能を検討。

### 4.3 アクセス制限
- **管理者限定**: バックアップの実行、設定、トークン管理は `is_superuser` または `is_staff` のみ可能とする。
- ログ監査機能 (`AuditLog`) と連携し、「誰がバックアップを実行したか」「自動バックアップの結果」を記録する。

## 5. 実装ステップ
1. **環境設定**: Dropbox App の作成 (App Console) と API Key の取得。`.env` への追加。
2. **モデル実装**: `DropboxToken` の作成とマイグレーション。
3. **サービス実装**: `DropboxService` の作成。
4. **認証 UI**: OAuth 連携用の View とテンプレートの作成。
5. **バックアップコマンド**: `python manage.py backup_db` コマンドの実装。
6. **スケジュール化**: Cron 等を使用して定期実行を設定（Docker 環境での運用を考慮）。
7. **管理画面統合**: ログ監査画面からバックアップの状態を確認できるようにする。
