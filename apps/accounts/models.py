from django.db import models


class Member(models.Model):
    member_id_1 = models.CharField(max_length=3, verbose_name='会員番号')
    member_id_2 = models.CharField(max_length=4, verbose_name='会員番号2')
    name = models.CharField(max_length=255, verbose_name='会員名')
    department = models.CharField(max_length=255, blank=True, default='', verbose_name='部署')
    manager_name = models.CharField(max_length=255, verbose_name='運用担当者')
    phone = models.CharField(max_length=20, verbose_name='Tel')
    email = models.EmailField(verbose_name='E-mail')

    class Meta:
        verbose_name = '会員情報'
        verbose_name_plural = '会員情報'

    def __str__(self):
        return self.name


class EmailTemplate(models.Model):
    to_address = models.EmailField(verbose_name='送信先アドレス')
    cc_address = models.CharField(max_length=255, blank=True, default='', verbose_name='CC', help_text='カンマ区切りで複数指定可能。{ユーザーEメールアドレス} も使用できます。')
    subject = models.CharField(max_length=255, verbose_name='件名')
    body = models.TextField(verbose_name='本文')

    class Meta:
        verbose_name = 'メールテンプレート'
        verbose_name_plural = 'メールテンプレート'

    def __str__(self):
        return self.subject
