from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('data', '0038_oauth_relay_state'),
    ]

    operations = [
        migrations.AddField(
            model_name='hostingpricingsettings',
            name='signup_bonus_chips',
            field=models.PositiveIntegerField(
                default=5000,
                help_text='Number of Void Chips automatically given to every new user on registration',
            ),
        ),
    ]
