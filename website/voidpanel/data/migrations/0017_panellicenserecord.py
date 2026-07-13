from django.db import migrations, models
import django.db.models.deletion
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('data', '0016_voidpanelserver_hostingpackage_server_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='PanelLicenseRecord',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('key', models.CharField(max_length=128, unique=True)),
                ('hostname', models.CharField(blank=True, help_text='Server hostname at activation time', max_length=255)),
                ('server_ip', models.GenericIPAddressField(blank=True, null=True)),
                ('status', models.CharField(
                    choices=[('active', 'Active'), ('suspended', 'Suspended'), ('revoked', 'Revoked')],
                    default='active', max_length=20,
                )),
                ('issued_at', models.DateTimeField(auto_now_add=True)),
                ('last_ping', models.DateTimeField(blank=True, help_text='Last time the panel pinged for validation', null=True)),
                ('notes', models.TextField(blank=True)),
                ('user', models.ForeignKey(
                    help_text='voidpanel.com account that owns this license',
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='panel_licenses',
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={
                'verbose_name': 'Panel License',
                'verbose_name_plural': 'Panel Licenses',
                'ordering': ['-issued_at'],
            },
        ),
    ]
