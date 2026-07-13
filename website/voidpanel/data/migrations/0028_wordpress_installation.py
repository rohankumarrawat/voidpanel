from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('data', '0027_hosting_sso_autosuspend'),
    ]

    operations = [
        migrations.CreateModel(
            name='WordPressInstallation',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('status', models.CharField(
                    choices=[
                        ('installing',  'Installing'),
                        ('active',      'Active'),
                        ('uninstalled', 'Uninstalled'),
                        ('failed',      'Failed'),
                    ],
                    default='installing',
                    max_length=20,
                )),
                ('wp_admin_user',  models.CharField(blank=True, max_length=60)),
                ('wp_admin_email', models.CharField(blank=True, max_length=120)),
                ('wp_admin_url',   models.URLField(blank=True)),
                ('wp_version',     models.CharField(blank=True, max_length=20)),
                ('db_name',        models.CharField(blank=True, max_length=80)),
                ('ssl_status', models.CharField(
                    choices=[
                        ('none',    'No SSL'),
                        ('pending', 'Pending'),
                        ('active',  'Active'),
                        ('expired', 'Expired'),
                    ],
                    default='none',
                    max_length=10,
                )),
                ('installed_at',   models.DateTimeField(blank=True, null=True)),
                ('uninstalled_at', models.DateTimeField(blank=True, null=True)),
                ('updated_at',     models.DateTimeField(auto_now=True)),
                ('service', models.OneToOneField(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='wp_installation',
                    to='data.hostingservice',
                )),
            ],
        ),
    ]
