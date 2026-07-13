from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('control', '0062_marketingworkflow_marketingworkflowstep_and_more'),
    ]

    operations = [
        # ── package suite add-on fields ───────────────────────────────────
        migrations.AddField(
            model_name='package',
            name='includes_social',
            field=models.BooleanField(default=False, help_text='Include Social Media Suite'),
        ),
        migrations.AddField(
            model_name='package',
            name='social_plan',
            field=models.CharField(blank=True, default='', help_text='Social plan slug e.g. starter/growth/agency', max_length=50),
        ),
        migrations.AddField(
            model_name='package',
            name='includes_seo',
            field=models.BooleanField(default=False, help_text='Include SEO Suite'),
        ),
        migrations.AddField(
            model_name='package',
            name='seo_plan',
            field=models.CharField(blank=True, default='', help_text='SEO plan slug e.g. lite/standard/advanced', max_length=50),
        ),
        migrations.AddField(
            model_name='package',
            name='includes_marketing',
            field=models.BooleanField(default=False, help_text='Include Marketing Suite'),
        ),
        migrations.AddField(
            model_name='package',
            name='marketing_plan',
            field=models.CharField(blank=True, default='', help_text='Marketing plan slug e.g. starter/pro/agency', max_length=50),
        ),

        # ── SuitePlan model ───────────────────────────────────────────────
        migrations.CreateModel(
            name='SuitePlan',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('suite', models.CharField(
                    choices=[('social', 'Social Media'), ('seo', 'SEO'), ('marketing', 'Marketing')],
                    max_length=20,
                )),
                ('slug', models.SlugField(max_length=50)),
                ('name', models.CharField(max_length=100)),
                ('price_usd', models.DecimalField(decimal_places=2, default=0, max_digits=8)),
                ('limits', models.JSONField(default=dict, help_text='JSON dict of plan limits')),
                ('is_active', models.BooleanField(default=True)),
                ('sort_order', models.PositiveIntegerField(default=0)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'verbose_name': 'Suite Plan',
                'ordering': ['suite', 'sort_order'],
                'unique_together': {('suite', 'slug')},
            },
        ),

        # ── SuiteSubscription model ───────────────────────────────────────
        migrations.CreateModel(
            name='SuiteSubscription',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('suite', models.CharField(
                    choices=[('social', 'Social Media'), ('seo', 'SEO'), ('marketing', 'Marketing')],
                    max_length=20,
                )),
                ('plan', models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name='subscriptions',
                    to='control.suiteplan',
                )),
                ('email', models.EmailField(max_length=254, unique=True)),
                ('password', models.CharField(max_length=128, help_text='hashed')),
                ('first_name', models.CharField(blank=True, max_length=100)),
                ('last_name', models.CharField(blank=True, max_length=100)),
                ('company', models.CharField(blank=True, max_length=150)),
                ('is_active', models.BooleanField(default=True)),
                ('expires_at', models.DateTimeField(blank=True, null=True, help_text='Null = never expires')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('last_login', models.DateTimeField(blank=True, null=True)),
                ('hosting_domain', models.CharField(blank=True, default='', max_length=255)),
            ],
            options={
                'verbose_name': 'Suite Subscription',
                'ordering': ['-created_at'],
            },
        ),

        # ── SuiteSSOToken model ───────────────────────────────────────────
        migrations.CreateModel(
            name='SuiteSSOToken',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('token', models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ('suite', models.CharField(
                    choices=[('social', 'Social Media'), ('seo', 'SEO'), ('marketing', 'Marketing')],
                    max_length=20,
                )),
                ('hosting_domain', models.CharField(max_length=255)),
                ('user_email', models.EmailField()),
                ('plan_slug', models.CharField(default='starter', max_length=50)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('expires_at', models.DateTimeField()),
                ('used', models.BooleanField(default=False)),
            ],
            options={
                'verbose_name': 'Suite SSO Token',
                'ordering': ['-created_at'],
            },
        ),
    ]
