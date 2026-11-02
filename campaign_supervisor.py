import os, sys, django, time, threading, gc
sys.path.insert(0, '/var/www/panel')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'panel.settings')
django.setup()

from django.db import reset_queries, close_old_connections
from control.models import MarketingCampaign
from control.views import _dispatch_campaign_worker, _dispatch_whatsapp_campaign_worker, is_campaign_worker_running

active_threads = {}

print('VoidPanel Campaign Supervisor started successfully with lock protection and memory management.', flush=True)

while True:
    try:
        close_old_connections()
        reset_queries()
        running_camps = list(MarketingCampaign.objects.filter(status='running'))
        for camp in running_camps:
            t = active_threads.get(camp.id)
            thread_alive = (t is not None and t.is_alive())

            # Only spawn if neither this supervisor nor another process (e.g. uWSGI web worker) is currently running it
            if not thread_alive and not is_campaign_worker_running(camp.id):
                print(f'Starting persistent worker for Campaign #{camp.id}: {camp.name} ({camp.channel})...', flush=True)
                if camp.channel == 'whatsapp':
                    t = threading.Thread(target=_dispatch_whatsapp_campaign_worker, args=(camp.id, camp.domain), daemon=True)
                else:
                    t = threading.Thread(target=_dispatch_campaign_worker, args=(camp.id, camp.domain), daemon=True)
                t.start()
                active_threads[camp.id] = t
        
        # Clean dead thread references
        dead_keys = [cid for cid, th in list(active_threads.items()) if not th.is_alive()]
        for cid in dead_keys:
            del active_threads[cid]

        gc.collect()
    except Exception as e:
        print(f'Error in supervisor loop: {e}', flush=True)
    time.sleep(10)

