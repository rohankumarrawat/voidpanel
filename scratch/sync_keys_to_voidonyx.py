import paramiko
import time

HOST = '207.180.209.216'
PORT = 22
USER = 'root'
PASS = '19072002ROHANkumar!'

def get_ssh():
    for attempt in range(3):
        try:
            print(f"Connecting to {HOST} (attempt {attempt+1})...")
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(HOST, port=PORT, username=USER, password=PASS, timeout=30)
            print("Connected!")
            return ssh
        except Exception as e:
            print(f"Connection failed: {e}, retrying in 3s...")
            time.sleep(3)
    raise Exception("Could not connect to server after 3 attempts")

ssh = get_ssh()
sftp = ssh.open_sftp()

# Step 1 script: Read from panel and output json to /tmp/extracted_social_keys.json
read_script = """import json
from control.models import DomainSocialAPIConfig, SocialMediaAPIConfig

extracted = {}

for d in DomainSocialAPIConfig.objects.all():
    print(f"Inspecting domain: {d.domain}")
    if d.twitter_api_key:
        extracted['twitter_api_key'] = d.twitter_api_key
        extracted['twitter_api_secret'] = d.twitter_api_secret
        extracted['twitter_bearer_token'] = d.twitter_bearer_token
    if d.linkedin_client_id:
        extracted['linkedin_client_id'] = d.linkedin_client_id
        extracted['linkedin_client_secret'] = d.linkedin_client_secret
    if d.pinterest_app_id:
        extracted['pinterest_app_id'] = d.pinterest_app_id
        extracted['pinterest_app_secret'] = d.pinterest_app_secret
    if d.google_client_id:
        extracted['google_client_id'] = d.google_client_id
        extracted['google_client_secret'] = d.google_client_secret
    if d.facebook_app_id:
        extracted['facebook_app_id'] = d.facebook_app_id
        extracted['facebook_app_secret'] = d.facebook_app_secret

m = SocialMediaAPIConfig.objects.first()
if m:
    for k in ['twitter_api_key', 'twitter_api_secret', 'twitter_bearer_token', 'linkedin_client_id', 'linkedin_client_secret', 'pinterest_app_id', 'pinterest_app_secret', 'google_client_id', 'google_client_secret']:
        val = getattr(m, k, '')
        if val and k not in extracted:
            extracted[k] = val

with open('/tmp/extracted_social_keys.json', 'w') as f:
    json.dump(extracted, f)

print(f"Dumped keys for: {list(extracted.keys())}")
"""

# Step 2 script: Read from /tmp/extracted_social_keys.json and save to VoidOnyx
write_script = """import json
from data.models import SocialPlatformSettings

with open('/tmp/extracted_social_keys.json', 'r') as f:
    extracted = json.load(f)

s, _ = SocialPlatformSettings.objects.get_or_create(pk=1)

if 'twitter_api_key' in extracted and extracted['twitter_api_key']:
    s.twitter_api_key = extracted['twitter_api_key']
    s.twitter_api_secret = extracted.get('twitter_api_secret', '')
    s.twitter_bearer_token = extracted.get('twitter_bearer_token', '')
    s.twitter_enabled = True
    s.twitter_auth_mode = 'admin'
    print("✓ Twitter configured & set to 1-Click (admin mode)")

if 'linkedin_client_id' in extracted and extracted['linkedin_client_id']:
    s.linkedin_client_id = extracted['linkedin_client_id']
    s.linkedin_client_secret = extracted.get('linkedin_client_secret', '')
    s.linkedin_enabled = True
    s.linkedin_auth_mode = 'admin'
    print("✓ LinkedIn configured & set to 1-Click (admin mode)")

if 'pinterest_app_id' in extracted and extracted['pinterest_app_id']:
    s.pinterest_app_id = extracted['pinterest_app_id']
    s.pinterest_app_secret = extracted.get('pinterest_app_secret', '')
    s.pinterest_enabled = True
    s.pinterest_auth_mode = 'admin'
    print("✓ Pinterest configured & set to 1-Click (admin mode)")

if 'google_client_id' in extracted and extracted['google_client_id']:
    s.google_client_id = extracted['google_client_id']
    s.google_client_secret = extracted.get('google_client_secret', '')
    s.youtube_enabled = True
    s.youtube_auth_mode = 'admin'
    s.gbusiness_enabled = True
    s.gbusiness_auth_mode = 'admin'
    print("✓ Google (YouTube + GBusiness) configured & set to 1-Click (admin mode)")

if 'facebook_app_id' in extracted and extracted['facebook_app_id']:
    s.facebook_app_id = extracted['facebook_app_id']
    s.facebook_app_secret = extracted.get('facebook_app_secret', '')
    s.facebook_enabled = True
    s.facebook_auth_mode = 'admin'
    s.instagram_enabled = True
    s.instagram_auth_mode = 'admin'
    print("✓ Facebook/IG confirmed 1-Click (admin mode)")

s.save()

print("=== VoidOnyx SocialPlatformSettings State ===")
print("enabled_platform_list:", s.enabled_platform_list())
print("admin_enabled_platform_list:", s.admin_enabled_platform_list())
print("Twitter mode:", s.twitter_auth_mode, "Key configured:", bool(s.twitter_api_key))
print("LinkedIn mode:", s.linkedin_auth_mode, "Key configured:", bool(s.linkedin_client_id))
print("Pinterest mode:", s.pinterest_auth_mode, "Key configured:", bool(s.pinterest_app_id))
print("Google mode:", getattr(s, 'gbusiness_auth_mode', 'N/A'), "Key configured:", bool(s.google_client_id))
"""

with sftp.file('/tmp/read_panel_keys.py', 'w') as f:
    f.write(read_script)

with sftp.file('/tmp/write_voidonyx_keys.py', 'w') as f:
    f.write(write_script)

sftp.close()

print("Step 1: Extracting keys from Panel...")
stdin, stdout, stderr = ssh.exec_command("cd /var/www/panel && /var/www/panel/venv/bin/python3 manage.py shell < /tmp/read_panel_keys.py")
print(stdout.read().decode())
print(stderr.read().decode())

print("\nStep 2: Saving keys into VoidOnyx...")
stdin, stdout, stderr = ssh.exec_command("cd /home/voidonyx/voidonyx && /home/voidonyx/voidonyx/venv/bin/python3 manage.py shell < /tmp/write_voidonyx_keys.py")
print(stdout.read().decode())
print(stderr.read().decode())

print("\nStep 3: Restarting VoidOnyx uwsgi & Panel...")
ssh.exec_command("systemctl restart uwsgi && systemctl restart voidpanel")
print("Services restarted successfully.")

ssh.close()
