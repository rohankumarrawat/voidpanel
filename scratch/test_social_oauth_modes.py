import os, sys, django

# Set up voidpanel environment
sys.path.insert(0, '/Users/rohan/Desktop/voidpanel')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'panel.settings')
django.setup()

print("--- Testing Control Models & Views ---")
from control.models import SocialMediaAPIConfig, DomainSocialAPIConfig, SocialAccount
from control.views import _get_social_portal_data_ctx, PLATFORM_SLUG_MAP

# 1. Test SocialMediaAPIConfig
cfg = SocialMediaAPIConfig.objects.first()
if not cfg:
    cfg = SocialMediaAPIConfig.objects.create(pk=1)
cfg.enabled_platforms = ['fb', 'ig', 'tw', 'li', 'yt', 'tt', 'pi', 'th', 'gb']
cfg.admin_enabled_platforms = ['fb', 'ig', 'tw']
cfg.auth_modes = {'fb': 'admin', 'ig': 'admin', 'tw': 'admin', 'li': 'user'}
cfg.save()

print("SocialMediaAPIConfig.is_admin_1click('fb'):", cfg.is_admin_1click('fb'))
print("SocialMediaAPIConfig.is_admin_1click('li'):", cfg.is_admin_1click('li'))
assert cfg.is_admin_1click('fb') == True
assert cfg.is_admin_1click('li') == False

print("✅ Control models verification passed.")

# 2. Test Website / Super Admin Models
sys.path.insert(0, '/Users/rohan/Desktop/voidpanel/website/voidpanel')
os.environ['DJANGO_SETTINGS_MODULE'] = 'voidpanel.settings'
# Reload django for voidpanel settings
from website.voidpanel.data.models import SocialPlatformSettings as WebSettings
from voidonyx_server.data.models import SocialPlatformSettings as ServerSettings

print("WebSettings fields check:", hasattr(WebSettings, 'facebook_auth_mode'), hasattr(WebSettings, 'admin_enabled_platform_list'))
print("ServerSettings fields check:", hasattr(ServerSettings, 'facebook_auth_mode'), hasattr(ServerSettings, 'admin_enabled_platform_list'))

assert hasattr(WebSettings, 'facebook_auth_mode')
assert hasattr(ServerSettings, 'facebook_auth_mode')

print("✅ Super Admin models verification passed.")
print("ALL TESTS PASSED SUCCESSFULLY! 🚀")
