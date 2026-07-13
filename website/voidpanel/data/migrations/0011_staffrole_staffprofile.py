from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('data', '0010_customerprofile_hostingservice_invoice_portalactivity_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='StaffRole',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=80, unique=True)),
                ('slug', models.SlugField(max_length=90, unique=True)),
                ('description', models.CharField(blank=True, max_length=255)),
                ('can_manage_clients', models.BooleanField(default=False)),
                ('can_manage_billing', models.BooleanField(default=False)),
                ('can_manage_support', models.BooleanField(default=False)),
                ('can_manage_infrastructure', models.BooleanField(default=False)),
                ('can_manage_staff', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'ordering': ['name'],
            },
        ),
        migrations.CreateModel(
            name='StaffProfile',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('display_title', models.CharField(blank=True, max_length=120)),
                ('department', models.CharField(blank=True, max_length=80)),
                ('status_message', models.CharField(blank=True, max_length=160)),
                ('is_portal_admin', models.BooleanField(default=False)),
                ('last_seen_at', models.DateTimeField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('role', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='staff_members', to='data.staffrole')),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='staff_profile', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['user__username'],
            },
        ),
    ]
