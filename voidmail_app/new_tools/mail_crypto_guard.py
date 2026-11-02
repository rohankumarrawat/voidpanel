#!/usr/bin/env python3
"""
MailCryptoGuard — 1-Click Automated Cryptographic Hardening Tool
Designed for Postfix & Dovecot mail servers to enforce modern TLS 1.3/1.2,
ECDHE Forward Secrecy, anti-STARTTLS stripping policies, and safe cipher suites.
"""

import os
import sys
import shutil
import subprocess
import datetime
import argparse
import socket
import ssl

POSTFIX_CONFIG_DEFAULT = "/etc/postfix/main.cf"
DOVECOT_SSL_CONFIG_DEFAULT = "/etc/dovecot/conf.d/10-ssl.conf"
DOVECOT_MAIN_DEFAULT = "/etc/dovecot/dovecot.conf"

HARDENED_POSTFIX_PARAMS = {
    # Restrict to modern TLS only
    "smtpd_tls_protocols": "!SSLv2, !SSLv3, !TLSv1, !TLSv1.1",
    "smtp_tls_protocols": "!SSLv2, !SSLv3, !TLSv1, !TLSv1.1",
    "smtpd_tls_mandatory_protocols": "!SSLv2, !SSLv3, !TLSv1, !TLSv1.1",
    "smtp_tls_mandatory_protocols": "!SSLv2, !SSLv3, !TLSv1, !TLSv1.1",

    # Enforce High-grade ciphers with Forward Secrecy (ECDHE)
    "smtpd_tls_ciphers": "high",
    "smtpd_tls_mandatory_ciphers": "high",
    "tls_high_cipherlist": "ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384:ECDHE-ECDSA-CHACHA20-POLY1305:ECDHE-RSA-CHACHA20-POLY1305:ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256",
    "smtpd_tls_exclude_ciphers": "aNULL, eNULL, EXPORT, DES, RC4, MD5, PSK, aECDH, EDH-DSS-DES-CBC3-SHA, EDH-RSA-DES-CBC3-SHA, KRB5-DES, 3DES",

    # Enforce TLS for authentication
    "smtpd_tls_auth_only": "yes",
    "smtpd_tls_security_level": "may",
    "smtpd_tls_received_header": "yes",

    # Protect outbound server-to-server delivery against stripping
    "smtp_tls_security_level": "dane",
    "smtp_dns_support_level": "dnssec",
    "smtp_tls_note_starttls_offer": "yes",

    # Prefer server cipher order
    "tls_preempt_cipherlist": "yes",
}

VULNERABLE_POSTFIX_PARAMS = {
    "smtpd_tls_protocols": "SSLv3, TLSv1, TLSv1.1, TLSv1.2",
    "smtpd_tls_mandatory_protocols": "SSLv3, TLSv1, TLSv1.1, TLSv1.2",
    "smtpd_tls_ciphers": "medium",
    "smtpd_tls_auth_only": "no",
    "smtp_tls_security_level": "may",
}

HARDENED_DOVECOT_PARAMS = {
    "ssl": "required",
    "ssl_min_protocol": "TLSv1.2",
    "ssl_cipher_list": "ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384:ECDHE-ECDSA-CHACHA20-POLY1305:ECDHE-RSA-CHACHA20-POLY1305:ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256",
    "ssl_prefer_server_ciphers": "yes",
}

VULNERABLE_DOVECOT_PARAMS = {
    "ssl": "yes",
    "ssl_min_protocol": "TLSv1",
    "ssl_cipher_list": "ALL:!LOW:!SSLv2:!EXP:!aNULL",
}


def create_backup(file_path):
    if not os.path.exists(file_path):
        return None
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = os.path.expanduser("~/.mail_crypto_backups")
    os.makedirs(backup_dir, exist_ok=True)
    filename = os.path.basename(file_path)
    backup_path = os.path.join(backup_dir, f"{filename}.{timestamp}.bak")
    shutil.copy2(file_path, backup_path)
    print(f"  [+] Backup saved: {backup_path}")
    return backup_path


def apply_key_value_config(file_path, params, separator=" = "):
    if not os.path.exists(file_path):
        print(f"  [-] Config file not found: {file_path}")
        return False

    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        lines = f.readlines()

    updated_keys = set()
    new_lines = []

    for line in lines:
        stripped = line.strip()
        matched_key = None
        for key in params:
            if stripped.startswith(key + " ") or stripped.startswith(key + "="):
                matched_key = key
                break

        if matched_key:
            new_val = params[matched_key]
            new_lines.append(f"{matched_key}{separator}{new_val}\n")
            updated_keys.add(matched_key)
        else:
            new_lines.append(line)

    # Append any keys that weren't in the file
    for key, val in params.items():
        if key not in updated_keys:
            new_lines.append(f"{key}{separator}{val}\n")

    with open(file_path, "w", encoding="utf-8") as f:
        f.writelines(new_lines)

    return True


def audit_config(postfix_path, dovecot_path):
    print("\n" + "=" * 60)
    print(" 🔍 MAIL SERVER CRYPTOGRAPHIC AUDIT")
    print("=" * 60)

    # Postfix audit
    print("\n--- Postfix Configuration (/etc/postfix/main.cf) ---")
    if os.path.exists(postfix_path):
        with open(postfix_path, "r", errors="ignore") as f:
            content = f.read()
            for key in ["smtpd_tls_protocols", "smtpd_tls_ciphers", "smtp_tls_security_level", "smtpd_tls_auth_only"]:
                found = False
                for line in content.splitlines():
                    if line.strip().startswith(key):
                        print(f"  • {line.strip()}")
                        found = True
                        break
                if not found:
                    print(f"  • {key}: [DEFAULT / UNSET - POTENTIALLY WEAK]")
    else:
        print(f"  [-] File not found: {postfix_path}")

    # Dovecot audit
    print("\n--- Dovecot Configuration ---")
    target_dc = dovecot_path if os.path.exists(dovecot_path) else DOVECOT_MAIN_DEFAULT
    if os.path.exists(target_dc):
        with open(target_dc, "r", errors="ignore") as f:
            content = f.read()
            for key in ["ssl", "ssl_min_protocol", "ssl_cipher_list", "ssl_prefer_server_ciphers"]:
                found = False
                for line in content.splitlines():
                    if line.strip().startswith(key):
                        print(f"  • {line.strip()}")
                        found = True
                        break
                if not found:
                    print(f"  • {key}: [DEFAULT / UNSET]")
    else:
        print(f"  [-] File not found: {target_dc}")


def test_live_handshake(host="127.0.0.1", port=465):
    print(f"\n[+] Testing live TLS connection to {host}:{port}...")
    try:
        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        with socket.create_connection((host, port), timeout=3) as sock:
            with context.wrap_socket(sock, server_hostname=host) as ssock:
                version = ssock.version()
                cipher = ssock.cipher()
                print(f"  ✅ Connection Succeeded!")
                print(f"  • Protocol Negotiated: {version}")
                print(f"  • Cipher Suite: {cipher[0] if cipher else 'Unknown'}")
                print(f"  • Key Bits: {cipher[2] if cipher else 'Unknown'}")
                return True
    except Exception as e:
        print(f"  ⚠️ Handshake test to {host}:{port} skipped/failed: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="MailCryptoGuard — 1-Click Server Hardener")
    parser.add_argument("--audit", action="store_true", help="Audit current configs without changing them")
    parser.add_argument("--harden", action="store_true", help="Apply modern TLS 1.3/1.2 & Forward Secrecy settings")
    parser.add_argument("--vulnerable", action="store_true", help="Set weak TLS 1.0 (for generating test/demo PCAP captures)")
    parser.add_argument("--postfix-file", default=POSTFIX_CONFIG_DEFAULT, help="Path to Postfix main.cf")
    parser.add_argument("--dovecot-file", default=DOVECOT_SSL_CONFIG_DEFAULT, help="Path to Dovecot 10-ssl.conf")
    parser.add_argument("--test-port", type=int, default=465, help="Test TLS handshake on port (default: 465)")
    args = parser.parse_args()

    if args.audit or (not args.harden and not args.vulnerable):
        audit_config(args.postfix_file, args.dovecot_file)
        if not args.harden and not args.vulnerable:
            print("\n💡 Run with --harden to enforce modern TLS 1.3/1.2 & Forward Secrecy.")
            sys.exit(0)

    target_postfix_params = HARDENED_POSTFIX_PARAMS if args.harden else VULNERABLE_POSTFIX_PARAMS
    target_dovecot_params = HARDENED_DOVECOT_PARAMS if args.harden else VULNERABLE_DOVECOT_PARAMS
    mode_label = "HARDENED (TLS 1.3/1.2, ECDHE, PFS)" if args.harden else "VULNERABLE TEST MODE (TLS 1.0, Legacy)"

    print("\n" + "=" * 60)
    print(f" 🛡️  APPLYING CRYPTOGRAPHIC PROFILE: {mode_label}")
    print("=" * 60)

    # 1. Backups
    print("\n[Step 1] Creating Backups...")
    create_backup(args.postfix_file)
    create_backup(args.dovecot_file)

    # 2. Apply Postfix changes
    print("\n[Step 2] Updating Postfix Directives...")
    if apply_key_value_config(args.postfix_file, target_postfix_params):
        print(f"  [+] Updated {len(target_postfix_params)} directives in {args.postfix_file}")

    # 3. Apply Dovecot changes
    print("\n[Step 3] Updating Dovecot Directives...")
    target_dc = args.dovecot_file if os.path.exists(args.dovecot_file) else DOVECOT_MAIN_DEFAULT
    if apply_key_value_config(target_dc, target_dovecot_params):
        print(f"  [+] Updated {len(target_dovecot_params)} directives in {target_dc}")

    # 4. Service verification & reload (if running on Linux with systemctl)
    print("\n[Step 4] Validating Configuration Syntax & Reloading...")
    if shutil.which("postfix"):
        try:
            res = subprocess.run(["postfix", "check"], capture_output=True, text=True)
            if res.returncode == 0:
                print("  [+] Postfix syntax check: OK")
                subprocess.run(["systemctl", "reload", "postfix"], check=False)
            else:
                print(f"  [-] Postfix syntax error: {res.stderr}")
        except Exception as e:
            print(f"  [!] Skipping systemctl reload: {e}")

    if shutil.which("dovecot"):
        try:
            res = subprocess.run(["dovecot", "-n"], capture_output=True, text=True)
            if res.returncode == 0:
                print("  [+] Dovecot syntax check: OK")
                subprocess.run(["systemctl", "reload", "dovecot"], check=False)
        except Exception as e:
            print(f"  [!] Skipping systemctl reload: {e}")

    print("\n[Step 5] Cryptographic Verification:")
    test_live_handshake("127.0.0.1", args.test_port)

    print("\n" + "=" * 60)
    print(" ✅ SERVER CRYPTOGRAPHIC CONFIGURATION COMPLETE!")
    print("=" * 60)


if __name__ == "__main__":
    main()
