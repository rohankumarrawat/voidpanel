from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('data', '0012_outboundemailprofile'),
    ]

    operations = [
        migrations.AddField(
            model_name='outboundemailprofile',
            name='purpose_category',
            field=models.CharField(
                choices=[
                    ('transactional', 'Transactional'),
                    ('billing', 'Billing'),
                    ('support', 'Support'),
                    ('security', 'Security'),
                    ('system', 'System Updates'),
                    ('marketing', 'Marketing'),
                    ('custom', 'Custom'),
                ],
                default='transactional',
                max_length=30,
            ),
        ),
    ]
