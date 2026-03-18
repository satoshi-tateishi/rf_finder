from django.db import migrations


class Migration(migrations.Migration):
    """
    auth.User.email にユニーク制約を追加する。

    同一メールアドレスで複数ユーザーが存在すると、PortalJWTMiddleware の
    email フォールバック検索で意図しないユーザーにマッピングされるリスクがある。
    RunSQL を使用するのは、auth.User は Django 組み込みモデルであり
    AlterField で直接変更できないため。

    注意: 既存 DB に重複メールが存在する場合は先にデータを整理してから適用すること。
    """

    dependencies = [
        ('accounts', '0013_remove_otp_fields'),
        ('auth', '0012_alter_user_first_name_max_length'),
    ]

    operations = [
        migrations.RunSQL(
            # MySQL 8.0+ の関数インデックスを使用。
            # IF(email = '', NULL, email) により空文字は NULL として扱われるため、
            # 未設定ユーザーが複数存在しても制約違反にならない。
            # 実際の Portal 連携ユーザーは必ず email が設定されるため重複を防止できる。
            sql=(
                "ALTER TABLE `auth_user` ADD UNIQUE INDEX `auth_user_email_nonempty_unique`"
                " ((IF(`email` = '', NULL, `email`)));"
            ),
            reverse_sql='ALTER TABLE `auth_user` DROP INDEX `auth_user_email_nonempty_unique`;',
        ),
    ]
