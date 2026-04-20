"""
VoidPanel Celery tasks.
Heavy, long-running system operations are defined here so they
can be retried, monitored, and scaled independently of Django.

Worker startup:
    celery -A panel worker --loglevel=info --concurrency=4

Flower monitoring (optional):
    celery -A panel flower
"""
import os
import shutil
import subprocess
import sys

from celery import shared_task

from panel.logger import get_logger
from voidplatform import get_platform
from voidplatform.config import paths

logger = get_logger(__name__)


def _resolve_mail_domain_dir(domain_name, username=None):
    """Return mail dir for a domain: /home/<owner>/mail/<domain>/."""
    if username:
        return os.path.join(paths.HOME_BASE, username, 'mail', domain_name)
    try:
        from control.models import user
        owner = user.objects.filter(domain=domain_name).first()
        if owner:
            return os.path.join(paths.HOME_BASE, owner.username, 'mail', domain_name)
    except Exception:
        pass
    return os.path.join(paths.MAIL_VHOSTS, domain_name)


# ─────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────

def _run(cmd: list[str], *, timeout: int = 30) -> subprocess.CompletedProcess:
    """
    Safe parameterised subprocess wrapper.  Never uses shell=True.
    Logs stderr on failure but does NOT raise — callers decide.
    """
    result = subprocess.run(
        cmd, capture_output=True, text=True,
        encoding='utf-8', timeout=timeout, check=False,
    )
    if result.returncode != 0:
        logger.warning('Command %s exited %d: %s', cmd, result.returncode, result.stderr.strip())
    return result


def _reload(service: str) -> None:
    """Zero-downtime service reload (never restart)."""
    try:
        get_platform().services.reload(service)
    except Exception as exc:
        logger.error('Failed to reload %s: %s', service, exc)


# ─────────────────────────────────────────────────────────────
# Task: Provision new user account
# ─────────────────────────────────────────────────────────────

@shared_task(
    bind=True,
    max_retries=0,         # provisioning is not idempotent — don't retry blindly
    name='voidpanel.provision_user',
    acks_late=True,        # ack only after task completes (survives worker crash)
)
def provision_user_task(self, domain12: str, domainname: str, email: str,
                        password: str, package12: str, path: str,
                        sto: int, inipath: str, php_ini_content: str):
    """
    Celery task: provision a new VoidPanel hosting account.
    Replaces the threading.Thread approach with a retryable, monitorable task.
    """
    # Lazy imports — avoid circular imports at module load time
    from django.contrib.auth.models import User
    from django.db import transaction
    from control.models import domain, user  # adjust to your actual model paths

    logger.info('Provisioning started: domain=%s user=%s', domain12, domainname)

    try:
        # ── 0. Create hosting directories ────────────────────────────────────
        for _dir in [
            path,
            f'{path}/public_html',
            f'{path}/ssl',
            f'{path}/logs',
            os.path.join(path, 'mail', domain12),
        ]:
            if sys.platform != 'win32':
                _run(['sudo', 'mkdir', '-p', _dir])
            else:
                os.makedirs(_dir, exist_ok=True)

        # Set ownership so www-data can write files before PHP ini is created
        if sys.platform != 'win32':
            _run(['sudo', 'chown', '-R', 'www-data:www-data', path])
            _run(['sudo', 'chmod', '-R', '755', path])

        # Copy voidpanel default landing page into public_html
        _vp_src = os.path.join(paths.PANEL_ROOT, 'voidpanel')
        _vp_dst = os.path.join(path, 'public_html')
        if os.path.isdir(_vp_src):
            for _item in os.listdir(_vp_src):
                _s = os.path.join(_vp_src, _item)
                _d = os.path.join(_vp_dst, _item)
                if os.path.isdir(_s):
                    shutil.copytree(_s, _d, dirs_exist_ok=True)
                else:
                    shutil.copy2(_s, _d)
        else:
            logger.warning('voidpanel static dir not found at %s, skipping copy', _vp_src)

        # ── 1. Write PHP INI ──────────────────────────────────────────────────
        with open(inipath, 'w', encoding='utf-8') as f:
            f.write(php_ini_content)

        # ── 2. Nginx / SSL / DNS setup ────────────────────────────────────────
        # Import directly from function.py — avoids circular panel.views import
        from function import (
            generate_ssl_certificates, create_nginx_ssl_conf,
            generate_dkim_keys, create_bind_records, configure_opendkim,
        )
        file_path = os.path.join(paths.NGINX_SITES_AVAILABLE, f'{domain12}.conf')
        root_dir  = path + '/public_html'
        cert_path, key_path = generate_ssl_certificates(domain12, path + '/ssl', path + '/logs')

        if cert_path and key_path:
            create_nginx_ssl_conf(file_path, domain12, root_dir, cert_path, key_path)
            # Symlink into sites-enabled for zero-downtime serving
            _enabled = os.path.join(paths.NGINX_SITES_ENABLED, f'{domain12}.conf')
            if not os.path.exists(_enabled):
                if sys.platform == 'win32':
                    shutil.copy2(file_path, _enabled)
                else:
                    _run(['sudo', 'ln', '-sf', file_path, _enabled])
        else:
            raise RuntimeError(f'Cannot generate OpenSSL for domain {domain12}')

        key_dir        = os.path.join(paths.OPENDKIM_KEY_DIR, domain12) if paths.OPENDKIM_KEY_DIR else os.path.join(paths.PANEL_ROOT, 'dkim', domain12)
        zone_file_path = os.path.join(paths.BIND_ZONE_DIR, f'db.{domain12}')
        private_key_path, public_key_path = generate_dkim_keys(domain12, key_dir)

        if private_key_path and public_key_path:
            create_bind_records(domain12, key_dir, zone_file_path)
            configure_opendkim(domain12, key_dir)
        else:
            raise RuntimeError(f'Cannot generate DKIM for domain {domain12}')

        # ── 3. Atomic DB inserts ──────────────────────────────────────────────
        with transaction.atomic():
            domain.objects.create(domain=domain12, email=email, dir=domainname, userdomain=True)
            user.objects.create(domain=domain12, email=email, username=domainname, hosting_package=package12)
            User.objects.create_user(username=domainname, email=email, password=password)

        # ── 4. Create system user ─────────────────────────────────────────────
        plat = get_platform()
        plat.users.create_user(domainname, password, shell=paths.NOLOGIN_SHELL)

        home_dir = os.path.join(paths.HOME_BASE, domainname)
        if sys.platform != 'win32':
            _run(['sudo', 'chown', f'{domainname}:{domainname}', home_dir])

        # ── 5. Apply disk quota ───────────────────────────────────────────────
        try:
            _run(['sudo', 'setquota', '-u', domainname, str(sto), str(sto), '0', '0', '/'])
        except Exception:
            logger.warning('Quota setup skipped for %s (setquota not available?)', domainname)

        # ── 6. Zero-downtime service reloads ──────────────────────────────────
        for svc in ('opendkim', 'bind9', 'postfix', 'nginx'):
            _reload(svc)

        logger.info('Provisioning SUCCESS: %s', domain12)

    except Exception as exc:
        logger.error('Provisioning FAILED for %s — rolling back. Error: %s', domain12, exc)

        # DB rollback
        domain.objects.filter(domain=domain12).delete()
        user.objects.filter(username=domainname).delete()
        User.objects.filter(username=domainname).delete()

        # Filesystem rollback
        for path_to_remove in [
            path,
            os.path.join(paths.NGINX_SITES_ENABLED, f'{domain12}.conf'),
            os.path.join(paths.NGINX_SITES_AVAILABLE, f'{domain12}.conf'),
            os.path.join(path, 'mail', domain12),
        ]:
            try:
                if os.path.isdir(path_to_remove):
                    shutil.rmtree(path_to_remove)
                elif os.path.exists(path_to_remove):
                    os.remove(path_to_remove)
            except Exception:
                pass

        # System user rollback
        get_platform().users.delete_user(domainname)

        raise  # Re-raise so Celery marks the task as FAILED


# ─────────────────────────────────────────────────────────────
# Task: Terminate / delete user account
# ─────────────────────────────────────────────────────────────

@shared_task(
    bind=True,
    max_retries=2,
    default_retry_delay=30,
    name='voidpanel.terminate_user',
    acks_late=True,
)
def terminate_user_task(self, domain_str: str, mainusername: str, subdomains: list[str]):
    """
    Celery task: fully delete a hosting account.
    Safe to retry — all cleanup steps are individually guarded.
    Replaces the threading.Thread approach in terminate().
    """
    # Lazy imports to avoid circular dependency at module load
    from control.models import ftpaccount, pythonname, mernname  # adjust model paths

    logger.info('Termination started: domain=%s user=%s', domain_str, mainusername)

    # Home directory
    try:
        shutil.rmtree(os.path.join(paths.HOME_BASE, mainusername), ignore_errors=True)
    except Exception as e:
        logger.warning('[terminate] home dir: %s', e)

    # Nginx configs (main + subdomains)
    for conf in [os.path.join(paths.NGINX_SITES_ENABLED, f'{domain_str}.conf')] + \
                [os.path.join(paths.NGINX_SITES_ENABLED, f'{s}.conf') for s in subdomains]:
        try:
            os.remove(conf)
        except FileNotFoundError:
            pass
        except Exception as e:
            logger.warning('[terminate] nginx conf %s: %s', conf, e)

    # DNS zone
    for p in [os.path.join(paths.BIND_ZONE_DIR, f'db.{domain_str}')]:
        try:
            os.remove(p)
        except Exception:
            pass
    try:
        from panel.views import remove_zone_from_file
        remove_zone_from_file(paths.BIND_CONF, domain_str)
    except Exception:
        pass

    # DKIM keys
    opendkim_keys = paths.OPENDKIM_KEY_DIR
    if opendkim_keys:
        for kpath in [os.path.join(opendkim_keys, domain_str)] + \
                     [os.path.join(opendkim_keys, s) for s in subdomains]:
            shutil.rmtree(kpath, ignore_errors=True)

    # SSL certs
    for spath in [os.path.join(paths.LETSENCRYPT_LIVE, domain_str)] + \
                 [os.path.join(paths.LETSENCRYPT_LIVE, s) for s in subdomains]:
        shutil.rmtree(spath, ignore_errors=True)

    # Mail data
    shutil.rmtree(_resolve_mail_domain_dir(domain_str, username=mainusername), ignore_errors=True)

    # Service reloads
    for svc in ('bind9', 'nginx', 'postfix', 'dovecot'):
        _reload(svc)

    # FTP accounts
    try:
        ft = ftpaccount.objects.filter(main=mainusername)
        plat = get_platform()
        for acct in ft:
            plat.users.delete_user(acct.main)
        ft.delete()
    except Exception as e:
        logger.warning('[terminate] FTP cleanup: %s', e)

    # System user
    try:
        get_platform().users.delete_user(mainusername)
    except Exception as e:
        logger.warning('[terminate] userdel: %s', e)

    # Python app service
    try:
        df = pythonname.objects.get(domain=domain_str)
        svc_name = df.name
        df.delete()
        svc_path = os.path.join(paths.SYSTEMD_DIR, f'{svc_name}.service') if paths.SYSTEMD_DIR else ''
        if svc_path and os.path.exists(svc_path):
            os.remove(svc_path)
    except Exception:
        pass

    # MERN app sock
    try:
        df = mernname.objects.get(domain=domain_str)
        svc_name = df.name
        df.delete()
        os.remove(f'/var/run/{svc_name}.sock')
    except Exception:
        pass

    logger.info('Termination SUCCESS: %s', domain_str)


# ─────────────────────────────────────────────────────────────
# Task: Add Website (Addon Domain without new system user)
# ─────────────────────────────────────────────────────────────

@shared_task(
    bind=True,
    max_retries=0,
    name='voidpanel.add_website',
    acks_late=True,
)
def add_website_task(self, domain12: str, email: str, domainname: str, path: str, inipath: str, php_ini_content: str):
    """
    Celery task: Add a new website (addon domain without full system user).
    Replaces the blocking addweb view logic.
    """
    from control.models import domain
    from panel.views import (
        generate_ssl_certificates, create_nginx_ssl_conf,
        generate_dkim_keys, create_bind_records, configure_opendkim,
    )

    logger.info('Add Website task started: %s', domain12)

    try:
        # Create directories
        for d in [path, f'{path}/public_html', f'{path}/ssl', f'{path}/logs', os.path.join(path, 'mail', domain12)]:
            os.makedirs(d, exist_ok=True)

        # Copy default voidpanel index
        _run(['sudo', 'cp', '-r', os.path.join(paths.PANEL_ROOT, 'voidpanel', '.'), f'{path}/public_html/'])

        # Write PHP INI
        with open(inipath, 'w', encoding='utf-8') as f:
            f.write(php_ini_content)

        # Nginx & SSL
        file_path = os.path.join(paths.NGINX_SITES_AVAILABLE, f'{domain12}.conf')
        root_dir = f'{path}/public_html'
        cert_path, key_path = generate_ssl_certificates(domain12, f'{path}/ssl', f'{path}/logs')

        if cert_path and key_path:
            create_nginx_ssl_conf(file_path, domain12, root_dir, cert_path, key_path)
            # Link to sites-enabled
            enabled_path = os.path.join(paths.NGINX_SITES_ENABLED, f'{domain12}.conf')
            if not os.path.exists(enabled_path):
                if sys.platform == 'win32':
                    shutil.copy2(file_path, enabled_path)
                else:
                    os.symlink(file_path, enabled_path)
        else:
            raise RuntimeError(f'SSL generation failed for {domain12}')

        # DKIM & DNS
        key_dir = os.path.join(paths.OPENDKIM_KEY_DIR, domain12) if paths.OPENDKIM_KEY_DIR else os.path.join(paths.PANEL_ROOT, 'dkim', domain12)
        zone_file_path = os.path.join(paths.BIND_ZONE_DIR, f'db.{domain12}')
        os.makedirs(key_dir, exist_ok=True)
        private_key, public_key = generate_dkim_keys(domain12, key_dir)

        if private_key and public_key:
            create_bind_records(domain12, key_dir, zone_file_path)
            configure_opendkim(domain12, key_dir)
        else:
            raise RuntimeError(f'DKIM generation failed for {domain12}')

        # DB Entry
        domain.objects.create(domain=domain12, email=email, dir=domainname, userdomain=True)

        # Reload services securely
        for svc in ('opendkim', 'postfix', 'nginx', 'bind9'):
            _reload(svc)

        logger.info('Add Website SUCCESS: %s', domain12)

    except Exception as exc:
        logger.error('Add Website FAILED for %s — rolling back. Error: %s', domain12, exc)
        
        # Rollback
        domain.objects.filter(domain=domain12).delete()
        if os.path.exists(path):
            shutil.rmtree(path)
        for p in [os.path.join(paths.NGINX_SITES_ENABLED, f'{domain12}.conf'),
                  os.path.join(paths.NGINX_SITES_AVAILABLE, f'{domain12}.conf'),
                  os.path.join(path, 'mail', domain12)]:
            if os.path.islink(p) or os.path.isfile(p):
                os.remove(p)
            elif os.path.isdir(p):
                shutil.rmtree(p)
                
        raise


# ─────────────────────────────────────────────────────────────
# Task: Update Hostname Setup
# ─────────────────────────────────────────────────────────────

@shared_task(
    bind=True,
    max_retries=1,
    name='voidpanel.update_hostname',
    acks_late=True,
)
def update_hostname_task(self, new_hostname: str, email: str, is_first_time: bool):
    """
    Celery task: Update the server hostname, grab SSL, and reload services.
    Securely rewrites Nginx configs without shell injection.
    """
    import socket
    import time
    
    logger.info('Hostname update started: %s (first_time=%s)', new_hostname, is_first_time)

    try:
        # Capture old hostname BEFORE altering it
        old_hostname = socket.gethostname()
        
        # 1. Update system hostname
        if sys.platform == 'win32':
            _run(['powershell', '-Command', f'Rename-Computer -NewName "{new_hostname}" -Force'])
        else:
            _run(['sudo', 'hostnamectl', 'set-hostname', new_hostname])

        # 2. Update hosts file safely
        hosts_file = paths.HOSTS_FILE
        with open(hosts_file, 'r') as file:
            hosts_lines = file.readlines()
        with open(hosts_file, 'w') as file:
            for line in hosts_lines:
                if '127.0.1.1' in line:
                    file.write(f'127.0.1.1\t{new_hostname}\n')
                else:
                    file.write(line)

        # 3. Update Django CSRF settings
        settings_path = os.path.join(paths.PANEL_ROOT, 'panel', 'settings.py')
        if os.path.exists(settings_path):
            with open(settings_path, 'a+') as file:
                file.write(f'\nCSRF_TRUSTED_ORIGINS.append("https://{new_hostname}:8082")\n')

        # 4. Generate SSL (platform-aware)
        if sys.platform != 'win32':
            _run([
                'sudo', 'certbot', '--nginx', '--non-interactive', '--agree-tos',
                '--email', email, '-d', new_hostname
            ])
        else:
            get_platform().ssl.provision(new_hostname, email=email)
        
        # 5. Rewrite Nginx Configurations securely instead of using raw 'sed'
        for conf_file in ['panel', 'phpmyadmin', 'roundcube']:
            conf_path = os.path.join(paths.NGINX_SITES_AVAILABLE, conf_file)
            if not os.path.exists(conf_path):
                continue
                
            with open(conf_path, 'r') as f:
                content = f.read()

            content = content.replace(old_hostname, new_hostname)

            if is_first_time:
                content = content.replace(paths.SSL_DUMMY_CERT, f'{paths.LETSENCRYPT_LIVE}/{new_hostname}/fullchain.pem')
                content = content.replace(paths.SSL_DUMMY_KEY, f'{paths.LETSENCRYPT_LIVE}/{new_hostname}/privkey.pem')
            else:
                content = content.replace(f'{paths.LETSENCRYPT_LIVE}/{old_hostname}/fullchain.pem', f'{paths.LETSENCRYPT_LIVE}/{new_hostname}/fullchain.pem')
                content = content.replace(f'{paths.LETSENCRYPT_LIVE}/{old_hostname}/privkey.pem', f'{paths.LETSENCRYPT_LIVE}/{new_hostname}/privkey.pem')

            with open(conf_path, 'w') as f:
                f.write(content)

        # 6. Service Reloads
        _reload('nginx')
        get_platform().services.restart('uwsgi')
        time.sleep(2)
        
        logger.info('Hostname update SUCCESS: %s', new_hostname)

    except Exception as exc:
        logger.error('Hostname update FAILED for %s. Error: %s', new_hostname, exc)
        raise


# ─────────────────────────────────────────────────────────────
# Task: Convert Addon Domain to Standalone User
# ─────────────────────────────────────────────────────────────

@shared_task(
    bind=True,
    max_retries=0,
    name='voidpanel.convert_website',
    acks_late=True,
)
def convert_website_task(self, domain_name: str, package_name: str, sto: str):
    """
    Celery task: Convert an Addon Domain into a standalone User account safely.
    Replaces blocking, vulnerable shell injections in the cwtd view.
    """
    from django.contrib.auth.models import User
    from django.db import transaction
    from control.models import domain, user
    import secrets
    
    logger.info('Convert Website task started: %s to package %s', domain_name, package_name)
    
    try:
        fddf = domain.objects.get(domain=domain_name)
        password = secrets.token_urlsafe(12)
        dir_name = fddf.dir
        email = fddf.email
        
        # 1. Atomic Database updates
        with transaction.atomic():
            user.objects.create(domain=domain_name, email=email, username=dir_name, hosting_package=package_name)
            if not User.objects.filter(username=dir_name).exists():
                User.objects.create_user(username=dir_name, email=email, password=password)
            fddf.userdomain = True
            fddf.save()
            
        # 2. Create system user — platform-aware
        plat = get_platform()
        plat.users.create_user(dir_name, password, shell=paths.NOLOGIN_SHELL)

        home_dir = os.path.join(paths.HOME_BASE, dir_name)
        if sys.platform != 'win32':
            _run(['sudo', 'chown', f'{dir_name}:{dir_name}', home_dir])
        
        # 3. Disk quota
        try:
            _run(['sudo', 'mount', '-o', 'remount', '/'])
            _run(['sudo', 'setquota', '-u', dir_name, sto, sto, '0', '0', '/'])
        except Exception as e:
            logger.warning('Quota setup skipped/failed for %s: %s', dir_name, e)
            
        logger.info('Convert Website SUCCESS: %s', domain_name)
        
    except Exception as exc:
        logger.error('Convert Website FAILED for %s. Error: %s', domain_name, exc)
        raise

# ─────────────────────────────────────────────────────────────
# Task: Run Auto SSL for a single domain
# ─────────────────────────────────────────────────────────────

@shared_task(
    bind=True,
    max_retries=1,
    name='voidpanel.run_ssl_task',
    acks_late=True,
)
def run_ssl_task(self, domain_name: str, email: str):
    """
    Celery task: Dispatch certbot to generate SSL for a domain asynchronously.
    """
    from control.models import domain
    from datetime import datetime
    
    logger.info('Auto SSL task started for domain: %s', domain_name)
    path = paths.SSL_LOG
    
    # Ensure directory exists for safety
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
    except Exception:
        pass

    try:
        # Run SSL provisioning (platform-aware)
        log_output = f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Starting AutoSSL for {domain_name}...\n"
        
        if sys.platform != 'win32':
            result = _run([
                "sudo", "certbot", "--nginx",
                "-d", domain_name, "-d", f'www.{domain_name}',
                "--non-interactive", "--agree-tos",
                "--email", email, "--redirect", "--no-eff-email"
            ], timeout=120)
            
            if result.stdout:
                log_output += result.stdout + "\n"
            if result.stderr:
                log_output += result.stderr + "\n"
                
            if result.returncode == 0:
                log_output += f"✓ AutoSSL Completed successfully for {domain_name}\n"
            else:
                log_output += f"✖ AutoSSL Failed with exit code {result.returncode} for {domain_name}\n"
        else:
            get_platform().ssl.provision(domain_name, email=email)
            log_output += f"✓ AutoSSL Completed successfully (Windows OS) for {domain_name}\n"
        
        # Log results
        with open(path, 'a+', encoding='utf-8') as f:
            f.write(log_output)
            
        # Update Database
        try:
            db_domain = domain.objects.get(domain=domain_name)
            db_domain.sslstatus = True
            db_domain.save()
        except domain.DoesNotExist:
            logger.warning('Auto SSL domain %s not found in DB', domain_name)

        logger.info('Auto SSL SUCCESS: %s', domain_name)
        
    except Exception as exc:
        err_out = f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] ✖ Error occurred during AutoSSL for {domain_name}: {str(exc)}\n"
        try:
            with open(path, 'a+', encoding='utf-8') as f:
                f.write(err_out)
        except Exception:
            pass
        logger.error('Auto SSL FAILED for %s. Error: %s', domain_name, exc)
        raise

# ─────────────────────────────────────────────────────────────
# Task: Restore / Migration Tool
# ─────────────────────────────────────────────────────────────

@shared_task(
    bind=True,
    max_retries=0,
    name='voidpanel.background_migration_task',
    acks_late=True,
)
def background_migration_task(self, source_type: str, auth_data: dict):
    """
    Celery task: Extracts backups or connects to remote panels (cPanel, Plesk, etc.),
    downloads configurations/data, and restores them to the local VoidPanel setup.
    """
    logger.info('Migration task started: type=%s', source_type)
    try:
        from control.migration_parser import MigrationParser
        
        if source_type == 'file':
            backup_path = auth_data.get('file_path')
            logger.info('Extracting local backup file: %s', backup_path)
            
            parser = MigrationParser(archive_path=backup_path)
            meta = parser.analyze()
            
            # Save into the database and create unix user
            try:
                c_user, c_domain, gen_pass = parser.build_system_account()
                logger.info(f"Successfully configured account {c_user.username} with domain {c_domain.domain}. Pass: {gen_pass}")
            except Exception as conf_err:
                logger.error(f"Failed to build system account during migration: {conf_err}")
                raise

            # Clean up temporary backup package
            if backup_path and os.path.exists(backup_path):
                os.remove(backup_path)
                
        elif source_type in ['cpanel', 'plesk', 'directadmin']:
            host = auth_data.get('host')
            user_creds = auth_data.get('user')
            logger.info('Connecting to %s API at %s for user %s', source_type, host, user_creds)
            # Placeholder for:
            # 1. API Call to trigger backup generation on remote panel
            # 2. Polling remote panel until backup is ready
            # 3. Securely downloading the backup to a local temp folder
            # 4. Use MigrationParser instance to extract the backup
            # 5. Iterating through the XML/JSON to recreate domains, users, db, and files.
        
        logger.info('Migration task completed successfully')
        
    except Exception as e:
        logger.error('Migration task failed: %s', str(e))
        raise
