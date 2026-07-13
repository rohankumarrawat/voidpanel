from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('data', '0058_add_email_category_and_whatsapp_template'),
    ]

    operations = [
        migrations.AddField(
            model_name='panellicenserecord',
            name='tier',
            field=models.CharField(
                choices=[
                    ('starter',   'Starter — Free'),
                    ('pro',       'Pro - Rs999/mo'),
                    ('advanced',  'Advanced - Rs2499/mo'),
                    ('unlimited', 'Unlimited - Rs4999/mo'),
                ],
                default='pro',
                help_text='License tier determines which features are available',
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name='panellicenserecord',
            name='is_trial',
            field=models.BooleanField(
                default=False,
                help_text='If True, this is a 30-day free trial',
            ),
        ),
        migrations.AddField(
            model_name='panellicenserecord',
            name='expires_at',
            field=models.DateTimeField(
                blank=True,
                null=True,
                help_text='License expiry. Null = lifetime/manual renewal',
            ),
        ),
        migrations.AddField(
            model_name='panellicenserecord',
            name='last_seen_ip',
            field=models.GenericIPAddressField(
                blank=True,
                null=True,
                help_text='Last IP that pinged validate (audit only)',
            ),
        ),
    ]
