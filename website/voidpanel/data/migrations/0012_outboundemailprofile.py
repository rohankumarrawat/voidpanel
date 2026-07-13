from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('data', '0011_staffrole_staffprofile'),
    ]

    operations = [
        migrations.CreateModel(
            name='OutboundEmailProfile',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('profile_name', models.CharField(max_length=120)),
                ('from_name', models.CharField(blank=True, max_length=120)),
                ('from_email', models.EmailField(max_length=254)),
                ('reply_to_email', models.EmailField(blank=True, max_length=254)),
                ('smtp_host', models.CharField(max_length=160)),
                ('smtp_port', models.PositiveIntegerField(default=587)),
                ('smtp_username', models.CharField(blank=True, max_length=160)),
                ('smtp_password', models.CharField(blank=True, max_length=255)),
                ('use_tls', models.BooleanField(default=True)),
                ('use_ssl', models.BooleanField(default=False)),
                ('is_active', models.BooleanField(default=True)),
                ('is_default', models.BooleanField(default=False)),
                ('send_on_purchase', models.BooleanField(default=True)),
                ('send_on_invoice_created', models.BooleanField(default=True)),
                ('send_on_payment_received', models.BooleanField(default=True)),
                ('send_on_service_activated', models.BooleanField(default=True)),
                ('send_on_service_suspended', models.BooleanField(default=False)),
                ('send_on_service_unsuspended', models.BooleanField(default=False)),
                ('send_on_service_terminated', models.BooleanField(default=False)),
                ('send_on_ticket_opened', models.BooleanField(default=True)),
                ('send_on_ticket_reply', models.BooleanField(default=True)),
                ('send_on_login_success', models.BooleanField(default=False)),
                ('send_on_password_reset', models.BooleanField(default=True)),
                ('send_on_account_created', models.BooleanField(default=True)),
                ('send_on_security_alert', models.BooleanField(default=True)),
                ('send_on_system_update', models.BooleanField(default=False)),
                ('send_on_domain_expiry_warning', models.BooleanField(default=True)),
                ('send_on_ssl_expiry_warning', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'ordering': ['-is_default', 'profile_name'],
            },
        ),
    ]
