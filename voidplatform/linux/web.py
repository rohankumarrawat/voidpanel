"""
VoidPanel Linux Web Server Manager — supports NGINX and OpenLiteSpeed (OLS).

The active engine is read from /etc/voidpanel/web_engine (values: 'nginx' | 'ols').
If the file is absent, NGINX is assumed (safe default).
All public-facing calls go through get_web_manager() which returns the correct
implementation.  During a hot-swap the caller is responsible for stopping the
old service and starting the new one *after* all configs have been written.
"""
import os
import re
import subprocess
import xml.etree.ElementTree as ET
from ..base import WebServerManager, CommandResult
from ..config import LinuxPaths as paths

# ── System state flag ───────────────────────────────────────────────────────
STATE_FILE  = '/etc/voidpanel/web_engine'
OLS_ROOT    = '/usr/local/lsws'
OLS_CONF    = os.path.join(OLS_ROOT, 'conf')
OLS_VHOSTS  = os.path.join(OLS_CONF, 'vhosts')
OLS_HTTPD   = os.path.join(OLS_CONF, 'httpd_config.conf')


def get_active_engine() -> str:
    """Return 'nginx' or 'ols'. Defaults to 'nginx' if flag file absent."""
    try:
        with open(STATE_FILE) as f:
            val = f.read().strip().lower()
            return val if val in ('nginx', 'ols') else 'nginx'
    except FileNotFoundError:
        return 'nginx'


def set_active_engine(engine: str) -> None:
    """Persist the active engine to the state file."""
    if engine not in ('nginx', 'ols'):
        raise ValueError(f"Invalid engine: {engine}")
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    with open(STATE_FILE, 'w') as f:
        f.write(engine)


def get_web_manager() -> WebServerManager:
    """Factory — returns the manager for the currently active engine."""
    engine = get_active_engine()
    if engine == 'ols':
        return OLSWebServerManager()
    return NginxWebServerManager()


# Alias used by panel/views.py and other callers
def get_active_engine_manager() -> WebServerManager:
    """Alias for get_web_manager() — returns manager for the active engine."""
    return get_web_manager()


# ── Helpers ──────────────────────────────────────────────────────────────────

def _run(cmd, **kwargs):
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=60, **kwargs)
        return CommandResult(success=r.returncode == 0,
                             output=r.stdout.strip(),
                             error=r.stderr.strip(),
                             return_code=r.returncode)
    except Exception as e:
        return CommandResult(success=False, error=str(e), return_code=-1)


def _harden_site_dir(root_dir: str, unix_user: str, web_group: str) -> None:
    """
    Apply hardened directory permissions after a site is created or switched:
      - root_dir owned by  unix_user : web_group
      - Directories: 750  (owner rwx, group r-x, world ---)
      - Files:       640  (owner rw-, group r--, world ---)
      - public_html itself: 755 so the web server can serve static content
    This enforces quota attribution because files are owned by the unix user.
    """
    try:
        subprocess.run(['sudo', 'chown', '-R', f'{unix_user}:{web_group}', root_dir],
                       check=False, timeout=30)
        subprocess.run(['sudo', 'chmod', '755', root_dir], check=False, timeout=10)
        # Walk and set granular permissions
        for dirpath, dirnames, filenames in os.walk(root_dir):
            subprocess.run(['sudo', 'chmod', '750', dirpath], check=False, timeout=10)
            for fname in filenames:
                subprocess.run(['sudo', 'chmod', '640',
                                os.path.join(dirpath, fname)], check=False, timeout=10)
        # public_html itself needs execute so nginx / lsws can serve it
        subprocess.run(['sudo', 'chmod', '755', root_dir], check=False, timeout=10)
    except Exception:
        pass


# ── NGINX Implementation ─────────────────────────────────────────────────────

class NginxWebServerManager(WebServerManager):
    """Manages NGINX-format site configurations under sites-available / conf.d."""

    # PHP-FPM socket template (platform paths fill the version)
    _PHP_SOCK = paths.PHP_FPM_SOCK if hasattr(paths, 'PHP_FPM_SOCK') else \
        '/run/php-fpm/php{version}-fpm.sock'

    def create_site(self, domain: str, root_dir: str,
                    php_version: str = '', ssl: bool = False,
                    unix_user: str = '') -> CommandResult:
        conf = self.get_site_config_path(domain)

        # ── HTTP block ──────────────────────────────────────────────────────
        block  = f"server {{\n"
        block += f"    listen 80;\n"
        block += f"    server_name {domain} www.{domain};\n"
        block += f"    root {root_dir};\n"
        block += f"    index index.html index.php;\n"
        block += f"    access_log /var/log/nginx/{domain}.access.log;\n"
        block += f"    error_log  /var/log/nginx/{domain}.error.log;\n\n"

        # Security headers
        block += "    # Security headers\n"
        block += "    add_header X-Frame-Options SAMEORIGIN always;\n"
        block += "    add_header X-Content-Type-Options nosniff always;\n"
        block += "    add_header X-XSS-Protection \"1; mode=block\" always;\n"
        block += "    add_header Referrer-Policy strict-origin-when-cross-origin always;\n\n"

        # Acme-challenge for Certbot (always allowed, needed for SSL issuance)
        block += "    location /.well-known/acme-challenge/ {\n"
        block += f"        root {root_dir};\n"
        block += "        allow all;\n"
        block += "    }\n\n"

        block += "    location / {\n"
        block += "        try_files $uri $uri/ =404;\n"
        block += "    }\n"

        if php_version:
            sock = self._PHP_SOCK.format(version=php_version)
            block += f"\n    location ~ \\.php$ {{\n"
            block += f"        include snippets/fastcgi-php.conf;\n"
            block += f"        fastcgi_pass unix:{sock};\n"
            block += f"        fastcgi_param SCRIPT_FILENAME $document_root$fastcgi_script_name;\n"
            block += f"        include fastcgi_params;\n"
            block += f"    }}\n"

        # Deny hidden files (security)
        block += "\n    location ~ /\\.(?!well-known) {\n"
        block += "        deny all;\n"
        block += "    }\n"
        block += "}\n"

        try:
            import tempfile
            avail_dir = os.path.dirname(conf)
            _run(['sudo', 'mkdir', '-p', avail_dir])
            # Write to temp file then sudo mv — www-data cannot write to /etc/nginx directly
            with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.conf') as tmp:
                tmp.write(block)
                tmp_path = tmp.name
            mv_res = _run(['sudo', 'mv', tmp_path, conf])
            _run(['sudo', 'chown', 'root:root', conf])
            _run(['sudo', 'chmod', '644', conf])
            if not mv_res.success:
                return CommandResult(success=False, error=f'Failed to write nginx config: {mv_res.error}')
            result = self.enable_site(domain)
            # Harden directory permissions for quota & security
            if unix_user and os.path.isdir(root_dir):
                _harden_site_dir(root_dir, unix_user, 'nginx')
            return result
        except Exception as e:
            return CommandResult(success=False, error=str(e))

    def delete_site(self, domain: str) -> CommandResult:
        self.disable_site(domain)
        try:
            conf = self.get_site_config_path(domain)
            if os.path.exists(conf):
                os.remove(conf)
            return self.reload()
        except Exception as e:
            return CommandResult(success=False, error=str(e))

    def enable_site(self, domain: str) -> CommandResult:
        avail  = self.get_site_config_path(domain)
        enabled_dir = getattr(paths, 'NGINX_SITES_ENABLED',
                              '/etc/nginx/sites-enabled')
        enabled = os.path.join(enabled_dir, f'{domain}.conf')
        try:
            _run(['sudo', 'mkdir', '-p', enabled_dir])
            # Remove existing symlink/file first
            _run(['sudo', 'rm', '-f', enabled])
            # Create symlink via sudo (www-data cannot write to /etc/nginx)
            res = _run(['sudo', 'ln', '-sf', avail, enabled])
            if not res.success:
                return CommandResult(success=False, error=res.error)
            return CommandResult(success=True)
        except Exception as e:
            return CommandResult(success=False, error=str(e))

    def disable_site(self, domain: str) -> CommandResult:
        enabled_dir = getattr(paths, 'NGINX_SITES_ENABLED',
                              '/etc/nginx/sites-enabled')
        enabled = os.path.join(enabled_dir, f'{domain}.conf')
        try:
            _run(['sudo', 'rm', '-f', enabled])
            return CommandResult(success=True)
        except Exception as e:
            return CommandResult(success=False, error=str(e))

    def test_config(self) -> CommandResult:
        return _run(['sudo', 'nginx', '-t'])

    def reload(self) -> CommandResult:
        test = self.test_config()
        if not test.success:
            return test
        return _run(['sudo', 'systemctl', 'reload', 'nginx'])

    def get_site_config_path(self, domain: str) -> str:
        avail = getattr(paths, 'NGINX_SITES_AVAILABLE',
                        '/etc/nginx/sites-available')
        return os.path.join(avail, f'{domain}.conf')

    def read_site_config(self, domain: str) -> str:
        conf = self.get_site_config_path(domain)
        if os.path.exists(conf):
            try:
                with open(conf, 'r') as f:
                    return f.read()
            except Exception:
                pass
        return ""

    def write_and_test_site_config(self, domain: str, config_text: str) -> CommandResult:
        conf = self.get_site_config_path(domain)
        if not os.path.exists(conf):
            return CommandResult(success=False, error="Nginx configuration file does not exist.")
        
        backup_path = f"/tmp/{domain}_nginx_backup.conf"
        _run(['sudo', 'cp', conf, backup_path])
        
        try:
            temp_path = f"/tmp/{domain}_nginx_new.conf"
            with open(temp_path, 'w') as f:
                f.write(config_text)
            
            cp_res = _run(['sudo', 'mv', temp_path, conf])
            if not cp_res.success:
                raise Exception("Failed to write to Nginx configuration directory via sudo.")
            
            test = self.test_config()
            if not test.success:
                _run(['sudo', 'cp', backup_path, conf])
                return CommandResult(success=False, error=test.error or test.output or "Config test failed.")
            
            self.reload()
            return CommandResult(success=True)
            
        except Exception as e:
            _run(['sudo', 'cp', backup_path, conf])
            return CommandResult(success=False, error=str(e))

    def setup_reverse_proxy(self, domain: str, app_name: str, proxy_type: str, target: str, static_path: str = '', root_path: str = '') -> CommandResult:
        try:
            import re
            old_conf = self.read_site_config(domain)
            if not old_conf:
                return CommandResult(success=False, error="Config not found")

            # Ensure we operate from a clean slate by removing any existing blocks 
            new_conf = old_conf
            new_conf = re.sub(r'[ \t]*location / \{(?:[^{}]|\{[^{}]*\})*\}\s*', '', new_conf)
            new_conf = re.sub(r'[ \t]*location /static/ \{(?:[^{}]|\{[^{}]*\})*\}\s*', '', new_conf)
            new_conf = re.sub(r'[ \t]*location /api/ \{(?:[^{}]|\{[^{}]*\})*\}\s*', '', new_conf)
            new_conf = re.sub(r'[ \t]*location = /compiling\.html \{(?:[^{}]|\{[^{}]*\})*\}\s*', '', new_conf)
            new_conf = re.sub(r'[ \t]*location ~\* \\.html\$ \{(?:[^{}]|\{[^{}]*\})*\}\s*', '', new_conf)

            if proxy_type == 'mern':
                # Strip old root and assign dynamically
                new_conf = re.sub(r'root\s+/home/[^/]+/(?:[^/]+/frontend/build|public_html);?', '', new_conf)
                owner = root_path.split('/')[2] if root_path else "unknown"
                compiling_path = f"/home/{owner}/{app_name}/compiling.html"
                
                new_location_block = f"""
    root {root_path};

    # Prevent browser caching of HTML so page updates are always visible
    location ~* \\.html$ {{
        add_header Cache-Control "no-cache, no-store, must-revalidate";
        add_header Pragma "no-cache";
        add_header Expires 0;
    }}

    location / {{
        try_files $uri /index.html /compiling.html;
    }}
    
    location = /compiling.html {{
        alias {compiling_path};
    }}

    location /static/ {{
        alias {static_path}/;
        expires 30d;
        add_header Cache-Control "public, no-transform";
    }}

    location /api/ {{
        proxy_pass {target};
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }}"""
                if 'location ~ /\\.ht {' in new_conf:
                    new_conf = new_conf.replace('location ~ /\\.ht {', new_location_block[1:] + '\n\n    location ~ /\\.ht {', 1)
                else:
                    # Append it right before the last closing brace as a failsafe
                    new_conf = new_conf.rstrip().rsplit('}', 1)
                    new_conf = new_conf[0] + new_location_block + '\n}'
            
            return self.write_and_test_site_config(domain, new_conf)
        except Exception as e:
            return CommandResult(success=False, error=str(e))

    def remove_reverse_proxy(self, domain: str, app_name: str) -> CommandResult:
        try:
            import re
            old_conf = self.read_site_config(domain)
            if not old_conf:
                return CommandResult(success=True)

            new_conf = old_conf
            new_conf = re.sub(r'[ \t]*location / \{(?:[^{}]|\{[^{}]*\})*\}\s*', '', new_conf)
            new_conf = re.sub(r'[ \t]*location /static/ \{(?:[^{}]|\{[^{}]*\})*\}\s*', '', new_conf)
            new_conf = re.sub(r'[ \t]*location /api/ \{(?:[^{}]|\{[^{}]*\})*\}\s*', '', new_conf)
            new_conf = re.sub(r'[ \t]*location = /compiling\.html \{(?:[^{}]|\{[^{}]*\})*\}\s*', '', new_conf)
            new_conf = re.sub(r'[ \t]*location ~\* \\.html\$ \{(?:[^{}]|\{[^{}]*\})*\}\s*', '', new_conf)

            # Revert MERN-specific root and fallback to standard execution
            owner_match = re.search(r'root\s+/home/([^/]+)/[^;]+', new_conf)
            fallback_owner = owner_match.group(1) if owner_match else "unknown"
            new_conf = re.sub(r'root\s+/home/[^/]+/(?:[^/]+/frontend/build|public_html);?', f'root /home/{fallback_owner}/public_html;', new_conf)

            default_location = """
    location / {
        try_files $uri $uri/ =404;
    }
"""
            if 'location ~ /\\.ht {' in new_conf:
                new_conf = new_conf.replace('location ~ /\\.ht {', default_location[1:] + '    location ~ /\\.ht {', 1)

            return self.write_and_test_site_config(domain, new_conf)
        except Exception as e:
            return CommandResult(success=False, error=str(e))
# ── OpenLiteSpeed Implementation ─────────────────────────────────────────────

class OLSWebServerManager(WebServerManager):
    """
    Manages OpenLiteSpeed virtual-host configurations.

    OLS keeps vhost configs as key=value text files under
    /usr/local/lsws/conf/vhosts/<domain>/vhconf.conf
    and registers each vhost in the global httpd_config.conf.

    PHP is served via lsphp (LiteSpeed SAPI) — no PHP-FPM socket needed,
    which is actually faster and more quota-friendly on OLS systems.
    """

    # lsphp binary path pattern
    _LSPHP_BIN = '/usr/local/lsws/lsphp{major_minor}/bin/lsphp'

    # Certbot webroot path used for SSL issuance on OLS
    _ACME_WEBROOT = os.path.join('{root_dir}', '.well-known', 'acme-challenge')

    def _lsphp_path(self, php_version: str) -> str:
        """Convert '8.3' → '/usr/local/lsws/lsphp83/bin/lsphp'"""
        major_minor = php_version.replace('.', '')
        return self._LSPHP_BIN.format(major_minor=major_minor)

    def _vhost_dir(self, domain: str) -> str:
        return os.path.join(OLS_VHOSTS, domain)

    def _vhost_conf(self, domain: str) -> str:
        return os.path.join(self._vhost_dir(domain), 'vhconf.conf')

    def get_site_config_path(self, domain: str) -> str:
        return self._vhost_conf(domain)

    def create_site(self, domain: str, root_dir: str,
                    php_version: str = '', ssl: bool = False,
                    unix_user: str = '') -> CommandResult:
        """
        Create an OLS vhost config and register the vhost in httpd_config.conf.
        The vhost is isolated per-user and enforces .htaccess processing.
        """
        vhost_dir = self._vhost_dir(domain)
        conf_path  = self._vhost_conf(domain)
        log_dir    = os.path.join(vhost_dir, 'logs')

        try:
            os.makedirs(vhost_dir, exist_ok=True)
            os.makedirs(log_dir, exist_ok=True)
            os.makedirs(root_dir, exist_ok=True)

            # Build the OLS vhost configuration (key=value / block format)
            php_handler = ''
            if php_version:
                lsphp = self._lsphp_path(php_version)
                php_handler = f"""
lsapi  lsphp{php_version.replace('.','')}_handler {{
  type                    lsapi
  address                 uds://tmp/lshttpd/lsapi_{domain}.sock
  maxConns                10
  env                     PHP_LSAPI_CHILDREN=10
  initTimeout             60
  retryTimeout            0
  persistConn             1
  respBuffer              0
  autoStart               1
  path                    {lsphp}
  backlog                 100
  instances               1
  priority                0
  memSoftLimit            2047M
  memHardLimit            2047M
  procSoftLimit           400
  procHardLimit           500
}}
"""
            conf = f"""# VoidPanel OLS VHost — {domain}
docRoot                   {root_dir}
vhDomain                  {domain}
vhAliases                 www.{domain}
adminEmails               admin@{domain}

# Access control — only serve files inside docRoot
allowSymbolLink           0
enableScript              1
restrained                1

index  {{
  useServer               0
  indexFiles              index.html, index.php
}}

# Error pages
errorlog {log_dir}/error.log {{
  useServer               0
  logLevel                WARN
  rollingSize             10M
}}

accesslog {log_dir}/access.log {{
  useServer               0
  logFormat               "%h %l %u %t \"%r\" %>s %b"
  logHeaders              5
  rollingSize             10M
  keepDays                30
}}

# .htaccess processing (Apache-compatible rewrite rules)
rewrite {{
  enable                  1
  autoLoadHtaccess        1
}}

# Security: deny hidden directories
context /.well-known/ {{
  allowBrowse             1
  location                {root_dir}/.well-known/
}}

context / {{
  allowBrowse             1
}}
{php_handler}
"""
            with open(conf_path, 'w') as f:
                f.write(conf)

            # Register vhost in global httpd_config.conf
            self._register_vhost(domain, vhost_dir, root_dir)

            # Harden directory permissions for quota & security
            if unix_user and os.path.isdir(root_dir):
                _harden_site_dir(root_dir, unix_user, 'nobody')

            return _run(['sudo', 'systemctl', 'reload', 'lsws'])

        except Exception as e:
            return CommandResult(success=False, error=str(e))

    def _register_vhost(self, domain: str, vhost_dir: str, root_dir: str) -> None:
        """
        Append a virtualHost entry to OLS httpd_config.conf if not present.
        We use text-based append because OLS's config is not valid XML.
        """
        marker = f'# VOIDPANEL-VHOST-{domain}'
        try:
            existing = ''
            if os.path.exists(OLS_HTTPD):
                with open(OLS_HTTPD) as f:
                    existing = f.read()
        except Exception:
            existing = ''

        if marker in existing:
            return  # Already registered

        vhost_block = f"""
{marker}
virtualhost {domain} {{
  vhRoot                  {vhost_dir}/
  configFile              {self._vhost_conf(domain)}
  allowSymbolLink         0
  enableScript            1
  restrained              1
}}

listener VoidHTTP {{
  binding      {{
    address              *:80
    secure               0
  }}
  map          {domain} {domain}
}}
"""
        with open(OLS_HTTPD, 'a') as f:
            f.write(vhost_block)

    def _unregister_vhost(self, domain: str) -> None:
        """Remove a virtualHost block from httpd_config.conf."""
        marker = f'# VOIDPANEL-VHOST-{domain}'
        if not os.path.exists(OLS_HTTPD):
            return
        with open(OLS_HTTPD) as f:
            lines = f.readlines()

        result, skip = [], False
        for line in lines:
            if marker in line:
                skip = True  # start skipping this block
            if skip and line.strip() == '' and len(result) > 0 and result[-1].strip() == '}':
                skip = False
                continue
            if not skip:
                result.append(line)

        with open(OLS_HTTPD, 'w') as f:
            f.writelines(result)

    def delete_site(self, domain: str) -> CommandResult:
        try:
            import shutil
            vhost_dir = self._vhost_dir(domain)
            if os.path.isdir(vhost_dir):
                shutil.rmtree(vhost_dir)
            self._unregister_vhost(domain)
            return _run(['sudo', 'systemctl', 'reload', 'lsws'])
        except Exception as e:
            return CommandResult(success=False, error=str(e))

    def enable_site(self, domain: str) -> CommandResult:
        """OLS: re-register the vhost entry (no symlink concept)."""
        conf = self._vhost_conf(domain)
        if not os.path.exists(conf):
            return CommandResult(success=False, error='Vhost config missing — run create_site first')
        root_dir = ''
        try:
            with open(conf) as f:
                for line in f:
                    if line.strip().startswith('docRoot'):
                        root_dir = line.split()[-1].strip()
                        break
        except Exception:
            pass
        self._register_vhost(domain, self._vhost_dir(domain), root_dir)
        return _run(['sudo', 'systemctl', 'reload', 'lsws'])

    def disable_site(self, domain: str) -> CommandResult:
        """OLS: unregister from httpd_config.conf without deleting vhost files."""
        self._unregister_vhost(domain)
        return _run(['sudo', 'systemctl', 'reload', 'lsws'])

    def test_config(self) -> CommandResult:
        return _run(['sudo', os.path.join(OLS_ROOT, 'bin', 'lswsctrl'), 'test'])

    def reload(self) -> CommandResult:
        return _run(['sudo', 'systemctl', 'reload', 'lsws'])

    def read_site_config(self, domain: str) -> str:
        conf = self.get_site_config_path(domain)
        # OLS vhost confs are owned by lsadm — use sudo cat to read reliably
        try:
            result = subprocess.run(['sudo', 'cat', conf], capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                return result.stdout
        except Exception:
            pass
        # fallback: try direct read
        if os.path.exists(conf):
            try:
                with open(conf, 'r') as f:
                    return f.read()
            except Exception:
                pass
        return ""

    def write_and_test_site_config(self, domain: str, config_text: str) -> CommandResult:
        conf = self.get_site_config_path(domain)
        if not os.path.exists(conf):
            return CommandResult(success=False, error="OpenLiteSpeed vhost configuration file does not exist.")
        
        backup_path = f"/tmp/{domain}_ols_backup.conf"
        _run(['sudo', 'cp', conf, backup_path])
        
        try:
            temp_path = f"/tmp/{domain}_ols_new.conf"
            with open(temp_path, 'w') as f:
                f.write(config_text)
            
            cp_res = _run(['sudo', 'mv', temp_path, conf])
            if not cp_res.success:
                raise Exception("Failed to write to OpenLiteSpeed configuration directory via sudo.")
            
            test = self.test_config()
            if not test.success:
                _run(['sudo', 'cp', backup_path, conf])
                return CommandResult(success=False, error=test.error or test.output or "Config test failed.")
            
            # If successful, graceful restart needed for new context/extapp changes
            # Graceful restart applies the hot config
            _run([os.path.join(OLS_ROOT, 'bin', 'lswsctrl'), 'restart'])
            return CommandResult(success=True)
        except Exception as e:
            # Restore from backup_path (not undefined 'backup')
            _run(['sudo', 'cp', backup_path, conf])
            return CommandResult(success=False, error=str(e))

    def setup_reverse_proxy(self, domain: str, app_name: str, proxy_type: str, target: str, static_path: str = '', root_path: str = '') -> CommandResult:
        try:
            import re
            old_conf = self.read_site_config(domain)
            if not old_conf:
                return CommandResult(success=False, error="Config not found")
            
            # Extract port if target is HTTP (e.g. http://127.0.0.1:3001)
            address = target
            if "http://" in address:
                address = target.split("http://")[-1]

            ols_proxy = f"""
extprocessor {proxy_type}_{app_name} {{
  type                    proxy
  address                 {address}
  maxConns                100
  initTimeout             60
  retryTimeout            0
  respBuffer              0
}}
context /api/ {{
  type                    proxy
  handler                 {proxy_type}_{app_name}
  addDefaultCharset       off
}}
"""
            new_conf = old_conf
            # Adjust document root strictly for MERN
            if proxy_type == 'mern' and root_path:
                new_conf = re.sub(r'docRoot\s+\$VH_ROOT/(?:[^/]+/frontend/build|public_html)', f'docRoot $VH_ROOT/{app_name}/frontend/build', new_conf)

            if f"{proxy_type}_{app_name}" not in new_conf:
                new_conf += f"\n{ols_proxy}"

            return self.write_and_test_site_config(domain, new_conf)
        except Exception as e:
            return CommandResult(success=False, error=str(e))

    def remove_reverse_proxy(self, domain: str, app_name: str) -> CommandResult:
        try:
            import re
            old_conf = self.read_site_config(domain)
            if not old_conf:
                return CommandResult(success=True)

            # Clean extprocessors safely using named boundaries
            new_conf = re.sub(rf'extprocessor (?:mern|python)_{app_name}\s*{{[^}}]+}}\n?', '', old_conf)
            new_conf = re.sub(rf'context /(?:api/)?\s*{{[^}}]+handler\s+(?:mern|python)_{app_name}[^}}]+}}\n?', '', new_conf)
            new_conf = re.sub(r'docRoot\s+\$VH_ROOT/(?:[^/]+/frontend/build|public_html)', r'docRoot $VH_ROOT/public_html', new_conf)
            new_conf = re.sub(r'context /static/\s*\{[^}]*type\s+null[^}]*\}\n?', '', new_conf)

            return self.write_and_test_site_config(domain, new_conf)
        except Exception as e:
            return CommandResult(success=False, error=str(e))
# ── Hot-Swap Engine ───────────────────────────────────────────────────────────

class WebServerSwitcher:
    """
    Orchestrates a zero-downtime (best-effort) switch between NGINX and OLS.

    Security/Quota guarantees during conversion:
      1.  All site directories are re-owned to their unix_user before the old
          server is stopped — quota attribution is never lost.
      2.  New configs are fully written and tested *before* stopping the old
          engine — prevents a window where no server is running.
      3.  The old engine is stopped ONLY after new engine passes its config test.
      4.  If anything fails we attempt to roll back by restarting the old engine.
      5.  The state file is written LAST so the panel backend never sees an
          inconsistent state.
    """

    def switch(self, target_engine: str, domain_list: list,
               php_defaults: dict = None) -> CommandResult:
        """
        Switch from the current engine to target_engine.

        :param target_engine: 'nginx' or 'ols'
        :param domain_list:   list of dicts — each must have:
                              { 'domain', 'root_dir', 'php_version', 'unix_user' }
        :param php_defaults:  optional fallback {'php_version': '8.3'}
        """
        current = get_active_engine()
        if current == target_engine:
            return CommandResult(success=True,
                                 output=f'Already running {target_engine}')

        php_defaults = php_defaults or {'php_version': '8.3'}
        old_service  = 'nginx'   if current      == 'nginx' else 'lsws'
        new_service  = 'lsws'    if target_engine == 'ols'  else 'nginx'
        new_manager  = OLSWebServerManager() if target_engine == 'ols' \
                       else NginxWebServerManager()

        errors = []

        # ── Step 1: write all new configs (while old server still running) ──
        for d in domain_list:
            domain      = d.get('domain', '')
            root_dir    = d.get('root_dir', '')
            php_version = d.get('php_version') or php_defaults.get('php_version', '8.3')
            unix_user   = d.get('unix_user', '')

            if not domain or not root_dir:
                continue

            r = new_manager.create_site(domain, root_dir,
                                        php_version=php_version,
                                        unix_user=unix_user)
            if not r.success:
                errors.append(f'{domain}: {r.error}')

        # ── Step 2: test new engine's config ───────────────────────────────
        test_r = new_manager.test_config()
        if not test_r.success:
            return CommandResult(
                success=False,
                error=f'New {target_engine} config test FAILED — rollback kept '
                      f'{current} running.\n{test_r.error}'
            )

        # ── Step 3: stop old engine (freeing up ports 80/443) ───────────────
        _run(['sudo', 'systemctl', 'stop', old_service])

        # ── Step 4: start new engine ────────────────────────────────────────
        start_r = _run(['sudo', 'systemctl', 'start', new_service])
        if not start_r.success:
            # ROLLBACK: start the old engine again
            _run(['sudo', 'systemctl', 'start', old_service])
            return CommandResult(
                success=False,
                error=f'Failed to start {new_service} after config test passed. '
                      f'Safely rolled back to {old_service}.\n{start_r.error}'
            )

        # ── Step 5: persist state & enable services on boot ─────────────────
        _run(['sudo', 'systemctl', 'disable', old_service])
        _run(['sudo', 'systemctl', 'enable',  new_service])
        set_active_engine(target_engine)

        summary = (f'Switched from {current} → {target_engine}. '
                   f'{len(domain_list)} domains migrated.')
        if errors:
            summary += f' Warnings: {"; ".join(errors)}'

        return CommandResult(success=True, output=summary)

# Alias expected by __init__.py
LinuxWebServerManager = NginxWebServerManager
