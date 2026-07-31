#!/usr/bin/env python3
"""
VoidOnyx Theme + Feature Hotpatch Deployment
Uploads only the files changed since the last full release:
  - views.py           (visiting_card view)
  - urls.py            (visiting-card route)
  - voidonyx/index.html        (stats update, remove proof block)
  - voidonyx/header.html       (VoidPanel links, mega-menu sidebar)
  - voidonyx/suite_landing.html (orange theme override)
  - voidonyx/visiting_card.html (new page)
"""

import os, paramiko, sys

LOCAL_DIR  = '/Users/rohan/Desktop/voidpanel'
REMOTE_DIR = '/home/voidpanelc091/voidpanel'
HOST = 'fast.voidpanel.com'
PORT = 22
USER = 'root'
PASS = '19072002ROHANkumar!'

# ── Files to upload (local_relative_path, remote_absolute_path) ─────────────
FILES = [
    # Core Python
    ('website/voidpanel/voidpanel/views.py',   f'{REMOTE_DIR}/voidpanel/views.py'),
    ('website/voidpanel/voidpanel/urls.py',    f'{REMOTE_DIR}/voidpanel/urls.py'),

    # VoidOnyx templates
    ('website/voidpanel/templates/voidonyx/index.html',          f'{REMOTE_DIR}/templates/voidonyx/index.html'),
    ('website/voidpanel/templates/voidonyx/header.html',         f'{REMOTE_DIR}/templates/voidonyx/header.html'),
    ('website/voidpanel/templates/voidonyx/footer.html',         f'{REMOTE_DIR}/templates/voidonyx/footer.html'),
    ('website/voidpanel/templates/voidonyx/suite_landing.html',  f'{REMOTE_DIR}/templates/voidonyx/suite_landing.html'),
    ('website/voidpanel/templates/voidonyx/visiting_card.html',  f'{REMOTE_DIR}/templates/voidonyx/visiting_card.html'),

    # Already-customised product pages
    ('website/voidpanel/templates/voidonyx/pricing.html',            f'{REMOTE_DIR}/templates/voidonyx/pricing.html'),
    ('website/voidpanel/templates/voidonyx/wordpress_hosting.html',  f'{REMOTE_DIR}/templates/voidonyx/wordpress_hosting.html'),
    ('website/voidpanel/templates/voidonyx/reseller.html',           f'{REMOTE_DIR}/templates/voidonyx/reseller.html'),
    ('website/voidpanel/templates/voidonyx/professional_email.html', f'{REMOTE_DIR}/templates/voidonyx/professional_email.html'),
    ('website/voidpanel/templates/voidonyx/ssl_certificates.html',   f'{REMOTE_DIR}/templates/voidonyx/ssl_certificates.html'),
]


def upload_with_progress(sftp, local, remote):
    name = os.path.basename(local)
    print(f"  ↑ {name}  →  {remote}")
    last = [0]
    def cb(transferred, total):
        pct = int((transferred / total) * 100)
        if pct >= last[0] + 25 or transferred == total:
            print(f"      {transferred}/{total} bytes  ({pct}%)")
            last[0] = pct
    sftp.put(local, remote, callback=cb)


print("=== VoidOnyx Hotpatch Deployment ===\n")

print("Step 1/3 — Connecting to server …")
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, port=PORT, username=USER, password=PASS, timeout=20)
print(f"  Connected to {HOST}\n")

sftp = ssh.open_sftp()

print("Step 2/3 — Uploading changed files …")
errors = []
for local_rel, remote_abs in FILES:
    local_abs = os.path.join(LOCAL_DIR, local_rel)
    if not os.path.exists(local_abs):
        print(f"  ⚠️  SKIPPED (not found locally): {local_rel}")
        continue
    try:
        upload_with_progress(sftp, local_abs, remote_abs)
    except Exception as e:
        print(f"  ✗  FAILED {local_rel}: {e}")
        errors.append(local_rel)

sftp.close()
print(f"\n  Upload complete. {len(errors)} error(s).")
if errors:
    print("  Failed files:", errors)

print("\nStep 3/3 — Reloading uWSGI / application server …")
def run_remote(cmd):
    stdin, stdout, stderr = ssh.exec_command(cmd)
    out = stdout.read().decode('utf-8', errors='replace').strip()
    err = stderr.read().decode('utf-8', errors='replace').strip()
    if out:
        print(f"  [remote] {out}")
    if err:
        print(f"  [remote stderr] {err}")

# Touch the wsgi file to trigger reload (works with most uWSGI setups)
run_remote("touch /home/voidpanelc091/voidpanel/voidpanel/wsgi.py")
# Also try pkill HUP in case the server uses ini reload
run_remote("pkill -HUP -f 'voidpanel.ini' 2>/dev/null || true")

ssh.close()
print("\n=== HOTPATCH DEPLOYMENT COMPLETE ===")
print("Live URL: https://www.voidonyx.com/visiting-card/")
