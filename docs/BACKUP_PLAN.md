# データベースバックアップ・復元 (Dropbox API) 実装記録

## 1. 目的
システムの継続性を確保するため、Dropbox API を使用してデータベースのバックアップを外部クラウドストレージに保存し、障害時やデータ移行時に迅速に復元できる機能を実装する。

## 2. 実装概要
Django環境に最適化した実装を行い、OAuth 2.0 (Refresh Token対応) を使用して長期的な無人運用を可能にしている。単なるバックアップだけでなく、Web UIからの履歴参照とワンクリック復元に対応。

## 3. 技術仕様

### 3.1 使用ライブラリ・ツール
- `dropbox`: Python 用公式 SDK。
- `mysqldump`: MySQL データベースのダンプ作成用。
- `mysql`: データベース復元（リストア）時のインポート用。
- ※ Dockerコンテナ (`web`) 内に `default-mysql-client` をインストール済み。

### 3.2 データモデル (`apps/accounts/models.py`)
`DropboxToken` モデルで認証情報を永続化。`service_name` は一意。

### 3.3 サービス層 (`apps/adjustments/services/dropbox_service.py`)
`DropboxService` クラスにより以下の機能を提供。
- **認証管理**: トークンの有効性確認、自動リフレッシュ。
- **ファイル操作**: 
  - `upload_file`: 常にチャンクアップロードを使用し、メモリ使用量を一定に保つ。
  - `list_backups`: Dropbox上の履歴取得。JSTへの自動変換。
- **バックアップ実行 (`create_db_backup`)**:
  - `fcntl` によるファイルロックを実施し、二重起動を防止。
  - `mysqldump` を使用（整合性確保オプション、パスワード露出防止）。
- **復元実行 (`restore_db_from_backup`)**:
  - `fcntl` による排他制御と、`confirm=True` フラグによる誤操作防止。
  - バイナリモードでのインポートによりエンコーディング問題を回避。

## 4. 機能要件

### 4.1 保存・表示ルール
- ファイル名: `db_backup_yyyyMMdd_HHmmss.sql.gz` (日本時間 JST)
- 保存先: `/backups/YYYY/MM/DD/`

### 4.2 UI/UX
- ハンバーガーメニューからの独立した管理UI。
- 復元時の強力な警告とカスタムダイアログ。

## 5. 完了済みの改善項目 (最終レビュー反映)
- [x] シングルトンパターンの廃止
- [x] カスタム例外の導入
- [x] チャンクアップロードへの統一（メモリ最適化）
- [x] 排他制御 (fcntl) による二重起動防止
- [x] 復元時の安全装置 (confirmフラグ)
- [x] バイナリモードでの復元処理（エンコーディング問題解消）
- [x] Aware Datetime による日付処理の厳密化
- [x] timezone処理の最適化 (replaceの廃止)

## 6. スケジュール実行
- **実行頻度**: 毎日1回、深夜帯に cron 等で定期実行。
- **実装手段**: Django管理コマンド `python manage.py backup_db`。

## 7. 保持ポリシー (Retention Policy)
1. **直近世代管理**: 最新の **5個** を常時保持。
2. **月次アーカイブ**: 過去 **3ヶ月分** の各月末データを保持。
3. **削除の実行**: `clean_old_backups` により自動適用。
