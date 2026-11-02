# Generated for UserDeletedVirtualEmail
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('mail_engine', '0006_userlinkedaccount_imap_host_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='UserDeletedVirtualEmail',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('email_id', models.CharField(db_index=True, max_length=255)),
                ('deleted_at', models.DateTimeField(auto_now_add=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='deleted_virtual_emails', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'unique_together': {('user', 'email_id')},
            },
        ),
    ]
