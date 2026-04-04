import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'panel.settings')
django.setup()
from control.models import package, user, domain, mernname, pythonname
from django.contrib.auth.models import User

user.objects.filter(username='macdomain.test').delete()
User.objects.filter(username='macdomain.test').delete()
domain.objects.filter(domain='macdomain.test').delete()
mernname.objects.filter(domain='macdomain.test').delete()
pythonname.objects.filter(domain='macdomain.test').delete()
package.objects.filter(name='ProPlan').delete()

print("Cleaned up test user, package, and apps!")
