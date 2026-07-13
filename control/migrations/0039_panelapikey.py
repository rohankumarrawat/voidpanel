from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('control', '0038_installedscript_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='PanelAPIKey',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('key', models.CharField(max_length=64, unique=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('label', models.CharField(
                    blank=True, default='Default Provisioning Key',
                    help_text='Friendly label for this key',
                    max_length=120,
                )),
            ],
            options={
                'verbose_name': 'Panel API Key',
                'verbose_name_plural': 'Panel API Keys',
            },
        ),
    ]
