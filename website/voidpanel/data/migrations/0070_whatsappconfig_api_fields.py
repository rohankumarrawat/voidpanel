from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('data', '0069_khatabookorder_owner_phone'),
    ]

    operations = [
        migrations.AddField(
            model_name='whatsappconfig',
            name='api_phone_number_id',
            field=models.CharField(
                blank=True, default='', max_length=100,
                help_text='Phone Number ID from Meta Business dashboard',
            ),
        ),
        migrations.AddField(
            model_name='whatsappconfig',
            name='api_waba_id',
            field=models.CharField(
                blank=True, default='', max_length=100,
                help_text='WhatsApp Business Account ID',
            ),
        ),
        migrations.AddField(
            model_name='whatsappconfig',
            name='api_access_token',
            field=models.TextField(
                blank=True, default='',
                help_text='Permanent access token from Meta Business',
            ),
        ),
        migrations.AddField(
            model_name='whatsappconfig',
            name='api_version',
            field=models.CharField(
                blank=True, default='v20.0', max_length=10,
                help_text='Graph API version (e.g. v20.0)',
            ),
        ),
    ]
