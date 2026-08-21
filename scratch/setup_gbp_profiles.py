import paramiko

HOST = '207.180.209.216'
PORT = 22
USER = 'root'
PASS = '19072002ROHANkumar!'

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, port=PORT, username=USER, password=PASS, timeout=15)

cmd = '''/var/www/panel/venv/bin/python3 -c "
import sys, os
sys.path.insert(0, '/var/www/panel')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'panel.settings')
import django; django.setup()
from control.models import SocialAccount

# Find existing gb token
old_gb = SocialAccount.objects.filter(domain='rkrawat1907', platform='gb').first()
access_token = old_gb.access_token if old_gb else ''
refresh_token = old_gb.refresh_token if old_gb else ''
token_expiry = old_gb.token_expiry if old_gb else None

# Delete generic Rohan Kumar Rawat GBP account
SocialAccount.objects.filter(domain='rkrawat1907', platform='gb').delete()

# Create 1: RKM Classes Library
SocialAccount.objects.create(
    domain='rkrawat1907',
    username='rkrawat1907',
    platform='gb',
    account_id='14825335853902133908',
    account_name='RKM Classes Library',
    page_name='RKM Classes Library',
    page_id='14825335853902133908',
    account_username='RKM Classes Library',
    profile_picture_url='https://lh3.googleusercontent.com/p/AF1QipN38j4e62y0L45s-3i5R33G1n_Qz_X_k7q_yA=s680-w680-h510',
    followers_count=48,
    access_token=access_token,
    refresh_token=refresh_token,
    token_expiry=token_expiry,
    is_active=True
)

# Create 2: VoidOnyX
SocialAccount.objects.create(
    domain='rkrawat1907',
    username='rkrawat1907',
    platform='gb',
    account_id='14963624212488462748',
    account_name='VoidOnyX',
    page_name='VoidOnyX',
    page_id='14963624212488462748',
    account_username='VoidOnyX',
    profile_picture_url='https://scontent-fra5-2.xx.fbcdn.net/v/t39.30808-1/759823982_122097958869422986_6449347865103869528_n.jpg?stp=dst-jpg_p200x200_tt6&_nc_cat=107&ccb=1-7&_nc_sid=08baa4&_nc_ohc=k_6NFfCtojEQ7kNvwFIhv_k&_nc_oc=AdqlTSRTLe5wNQHeM2P4lMj09ZIlZfZTAqoxtEcbEiFk-Uc04mx-92hgWeHHvz4yBxpVrvpWT2OBA0mkxEfw2VYJ&_nc_zt=24&_nc_ht=scontent-fra5-2.xx&edm=AJdBtusEAAAA&_nc_gid=nPTwRKJGFFDVH4IOwfTMwQ&_nc_tpa=Q5bMBQKPw8CFDLXOH3UR-LfwrfmhUKNjO05aepSetXT1xk-JHjhj1HHtmUqFR0GQ-W-X2KzZmJjuXq5WVPM&oh=00_AQFpqXYI8kgZPrcSD_8EIcnb06ToK2UZBb20jK3QKrDdiw&oe=6A8CADA3',
    followers_count=120,
    access_token=access_token,
    refresh_token=refresh_token,
    token_expiry=token_expiry,
    is_active=True
)

print('Successfully configured both Google Business Profiles!')
for a in SocialAccount.objects.filter(domain='rkrawat1907'):
    print(f' -> {a.platform}: {a.account_name} ({a.account_id}) | pic={bool(a.profile_picture_url)}')
"'''

stdin, stdout, stderr = ssh.exec_command(cmd)
print("STDOUT:")
print(stdout.read().decode())
print("STDERR:")
print(stderr.read().decode())
ssh.close()
