import os
import sys
import django

sys.path.append('/Users/rohan/Downloads/voidpanel-main')
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "voidpanel.settings")
django.setup()

from panel.models import mernname
apps = mernname.objects.all()
for app in apps:
    print(f"Domain: {app.domain}, Name: {app.name}, Port: {app.port}")
