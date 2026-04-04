import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'panel.settings')
django.setup()

from control.models import package, user, domain
from django.contrib.auth.models import User

# 1. Create Package
p, _ = package.objects.get_or_create(name='ProPlan', defaults={
    'storage': '50000', 'bandwidth': '500000', 'databases': '10',
    'subdomain': '5', 'ftp': '2', 'email': '5', 'ftp1_size': '2000'
})

# 2. Create Django Auth User
u, created = User.objects.get_or_create(username='macdomain.test')
if created:
    u.set_password('macpass123')
    u.save()

# 3. Create Control User and Domain
user.objects.get_or_create(username='macdomain.test', domain='macdomain.test', hosting_package='ProPlan', status=True)
domain.objects.get_or_create(domain='macdomain.test', dir='macdomain.test')

print("Test user macdomain.test created with password macpass123")
