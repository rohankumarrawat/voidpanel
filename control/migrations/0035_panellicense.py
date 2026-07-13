from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('control', '0034_alter_ftpaccount_main_alter_mernname_main_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='PanelLicense',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('key', models.CharField(max_length=128, unique=True)),
                ('email', models.EmailField(help_text='voidpanel.com account email used to activate', max_length=254)),
                ('status', models.CharField(default='active', max_length=20)),
                ('hostname', models.CharField(blank=True, max_length=255)),
                ('issued_at', models.DateTimeField(blank=True, null=True)),
                ('last_checked', models.DateTimeField(blank=True, null=True)),
            ],
            options={
                'verbose_name': 'Panel License',
                'verbose_name_plural': 'Panel Licenses',
            },
        ),
    ]
