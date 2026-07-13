"""
Celery application instance for VoidPanel.

Setup:
    pip install celery redis

Start worker (development):
    celery -A panel worker --loglevel=info

Start worker (production with supervisor):
    See /etc/supervisor/conf.d/celery.conf
"""
import os
from celery import Celery

# Tell Celery which Django settings module to use
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'panel.settings')

app = Celery('voidpanel')

# Load celery config from Django settings under the CELERY_ namespace
app.config_from_object('django.conf:settings', namespace='CELERY')

# Auto-discover tasks.py in every INSTALLED_APP
app.autodiscover_tasks()
