import os, sys, django

sys.path.insert(0, '/Users/rohan/Desktop/voidpanel/website/voidpanel')
os.environ['DJANGO_SETTINGS_MODULE'] = 'voidpanel.settings'
django.setup()

from data.models import SocialPlatformSettings

cfg = SocialPlatformSettings()
cfg.facebook_enabled = True
cfg.facebook_auth_mode = 'admin'
cfg.instagram_enabled = True
cfg.instagram_auth_mode = 'user'
cfg.twitter_enabled = True
cfg.twitter_auth_mode = 'admin'

modes = cfg.auth_modes_dict()
enabled = cfg.enabled_platform_list()
admin_enabled = cfg.admin_enabled_platform_list()

print("Auth modes:", modes)
print("Enabled:", enabled)
print("Admin 1-Click enabled:", admin_enabled)

assert 'fb' in admin_enabled
assert 'tw' in admin_enabled
assert 'ig' not in admin_enabled # because auth_mode is user!

print("✅ Super Admin SocialPlatformSettings Auth Mode Logic Passed!")
