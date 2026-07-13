from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('data', '0035_updates_migration_fields'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='EmailOrder',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('domain', models.CharField(help_text='Customer domain, e.g. mycompany.com', max_length=200)),
                ('billing_cycle', models.CharField(default='monthly', max_length=20)),
                ('price', models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ('status', models.CharField(
                    choices=[
                        ('pending_payment', 'Pending Payment'),
                        ('provisioning', 'Provisioning'),
                        ('active', 'Active'),
                        ('failed', 'Failed'),
                        ('cancelled', 'Cancelled'),
                    ],
                    default='pending_payment',
                    max_length=30,
                )),
                ('provision_response', models.JSONField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('user', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='email_orders',
                    to=settings.AUTH_USER_MODEL,
                )),
                ('email_plan', models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name='orders',
                    to='data.emailplan',
                )),
                ('invoice', models.OneToOneField(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='email_order',
                    to='data.invoice',
                )),
            ],
            options={
                'verbose_name': 'Email Order',
                'ordering': ['-created_at'],
            },
        ),
    ]
