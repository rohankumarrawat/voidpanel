import datetime
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip

def send_admin_notification(subject, html_content):
    try:
        from control.models import NotificationSettings, quick
        
        cfg = NotificationSettings.objects.first()
        if not cfg or not cfg.is_smtp_verified:
            return False
            
        admin_email_obj = quick.objects.first()
        if not admin_email_obj or not admin_email_obj.email:
            return False
            
        to_email = admin_email_obj.email
        
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = cfg.from_email or cfg.smtp_user
        msg['To'] = to_email
        
        part = MIMEText(html_content, 'html')
        msg.attach(part)
        
        if cfg.smtp_encryption == 'ssl':
            server = smtplib.SMTP_SSL(cfg.smtp_host, cfg.smtp_port, timeout=10)
        else:
            server = smtplib.SMTP(cfg.smtp_host, cfg.smtp_port, timeout=10)
            server.ehlo()
            if cfg.smtp_encryption == 'tls':
                server.starttls()
                server.ehlo()
                
        server.login(cfg.smtp_user, cfg.smtp_password)
        server.sendmail(msg['From'], to_email, msg.as_string())
        server.quit()
        return True
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Failed to send admin notification: {e}")
        return False

def _ts():
    return datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

def _badge(color, text):
    colors = {
        'green': '#10b981',
        'red':   '#ef4444',
        'amber': '#f59e0b',
        'blue':  '#3b82f6',
        'purple':'#a855f7',
        'cyan':  '#06b6d4',
    }
    bg = colors.get(color, '#6b7280')
    return f'<span style="display:inline-block;background:{bg};color:#fff;border-radius:4px;padding:2px 10px;font-size:0.78rem;font-weight:600;">{text}</span>'

def _email_wrapper(icon, accent, title, rows):
    """
    Generic pretty HTML email template.
    rows: list of (label, value) tuples
    """
    rows_html = ''.join(
        f'<tr><td style="padding:8px 0;color:#6b7280;font-weight:600;width:160px;">{label}</td>'
        f'<td style="padding:8px 0;color:#1f2937;">{value}</td></tr>'
        for label, value in rows
    )
    return f"""
    <div style="font-family:'Inter',Arial,sans-serif;background:#f8fafc;padding:32px 0;">
      <div style="max-width:560px;margin:0 auto;background:#ffffff;border-radius:12px;box-shadow:0 2px 16px rgba(0,0,0,0.08);overflow:hidden;">
        <div style="background:linear-gradient(135deg,{accent},#1e1b4b);padding:28px 32px;display:flex;align-items:center;gap:16px;">
          <span style="font-size:2.2rem;">{icon}</span>
          <div>
            <div style="color:#fff;font-size:1.1rem;font-weight:700;letter-spacing:-0.2px;">{title}</div>
            <div style="color:rgba(255,255,255,0.7);font-size:0.8rem;margin-top:2px;">VoidPanel Admin Alert</div>
          </div>
        </div>
        <div style="padding:28px 32px;">
          <table style="width:100%;border-collapse:collapse;">
            {rows_html}
          </table>
          <div style="margin-top:20px;border-top:1px solid #f1f5f9;padding-top:16px;color:#9ca3af;font-size:0.75rem;">
            This is an automated notification from VoidPanel. Timestamp: {_ts()}
          </div>
        </div>
      </div>
    </div>
    """

# ───────────────────────────────────────────────
# Event Trigger Functions
# ───────────────────────────────────────────────

def trigger_user_created_notification(username, domain_name, email, package):
    try:
        from control.models import NotificationSettings
        cfg = NotificationSettings.objects.first()
        if cfg and cfg.is_smtp_verified and cfg.notify_user_created:
            html = _email_wrapper('🧑‍💻', '#4f46e5', 'New Hosting Account Created', [
                ('Username',  username),
                ('Domain',    domain_name),
                ('Email',     email),
                ('Package',   package),
                ('Status',    _badge('green', 'Provisioned')),
            ])
            return send_admin_notification(f"[VoidPanel] New User Created: {username}", html)
    except Exception as e:
        import logging; logging.getLogger(__name__).error(f"User created notification error: {e}")
    return False

def trigger_user_suspended_notification(username, domain_name):
    try:
        from control.models import NotificationSettings
        cfg = NotificationSettings.objects.first()
        if cfg and cfg.is_smtp_verified and cfg.notify_user_suspended:
            html = _email_wrapper('🔒', '#dc2626', 'Account Suspended', [
                ('Username', username),
                ('Domain',   domain_name),
                ('Status',   _badge('red', 'Suspended')),
            ])
            return send_admin_notification(f"[VoidPanel] Account Suspended: {domain_name}", html)
    except Exception as e:
        import logging; logging.getLogger(__name__).error(f"User suspend notification error: {e}")
    return False

def trigger_user_unsuspended_notification(username, domain_name):
    try:
        from control.models import NotificationSettings
        cfg = NotificationSettings.objects.first()
        if cfg and cfg.is_smtp_verified and cfg.notify_user_unsuspended:
            html = _email_wrapper('🔓', '#10b981', 'Account Unsuspended', [
                ('Username', username),
                ('Domain',   domain_name),
                ('Status',   _badge('green', 'Active')),
            ])
            return send_admin_notification(f"[VoidPanel] Account Unsuspended: {domain_name}", html)
    except Exception as e:
        import logging; logging.getLogger(__name__).error(f"User unsuspend notification error: {e}")
    return False

def trigger_user_terminated_notification(username, domain_name):
    try:
        from control.models import NotificationSettings
        cfg = NotificationSettings.objects.first()
        if cfg and cfg.is_smtp_verified and cfg.notify_user_terminated:
            html = _email_wrapper('❌', '#7f1d1d', 'Account Terminated', [
                ('Username', username),
                ('Domain',   domain_name),
                ('Status',   _badge('red', 'Terminated')),
            ])
            return send_admin_notification(f"[VoidPanel] Account Terminated: {domain_name}", html)
    except Exception as e:
        import logging; logging.getLogger(__name__).error(f"User terminated notification error: {e}")
    return False

def trigger_ssl_notification(domain_name):
    try:
        from control.models import NotificationSettings
        cfg = NotificationSettings.objects.first()
        if cfg and cfg.is_smtp_verified and cfg.notify_ssl_generated:
            html = _email_wrapper('🔐', '#0891b2', 'SSL Certificate Provisioned', [
                ('Domain',  domain_name),
                ('Status',  _badge('green', '✓ Active & Secure')),
                ('Issuer',  "Let's Encrypt"),
            ])
            return send_admin_notification(f"[VoidPanel] SSL Generated: {domain_name}", html)
    except Exception as e:
        import logging; logging.getLogger(__name__).error(f"SSL notification error: {e}")
    return False

def trigger_backup_created_notification(username, domain_name, backup_file=''):
    try:
        from control.models import NotificationSettings
        cfg = NotificationSettings.objects.first()
        if cfg and cfg.is_smtp_verified and cfg.notify_backup_created:
            html = _email_wrapper('💾', '#7c3aed', 'Backup Created', [
                ('Username',     username),
                ('Domain',       domain_name),
                ('Backup File',  backup_file or 'N/A'),
                ('Status',       _badge('green', 'Completed')),
            ])
            return send_admin_notification(f"[VoidPanel] Backup Created: {domain_name}", html)
    except Exception as e:
        import logging; logging.getLogger(__name__).error(f"Backup notification error: {e}")
    return False

def trigger_script_installed_notification(script_name, domain_name, username, admin_url=''):
    try:
        from control.models import NotificationSettings
        cfg = NotificationSettings.objects.first()
        if cfg and cfg.is_smtp_verified and cfg.notify_script_installed:
            html = _email_wrapper('🚀', '#059669', f'{script_name} Installed', [
                ('Application', script_name),
                ('Domain',      domain_name),
                ('Username',    username),
                ('Admin URL',   f'<a href="{admin_url}" style="color:#4f46e5;">{admin_url}</a>' if admin_url else 'N/A'),
                ('Status',      _badge('green', 'Active')),
            ])
            return send_admin_notification(f"[VoidPanel] {script_name} Installed on {domain_name}", html)
    except Exception as e:
        import logging; logging.getLogger(__name__).error(f"Script install notification error: {e}")
    return False

def trigger_login_notification(username, ip_address):
    try:
        from control.models import NotificationSettings
        cfg = NotificationSettings.objects.first()
        if cfg and cfg.is_smtp_verified and cfg.notify_login_alert:
            html = _email_wrapper('🔑', '#d97706', 'Panel Login Detected', [
                ('Username',    username),
                ('IP Address',  ip_address),
            ])
            return send_admin_notification(f"[VoidPanel] Login Alert: {username}", html)
    except Exception as e:
        import logging; logging.getLogger(__name__).error(f"Login notification error: {e}")
    return False
