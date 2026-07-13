from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('control', '0039_panelapikey'),
    ]

    operations = [
        migrations.CreateModel(
            name='APIToken',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('key', models.CharField(db_index=True, max_length=80, unique=True)),
                ('label', models.CharField(help_text='Friendly name for this token', max_length=120)),
                ('owner_type', models.CharField(
                    choices=[('superadmin', 'Super Admin'), ('reseller', 'Reseller')],
                    default='superadmin',
                    max_length=20,
                )),
                ('reseller', models.ForeignKey(
                    blank=True,
                    help_text='If set, this token belongs to this reseller',
                    null=True,
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='api_tokens',
                    to='control.resellerprofile',
                )),
                ('scopes', models.JSONField(
                    default=list,
                    help_text='List of allowed scope strings',
                )),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('last_used_at', models.DateTimeField(blank=True, null=True)),
                ('created_by', models.CharField(
                    blank=True,
                    help_text='Username who created this token',
                    max_length=150,
                )),
            ],
            options={
                'verbose_name': 'API Token',
                'verbose_name_plural': 'API Tokens',
                'ordering': ['-created_at'],
            },
        ),
    ]
