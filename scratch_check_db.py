import os, sys
sys.path.insert(0, '/var/www/panel')
os.environ["DJANGO_SETTINGS_MODULE"] = "panel.settings"
import django
django.setup()
from control.models import domain, user
for u in user.objects.all():
    print("username:", u.username, "domain:", u.domain)
for d in domain.objects.all():
    print("domain_obj:", d.domain, "dir:", d.dir)
