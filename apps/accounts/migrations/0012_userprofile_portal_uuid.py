"""
shin•on Portal との JWT 連携のために UserProfile に portal_uuid フィールドを追加する。

portal_uuid は Portal の User.username（不変 UUID）に対応し、
PortalJWTMiddleware が初回ログイン時に email マッチングで自動設定する。
"""

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('accounts', '0011_emailtemplate_name'),
    ]

    operations = [
        migrations.AddField(
            model_name='userprofile',
            name='portal_uuid',
            field=models.CharField(
                blank=True,
                db_index=True,
                help_text='shin•on Portal の portal_uuid（不変ID）。JWT 連携時に自動設定される。',
                max_length=100,
                null=True,
                unique=True,
                verbose_name='ポータルUUID',
            ),
        ),
    ]
