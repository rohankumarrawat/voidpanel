"""
VoidPanel One-Click Script Installer Engine
============================================
Each function handles the full automated provisioning of a given
script onto the server. Functions are designed to be called from
a Celery background task so they never block the web request.

Conventions:
  - All functions accept (domain, username, **kwargs) as the base args.
  - All functions return a dict: {'status': 'success'|'failed', 'log': str, 'admin_url': str, ...}
  - Database credentials are auto-generated here and returned in the dict.
"""

import os
import re
import subprocess
import secrets
import string


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _run(cmd, timeout=300):
    """Run a shell command, return (returncode, stdout+stderr)."""
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, timeout=timeout
        )
        return result.returncode, result.stdout + result.stderr
    except subprocess.TimeoutExpired:
        return 1, "Command timed out after {} seconds.".format(timeout)
    except Exception as e:
        return 1, str(e)


def _gen_password(length=16):
    """Generate a secure random password."""
    chars = string.ascii_letters + string.digits + '!@#$%^&*'
    return ''.join(secrets.choice(chars) for _ in range(length))


def _sanitize_db_name(value, max_len=16):
    """Convert a domain/string into a safe DB name component."""
    safe = re.sub(r'[^a-zA-Z0-9_]', '_', value)
    return safe[:max_len]


def _get_mysql_password():
    """Read the MySQL root password from the server credential file."""
    # Plain-text password file (primary location on VoidPanel servers)
    for path in ('/etc/dontdelete.txt', '/var/www/panel/credentials/mysql_password.txt'):
        try:
            with open(path, 'r') as f:
                pw = f.read().strip()
                if pw:
                    return pw
        except Exception:
            continue
    # Fallback: parse /root/.my.cnf
    try:
        with open('/root/.my.cnf', 'r') as f:
            for line in f:
                line = line.strip()
                if line.startswith('password') and '=' in line:
                    return line.split('=', 1)[1].strip()
    except Exception:
        pass
    return ''


def _mysql(sql):
    """Run a MySQL statement as root using a safe temp config file."""
    import tempfile
    pw = _get_mysql_password()
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', suffix='.cnf', delete=False) as tmp:
            tmp.write('[client]\n')
            tmp.write('user=root\n')
            if pw:
                tmp.write(f'password={pw}\n')
            tmp_path = tmp.name
        # Use subprocess list form to avoid ALL shell quoting issues
        import subprocess
        result = subprocess.run(
            ['mysql', f'--defaults-extra-file={tmp_path}', '-e', sql],
            capture_output=True, text=True, timeout=60
        )
        out = result.stdout + result.stderr
        return result.returncode, out
    except Exception as e:
        return 1, str(e)
    finally:
        if tmp_path:
            try:
                os.unlink(tmp_path)
            except Exception:
                pass


def _create_mysql_db(db_name, db_user, db_pass):
    """Create a MySQL database and user, return (success_bool, log).
    Always drops and recreates the user to avoid stale-password conflicts
    from previous failed installations."""
    log = ""
    statements = [
        f'CREATE DATABASE IF NOT EXISTS `{db_name}`;',
        # Drop user first so we always set the correct password (handles retries)
        f"DROP USER IF EXISTS '{db_user}'@'localhost';",
        f"CREATE USER '{db_user}'@'localhost' IDENTIFIED BY '{db_pass}';",
        f"GRANT ALL PRIVILEGES ON `{db_name}`.* TO '{db_user}'@'localhost';",
        'FLUSH PRIVILEGES;',
    ]
    for sql in statements:
        rc, out = _mysql(sql)
        log += out
        if rc != 0:
            return False, log
    return True, log


def _ensure_public_html(username, subdomain=None):
    """Return the correct public_html path for a domain or subdomain."""
    if subdomain:
        return f"/home/{username}/subdomains/{subdomain}/public_html"
    return f"/home/{username}/public_html"


def _get_wp_php():
    """Return PHP binary that has the mysqli extension (needed by WP-CLI)."""
    import subprocess as _sp
    for php in (
        '/usr/bin/php8.5', '/usr/bin/php8.4', '/usr/bin/php8.3', '/usr/bin/php8.2', '/usr/bin/php8.1',
        'php8.5', 'php8.4', 'php8.3', 'php8.2', 'php8.1', 'php8.0', 'php7.4',
        '/usr/bin/php', 'php'
    ):
        try:
            r = _sp.run([php, '-r', 'mysqli_init();'], capture_output=True, timeout=5)
            if r.returncode == 0:
                return php
        except Exception:
            continue
    return 'php'  # fallback


# ─── WordPress ────────────────────────────────────────────────────────────────

def install_wordpress(domain, username, admin_user, admin_pass, admin_email,
                       install_url=None, site_title=None, **kwargs):
    """Install WordPress using WP-CLI. Celery runs as www-data, so all
    file operations in user home directories go through sudo."""
    import subprocess as _sp
    log = ""
    install_url = install_url or domain
    site_title  = site_title or f"{domain} WordPress Site"

    # Derive the correct install path — subdomains live at public_html/{sub}/
    if install_url == domain:
        public_html = f"/home/{username}/public_html"
    else:
        sub_label = install_url.replace(f'.{domain}', '').strip('.')
        public_html = f"/home/{username}/public_html/{sub_label}"

    # DB credentials — unique per install_url (not just per username) to avoid conflicts
    import hashlib
    url_hash = hashlib.md5(install_url.encode()).hexdigest()[:4]   # short 4-char hash
    suffix   = _sanitize_db_name(username, 8)
    db_name  = f"{suffix}_wp_{url_hash}"    # e.g. namanitw_wp_a3f1
    db_user  = f"{suffix}_wpu{url_hash}"    # e.g. namanitw_wpua3f1  (max 32 chars)
    db_pass  = _gen_password(14)

    # 1. Ensure WP-CLI is installed as root
    _run("test -x /usr/local/bin/wp || (curl -fsSL https://raw.githubusercontent.com/wp-cli/builds/gh-pages/phar/wp-cli.phar -o /usr/local/bin/wp && chmod +x /usr/local/bin/wp)")
    WP_PHP = _get_wp_php()
    log += f"[WP-CLI] Using {WP_PHP}\n"

    # 2. Create and fully open the target directory using sudo (www-data can't write to user home)
    rc, out = _run(f"sudo mkdir -p {public_html}")
    log += f"[mkdir] {out}\n"
    rc, out = _run(f"sudo chmod -R 777 {public_html}")   # open for all writes
    log += f"[chmod pre] {out}\n"

    # 3. Create database
    ok, db_log = _create_mysql_db(db_name, db_user, db_pass)
    log += f"[MySQL] {db_log}\n"
    if not ok:
        _run(f"sudo chmod -R 755 {public_html}")
        return {'status': 'failed', 'log': log, 'error': 'Database creation failed'}

    # 4. Download WordPress zip (cached to /tmp)
    wp_zip = '/tmp/wordpress-6.5.zip'
    if not os.path.exists(wp_zip):
        rc, out = _run(f"wget -q https://downloads.wordpress.org/release/wordpress-6.5.zip -O {wp_zip} 2>&1")
        log += f"[WP Download] {out}\n"
        if rc != 0:
            _run(f"sudo chmod -R 755 {public_html}")
            return {'status': 'failed', 'log': log, 'error': 'WordPress download failed'}
    else:
        log += "[WP Download] Using cached wordpress-6.5.zip\n"

    # 5. Extract to /tmp as current user, then sudo-copy to target
    tmp_dir = f"/tmp/wp_extract_{os.getpid()}"
    _run(f"rm -rf {tmp_dir}")
    rc, out = _run(f"unzip -q {wp_zip} -d {tmp_dir} 2>&1")
    log += f"[WP Extract] rc={rc} {out}\n"
    # Use sudo cp so files land in the target regardless of ownership
    rc, out = _run(f"sudo cp -rp {tmp_dir}/wordpress/. {public_html}/ 2>&1")
    log += f"[WP Copy] rc={rc} {out[:200]}\n"
    _run(f"rm -rf {tmp_dir}")
    if rc != 0:
        _run(f"sudo chmod -R 755 {public_html}")
        return {'status': 'failed', 'log': log, 'error': 'WordPress file copy failed'}

    # Remove any leftover placeholder files (React index.html, static/ folder from subdomain creation)
    _run(f"sudo rm -f {public_html}/index.html")
    _run(f"sudo rm -rf {public_html}/static")

    # 6. Create wp-config.php via sudo so it can write to the dir
    r = _sp.run(
        ['sudo', WP_PHP, '/usr/local/bin/wp', 'config', 'create',
         f'--dbname={db_name}', f'--dbuser={db_user}', f'--dbpass={db_pass}',
         '--dbhost=localhost', f'--path={public_html}', '--allow-root', '--force'],
        capture_output=True, text=True, timeout=60
    )
    log += f"[WP Config] {r.stdout}{r.stderr}\n"
    if r.returncode != 0:
        _run(f"sudo chmod -R 755 {public_html}")
        return {'status': 'failed', 'log': log, 'error': 'wp-config creation failed'}

    # 7. Run core install via sudo
    r = _sp.run(
        ['sudo', WP_PHP, '/usr/local/bin/wp', 'core', 'install',
         f'--url=https://{install_url}',
         f'--title={site_title}',
         f'--admin_user={admin_user}',
         f'--admin_password={admin_pass}',
         f'--admin_email={admin_email}',
         f'--path={public_html}', '--allow-root'],
        capture_output=True, text=True, timeout=120
    )
    log += f"[WP Install] {r.stdout}{r.stderr}\n"
    if r.returncode != 0:
        _run(f"sudo chmod -R 755 {public_html}")
        return {'status': 'failed', 'log': log, 'error': 'WordPress core install failed'}

    # 8. Fix final ownership and permissions
    _run(f"sudo chown -R {username}:www-data {public_html}")
    _run(f"sudo find {public_html} -type d -exec chmod 755 {{}} \\;")
    _run(f"sudo find {public_html} -type f -exec chmod 644 {{}} \\;")

    return {
        'status':    'success',
        'log':       log,
        'admin_url': f"https://{install_url}/wp-admin/",
        'db_name':   db_name,
        'db_user':   db_user,
        'db_pass':   db_pass,
    }



# ─── Ghost (Node.js) ──────────────────────────────────────────────────────────

def install_ghost(domain, username, admin_user, admin_pass, admin_email,
                   install_url=None, **kwargs):
    """Install Ghost CMS using ghost-cli."""
    log = ""
    install_url  = install_url or domain
    ghost_dir    = f"/home/{username}/ghost_{domain.replace('.','_')}"
    port         = kwargs.get('port', 2368)

    # ── Ensure npm log dir writable ─────────────────────────────────────────
    _run("sudo mkdir -p /var/www/.npm/_logs && sudo chmod -R 777 /var/www/.npm")
    _run("sudo mkdir -p /root/.npm && sudo chmod -R 777 /root/.npm")

    # ── Install ghost-cli globally with sudo (requires root perms) ────────────
    import shutil
    ghost_bin = shutil.which('ghost') or '/usr/local/bin/ghost'
    if not (ghost_bin and os.path.exists(ghost_bin)):
        rc, out = _run("sudo npm install -g ghost-cli@latest 2>&1", timeout=300)
        log += f"[Ghost CLI Install] {out}\n"
        ghost_bin = shutil.which('ghost') or '/usr/local/bin/ghost'
    else:
        log += f"[Ghost CLI] Already at {ghost_bin}\n"

    if not (ghost_bin and os.path.exists(ghost_bin)):
        return {'status': 'failed', 'log': log, 'error': 'ghost-cli could not be installed'}

    # ── Create Ghost directory ────────────────────────────────────────────────
    rc, out = _run(f"sudo mkdir -p {ghost_dir} && sudo chown -R {username}:{username} {ghost_dir} && sudo chmod 755 {ghost_dir}")
    log += f"[mkdir] {out}\n"

    # ── Run ghost install as the hosting user ─────────────────────────────────
    rc, out = _run(
        f"cd {ghost_dir} && sudo -u {username} "
        f"HOME=/home/{username} {ghost_bin} install --no-prompt "
        f"--url https://{install_url} --port {port} "
        f"--db sqlite3 --no-setup-nginx --no-setup-ssl --no-setup-systemd "
        f"--no-setup-linux-user --process local 2>&1",
        timeout=600
    )
    log += f"[Ghost Install] {out}\n"
    if rc != 0:
        return {'status': 'failed', 'log': log, 'error': 'Ghost installation failed'}

    # ── Start Ghost ───────────────────────────────────────────────────────────
    _run(f"cd {ghost_dir} && sudo -u {username} HOME=/home/{username} {ghost_bin} start 2>&1", timeout=60)

    # ── Create SSL Nginx reverse proxy config ────────────────────────────────
    from function import generate_ssl_certificates, create_nginx_ssl_conf
    ssl_dir  = f"/home/{username}/ssl"
    logs_dir = f"/home/{username}/logs"
    cert_path, key_path = generate_ssl_certificates(install_url, ssl_dir, logs_dir)

    conf_path = f"/etc/nginx/sites-available/{install_url}.conf"
    if cert_path and key_path:
        # SSL config with proxy
        nginx_conf = f"""
server {{
    listen 443 ssl;
    server_name {install_url};
    ssl_certificate {cert_path};
    ssl_certificate_key {key_path};
    client_max_body_size 100M;
    location / {{
        proxy_pass http://127.0.0.1:{port};
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto https;
        proxy_read_timeout 90;
    }}
}}
server {{
    listen 80;
    server_name {install_url};
    return 301 https://$host$request_uri;
}}
"""
    else:
        nginx_conf = f"""
server {{
    listen 80;
    server_name {install_url};
    location / {{
        proxy_pass http://127.0.0.1:{port};
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }}
}}
"""
    import tempfile, subprocess as _sp
    with tempfile.NamedTemporaryFile('w', delete=False) as tf:
        tf.write(nginx_conf)
        tmp = tf.name
    _sp.run(f"sudo cp {tmp} {conf_path} && sudo chmod 644 {conf_path}", shell=True, check=False)
    _sp.run(f"sudo ln -sf {conf_path} /etc/nginx/sites-enabled/ && sudo nginx -t && sudo systemctl reload nginx", shell=True, check=False)
    import os as _os; _os.unlink(tmp)

    return {
        'status':    'success',
        'log':       log,
        'admin_url': f"https://{install_url}/ghost/",
        'db_name':   '',
        'db_user':   '',
    }


# ─── Nextcloud ────────────────────────────────────────────────────────────────

def install_nextcloud(domain, username, admin_user, admin_pass, admin_email,
                       install_url=None, **kwargs):
    """Install Nextcloud via direct download and occ installer."""
    log = ""
    install_url = install_url or domain
    public_html = _ensure_public_html(username)
    nc_url      = "https://download.nextcloud.com/server/releases/latest.zip"

    import hashlib
    url_hash = hashlib.md5(install_url.encode()).hexdigest()[:4]
    suffix  = _sanitize_db_name(username, 8)
    db_name = f"{suffix}_nc_{url_hash}"
    db_user = f"{suffix}_ncu{url_hash}"
    db_pass = _gen_password(14)

    ok, db_log = _create_mysql_db(db_name, db_user, db_pass)
    log += f"[MySQL] {db_log}\n"
    if not ok:
        return {'status': 'failed', 'log': log, 'error': 'DB creation failed'}

    rc, out = _run(f"wget -q {nc_url} -O /tmp/nextcloud.zip && unzip -q /tmp/nextcloud.zip -d /tmp/ && rsync -a /tmp/nextcloud/ {public_html}/ && rm -rf /tmp/nextcloud /tmp/nextcloud.zip", timeout=300)
    log += f"[Download] {out}\n"

    rc, out = _run(
        f"cd {public_html} && sudo -u {username} php occ maintenance:install "
        f"--database='mysql' --database-name='{db_name}' --database-user='{db_user}' --database-pass='{db_pass}' "
        f"--admin-user='{admin_user}' --admin-pass='{admin_pass}' --data-dir={public_html}/data 2>&1",
        timeout=180
    )
    log += f"[OCC Install] {out}\n"
    if rc != 0:
        return {'status': 'failed', 'log': log, 'error': 'Nextcloud occ install failed'}

    rc, out = _run(
        f"cd {public_html} && sudo -u {username} php occ config:system:set trusted_domains 1 --value='{install_url}' 2>&1"
    )
    _run(f"chown -R {username}:www-data {public_html} && chmod -R 770 {public_html}")

    return {
        'status':    'success',
        'log':       log,
        'admin_url': f"https://{install_url}/index.php/login",
        'db_name':   db_name,
        'db_user':   db_user,
    }


# ─── PrestaShop ───────────────────────────────────────────────────────────────

def install_prestashop(domain, username, admin_user, admin_pass, admin_email,
                        install_url=None, **kwargs):
    """Install PrestaShop eCommerce platform."""
    log = ""
    install_url = install_url or domain
    public_html = _ensure_public_html(username)
    ps_url      = "https://github.com/PrestaShop/PrestaShop/releases/download/8.1.7/prestashop_8.1.7.zip"

    suffix  = _sanitize_db_name(username, 8)
    db_name = f"{suffix}_ps"
    db_user = f"{suffix}_psu"
    db_pass = _gen_password(14)

    ok, db_log = _create_mysql_db(db_name, db_user, db_pass)
    log += db_log
    if not ok:
        return {'status': 'failed', 'log': log, 'error': 'DB creation failed'}

    rc, out = _run(f"wget -q {ps_url} -O /tmp/ps.zip && unzip -q /tmp/ps.zip -d {public_html}/ && rm /tmp/ps.zip", timeout=300)
    log += out

    _run(f"chown -R {username}:www-data {public_html}")

    return {
        'status':    'success',
        'log':       log,
        'admin_url': f"https://{install_url}/install/",
        'db_name':   db_name,
        'db_user':   db_user,
        'note':      'Complete setup by visiting the install URL in your browser.',
    }


# ─── Gitea ────────────────────────────────────────────────────────────────────

def install_gitea(domain, username, admin_user, admin_pass, admin_email,
                   install_url=None, **kwargs):
    """Install lightweight Gitea self-hosted Git service."""
    log = ""
    install_url = install_url or domain
    port        = kwargs.get('port', 3000)
    gitea_dir   = f"/home/{username}/gitea"

    gitea_url   = "https://dl.gitea.com/gitea/1.21.11/gitea-1.21.11-linux-amd64"
    rc, out = _run(f"mkdir -p {gitea_dir} && wget -q {gitea_url} -O {gitea_dir}/gitea && chmod +x {gitea_dir}/gitea", timeout=120)
    log += out

    # Create systemd service
    service = f"""[Unit]
Description=Gitea for {domain}
After=network.target

[Service]
User={username}
WorkingDirectory={gitea_dir}
ExecStart={gitea_dir}/gitea web --port {port}
Restart=always

[Install]
WantedBy=multi-user.target
"""
    svc_path = f"/etc/systemd/system/gitea-{username}.service"
    with open(svc_path, 'w') as f:
        f.write(service)

    _run(f"systemctl daemon-reload && systemctl enable gitea-{username} && systemctl start gitea-{username}")

    # Nginx reverse proxy
    nginx_conf = f"""
server {{
    listen 80;
    server_name {install_url};
    location / {{
        proxy_pass http://127.0.0.1:{port};
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }}
}}
"""
    conf_path = f"/etc/nginx/sites-available/{install_url}.gitea.conf"
    with open(conf_path, 'w') as f:
        f.write(nginx_conf)
    _run(f"ln -sf {conf_path} /etc/nginx/sites-enabled/ && nginx -t && systemctl reload nginx")

    return {
        'status':    'success',
        'log':       log,
        'admin_url': f"https://{install_url}",
        'db_name':   '',
        'db_user':   '',
        'note':      f'Gitea running on port {port}. Complete setup via browser.',
    }


# ─── Uptime Kuma ──────────────────────────────────────────────────────────────

def install_uptimekuma(domain, username, admin_user, admin_pass, admin_email,
                        install_url=None, **kwargs):
    """Install Uptime Kuma monitoring tool via Docker or Node."""
    log = ""
    install_url = install_url or domain
    port        = kwargs.get('port', 3001)
    kuma_dir    = f"/home/{username}/uptimekuma"

    rc, out = _run(f"git clone https://github.com/louislam/uptime-kuma.git {kuma_dir} --depth=1 2>&1", timeout=120)
    log += out
    rc, out = _run(f"cd {kuma_dir} && npm install --production 2>&1", timeout=300)
    log += out

    service = f"""[Unit]
Description=Uptime Kuma for {domain}
After=network.target

[Service]
User={username}
WorkingDirectory={kuma_dir}
ExecStart=/usr/bin/node {kuma_dir}/server/server.js
Environment=PORT={port}
Restart=always

[Install]
WantedBy=multi-user.target
"""
    svc_path = f"/etc/systemd/system/kuma-{username}.service"
    with open(svc_path, 'w') as f:
        f.write(service)
    _run(f"systemctl daemon-reload && systemctl enable kuma-{username} && systemctl start kuma-{username}")

    # Nginx proxy
    nginx_conf = f"server {{ listen 80; server_name {install_url}; location / {{ proxy_pass http://127.0.0.1:{port}; proxy_set_header Host $host; }} }}"
    conf_path = f"/etc/nginx/sites-available/{install_url}.kuma.conf"
    with open(conf_path, 'w') as f:
        f.write(nginx_conf)
    _run(f"ln -sf {conf_path} /etc/nginx/sites-enabled/ && nginx -t && systemctl reload nginx")

    return {
        'status':    'success',
        'log':       log,
        'admin_url': f"https://{install_url}",
        'db_name':   '',
        'db_user':   '',
    }


# ─── N8N ──────────────────────────────────────────────────────────────────────

def install_n8n(domain, username, admin_user, admin_pass, admin_email,
                 install_url=None, **kwargs):
    """Install n8n workflow automation via npx."""
    log = ""
    install_url = install_url or domain
    port        = kwargs.get('port', 5678)

    rc, out = _run("npm install -g n8n 2>&1", timeout=300)
    log += out

    service = f"""[Unit]
Description=n8n for {domain}
After=network.target

[Service]
User={username}
ExecStart=/usr/bin/n8n
Environment=N8N_PORT={port}
Environment=N8N_HOST=127.0.0.1
Environment=WEBHOOK_URL=https://{install_url}/
Restart=always

[Install]
WantedBy=multi-user.target
"""
    svc_path = f"/etc/systemd/system/n8n-{username}.service"
    with open(svc_path, 'w') as f:
        f.write(service)
    _run(f"systemctl daemon-reload && systemctl enable n8n-{username} && systemctl start n8n-{username}")

    nginx_conf = f"server {{ listen 80; server_name {install_url}; location / {{ proxy_pass http://127.0.0.1:{port}; proxy_set_header Host $host; proxy_http_version 1.1; proxy_set_header Upgrade $http_upgrade; proxy_set_header Connection 'upgrade'; }} }}"
    conf_path = f"/etc/nginx/sites-available/{install_url}.n8n.conf"
    with open(conf_path, 'w') as f:
        f.write(nginx_conf)
    _run(f"ln -sf {conf_path} /etc/nginx/sites-enabled/ && nginx -t && systemctl reload nginx")

    return {
        'status':    'success',
        'log':       log,
        'admin_url': f"https://{install_url}",
        'db_name':   '',
        'db_user':   '',
    }


# ─── Dispatcher ───────────────────────────────────────────────────────────────

INSTALLER_MAP = {
    'wordpress':  install_wordpress,
    'ghost':      install_ghost,
    'nextcloud':  install_nextcloud,
    'prestashop': install_prestashop,
    'gitea':      install_gitea,
    'uptimekuma': install_uptimekuma,
    'n8n':        install_n8n,
}


def run_installer(script_name, domain, username, admin_user, admin_pass,
                  admin_email, **kwargs):
    """
    Dispatcher — call this from the Celery task.
    Returns a result dict or raises an error.
    """
    script_name = script_name.lower().replace(' ', '').replace('-', '')
    fn = INSTALLER_MAP.get(script_name)
    if not fn:
        return {
            'status': 'failed',
            'log': f"No installer found for script '{script_name}'.",
        }
    try:
        return fn(
            domain=domain, username=username,
            admin_user=admin_user, admin_pass=admin_pass,
            admin_email=admin_email, **kwargs
        )
    except Exception as e:
        return {
            'status': 'failed',
            'log': str(e),
        }


def run_uninstaller(installed_script_obj):
    """
    Cleans up an installed script.  For now: removes the
    public_html files and drops the MySQL DB if known.
    Returns a result dict.
    """
    log  = ""
    inst = installed_script_obj

    # Drop MySQL database (using root credentials)
    if inst.db_name:
        rc, out = _mysql(f"DROP DATABASE IF EXISTS `{inst.db_name}`;")
        log += f"[Drop DB] {out}\n"
    if inst.db_user:
        rc, out = _mysql(f"DROP USER IF EXISTS '{inst.db_user}'@'localhost';")
        log += f"[Drop User] {out}\n"

    # Remove files for WordPress/PHP apps (not Node services)
    if inst.install_dir and inst.script_name in ('wordpress', 'nextcloud', 'prestashop', 'opencart'):
        install_dir = inst.install_dir.rstrip('/')

        # ── SAFETY CHECK: if install_dir IS public_html itself, only remove WP files
        #    rather than deleting the entire public_html directory (the user's web root).
        is_public_html_root = install_dir.endswith('/public_html')

        if is_public_html_root and inst.script_name == 'wordpress':
            # Remove WordPress-specific files and folders, keep the directory
            wp_dirs  = ['wp-admin', 'wp-includes', 'wp-content']
            wp_files = [
                'wp-config.php', 'wp-config-sample.php', 'wp-login.php',
                'wp-cron.php', 'wp-load.php', 'wp-settings.php', 'wp-signup.php',
                'wp-trackback.php', 'wp-comments-post.php', 'wp-links-opml.php',
                'wp-mail.php', 'wp-blog-header.php', 'wp-activate.php',
                'xmlrpc.php', 'index.php', '.htaccess', 'license.txt', 'readme.html',
            ]
            for d in wp_dirs:
                rc, out = _run(f"sudo rm -rf {install_dir}/{d}")
                log += f"[Delete WP dir {d}] rc={rc}\n"
            for f_name in wp_files:
                rc, out = _run(f"sudo rm -f {install_dir}/{f_name}")

            # Recreate a minimal placeholder index.html so the domain isn't broken
            placeholder = "<html><body><p>No website installed.</p></body></html>"
            _run(f"sudo bash -c 'echo \"{placeholder}\" > {install_dir}/index.html'")
            _run(f"sudo chown {inst.username}:www-data {install_dir}/index.html")
            log += "[Cleanup] WordPress files removed. Directory preserved.\n"

        else:
            # Sub-directory install OR non-WordPress: safe to remove the whole subdirectory
            if os.path.exists(install_dir):
                # Extra safety: never rm -rf a path shorter than /home/x/xxx
                parts = [p for p in install_dir.split('/') if p]
                if len(parts) >= 3:
                    rc, out = _run(f"sudo rm -rf {install_dir}")
                    log += f"[Delete Files] rc={rc} {out}\n"

                    # If it was a subdomain subfolder under public_html, recreate it empty
                    parent = '/'.join(install_dir.split('/')[:-1])
                    if '/public_html/' in install_dir:
                        _run(f"sudo mkdir -p {install_dir}")
                        placeholder = "<html><body><p>No website installed.</p></body></html>"
                        _run(f"sudo bash -c 'echo \"{placeholder}\" > {install_dir}/index.html'")
                        _run(f"sudo chown -R {inst.username}:www-data {install_dir}")
                else:
                    log += f"[Safety] Refusing to delete short path: {install_dir}\n"

    # Stop and remove systemd service for Node apps
    for svc_prefix in ('gitea', 'kuma', 'n8n'):
        if inst.script_name == svc_prefix or inst.script_name.startswith(svc_prefix):
            svc = f"{svc_prefix}-{inst.username}"
            _run(f"systemctl stop {svc} && systemctl disable {svc}")
            svc_path = f"/etc/systemd/system/{svc}.service"
            if os.path.exists(svc_path):
                os.remove(svc_path)
            _run("systemctl daemon-reload")

    # Remove Nginx conf
    for ext in ('.ghost.conf', '.gitea.conf', '.kuma.conf', '.n8n.conf'):
        for base in ('/etc/nginx/sites-available/', '/etc/nginx/sites-enabled/'):
            path = f"{base}{inst.install_url}{ext}"
            if os.path.exists(path):
                os.remove(path)
    _run("nginx -t && systemctl reload nginx")

    return {'status': 'success', 'log': log}
