from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('data', '0028_wordpress_installation'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [

        # ── EmailPlan ─────────────────────────────────────────────────────────
        migrations.CreateModel(
            name='EmailPlan',
            fields=[
                ('id',                   models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name',                 models.CharField(max_length=80)),
                ('slug',                 models.SlugField(max_length=90, unique=True)),
                ('short_description',    models.CharField(blank=True, max_length=200)),
                ('max_mailboxes',        models.PositiveIntegerField(default=5)),
                ('storage_per_mailbox_gb', models.PositiveIntegerField(default=5)),
                ('monthly_price',        models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ('is_active',            models.BooleanField(default=True)),
                ('is_featured',          models.BooleanField(default=False)),
                ('sort_order',           models.PositiveIntegerField(default=0)),
                ('created_at',           models.DateTimeField(auto_now_add=True)),
                ('updated_at',           models.DateTimeField(auto_now=True)),
                ('server', models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='email_plans',
                    to='data.voidpanelserver',
                )),
            ],
            options={'ordering': ['sort_order', 'monthly_price'], 'verbose_name': 'Email Plan'},
        ),

        # ── EmailService ─────────────────────────────────────────────────────
        migrations.CreateModel(
            name='EmailService',
            fields=[
                ('id',            models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('domain',        models.CharField(max_length=120)),
                ('status',        models.CharField(
                    choices=[('pending','Pending'),('active','Active'),('suspended','Suspended'),('terminated','Terminated')],
                    default='pending', max_length=20,
                )),
                ('billing_cycle', models.CharField(
                    choices=[('monthly','Monthly'),('quarterly','Quarterly'),('annually','Annually')],
                    default='monthly', max_length=20,
                )),
                ('monthly_price', models.DecimalField(decimal_places=2, default=0, max_digits=8)),
                ('next_due_date', models.DateField(blank=True, null=True)),
                ('panel_url',     models.URLField(blank=True)),
                ('webmail_url',   models.URLField(blank=True)),
                ('max_mailboxes', models.PositiveIntegerField(default=5)),
                ('created_at',    models.DateTimeField(auto_now_add=True)),
                ('updated_at',    models.DateTimeField(auto_now=True)),
                ('user', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='email_services',
                    to=settings.AUTH_USER_MODEL,
                )),
                ('plan', models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='subscriptions',
                    to='data.emailplan',
                )),
                ('server', models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='email_services',
                    to='data.voidpanelserver',
                )),
            ],
            options={'ordering': ['-created_at'], 'verbose_name': 'Email Service'},
        ),

        # ── EmailMailbox ─────────────────────────────────────────────────────
        migrations.CreateModel(
            name='EmailMailbox',
            fields=[
                ('id',            models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('email_address', models.EmailField(unique=True)),
                ('password',      models.CharField(blank=True, max_length=255)),
                ('created_at',    models.DateTimeField(auto_now_add=True)),
                ('service', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='mailboxes',
                    to='data.emailservice',
                )),
            ],
            options={'ordering': ['email_address'], 'verbose_name': 'Email Mailbox'},
        ),
    ]
