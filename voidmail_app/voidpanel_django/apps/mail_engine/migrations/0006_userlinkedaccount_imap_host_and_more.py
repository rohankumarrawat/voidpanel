# Generated for UserLinkedAccount IMAP & SMTP settings

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('mail_engine', '0005_systemsetting_ai_auto_approve_new_users_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='userlinkedaccount',
            name='imap_host',
            field=models.CharField(blank=True, default='', max_length=255),
        ),
        migrations.AddField(
            model_name='userlinkedaccount',
            name='imap_port',
            field=models.IntegerField(default=993),
        ),
        migrations.AddField(
            model_name='userlinkedaccount',
            name='imap_user',
            field=models.CharField(blank=True, default='', max_length=255),
        ),
        migrations.AddField(
            model_name='userlinkedaccount',
            name='imap_password',
            field=models.CharField(blank=True, default='', max_length=255),
        ),
        migrations.AddField(
            model_name='userlinkedaccount',
            name='imap_security',
            field=models.CharField(default='SSL/TLS', max_length=20),
        ),
        migrations.AddField(
            model_name='userlinkedaccount',
            name='smtp_host',
            field=models.CharField(blank=True, default='', max_length=255),
        ),
        migrations.AddField(
            model_name='userlinkedaccount',
            name='smtp_port',
            field=models.IntegerField(default=465),
        ),
        migrations.AddField(
            model_name='userlinkedaccount',
            name='smtp_user',
            field=models.CharField(blank=True, default='', max_length=255),
        ),
        migrations.AddField(
            model_name='userlinkedaccount',
            name='smtp_password',
            field=models.CharField(blank=True, default='', max_length=255),
        ),
        migrations.AddField(
            model_name='userlinkedaccount',
            name='smtp_security',
            field=models.CharField(default='SSL/TLS', max_length=20),
        ),
        migrations.AddField(
            model_name='userlinkedaccount',
            name='is_verified',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='userlinkedaccount',
            name='last_sync_error',
            field=models.TextField(blank=True, default=''),
        ),
    ]
