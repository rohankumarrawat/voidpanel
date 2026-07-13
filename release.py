#!/usr/bin/env python3
"""
VoidPanel Control Panel Release Builder
Packages the control panel (excludes website/, venv/, db, scratch etc.)
and uploads it to voidpanel.com for fresh server installs.

Usage: python3 release.py [version] [notes]
Example: python3 release.py 2.5.20 "Added configurable registration bonus"
"""

import os
import sys
import zipfile
import shutil
import paramiko

# ── CONFIG ────────────────────────────────────────────────────────────────────
SERVER_IP   = "94.136.184.183"
SERVER_USER = "root"
SERVER_PASS = "19072002ROHANkumar"
SERVER_BASE = "/home/voidpanelc091/voidpanel"

LOCAL_ROOT  = os.path.dirname(os.path.abspath(__file__))   # /Users/rohan/Desktop/voidpanel

VERSION_FILE = os.path.join(LOCAL_ROOT, "version.txt")
ARCHIVE_OUT  = os.path.join(LOCAL_ROOT, "Archive.zip")

# Directories/files to EXCLUDE from the release zip
EXCLUDE_DIRS  = {".git", "venv", "website", "__pycache__", "staticfiles",
                 "scratch", "demo", "media", ".gemini", "node_modules", "auth_session"}
EXCLUDE_FILES = {".env", "db.sqlite3", "Archive.zip", ".DS_Store",
                 ".secret_key", ".gitignore", "deploy_chips_feature.sh",
                 "rewrite_portal.py", "split_tabs.py",
                 "api.txt", "updatedocs.txt", "test.png"}
EXCLUDE_EXTS  = {".pyc", ".pyo", ".log", ".DS_Store"}
# ──────────────────────────────────────────────────────────────────────────────


def read_version():
    with open(VERSION_FILE) as f:
        return f.read().strip()


def bump_version(new_ver):
    with open(VERSION_FILE, "w") as f:
        f.write(new_ver)
    print(f"  [OK] version.txt updated to {new_ver}")


def build_zip():
    print(f"\n📦 Building release zip → {ARCHIVE_OUT}")
    if os.path.exists(ARCHIVE_OUT):
        os.remove(ARCHIVE_OUT)

    added = 0
    with zipfile.ZipFile(ARCHIVE_OUT, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(LOCAL_ROOT):
            # Prune excluded dirs in-place so os.walk skips them
            dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]

            for fname in files:
                if fname in EXCLUDE_FILES:
                    continue
                ext = os.path.splitext(fname)[1]
                if ext in EXCLUDE_EXTS:
                    continue

                abs_path = os.path.join(root, fname)
                rel_path = os.path.relpath(abs_path, LOCAL_ROOT)

                zf.write(abs_path, rel_path)
                added += 1

    size_mb = os.path.getsize(ARCHIVE_OUT) / (1024 * 1024)
    print(f"  [OK] {added} files → {size_mb:.1f} MB")
    return ARCHIVE_OUT


def upload_and_release(version, notes):
    print(f"\n🚀 Connecting to {SERVER_IP}…")
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(SERVER_IP, username=SERVER_USER, password=SERVER_PASS, timeout=20)
    print("  [OK] Connected")

    sftp = ssh.open_sftp()

    # ── Upload Archive.zip to two locations ──────────────────────────────────
    print("\n📤 Uploading Archive.zip …")
    sftp.put(ARCHIVE_OUT, f"{SERVER_BASE}/Archive.zip")
    sftp.put(ARCHIVE_OUT, f"{SERVER_BASE}/static/voidpanel.zip")
    print("  [OK] Archive.zip → server/Archive.zip")
    print("  [OK] Archive.zip → server/static/voidpanel.zip")

    # ── Upload installers ─────────────────────────────────────────────────────
    for script in ("install.sh", "ubuntu.sh", "almalinux.sh"):
        local_f = os.path.join(LOCAL_ROOT, script)
        if os.path.exists(local_f):
            sftp.put(local_f, f"{SERVER_BASE}/static/{script}")
            print(f"  [OK] {script} uploaded")

    sftp.close()

    # ── Fix permissions ───────────────────────────────────────────────────────
    print("\n🔧 Fixing static file permissions…")
    for cmd in [
        f"find {SERVER_BASE}/static -type f -exec chmod 644 {{}} +",
        f"find {SERVER_BASE}/static -type d -exec chmod 755 {{}} +",
        f"chmod 644 {SERVER_BASE}/Archive.zip",
    ]:
        _, out, err = ssh.exec_command(cmd)
        out.channel.recv_exit_status()
    print("  [OK] Permissions fixed")

    # ── Run deploy.sh on server ───────────────────────────────────────────────
    print(f"\n🏗  Running deploy.sh v{version} on server…")
    deploy_cmd = (
        f"cd {SERVER_BASE} && bash deploy/deploy.sh {version} '{notes}' 2>&1"
    )
    _, out, err = ssh.exec_command(deploy_cmd)
    for line in out:
        line = line.rstrip()
        print(f"  [SERVER] {line}")

    exit_code = out.channel.recv_exit_status()

    ssh.close()

    if exit_code == 0:
        print(f"\n✅  v{version} released successfully!")
        print(f"    Install:  curl -fsSL https://voidpanel.com/install.sh | bash")
        print(f"    API:      https://voidpanel.com/version_name/")
        print(f"    Tarball:  https://voidpanel.com/releases/voidpanel-{version}.tar.gz")
    else:
        print(f"\n❌  deploy.sh exited with code {exit_code}")


def update_installer_versions(new_ver):
    ubuntu_sh_path = os.path.join(LOCAL_ROOT, "ubuntu.sh")
    if os.path.exists(ubuntu_sh_path):
        with open(ubuntu_sh_path, "r") as f:
            content = f.read()
        
        import re
        # Substitute 'vX.Y.Z' in banner and main status message
        content = re.sub(r'Pipeline v\d+\.\d+\.\d+', f'Pipeline v{new_ver}', content)
        content = re.sub(r'VoidPanel v\d+\.\d+\.\d+', f'VoidPanel v{new_ver}', content)
        
        # Substitute version text files output
        content = re.sub(r'echo "\d+\.\d+\.\d+" > "\$VFILE"', f'echo "{new_ver}" > "$VFILE"', content)
        content = re.sub(r'echo "\d+\.\d+\.\d+" > "\$PROJECT_DIR/version.txt"', f'echo "{new_ver}" > "$PROJECT_DIR/version.txt"', content)
        
        with open(ubuntu_sh_path, "w") as f:
            f.write(content)
        print(f"  [OK] ubuntu.sh updated to version {new_ver}")


def main():
    args = sys.argv[1:]
    if args:
        new_version = args[0]
        notes = args[1] if len(args) > 1 else f"VoidPanel v{new_version}"
    else:
        new_version = read_version()
        notes = f"VoidPanel v{new_version}"

    print(f"═══════════════════════════════════════════")
    print(f"  VoidPanel Control Panel Release Builder")
    print(f"  Version : {new_version}")
    print(f"  Notes   : {notes}")
    print(f"═══════════════════════════════════════════")

    # 1. Update version.txt if a new version was given
    current = read_version()
    if new_version != current:
        bump_version(new_version)

    # Update installer files with new version
    update_installer_versions(new_version)

    # 2. Build the zip
    build_zip()

    # 3. Upload + deploy
    upload_and_release(new_version, notes)


if __name__ == "__main__":
    main()
