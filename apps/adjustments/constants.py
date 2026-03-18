# ステータス定義
STATUS_DRAFT = 'draft'
STATUS_SUBMITTED = 'submitted'

STATUS_CHOICES = [
    (STATUS_DRAFT, '下書き'),
    (STATUS_SUBMITTED, '送信済み'),
]

# 申請区分定義
APP_TYPE_NEW = 'new'
APP_TYPE_CHANGE = 'change'
APP_TYPE_DELETE = 'delete'

APP_TYPE_CHOICES = [
    (APP_TYPE_NEW, '新規'),
    (APP_TYPE_CHANGE, '変更'),
    (APP_TYPE_DELETE, '削除'),
]

# 申請区分の日本語マッピング
APP_TYPE_MAP = dict(APP_TYPE_CHOICES)
