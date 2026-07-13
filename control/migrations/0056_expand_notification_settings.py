# Generated manually — adds 5 new event toggle fields to NotificationSettings

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('control', '0055_notificationsettings'),
    ]

    operations = [
        migrations.AddField(
            model_name='notificationsettings',
            name='notify_user_suspended',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='notificationsettings',
            name='notify_user_unsuspended',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='notificationsettings',
            name='notify_user_terminated',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='notificationsettings',
            name='notify_backup_created',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='notificationsettings',
            name='notify_script_installed',
            field=models.BooleanField(default=False),
        ),
    ]
