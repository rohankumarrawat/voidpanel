import paramiko

HOST = '207.180.209.216'
PORT = 22
USER = 'root'
PASS = '19072002ROHANkumar!'

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, port=PORT, username=USER, password=PASS, timeout=15)

inspect_and_delete_script = """
import os, django, sys
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'panel.settings')
django.setup()

from control.models import SocialAccount, SocialPost, SocialMessage, SocialAnalyticsCache

# Find all accounts for rkrawat1907 or related domains
print("=== Querying Social Accounts on Live Server ===")
all_accs = list(SocialAccount.objects.all().values('id', 'domain', 'username', 'platform', 'account_name', 'account_username', 'is_active'))
print(f"Total Social Accounts in DB: {len(all_accs)}")
for a in all_accs:
    print(f"  ID: {a['id']} | Domain: {a['domain']} | User: {a['username']} | Plat: {a['platform']} | Name: {a['account_name']} | @{a['account_username']}")

target_accs = SocialAccount.objects.filter(username__iexact='rkrawat1907') | SocialAccount.objects.filter(domain__icontains='rkrawat') | SocialAccount.objects.filter(domain='fast.voidpanel.com')
print(f"\\nMatching accounts for user 'rkrawat1907': {target_accs.count()}")

# Delete matching accounts
deleted_count, deleted_details = target_accs.delete()
print(f"Deleted {deleted_count} account objects successfully!")
print("Deleted details:", deleted_details)

# Check remaining accounts
remaining = SocialAccount.objects.all().count()
print(f"Remaining Social Accounts in DB: {remaining}")
"""

print("Executing removal script on live server...")
stdin, stdout, stderr = ssh.exec_command(f"cd /var/www/panel && /var/www/panel/venv/bin/python3 -c \"{inspect_and_delete_script}\"")
print("STDOUT:\n", stdout.read().decode())
print("STDERR:\n", stderr.read().decode())

# Also check other databases if any
check_other_dbs_script = """
import sqlite3, glob

dbs = glob.glob('/home/*/voidpanel/db.sqlite3') + glob.glob('/home/*/voidonyx/db.sqlite3')
for db in dbs:
    print(f"Checking DB: {db}")
    conn = sqlite3.connect(db)
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='control_socialaccount'")
    if cur.fetchone():
        cur.execute("SELECT id, domain, username, platform, account_name FROM control_socialaccount WHERE username LIKE '%rkrawat%' OR domain LIKE '%rkrawat%' OR domain='fast.voidpanel.com'")
        rows = cur.fetchall()
        print(f"  Found {len(rows)} matching in {db}: {rows}")
        if rows:
            cur.execute("DELETE FROM control_socialaccount WHERE username LIKE '%rkrawat%' OR domain LIKE '%rkrawat%' OR domain='fast.voidpanel.com'")
            conn.commit()
            print(f"  Deleted matching rows from {db}")
    conn.close()
"""

stdin, stdout, stderr = ssh.exec_command(f"python3 -c \"{check_other_dbs_script}\"")
print("OTHER DBS STDOUT:\n", stdout.read().decode())
print("OTHER DBS STDERR:\n", stderr.read().decode())

# Restart panel services to clear any cache
ssh.exec_command("systemctl restart voidpanel.service app-voidpanelc091-voidpanel.service")
print("Panel services restarted.")

ssh.close()
