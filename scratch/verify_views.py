import sys, os, json, requests
sys.path.insert(0, "/var/www/panel")
os.chdir("/var/www/panel")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "panel.settings")
import django; django.setup()

from control import views
print("Views imported OK")

from django.test import RequestFactory
from django.contrib.sessions.backends.db import SessionStore

factory = RequestFactory()
req = factory.get("/api/social/inbox/")
req.session = SessionStore()
req.session["domain"] = "rkrawat1907"
req.session["auth_user"] = "rkrawat1907"
req.session.save()

try:
    resp = views.social_inbox(req, "rkrawat1907")
    data = json.loads(resp.content)
    print("")
    print("=== SOCIAL INBOX ===")
    print("Status:", data.get("status"))
    print("Message count:", data.get("count"))
    for m in data.get("messages", []):
        txt = m.get("text", "")[:80]
        print("  [%s] %s: %s | type=%s" % (m.get("platform"), m.get("author_name"), txt, m.get("type")))
except Exception as e:
    print("Inbox error:", e)
    import traceback; traceback.print_exc()

try:
    req2 = factory.get("/api/social/mentions/")
    req2.session = SessionStore()
    req2.session["domain"] = "rkrawat1907"
    req2.session["auth_user"] = "rkrawat1907"
    req2.session.save()
    resp2 = views.social_mentions(req2, "rkrawat1907")
    data2 = json.loads(resp2.content)
    print("")
    print("=== SOCIAL MENTIONS ===")
    print("Status:", data2.get("status"))
    print("Mention count:", data2.get("count"))
    print("Stats:", json.dumps(data2.get("stats", {}), indent=2))
    for m in data2.get("mentions", []):
        txt = m.get("text", "")[:80]
        print("  [%s] %s: %s | type=%s" % (m.get("platform"), m.get("author_name"), txt, m.get("mention_type")))
except Exception as e:
    print("Mentions error:", e)
    import traceback; traceback.print_exc()
