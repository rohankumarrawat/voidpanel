from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('data', '0009_negative_review_content_positive_review_content'),
    ]

    operations = [
        migrations.CreateModel(
            name='CustomerProfile',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('company_name', models.CharField(blank=True, max_length=160)),
                ('phone', models.CharField(blank=True, max_length=30)),
                ('country', models.CharField(blank=True, default='India', max_length=80)),
                ('address', models.CharField(blank=True, max_length=255)),
                ('city', models.CharField(blank=True, max_length=80)),
                ('state', models.CharField(blank=True, max_length=80)),
                ('postal_code', models.CharField(blank=True, max_length=20)),
                ('portal_role', models.CharField(default='Account Owner', max_length=40)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='customer_profile', to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='HostingService',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('service_name', models.CharField(max_length=120)),
                ('domain', models.CharField(max_length=120)),
                ('product_type', models.CharField(default='Shared Hosting', max_length=80)),
                ('status', models.CharField(choices=[('active', 'Active'), ('pending', 'Pending'), ('suspended', 'Suspended')], default='pending', max_length=20)),
                ('billing_cycle', models.CharField(choices=[('monthly', 'Monthly'), ('quarterly', 'Quarterly'), ('annually', 'Annually')], default='monthly', max_length=20)),
                ('monthly_price', models.DecimalField(decimal_places=2, default=0, max_digits=8)),
                ('next_due_date', models.DateField()),
                ('server_hostname', models.CharField(blank=True, max_length=120)),
                ('panel_url', models.URLField(blank=True)),
                ('storage_gb', models.PositiveIntegerField(default=25)),
                ('bandwidth_gb', models.PositiveIntegerField(default=250)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='hosting_services', to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='Invoice',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('invoice_number', models.CharField(max_length=30, unique=True)),
                ('description', models.CharField(max_length=200)),
                ('status', models.CharField(choices=[('paid', 'Paid'), ('unpaid', 'Unpaid'), ('overdue', 'Overdue'), ('draft', 'Draft')], default='draft', max_length=20)),
                ('total', models.DecimalField(decimal_places=2, max_digits=10)),
                ('currency', models.CharField(default='USD', max_length=10)),
                ('due_date', models.DateField()),
                ('paid_date', models.DateField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='invoices', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['due_date', '-created_at'],
            },
        ),
        migrations.CreateModel(
            name='PortalActivity',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('category', models.CharField(default='account', max_length=40)),
                ('title', models.CharField(max_length=140)),
                ('description', models.CharField(blank=True, max_length=255)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='portal_activities', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='SupportTicket',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('ticket_number', models.CharField(max_length=30, unique=True)),
                ('subject', models.CharField(max_length=180)),
                ('department', models.CharField(default='Support', max_length=80)),
                ('priority', models.CharField(choices=[('low', 'Low'), ('medium', 'Medium'), ('high', 'High')], default='medium', max_length=20)),
                ('status', models.CharField(choices=[('open', 'Open'), ('answered', 'Answered'), ('in_progress', 'In Progress'), ('closed', 'Closed')], default='open', max_length=20)),
                ('last_reply_at', models.DateTimeField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='support_tickets', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-last_reply_at'],
            },
        ),
    ]
