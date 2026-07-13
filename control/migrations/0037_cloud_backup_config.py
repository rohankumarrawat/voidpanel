from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('control', '0036_reseller_profile'),
    ]

    operations = [
        migrations.CreateModel(
            name='CloudBackupConfig',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('domain', models.CharField(max_length=255, unique=True, help_text='Domain this config belongs to')),
                ('provider', models.CharField(choices=[('gcs', 'Google Cloud Storage'), ('s3', 'Amazon S3')], default='gcs', max_length=10)),
                ('gcs_bucket', models.CharField(blank=True, max_length=220, help_text='GCS bucket name')),
                ('gcs_key_json', models.TextField(blank=True, help_text='Service Account JSON key')),
                ('s3_bucket', models.CharField(blank=True, max_length=220)),
                ('s3_access_key', models.CharField(blank=True, max_length=220)),
                ('s3_secret_key', models.CharField(blank=True, max_length=255)),
                ('s3_region', models.CharField(blank=True, default='us-east-1', max_length=60)),
                ('auto_backup_enabled', models.BooleanField(default=False)),
                ('auto_schedule_preset', models.CharField(choices=[('daily', 'Daily at 2:00 AM'), ('weekly', 'Weekly (Sunday 2:00 AM)'), ('custom', 'Custom Cron')], default='daily', max_length=20)),
                ('auto_schedule_cron', models.CharField(blank=True, default='0 2 * * *', max_length=100)),
                ('sync_after_backup', models.BooleanField(default=False)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'Cloud Backup Config',
                'verbose_name_plural': 'Cloud Backup Configs',
            },
        ),
    ]
