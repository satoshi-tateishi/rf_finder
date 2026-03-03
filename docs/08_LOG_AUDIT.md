# ログ監査機能 (Audit Log) 実装仕様

## 1. 目的

システムの利用状況を可視化し、セキュリティの向上と運用実態の把握を行う。「誰が」「いつ」「どのデータに対して」「どのような操作（出力・送信）を行ったか」を記録する。

## 2. 実装状況

`AuditLog` モデルは `apps/accounts` アプリ内に実装済み・稼働中。

### 2.1 データモデル (`apps/accounts/models.py`)

| フィールド名 | 型 | 説明 |
| :--- | :--- | :--- |
| `user` | ForeignKey | 操作を行ったユーザー（未認証の場合は null） |
| `action` | CharField | 操作種別（下記「アクション種別」参照） |
| `description` | TextField | 操作の詳細（ファイル名、送信先アドレス、催事名など） |
| `ip_address` | GenericIPAddressField | 操作元の IP アドレス |
| `timestamp` | DateTimeField | 操作日時（自動付与） |
| `content_type` | ForeignKey | 関連するモデル（例: OperationAdjustment） |
| `object_id` | PositiveIntegerField | 関連するオブジェクトの ID |

### 2.2 ユーティリティ関数 (`apps/accounts/utils.py`)

```python
from apps.accounts.utils import log_action

log_action(
    user=request.user,
    action='PDF_EXPORT',
    description='催事名: ハムレット',
    request=request,
    obj=adjustment_instance,  # 任意
)
```

### 2.3 ログ記録対象アクション

| アクション定数 | タイミング |
| :--- | :--- |
| `LOGIN` | PortalJWTMiddleware でのセッション確立時 |
| `PDF_EXPORT` | PDF 生成・ダウンロード時 |
| `EXCEL_EXPORT` | Excel 生成・ダウンロード時 |
| `CSV_EXPORT` | WSM CSV エクスポート時 |
| `EMAIL_SEND` | 特ラ機構へのメール送信時（成功/失敗含む） |
| `DROPBOX_BACKUP` | Dropbox バックアップ実行時 |
| `DROPBOX_RESTORE` | Dropbox からの DB 復元時 |

## 3. 管理画面

管理画面 (`/admin/accounts/auditlog/`) でログを閲覧できる。

- **アクセス制限**: `is_staff` かつ `is_superuser` のユーザーのみ閲覧可能 (ReadOnly)。
- **フィルタリング**: ユーザー、操作種別、期間で絞り込み可能。
- **検索**: ユーザー名・IP アドレス・説明文で全文検索可能。
- **編集・削除は禁止**: 証跡改ざん防止のため ReadOnly として設定。

## 4. 監査ログ API

管理者権限ユーザーは以下の API でログを取得できる。

```
GET /auth/audit-logs/
    ?action=PDF_EXPORT     # 操作種別でフィルタ
    &user_id=1             # ユーザー ID でフィルタ
    &start_date=2025-01-01 # 期間フィルタ
    &end_date=2025-12-31
```

実装: `apps/accounts/views.py` の `list_audit_logs` ビュー（管理者のみアクセス可）。
