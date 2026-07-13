from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('data', '0051_voidpanelserver_nameservers'),
        migrations.swappable_dependency('auth.User'),
    ]

    operations = [
        migrations.CreateModel(
            name='SuitePlan',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('suite', models.CharField(choices=[('social', 'Social Media Suite'), ('seo', 'SEO Suite'), ('marketing', 'Marketing Suite')], db_index=True, max_length=20)),
                ('name', models.CharField(max_length=120)),
                ('slug', models.SlugField(max_length=120, unique=True)),
                ('short_description', models.TextField(blank=True)),
                ('monthly_price', models.DecimalField(decimal_places=2, max_digits=10)),
                ('yearly_price', models.DecimalField(decimal_places=2, default=0, help_text='Annual price (total). Set 0 to disable yearly billing.', max_digits=10)),
                ('panel_plan_slug', models.CharField(blank=True, default='', help_text='Slug sent to panel API e.g. starter / growth / pro', max_length=50)),
                ('features', models.JSONField(default=list, help_text='List of feature strings shown on pricing card.')),
                ('limits', models.JSONField(default=dict, help_text='Dict of plan limits e.g. {"accounts":5,"posts_per_month":90}')),
                ('is_active', models.BooleanField(default=True)),
                ('is_featured', models.BooleanField(default=False, help_text='Highlight this plan as "Most Popular".')),
                ('sort_order', models.PositiveIntegerField(default=0)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('server', models.ForeignKey(blank=True, help_text='VoidPanel server that hosts this suite.', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='suite_plans', to='data.voidpanelserver')),
            ],
            options={
                'verbose_name': 'Suite Plan',
                'verbose_name_plural': 'Suite Plans',
                'ordering': ['suite', 'sort_order', 'monthly_price'],
            },
        ),
        migrations.CreateModel(
            name='SuiteService',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('suite', models.CharField(max_length=20)),
                ('service_name', models.CharField(max_length=150)),
                ('status', models.CharField(choices=[('pending', 'Pending'), ('active', 'Active'), ('suspended', 'Suspended'), ('cancelled', 'Cancelled')], default='pending', max_length=20)),
                ('billing_cycle', models.CharField(choices=[('monthly', 'Monthly'), ('annually', 'Annually')], default='monthly', max_length=20)),
                ('monthly_price', models.DecimalField(decimal_places=2, max_digits=10)),
                ('next_due_date', models.DateField(blank=True, null=True)),
                ('activated_at', models.DateTimeField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('sso_token', models.CharField(blank=True, max_length=64)),
                ('sso_token_expires', models.DateTimeField(blank=True, null=True)),
                ('plan', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='services', to='data.suiteplan')),
                ('server', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='suite_services', to='data.voidpanelserver')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='suite_services', to='auth.user')),
            ],
            options={
                'verbose_name': 'Suite Service',
                'verbose_name_plural': 'Suite Services',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='SuiteOrder',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('suite', models.CharField(max_length=20)),
                ('billing_cycle', models.CharField(default='monthly', max_length=20)),
                ('price', models.DecimalField(decimal_places=2, max_digits=10)),
                ('status', models.CharField(choices=[('pending_payment', 'Pending Payment'), ('paid', 'Paid'), ('failed', 'Failed'), ('cancelled', 'Cancelled')], default='pending_payment', max_length=20)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('invoice', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='suite_order', to='data.invoice')),
                ('plan', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='orders', to='data.suiteplan')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='suite_orders', to='auth.user')),
            ],
            options={
                'verbose_name': 'Suite Order',
                'ordering': ['-created_at'],
            },
        ),
    ]
