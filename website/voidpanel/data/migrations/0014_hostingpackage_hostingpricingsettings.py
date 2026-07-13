from django.db import migrations, models


def create_default_hosting_catalog(apps, schema_editor):
    HostingPackage = apps.get_model('data', 'HostingPackage')
    HostingPricingSettings = apps.get_model('data', 'HostingPricingSettings')

    HostingPricingSettings.objects.get_or_create(
        id=1,
        defaults={
            'title': 'Primary Pricing Rules',
            'storage_price_per_10gb': 1.50,
            'ram_price_per_1gb': 4.00,
            'cpu_price_per_core': 8.00,
            'bandwidth_100gb_price': 5.00,
            'bandwidth_500gb_price': 12.00,
            'bandwidth_1000gb_price': 20.00,
            'bandwidth_unmetered_price': 35.00,
            'storage_min_gb': 10,
            'storage_max_gb': 500,
            'ram_min_gb': 1,
            'ram_max_gb': 32,
            'cpu_min_cores': 1,
            'cpu_max_cores': 16,
            'quarterly_discount_percent': 0,
            'annual_discount_percent': 10,
        },
    )

    defaults = [
        {
            'name': 'Starter',
            'slug': 'starter',
            'short_description': 'Great for a first website or lightweight applications.',
            'storage_gb': 25,
            'ram_gb': 2,
            'cpu_cores': 1,
            'bandwidth_label': '500GB',
            'allowed_domains': 1,
            'monthly_price': 19.00,
            'sort_order': 1,
        },
        {
            'name': 'Professional',
            'slug': 'professional',
            'short_description': 'Balanced compute for production workloads and growing businesses.',
            'storage_gb': 80,
            'ram_gb': 8,
            'cpu_cores': 4,
            'bandwidth_label': '1TB',
            'allowed_domains': 10,
            'monthly_price': 49.00,
            'is_featured': True,
            'sort_order': 2,
        },
        {
            'name': 'Business',
            'slug': 'business',
            'short_description': 'Higher performance footprint for agencies and serious multi-site hosting.',
            'storage_gb': 200,
            'ram_gb': 16,
            'cpu_cores': 8,
            'bandwidth_label': 'Unmetered',
            'allowed_domains': 50,
            'monthly_price': 99.00,
            'sort_order': 3,
        },
    ]
    for item in defaults:
        HostingPackage.objects.get_or_create(slug=item['slug'], defaults=item)


class Migration(migrations.Migration):

    dependencies = [
        ('data', '0013_outboundemailprofile_purpose_category'),
    ]

    operations = [
        migrations.CreateModel(
            name='HostingPackage',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=80)),
                ('slug', models.SlugField(max_length=90, unique=True)),
                ('short_description', models.CharField(blank=True, max_length=180)),
                ('storage_gb', models.PositiveIntegerField(default=25)),
                ('ram_gb', models.PositiveIntegerField(default=2)),
                ('cpu_cores', models.PositiveIntegerField(default=1)),
                ('bandwidth_label', models.CharField(default='500GB', max_length=40)),
                ('allowed_domains', models.PositiveIntegerField(default=1)),
                ('monthly_price', models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ('is_featured', models.BooleanField(default=False)),
                ('is_active', models.BooleanField(default=True)),
                ('sort_order', models.PositiveIntegerField(default=0)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={'ordering': ['sort_order', 'monthly_price']},
        ),
        migrations.CreateModel(
            name='HostingPricingSettings',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(default='Primary Pricing Rules', max_length=120)),
                ('storage_price_per_10gb', models.DecimalField(decimal_places=2, default=1.5, max_digits=8)),
                ('ram_price_per_1gb', models.DecimalField(decimal_places=2, default=4.0, max_digits=8)),
                ('cpu_price_per_core', models.DecimalField(decimal_places=2, default=8.0, max_digits=8)),
                ('bandwidth_100gb_price', models.DecimalField(decimal_places=2, default=5.0, max_digits=8)),
                ('bandwidth_500gb_price', models.DecimalField(decimal_places=2, default=12.0, max_digits=8)),
                ('bandwidth_1000gb_price', models.DecimalField(decimal_places=2, default=20.0, max_digits=8)),
                ('bandwidth_unmetered_price', models.DecimalField(decimal_places=2, default=35.0, max_digits=8)),
                ('storage_min_gb', models.PositiveIntegerField(default=10)),
                ('storage_max_gb', models.PositiveIntegerField(default=500)),
                ('ram_min_gb', models.PositiveIntegerField(default=1)),
                ('ram_max_gb', models.PositiveIntegerField(default=32)),
                ('cpu_min_cores', models.PositiveIntegerField(default=1)),
                ('cpu_max_cores', models.PositiveIntegerField(default=16)),
                ('quarterly_discount_percent', models.PositiveIntegerField(default=0)),
                ('annual_discount_percent', models.PositiveIntegerField(default=10)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={'verbose_name_plural': 'Hosting pricing settings'},
        ),
        migrations.RunPython(create_default_hosting_catalog, migrations.RunPython.noop),
    ]
