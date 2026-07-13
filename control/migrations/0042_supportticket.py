from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('control', '0040_apitoken'),
    ]

    operations = [
        migrations.CreateModel(
            name='SupportTicket',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('ticket_id', models.CharField(editable=False, max_length=16, unique=True)),
                ('subject', models.CharField(max_length=255)),
                ('department', models.CharField(
                    choices=[
                        ('Technical Support', 'Technical Support'),
                        ('Billing', 'Billing'),
                        ('Sales', 'Sales'),
                        ('Abuse', 'Abuse'),
                    ],
                    default='Technical Support',
                    max_length=60,
                )),
                ('priority', models.CharField(
                    choices=[
                        ('low', 'Low'), ('medium', 'Medium'),
                        ('high', 'High'), ('urgent', 'Urgent'),
                    ],
                    default='medium',
                    max_length=20,
                )),
                ('status', models.CharField(
                    choices=[
                        ('open', 'Open'), ('in_progress', 'In Progress'),
                        ('resolved', 'Resolved'), ('closed', 'Closed'),
                    ],
                    default='open',
                    max_length=20,
                )),
                ('message', models.TextField()),
                ('created_by', models.CharField(help_text='Username of superadmin who created it', max_length=150)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'Support Ticket',
                'verbose_name_plural': 'Support Tickets',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='TicketReply',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('ticket', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='replies',
                    to='control.supportticket',
                )),
                ('author', models.CharField(max_length=150)),
                ('is_staff', models.BooleanField(default=False)),
                ('message', models.TextField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={'ordering': ['created_at']},
        ),
    ]
