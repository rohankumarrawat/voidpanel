import os, sys, django, json

sys.path.insert(0, '/Users/rohan/Desktop/voidpanel')
os.environ['DJANGO_SETTINGS_MODULE'] = 'panel.settings'
django.setup()

from control.models import SocialMediaAPIConfig, DomainSocialAPIConfig
from control.views import _get_social_portal_data_ctx
from django.test import RequestFactory
from django.contrib.auth.models import AnonymousUser

factory = RequestFactory()
request = factory.get('/control/social-portal/fast.voidpanel.com/')
request.user = AnonymousUser()

# Configure SocialMediaAPIConfig with Admin 1-Click
cfg = SocialMediaAPIConfig.get()
cfg.enabled_platforms = ['fb', 'ig', 'tw', 'li', 'yt', 'tt', 'pi', 'th', 'gb']
cfg.admin_enabled_platforms = ['fb', 'tw', 'yt', 'li']
cfg.auth_modes = {'fb': 'admin', 'tw': 'admin', 'yt': 'admin', 'li': 'admin', 'ig': 'user'}
cfg.save()

ctx = _get_social_portal_data_ctx(request, 'fast.voidpanel.com')
admin_1click = json.loads(ctx['admin_1click_platforms'])
auth_modes = json.loads(ctx['auth_modes'])
enabled = json.loads(ctx['enabled_platforms'])

print("Portal Context admin_1click_platforms:", admin_1click)
print("Portal Context auth_modes:", auth_modes)
print("Portal Context enabled_platforms:", enabled)

assert 'fb' in admin_1click
assert 'tw' in admin_1click
assert 'ig' not in admin_1click

print("✅ Control Portal Context Generation Verified Successfully!")
