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
| `created_at` | DateTimeField | 更新日時 |
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

---

## 6. コードレビューからの改善点と対応計画

### 6.1 `apps/adjustments/services/dropbox_service.py` のコードレビュー (by ChatGPT)

#### ① 大きな問題：大容量アップロード非対応
- **指摘**: `client.files_upload(f.read(), remote_path)` はファイルを全読み込みしてから一括アップロードするため、150MB制限に抵触し、DBが大きくなるとメモリ使用量が爆発する可能性がある。
- **対応計画**:
    - `upload_file` メソッドを修正し、Dropbox公式推奨の `files_upload_session_start()` を用いたチャンクアップロード方式を導入する。
    - 閾値（例: 150MB）を設定し、それ以下のファイルサイズの場合は既存の一括アップロード、それ以上の場合はチャンクアップロードに切り替えるロジックを実装する。

#### ② `mysqldump` セキュリティ懸念
- **指摘**: 一時的な `my.cnf` ファイルのパーミッションがデフォルトのままであり、他ユーザーから読める可能性がある。
- **対応計画**:
    - `create_db_backup` メソッド内で `cnf_path` を作成する際に、`os.chmod(cnf_path, 0o600)` を追加し、ファイルパーミッションを所有者のみ読み書き可能に設定する。

#### ③ `datetime.now()` を使用している
- **指摘**: `datetime.now()` を使用しているため、タイムゾーン不整合や `USE_TZ=True` 環境でのズレが生じる可能性がある。Djangoでは `django.utils.timezone.now()` を使用すべき。
- **対応計画**:
    - `create_db_backup` メソッド内の `timestamp` および `remote_dir` の生成に `datetime.now()` ではなく `timezone.now()` を使用するように修正する。

#### ④ Singleton設計はDjangoでは不要
- **指摘**: `DropboxService` クラスがシングルトンパターン (`_instance` を用いた実装) を採用しているが、Djangoのプロセスモデル（workerごとインスタンスが分かれる等）と相性が悪く、テスト時の副作用も出やすいため不要。
- **対応計画**:
    - `DropboxService` クラスからシングルトンパターンを削除し、通常のクラスとして実装する。(`__new__` メソッドと `_instance`, `_initialized` 関連のコードを削除)

#### ⑤ `get_token_model()` の設計
- **指摘**: `DropboxToken.objects.filter(service_name='backup').first()` の設計では、複数レコードができた場合に不安定になり、無言で1件を返す `.first()` の挙動が問題。
- **対応計画**:
    - `DropboxToken` モデルの `service_name` フィールドに `unique=True` 制約を追加する。
    - `get_token_model()` メソッドを `DropboxToken.objects.get(service_name='backup')` に変更し、単一レコードであることを保証する。

#### ⑥ 例外設計が雑
- **指摘**: すべて `Exception` で捕捉・スローしているため、呼び出し側で具体的なエラーハンドリングが難しい。
- **対応計画**:
    - Dropbox API関連のエラーや認証エラーなど、特定のシナリオに対応するカスタム例外クラス（例: `DropboxAuthError`, `DropboxBackupError`）を定義し、適切に使い分けるように修正する。

#### ⑦ 自動フォルダ作成未対応
- **指摘**: Dropboxは親フォルダが存在しないとエラーになるが、現在はフォルダ作成処理がない。
- **対応計画**:
    - `upload_file` メソッド、またはバックアップ処理の開始時に、アップロード先の `remote_dir` が存在するかを確認し、存在しない場合は `client.files_create_folder_v2()` を用いてフォルダを自動作成するロジックを追加する。

#### ⑧ バックアップ整合性オプション不足
- **指摘**: `mysqldump` の実行に `--single-transaction`, `--quick`, `--routines`, `--events`, `--triggers` などのオプションが不足しており、特にトランザクション系DBでの整合性に懸念がある。
- **対応計画**:
    - `create_db_backup` メソッド内の `mysqldump` コマンドに、上記の推奨オプションを追加する。

#### ⑨ バックアップ保持ポリシーがない
- **指摘**: バックアップファイルがどんどん溜まり、削除処理がないため、実運用では保持ポリシー（例: 30日以上削除、月次だけ残す、世代管理）が必要。
- **対応計画**:
    - `DropboxService` クラスに、古いバックアップファイルを定期的に削除する `clean_old_backups` メソッドを実装する。
    - 保持期間の設定をDjangoのsettingsに追加し、柔軟に設定できるようにする。
    - このメソッドを定期実行する仕組み（例: Django管理コマンド + Cron）を検討する。

#### ⑩ 並列実行対策なし
- **指摘**: もしcronが重なると、同時 `mysqldump` や同時 `upload` によりサーバー負荷が増大する可能性がある。
- **対応計画**:
    - バックアップ処理の開始時にロック機構（例: `fcntl.flock()` やデータベースにフラグ管理用のレコードを設ける）を導入し、複数のバックアップ処理が同時に実行されないようにする。

#### ⑪ ログに機密が出る可能性
- **指摘**: `logger.error(f'Database backup failed: {e}')` の `e` に `mysqldump` エラーからパスワードなどの機密情報が含まれる可能性がある。
- **対応計画**:
    - エラーログ出力時に `e` の内容を精査し、機密情報が含まれないようにフィルタリングするか、または `mysqldump` のエラーメッセージから機密情報（パスワードなど）をマスクする処理を追加する。
