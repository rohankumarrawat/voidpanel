import sys, os
sys.path.insert(0, '/var/www/panel')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'panel.settings')
import django; django.setup()
from control.models import SocialAccount, SocialPost

print('=== ACCOUNTS ===')
for a in SocialAccount.objects.filter(domain='rkrawat1907'):
    pic = a.profile_picture_url[:60] if a.profile_picture_url else 'NONE'
    print('  id=%s platform=%s name=%s page_id=%s pic=%s followers=%s active=%s' % (
        a.id, a.platform, a.account_name, a.page_id, pic, a.followers_count, a.is_active))

print('')
print('=== POSTS ===')
posts = SocialPost.objects.filter(domain='rkrawat1907').order_by('-created_at')
print('  Total: %d' % posts.count())
print('  Published: %d' % posts.filter(status='published').count())
print('  Scheduled: %d' % posts.filter(status='scheduled').count())
print('  Drafts: %d' % posts.filter(status='draft').count())
print('  Failed: %d' % posts.filter(status='failed').count())
for p in posts[:5]:
    cap = p.caption_text[:40] if p.caption_text else ''
    print('  [%s] id=%s caption=%s platforms=%s' % (p.status, p.id, cap, p.platform_list))
