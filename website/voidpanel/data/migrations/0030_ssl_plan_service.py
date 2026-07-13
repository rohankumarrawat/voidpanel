from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('data', '0029_email_plan_service_mailbox'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [

        # ── SSLPlan ───────────────────────────────────────────────────────────
        migrations.CreateModel(
            name='SSLPlan',
            fields=[
                ('id',               models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name',             models.CharField(max_length=80)),
                ('slug',             models.SlugField(max_length=90, unique=True)),
                ('short_description',models.CharField(blank=True, max_length=200)),
                ('ssl_type', models.CharField(
                    choices=[('dv', 'Domain Validated (DV) — Single Domain'),
                              ('wildcard', 'Wildcard — *.domain.com'),
                              ('multi', 'Multi-Domain — Up to 5 SANs')],
                    default='dv', max_length=20,
                )),
                ('validity_days',    models.PositiveIntegerField(default=90)),
                ('max_domains',      models.PositiveIntegerField(default=1)),
                ('monthly_price',    models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ('annual_price',     models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ('auto_renew',       models.BooleanField(default=True)),
                ('is_active',        models.BooleanField(default=True)),
                ('is_featured',      models.BooleanField(default=False)),
                ('sort_order',       models.PositiveIntegerField(default=0)),
                ('created_at',       models.DateTimeField(auto_now_add=True)),
                ('updated_at',       models.DateTimeField(auto_now=True)),
                ('server', models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='ssl_plans',
                    to='data.voidpanelserver',
                )),
            ],
            options={'ordering': ['sort_order', 'monthly_price'], 'verbose_name': 'SSL Plan'},
        ),

        # ── SSLService ────────────────────────────────────────────────────────
        migrations.CreateModel(
            name='SSLService',
            fields=[
                ('id',             models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('domain',         models.CharField(max_length=120)),
                ('san_domains',    models.JSONField(blank=True, default=list)),
                ('status', models.CharField(
                    choices=[('pending','Pending'),('active','Active'),('expiring','Expiring Soon'),
                              ('expired','Expired'),('failed','Failed'),('suspended','Suspended')],
                    default='pending', max_length=20,
                )),
                ('monthly_price',  models.DecimalField(decimal_places=2, default=0, max_digits=8)),
                ('next_due_date',  models.DateField(blank=True, null=True)),
                ('cert_path',      models.CharField(blank=True, max_length=255)),
                ('issued_at',      models.DateTimeField(blank=True, null=True)),
                ('expires_at',     models.DateTimeField(blank=True, null=True)),
                ('last_renewed_at',models.DateTimeField(blank=True, null=True)),
                ('notes',          models.TextField(blank=True)),
                ('created_at',     models.DateTimeField(auto_now_add=True)),
                ('updated_at',     models.DateTimeField(auto_now=True)),
                ('user', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='ssl_services',
                    to=settings.AUTH_USER_MODEL,
                )),
                ('plan', models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='subscriptions',
                    to='data.sslplan',
                )),
                ('server', models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='ssl_services',
                    to='data.voidpanelserver',
                )),
            ],
            options={'ordering': ['-created_at'], 'verbose_name': 'SSL Service'},
        ),
    ]
