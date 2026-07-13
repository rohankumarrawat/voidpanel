from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('control', '0063_suite_fields'),
    ]

    operations = [
        # ── PanelLicense: add tier, is_trial, expires_at, features_json ──────
        migrations.AddField(
            model_name='panellicense',
            name='tier',
            field=models.CharField(
                max_length=20, default='starter',
                help_text='License tier: starter / pro / advanced / unlimited',
            ),
        ),
        migrations.AddField(
            model_name='panellicense',
            name='is_trial',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='panellicense',
            name='expires_at',
            field=models.DateTimeField(null=True, blank=True),
        ),
        migrations.AddField(
            model_name='panellicense',
            name='features_json',
            field=models.JSONField(
                default=dict, blank=True,
                help_text='Feature flags dict from api/license/validate',
            ),
        ),
        # Make email blank=True (was required before)
        migrations.AlterField(
            model_name='panellicense',
            name='email',
            field=models.EmailField(
                help_text='voidpanel.com account email used to activate',
                blank=True,
            ),
        ),

        # ── PanelBranding: new singleton model ────────────────────────────────
        migrations.CreateModel(
            name='PanelBranding',
            fields=[
                ('id',                   models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('panel_name',           models.CharField(max_length=60, default='VoidPanel', help_text='Brand name in sidebar and browser title')),
                ('panel_logo_url',       models.URLField(blank=True, default='', help_text='URL to custom logo image (leave blank for default)')),
                ('favicon_url',          models.URLField(blank=True, default='', help_text='URL to custom favicon .ico/.png (32x32)')),
                ('primary_color',        models.CharField(max_length=20, default='#6366f1', help_text='CSS hex accent colour')),
                ('support_url',          models.URLField(blank=True, default='', help_text='Support/helpdesk link (replaces default tickets link)')),
                ('hide_voidpanel_badge', models.BooleanField(default=False, help_text='Hide "Powered by VoidPanel" footer badge')),
                ('updated_at',           models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name':        'Panel Branding',
                'verbose_name_plural': 'Panel Branding',
            },
        ),
    ]
