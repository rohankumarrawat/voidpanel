"""
VoidPanel Unified Account & Domain Suspension Manager
Handles full lifecycle suspension and unsuspension:
1. Database status sync for both user (UserModel) and domain (DomainModel / subdomainname).
2. Nginx virtual host transformation to serve the suspended landing page across all paths.
3. Automatic SSL certificate preservation to avoid browser security warnings.
4. Active vhost backup and full restoration upon unsuspension.
5. Email service suspension and reactivation.
6. Safe Nginx reload with validation check.
7. Admin and client notifications.
"""
import os
import re
import subprocess
import shutil
from panel.logger import get_logger

logger = get_logger(__name__)

SUSPEND_ROOT = "/var/www/suspend"
SUSPEND_INDEX = os.path.join(SUSPEND_ROOT, "index.html")

NGINX_SITES_AVAILABLE = "/etc/nginx/sites-available"
NGINX_SITES_ENABLED = "/etc/nginx/sites-enabled"


def ensure_suspend_infrastructure():
    """Ensures /var/www/suspend/index.html exists and has proper permissions."""
    try:
        if not os.path.exists(SUSPEND_INDEX):
            os.makedirs(SUSPEND_ROOT, exist_ok=True)
            html_content = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Account Suspended — Website Offline</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            background: #090d16;
            color: #f1f5f9;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 24px;
        }
        .container {
            max-width: 600px;
            width: 100%;
            background: rgba(15, 23, 42, 0.85);
            border: 1px solid rgba(239, 68, 68, 0.25);
            border-radius: 20px;
            padding: 44px 36px;
            text-align: center;
            box-shadow: 0 25px 60px -15px rgba(0, 0, 0, 0.7), 0 0 30px rgba(239, 68, 68, 0.08);
            backdrop-filter: blur(12px);
        }
        .icon-wrap {
            width: 72px;
            height: 72px;
            background: rgba(239, 68, 68, 0.12);
            border: 1px solid rgba(239, 68, 68, 0.3);
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            margin: 0 auto 24px auto;
            color: #f87171;
        }
        .icon-wrap svg { width: 36px; height: 36px; }
        .badge {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            background: rgba(239, 68, 68, 0.15);
            border: 1px solid rgba(239, 68, 68, 0.3);
            color: #fca5a5;
            font-size: 12px;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            padding: 6px 14px;
            border-radius: 9999px;
            margin-bottom: 20px;
        }
        .badge .dot {
            width: 7px;
            height: 7px;
            border-radius: 50%;
            background: #ef4444;
            box-shadow: 0 0 8px #ef4444;
        }
        h1 {
            font-size: 28px;
            font-weight: 800;
            color: #ffffff;
            margin-bottom: 12px;
            letter-spacing: -0.02em;
        }
        p {
            font-size: 15px;
            line-height: 1.6;
            color: #94a3b8;
            margin-bottom: 28px;
        }
        .details-card {
            background: #090f1d;
            border: 1px solid rgba(255, 255, 255, 0.06);
            border-radius: 12px;
            padding: 16px 20px;
            margin-bottom: 30px;
            text-align: left;
        }
        .detail-row {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 8px 0;
            font-size: 13px;
            border-bottom: 1px solid rgba(255, 255, 255, 0.04);
        }
        .detail-row:last-child { border-bottom: none; }
        .detail-lbl { color: #64748b; font-weight: 500; }
        .detail-val {
            color: #e2e8f0;
            font-weight: 600;
            font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
        }
        .btn-group {
            display: flex;
            gap: 12px;
            justify-content: center;
            flex-wrap: wrap;
        }
        .btn {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            gap: 8px;
            padding: 12px 24px;
            border-radius: 10px;
            font-size: 14px;
            font-weight: 600;
            text-decoration: none;
            transition: all 0.2s ease;
            cursor: pointer;
        }
        .btn-primary {
            background: #2563eb;
            color: #ffffff;
            border: 1px solid #3b82f6;
        }
        .btn-primary:hover { background: #1d4ed8; }
        .btn-secondary {
            background: rgba(255, 255, 255, 0.05);
            color: #cbd5e1;
            border: 1px solid rgba(255, 255, 255, 0.12);
        }
        .btn-secondary:hover {
            background: rgba(255, 255, 255, 0.08);
            color: #ffffff;
        }
        .footer-note {
            margin-top: 32px;
            font-size: 12px;
            color: #475569;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="icon-wrap">
            <svg fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"></path>
            </svg>
        </div>
        <div class="badge">
            <span class="dot"></span>
            Account Suspended
        </div>
        <h1>This Account Has Been Suspended</h1>
        <p>This website is currently offline. If you are the owner of this domain, please log in to your hosting client area or reach out to technical support to reactivate your service.</p>

        <div class="details-card">
            <div class="detail-row">
                <span class="detail-lbl">Domain</span>
                <span class="detail-val" id="dispDomain">Loading...</span>
            </div>
            <div class="detail-row">
                <span class="detail-lbl">Status</span>
                <span class="detail-val" style="color: #f87171;">Suspended / Inactive</span>
            </div>
            <div class="detail-row">
                <span class="detail-lbl">Server Node</span>
                <span class="detail-val">VoidPanel Cloud Edge</span>
            </div>
        </div>

        <div class="btn-group">
            <a href="https://voidonyx.in/login/" class="btn btn-primary" id="loginBtn">Client Area Login</a>
            <a href="mailto:support@voidonyx.com" class="btn btn-secondary">Contact Support</a>
        </div>

        <div class="footer-note">
            VoidPanel Edge Virtualization &bull; Hosting & Infrastructure Management
        </div>
    </div>

    <script>
        document.getElementById("dispDomain").textContent = window.location.hostname || "Domain";
    </script>
</body>
</html>"""
            tmp_path = "/tmp/suspend_default.html"
            with open(tmp_path, "w", encoding="utf-8") as tf:
                tf.write(html_content)
            subprocess.run(["sudo", "mkdir", "-p", SUSPEND_ROOT], check=False)
            subprocess.run(["sudo", "cp", tmp_path, SUSPEND_INDEX], check=False)
            subprocess.run(["sudo", "chmod", "755", SUSPEND_ROOT], check=False)
            subprocess.run(["sudo", "chmod", "644", SUSPEND_INDEX], check=False)
            subprocess.run(["sudo", "chown", "-R", "www-data:www-data", SUSPEND_ROOT], check=False)
            try:
                os.remove(tmp_path)
            except Exception:
                pass
    except Exception as e:
        logger.error(f"Error ensuring suspend infrastructure: {e}")


def suspend_domain_vhost(domain_name):
    """
    Safely modifies the Nginx vhost for domain_name to point to /var/www/suspend.
    Preserves exact SSL certificates and server_names.
    Backs up active vhost to <vhost>.active_vhost.
    """
    ensure_suspend_infrastructure()
    vhost_path = os.path.join(NGINX_SITES_AVAILABLE, f"{domain_name}.conf")
    symlink_path = os.path.join(NGINX_SITES_ENABLED, f"{domain_name}.conf")

    if not os.path.exists(vhost_path) and os.path.exists(symlink_path):
        vhost_path = symlink_path

    if not os.path.exists(vhost_path):
        logger.warning(f"No Nginx vhost found for {domain_name} at {vhost_path}")
        return False

    active_backup = os.path.join(NGINX_SITES_AVAILABLE, f"{domain_name}.conf.active_vhost")

    # If already suspended, don't overwrite backup
    if not os.path.exists(active_backup):
        subprocess.run(["sudo", "cp", vhost_path, active_backup], check=False)

    try:
        with open(active_backup if os.path.exists(active_backup) else vhost_path, "r", encoding="utf-8") as f:
            orig = f.read()
    except Exception as e:
        logger.error(f"Failed to read active vhost for {domain_name}: {e}")
        return False

    server_name_m = re.search(r"server_name\s+([^;]+);", orig)
    server_names = server_name_m.group(1).strip() if server_name_m else f"{domain_name} www.{domain_name}"

    # Ensure letsencrypt directories are searchable
    subprocess.run(["sudo", "chmod", "755", "/etc/letsencrypt", "/etc/letsencrypt/live", "/etc/letsencrypt/archive"], check=False)

    ssl_cert_m = re.search(r"ssl_certificate\s+([^;]+);", orig)
    ssl_key_m = re.search(r"ssl_certificate_key\s+([^;]+);", orig)

    ssl_cert = ssl_cert_m.group(1).strip() if ssl_cert_m else None
    ssl_key = ssl_key_m.group(1).strip() if ssl_key_m else None

    has_ssl = False
    if ssl_cert and ssl_key:
        if os.path.exists(ssl_cert) and os.path.exists(ssl_key):
            has_ssl = True
        else:
            c_check = subprocess.run(["sudo", "test", "-e", ssl_cert], check=False)
            k_check = subprocess.run(["sudo", "test", "-e", ssl_key], check=False)
            has_ssl = (c_check.returncode == 0 and k_check.returncode == 0)

    # If domain doesn't have its own SSL cert, use fallback dummy SSL
    # to guarantee HTTPS traffic gets intercepted and never routes to another tenant's site
    if not has_ssl:
        fallback_cert = "/etc/nginx/dummy.crt"
        fallback_key = "/etc/nginx/dummy.key"
        if os.path.exists(fallback_cert) and os.path.exists(fallback_key):
            ssl_cert = fallback_cert
            ssl_key = fallback_key
            has_ssl = True

    if has_ssl:
        suspended_conf = f"""# VOIDPANEL SUSPENDED VHOST - {domain_name}
server {{
    listen 80;
    server_name {server_names};
    return 301 https://$host$request_uri;
}}

server {{
    listen 443 ssl http2;
    server_name {server_names};

    ssl_certificate {ssl_cert};
    ssl_certificate_key {ssl_key};

    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_prefer_server_ciphers on;
    ssl_ciphers HIGH:!aNULL:!MD5;

    root /var/www/suspend;
    index index.html;
    client_max_body_size 10M;

    location / {{
        try_files $uri /index.html;
    }}

    access_log /var/log/nginx/{domain_name}.access.log;
    error_log  /var/log/nginx/{domain_name}.error.log;
}}
"""
    else:
        suspended_conf = f"""# VOIDPANEL SUSPENDED VHOST - {domain_name}
server {{
    listen 80;
    server_name {server_names};

    root /var/www/suspend;
    index index.html;
    client_max_body_size 10M;

    location / {{
        try_files $uri /index.html;
    }}

    access_log /var/log/nginx/{domain_name}.access.log;
    error_log  /var/log/nginx/{domain_name}.error.log;
}}
"""

    tmp_file = f"/tmp/vhost_susp_{domain_name}.conf"
    try:
        with open(tmp_file, "w", encoding="utf-8") as tf:
            tf.write(suspended_conf)

        target_vhost = os.path.join(NGINX_SITES_AVAILABLE, f"{domain_name}.conf")
        subprocess.run(["sudo", "cp", tmp_file, target_vhost], check=False)
        subprocess.run(["sudo", "chmod", "644", target_vhost], check=False)
        target_enabled = os.path.join(NGINX_SITES_ENABLED, f"{domain_name}.conf")
        subprocess.run(["sudo", "ln", "-sf", target_vhost, target_enabled], check=False)
        try:
            os.remove(tmp_file)
        except Exception:
            pass
        return True
    except Exception as e:
        logger.error(f"Error writing suspended vhost for {domain_name}: {e}")
        return False


def unsuspend_domain_vhost(domain_name, user_dir=None):
    """
    Restores the active Nginx vhost from backup or re-points root to public_html.
    """
    vhost_path = os.path.join(NGINX_SITES_AVAILABLE, f"{domain_name}.conf")
    active_backup = os.path.join(NGINX_SITES_AVAILABLE, f"{domain_name}.conf.active_vhost")

    restored = False
    if os.path.exists(active_backup):
        subprocess.run(["sudo", "cp", active_backup, vhost_path], check=False)
        subprocess.run(["sudo", "rm", "-f", active_backup], check=False)
        restored = True
    elif os.path.exists(vhost_path):
        # Fallback in-place replacement
        try:
            with open(vhost_path, "r", encoding="utf-8") as vf:
                lines = vf.readlines()
            for i, line in enumerate(lines):
                if "/var/www/suspend" in line:
                    if user_dir:
                        lines[i] = f"    root /home/{user_dir}/public_html;\n"
                    else:
                        lines[i] = f"    root /home/{domain_name}/public_html;\n"
            tmp_f = f"/tmp/unsusp_{domain_name}.conf"
            with open(tmp_f, "w", encoding="utf-8") as tf:
                tf.writelines(lines)
            subprocess.run(["sudo", "cp", tmp_f, vhost_path], check=False)
            try:
                os.remove(tmp_f)
            except Exception:
                pass
            restored = True
        except Exception as e:
            logger.error(f"Failed in-place restore for {domain_name}: {e}")

    target_enabled = os.path.join(NGINX_SITES_ENABLED, f"{domain_name}.conf")
    subprocess.run(["sudo", "ln", "-sf", vhost_path, target_enabled], check=False)
    return restored


def suspend_account_action(identifier):
    """
    Master function to suspend any hosting account or domain.
    Works with either a domain name ('example.com') or a username ('john').
    """
    from control.models import user as UserModel, domain as DomainModel, subdomainname

    # 1. Resolve User and Domain objects
    u_obj = UserModel.objects.filter(domain=identifier).first() or UserModel.objects.filter(username=identifier).first()
    d_obj = DomainModel.objects.filter(domain=identifier).first() or (DomainModel.objects.filter(dir=identifier).first() if u_obj is None else DomainModel.objects.filter(dir=u_obj.username).first())

    target_domain = d_obj.domain if d_obj else (u_obj.domain if u_obj else identifier)
    target_username = u_obj.username if u_obj else (d_obj.dir if d_obj else identifier)

    # 2. Update Database Records
    if u_obj:
        u_obj.status = False
        u_obj.save(update_fields=['status'])
    else:
        UserModel.objects.filter(domain=target_domain).update(status=False)
        UserModel.objects.filter(username=target_username).update(status=False)

    if d_obj:
        d_obj.status = False
        d_obj.save(update_fields=['status'])
    else:
        DomainModel.objects.filter(domain=target_domain).update(status=False)

    # 3. Suspend Nginx Virtual Hosts
    suspend_domain_vhost(target_domain)
    # Also suspend any subdomains
    for sub in subdomainname.objects.filter(domain=target_domain):
        suspend_domain_vhost(sub.subdomain)

    # 4. Suspend Mail
    try:
        from panel.views import toggle_email_suspension
        toggle_email_suspension(target_domain, True)
    except Exception as e:
        logger.warning(f"toggle_email_suspension warning for {target_domain}: {e}")

    # 5. Reload Nginx safely
    t = subprocess.run(["sudo", "nginx", "-t"], capture_output=True, text=True)
    if t.returncode == 0:
        subprocess.run(["sudo", "systemctl", "reload", "nginx"], check=False)
    else:
        logger.error(f"Nginx test failed after suspending {target_domain}: {t.stderr}")

    # 6. Trigger Notifications
    try:
        from control.utils import trigger_user_suspended_notification
        trigger_user_suspended_notification(target_username, target_domain)
    except Exception:
        pass

    logger.info(f"Successfully suspended account/domain {target_domain} (user: {target_username})")
    return {'status': 'success', 'message': f'Account {target_domain} successfully suspended.'}


def unsuspend_account_action(identifier):
    """
    Master function to unsuspend any hosting account or domain.
    Restores active vhosts, database status, emails, and reloads Nginx.
    """
    from control.models import user as UserModel, domain as DomainModel, subdomainname

    u_obj = UserModel.objects.filter(domain=identifier).first() or UserModel.objects.filter(username=identifier).first()
    d_obj = DomainModel.objects.filter(domain=identifier).first() or (DomainModel.objects.filter(dir=identifier).first() if u_obj is None else DomainModel.objects.filter(dir=u_obj.username).first())

    target_domain = d_obj.domain if d_obj else (u_obj.domain if u_obj else identifier)
    target_username = u_obj.username if u_obj else (d_obj.dir if d_obj else identifier)

    # 1. Update Database Records
    if u_obj:
        u_obj.status = True
        u_obj.save(update_fields=['status'])
    else:
        UserModel.objects.filter(domain=target_domain).update(status=True)
        UserModel.objects.filter(username=target_username).update(status=True)

    if d_obj:
        d_obj.status = True
        d_obj.save(update_fields=['status'])
    else:
        DomainModel.objects.filter(domain=target_domain).update(status=True)

    # 2. Restore Nginx Virtual Hosts
    unsuspend_domain_vhost(target_domain, target_username)
    for sub in subdomainname.objects.filter(domain=target_domain):
        unsuspend_domain_vhost(sub.subdomain, target_username)

    # 3. Unsuspend Mail
    try:
        from panel.views import toggle_email_suspension
        toggle_email_suspension(target_domain, False)
    except Exception as e:
        logger.warning(f"toggle_email_suspension warning for {target_domain}: {e}")

    # 4. Reload Nginx safely
    t = subprocess.run(["sudo", "nginx", "-t"], capture_output=True, text=True)
    if t.returncode == 0:
        subprocess.run(["sudo", "systemctl", "reload", "nginx"], check=False)
    else:
        logger.error(f"Nginx test failed after unsuspending {target_domain}: {t.stderr}")

    # 5. Trigger Notifications
    try:
        from control.utils import trigger_user_unsuspended_notification
        trigger_user_unsuspended_notification(target_username, target_domain)
    except Exception:
        pass

    logger.info(f"Successfully unsuspended account/domain {target_domain} (user: {target_username})")
    return {'status': 'success', 'message': f'Account {target_domain} successfully unsuspended.'}
