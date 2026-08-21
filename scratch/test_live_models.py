import paramiko

HOST = '207.180.209.216'
PORT = 22
USER = 'root'
PASS = '19072002ROHANkumar!'

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, port=PORT, username=USER, password=PASS, timeout=15)

test_script = """
import os, django, sys
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'voidpanel.settings')
django.setup()
from data.models import SocialPlatformSettings

cfg = SocialPlatformSettings.get()
print('SUCCESS! Live facebook_auth_mode:', getattr(cfg, 'facebook_auth_mode', None))
print('Live enabled_platforms:', cfg.enabled_platform_list())
print('Live admin_enabled_platforms:', cfg.admin_enabled_platform_list())
"""

# Test Voidonyx
print("=== Testing Voidonyx (https://voidonyx.in) ===")
stdin, stdout, stderr = ssh.exec_command(f"cd /home/voidonyx/voidonyx && /home/voidonyx/voidonyx/venv/bin/python3 -c \"{test_script}\"")
print("STDOUT:", stdout.read().decode())
print("STDERR:", stderr.read().decode())

# Test Voidpanel
print("=== Testing Voidpanel ===")
stdin, stdout, stderr = ssh.exec_command(f"cd /home/voidpanelc091/voidpanel && /home/voidpanelc091/voidpanel/venv/bin/python3 -c \"{test_script}\"")
print("STDOUT:", stdout.read().decode())
print("STDERR:", stderr.read().decode())

ssh.close()
