"""
VoidPanel Local AI Agent Engine
--------------------------------
This module powers the local side of the Agentic AI.
It gathers rich server context, injects deep VoidPanel knowledge,
and routes the request to the central voidpanel.com API gateway.

Endpoints registered in urls.py:
  POST /api/agent/chat/    -> ai_chat_handler
  POST /api/agent/execute/ -> ai_execute_tool
"""

import json
import os
import platform
import socket
import subprocess
import psutil
import requests

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 1: VoidPanel Structural Knowledge Base (The AI's Brain)
# ═══════════════════════════════════════════════════════════════════════════════

VOIDPANEL_KNOWLEDGE = """
You are VoidPanel AI — an advanced, autonomous server management agent embedded
directly inside the VoidPanel hosting control panel.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  VOIDPANEL COMPLETE ARCHITECTURE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## PANEL STACK
- OS: Ubuntu 22.04 LTS or AlmaLinux 8/9 (RHEL-compatible)
- Web Server: NGINX (handles ALL domain vhosts, SSL, reverse proxy)
- PHP Handler: PHP-FPM (multiple PHP versions supported: 7.4, 8.0, 8.1, 8.2, 8.3)
- Panel Backend: Django (Python 3), running via uWSGI/Daphne on port 8082
- Panel URL: https://<server-ip>:8082 or https://<hostname>:8082
- Task Queue: Celery (with Redis as broker) - handles background jobs like user creation
- Database (Panel): SQLite at /var/www/panel/db.sqlite3
- Database (User): MariaDB/MySQL - root access via /root/.my.cnf
- FTP: vsftpd
- Mail Stack: Postfix (SMTP), Dovecot (IMAP/POP3), Roundcube Webmail (port 9000/9002), SpamAssassin, OpenDKIM
- DNS Server: BIND9 (named)
- Firewall: CSF (ConfigServer Security & Firewall) + iptables

## KEY DIRECTORIES & FILES

### Panel (Django App)
- App Root:          /var/www/panel/
- Django Settings:   /var/www/panel/panel/settings.py
- URL Config:        /var/www/panel/panel/urls.py
- Main Views:        /var/www/panel/panel/views.py
- AI Views:          /var/www/panel/panel/ai_views.py
- Celery Worker:     /var/www/panel/panel/celery.py
- SQLite DB:         /var/www/panel/db.sqlite3
- Static Files:      /var/www/panel/static/
- Panel Logs:        /var/log/voidpanel/ (panel.log, celery.log)
- uWSGI Config:      /etc/uwsgi/sites/panel.ini
- Daphne Service:    systemd unit 'daphne'

### NGINX (Web Server)
- Main Config:       /etc/nginx/nginx.conf
- Panel vHost:       /etc/nginx/conf.d/voidpanel.conf  (port 8082)
- Domain vHosts:     /etc/nginx/conf.d/<domain>.conf   (one per hosted domain)
- SSL Certificates:  /etc/nginx/ssl/<domain>.crt and .key
                     Also via Certbot: /etc/letsencrypt/live/<domain>/
- NGINX Error Log:   /var/log/nginx/error.log
- NGINX Access Log:  /var/log/nginx/access.log
- PHP-FPM Sockets:   /run/php/php<version>-fpm.sock (Ubuntu)
                     /run/php-fpm/www.sock (AlmaLinux)

### Domain Hosting Structure (per user account)
- User System Account: <domain>_user (e.g., example_com_user)
- User Home Dir:     /home/<username>/
- Web Root:          /home/<username>/public_html/
- PHP Error Log:     /home/<username>/logs/php_errors.log
- Domain NGINX conf: /etc/nginx/conf.d/<username>.conf
- Domain SSL:        /etc/nginx/ssl/<domain>.crt

### Mail Stack
- Postfix Config:    /etc/postfix/main.cf
- Dovecot Config:    /etc/dovecot/dovecot.conf
- Mail Spool:        /var/spool/mail/<username>
- DKIM Keys:         /etc/opendkim/keys/<domain>/
- Roundcube:         /var/www/roundcube/ (accessible on port 9000 or 9002)

### DNS (BIND9)
- Zone Files:        /var/named/<domain>.zone (AlmaLinux)
                     /etc/bind/zones/<domain>.zone (Ubuntu)
- Named Config:      /etc/named.conf (AlmaLinux) or /etc/bind/named.conf (Ubuntu)

### MariaDB / MySQL
- Root Credentials:  /root/.my.cnf
- Data Dir:          /var/lib/mysql/
- Config:            /etc/my.cnf or /etc/mysql/mariadb.conf.d/

### CSF Firewall
- Config:            /etc/csf/csf.conf
- Allow List:        /etc/csf/csf.allow
- Deny List:         /etc/csf/csf.deny
- Command:           csf -r (reload), csf -s (start), csf -f (flush/stop)

## KEY PANEL FEATURES & HOW THEY WORK
- Adding a domain: Creates a Linux user, NGINX vHost, webroot directory, DNS zone
- SSL: Uses certbot (Let's Encrypt) or copies uploaded certs to /etc/nginx/ssl/
- PHP version switching: Edits the NGINX vHost to point to a different PHP-FPM socket
- Database creation: Runs CREATE DATABASE and CREATE USER in MariaDB
- Email account creation: Adds user to Postfix/Dovecot via PAM or virtual users
- Backup: Creates a ZIP of /home/<username>/public_html/ + DB dump
- Celery workers: Process provisioning tasks asynchronously (user creation, SSL, etc.)

## COMMON PROBLEMS & HOW TO DIAGNOSE

### 502 Bad Gateway
- Check: `systemctl status php-fpm` or `systemctl status php8.1-fpm`
- Check: `systemctl status nginx`
- Check: `tail -50 /var/log/nginx/error.log`
- Cause: PHP-FPM socket missing, permission issue, or service crashed

### NGINX not starting
- Check: `nginx -t` (test config for syntax errors)
- Check: `systemctl status nginx`
- Cause: Syntax error in /etc/nginx/conf.d/ file, port conflict

### Celery worker down (provisioning fails)
- Check: `systemctl status celery`
- Check: `tail -50 /var/log/voidpanel/celery.log`
- Restart: `systemctl restart celery`

### Email not sending
- Check: `systemctl status postfix`
- Check: `tail -50 /var/log/mail.log`

### DNS not resolving
- Check: `systemctl status named` or `systemctl status bind9`
- Check zone file: `named-checkzone <domain> /var/named/<domain>.zone`

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  YOUR CAPABILITIES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. ANSWER any question about VoidPanel — features, configs, file locations.
2. DIAGNOSE issues by requesting to read logs or check service status.
3. EXECUTE fixes after the user explicitly approves the action.
4. GUIDE users step-by-step through complex server management tasks.

IMPORTANT: Always be specific. Use exact paths and commands from the knowledge above.
If you need to run a command, request it via the tool system — do NOT guess.
"""


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 2: Dynamic Server Context Gathering
# ═══════════════════════════════════════════════════════════════════════════════

def _run(cmd, timeout=5):
    """Safely run a shell command and return output string."""
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, timeout=timeout
        )
        return (result.stdout or '').strip()
    except Exception:
        return ''


def get_server_context():
    """
    Gathers a comprehensive snapshot of the live server state.
    This is injected into every AI request so the model knows exactly
    what is happening on the server RIGHT NOW.
    """
    ctx = {}

    # Basic identity
    ctx['hostname'] = socket.gethostname()
    ctx['os'] = platform.platform()

    # CPU
    ctx['cpu_cores'] = psutil.cpu_count()
    ctx['cpu_percent'] = psutil.cpu_percent(interval=0.5)
    ctx['load_avg_1m'] = os.getloadavg()[0]

    # RAM
    mem = psutil.virtual_memory()
    ctx['ram_total_gb']  = round(mem.total  / (1024**3), 2)
    ctx['ram_used_gb']   = round(mem.used   / (1024**3), 2)
    ctx['ram_percent']   = mem.percent

    # Disk (root partition)
    disk = psutil.disk_usage('/')
    ctx['disk_total_gb'] = round(disk.total / (1024**3), 2)
    ctx['disk_used_gb']  = round(disk.used  / (1024**3), 2)
    ctx['disk_percent']  = disk.percent

    # Uptime
    ctx['uptime'] = _run("uptime -p")

    # Hosted domains (from nginx conf.d)
    domains = []
    nginx_conf_dir = '/etc/nginx/conf.d'
    if os.path.exists(nginx_conf_dir):
        for f in os.listdir(nginx_conf_dir):
            if (f.endswith('.conf')
                    and not f.startswith('default')
                    and f != 'voidpanel.conf'
                    and f != 'ssl_params.conf'):
                domains.append(f.replace('.conf', ''))
    ctx['hosted_domains'] = domains
    ctx['domain_count'] = len(domains)

    # Key service statuses
    services = ['nginx', 'php-fpm', 'php8.1-fpm', 'php8.2-fpm',
                'mariadb', 'mysql', 'celery', 'postfix',
                'dovecot', 'named', 'bind9', 'vsftpd', 'redis']
    running = []
    stopped = []
    for svc in services:
        status = _run(f'systemctl is-active {svc} 2>/dev/null')
        if status == 'active':
            running.append(svc)
        elif status in ('inactive', 'failed'):
            stopped.append(svc)
    ctx['services_running'] = running
    ctx['services_stopped_or_failed'] = stopped

    # Recent NGINX errors (last 20 lines)
    ctx['nginx_recent_errors'] = _run('tail -20 /var/log/nginx/error.log 2>/dev/null')

    # Recent VoidPanel panel log (last 20 lines)
    ctx['panel_recent_log'] = _run('tail -20 /var/log/voidpanel/panel.log 2>/dev/null')

    # PHP versions installed
    ctx['php_versions_installed'] = _run(
        "update-alternatives --list php 2>/dev/null || ls /usr/bin/php* 2>/dev/null | grep -oP 'php\\d\\.\\d' | sort -u"
    )

    return ctx


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 3: Agentic Tool Definitions (JSON Schemas for the AI)
# ═══════════════════════════════════════════════════════════════════════════════

AI_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "run_terminal_command",
            "description": (
                "Execute a bash command on the server. Use this to: "
                "read log files, check service status, restart services, "
                "view config files, or fix issues. "
                "IMPORTANT: The user must approve this before it runs."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "The exact bash command to execute on the server."
                    }
                },
                "required": ["command"]
            }
        }
    }
]

# Blocklist of dangerous commands the AI must never be allowed to run
BLOCKED_COMMAND_PATTERNS = [
    'rm -rf /',
    'mkfs',
    'dd if=',
    '> /dev/sda',
    'shutdown -h now',
    'reboot',
    'halt',
    ':(){:|:&};:',  # fork bomb
]


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 4: Chat Handler View
# ═══════════════════════════════════════════════════════════════════════════════

@csrf_exempt
@login_required(login_url='/login/')
def ai_chat_handler(request):
    """
    POST /api/agent/chat/
    Bundles server context + user message + VoidPanel knowledge and sends
    the whole payload to the central voidpanel.com gateway.
    """
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Only POST allowed'}, status=405)

    try:
        body = json.loads(request.body)
        user_message = body.get('message', '').strip()
        chat_history = body.get('history', [])

        if not user_message:
            return JsonResponse({'status': 'error', 'message': 'Message is required'}, status=400)

        # Build the rich payload
        payload = {
            'system_prompt': VOIDPANEL_KNOWLEDGE,
            'server_context': get_server_context(),
            'tools': AI_TOOLS,
            'history': chat_history,
            'message': user_message,
        }

        # Route to central gateway on voidpanel.com
        gateway_url = getattr(settings, 'VOIDPANEL_AI_GATEWAY', 'https://voidpanel.com/api/ai/chat/')
        panel_host  = request.get_host()

        # Get local license key
        from control.license import get_license
        lic = get_license()
        lic_key = lic.key if lic else ''

        try:
            resp = requests.post(
                gateway_url,
                json=payload,
                headers={
                    'Content-Type': 'application/json',
                    'X-Panel-Host': panel_host,
                    'X-License-Key': lic_key,
                },
                timeout=45
            )

            if resp.status_code == 200:
                ai_data = resp.json()
                return JsonResponse({
                    'status': 'success',
                    'response':    ai_data.get('response', ''),
                    'tool_calls':  ai_data.get('tool_calls', []),
                })
            else:
                error_msg = f'AI Gateway returned HTTP {resp.status_code}.'
                try:
                    gateway_data = resp.json()
                    if 'message' in gateway_data:
                        error_msg = f"Gateway Error: {gateway_data['message']}"
                except ValueError:
                    pass
                
                return JsonResponse({
                    'status': 'error',
                    'message': error_msg
                }, status=502)

        except requests.exceptions.ConnectionError:
            return JsonResponse({
                'status': 'error',
                'message': (
                    'Could not reach the VoidPanel AI Gateway at voidpanel.com. '
                    'Please ensure the gateway is deployed and your server has internet access.'
                )
            }, status=503)

        except requests.exceptions.Timeout:
            return JsonResponse({
                'status': 'error',
                'message': 'The AI Gateway took too long to respond. Please try again.'
            }, status=504)

    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'message': 'Invalid JSON body'}, status=400)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 5: Tool Execution View
# ═══════════════════════════════════════════════════════════════════════════════

@csrf_exempt
@login_required(login_url='/login/')
def ai_execute_tool(request):
    """
    POST /api/agent/execute/
    Executes a tool ONLY after the user clicks [Approve] on the frontend.
    This is the safety gate — the AI cannot run anything without this approval.
    """
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Only POST allowed'}, status=405)

    try:
        body      = json.loads(request.body)
        tool_name = body.get('tool_name', '')
        arguments = body.get('arguments', {})

        if tool_name == 'run_terminal_command':
            cmd = arguments.get('command', '').strip()

            if not cmd:
                return JsonResponse({'status': 'error', 'message': 'No command provided'}, status=400)

            # Safety: block dangerous patterns
            cmd_lower = cmd.lower()
            for pattern in BLOCKED_COMMAND_PATTERNS:
                if pattern.lower() in cmd_lower:
                    return JsonResponse({
                        'status': 'error',
                        'message': f'Command blocked by safety filter: contains "{pattern}"'
                    }, status=403)

            # Execute safely
            try:
                result = subprocess.run(
                    cmd,
                    shell=True,
                    capture_output=True,
                    text=True,
                    timeout=20
                )
                output = result.stdout or ''
                if result.stderr:
                    output += '\n[stderr]:\n' + result.stderr
                if not output.strip():
                    output = f'Command exited with code {result.returncode} (no output)'

                return JsonResponse({
                    'status': 'success',
                    'result': output,
                    'exit_code': result.returncode
                })

            except subprocess.TimeoutExpired:
                return JsonResponse({
                    'status': 'error',
                    'message': 'Command timed out after 20 seconds'
                }, status=408)

        else:
            return JsonResponse({
                'status': 'error',
                'message': f'Unknown tool: {tool_name}'
            }, status=400)

    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'message': 'Invalid JSON body'}, status=400)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
