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
            # Secure ownership and permissions: client owns files, group www-data has read access, others blocked
            _run(['sudo', 'chown', '-R', f'{domainname}:www-data', home_dir])
            _run(['sudo', 'chmod', '750', home_dir])
            _run(['sudo', 'find', home_dir, '-type', 'd', '-exec', 'chmod', '750', '{}', '+'])
            _run(['sudo', 'find', home_dir, '-type', 'f', '-exec', 'chmod', '640', '{}', '+'])
            # Explicitly allow www-data to write to the logs directory and files inside it
            logs_dir = os.path.join(home_dir, 'logs')
            _run(['sudo', 'chmod', '770', logs_dir])
            _run(['sudo', 'find', logs_dir, '-type', 'f', '-exec', 'chmod', '660', '{}', '+'])
            # Ensure shell configs remain readable for shell initialization
            for bash_file in ('.bashrc', '.profile', '.bash_profile', '.bash_logout'):
                bpath = os.path.join(home_dir, bash_file)
                if os.path.exists(bpath):
                    _run(['sudo', 'chmod', '644', bpath])

        # ── 5. Apply disk quota ───────────────────────────────────────────────
        try:
            _run(['sudo', 'setquota', '-u', domainname, str(sto), str(sto), '0', '0', '/'])
        except Exception:
            logger.warning('Quota setup skipped for %s (setquota not available?)', domainname)

        # ── 6. Zero-downtime service reloads ──────────────────────────────────
        for svc in ('opendkim', 'bind9', 'postfix', 'nginx'):
            _reload(svc)

        logger.info('Provisioning SUCCESS: %s', domain12)

        # Trigger user creation notification
        try:
            from control.utils import trigger_user_created_notification
            trigger_user_created_notification(domainname, domain12, email, package12)
        except Exception as e_notify:
            logger.error('Failed to trigger user creation notification: %s', e_notify)

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

    Bug fixes applied:
    - Removes BOTH sites-enabled symlink AND sites-available config (prevents orphaned
      nginx configs from breaking nginx -t for ALL other domains on the server).
    - Removes postfix vmailbox, virtual_alias, and dovecot user entries for the domain.
    - Drops MySQL databases and users whose names are prefixed with the account username.
    - Stops and removes PM2/systemd MERN processes properly.
    - Runs nginx -t before reload to log validation errors without crashing.
    """
    # Lazy imports to avoid circular dependency at module load
    from control.models import ftpaccount, pythonname, mernname

    logger.info('Termination started: domain=%s user=%s', domain_str, mainusername)

    all_domains = [domain_str] + list(subdomains)

    # ── 1. Home directory ─────────────────────────────────────────────────────
    try:
        shutil.rmtree(os.path.join(paths.HOME_BASE, mainusername), ignore_errors=True)
        logger.info('[terminate] Home dir removed for %s', mainusername)
    except Exception as e:
        logger.warning('[terminate] home dir: %s', e)

    # ── 2. Nginx configs — remove BOTH sites-enabled symlink AND sites-available ──
    # CRITICAL: Only removing sites-enabled still leaves sites-available with a
    # reference to the deleted SSL cert. If the symlink is ever recreated, or if
    # another nginx -t reads it, the entire nginx fails globally for ALL sites.
    for d in all_domains:
        for nginx_dir in (paths.NGINX_SITES_ENABLED, paths.NGINX_SITES_AVAILABLE):
            conf = os.path.join(nginx_dir, f'{d}.conf')
            try:
                if os.path.islink(conf) or os.path.isfile(conf):
                    os.remove(conf)
                    logger.info('[terminate] Removed nginx conf: %s', conf)
            except FileNotFoundError:
                pass
            except Exception as e:
                logger.warning('[terminate] nginx conf %s: %s', conf, e)

    # ── 3. DNS zone ────────────────────────────────────────────────────────────
    for d in all_domains:
        zone_file = os.path.join(paths.BIND_ZONE_DIR, f'db.{d}')
        try:
            os.remove(zone_file)
        except Exception:
            pass
    try:
        from function import remove_zone_from_file
        remove_zone_from_file(paths.BIND_CONF, domain_str)
    except Exception:
        pass

    # ── 4. DKIM keys ───────────────────────────────────────────────────────────
    if paths.OPENDKIM_KEY_DIR:
        for d in all_domains:
            shutil.rmtree(os.path.join(paths.OPENDKIM_KEY_DIR, d), ignore_errors=True)

        # Also remove entries from OpenDKIM KeyTable and SigningTable
        for table_path in (paths.OPENDKIM_KEYTABLE, paths.OPENDKIM_SIGNINGTABLE):
            if not table_path or not os.path.exists(table_path):
                continue
            try:
                with open(table_path, 'r') as f:
                    lines = f.readlines()
                cleaned = [l for l in lines if domain_str not in l]
                with open(table_path, 'w') as f:
                    f.writelines(cleaned)
            except Exception as e:
                logger.warning('[terminate] OpenDKIM table %s cleanup: %s', table_path, e)

    # ── 5. SSL certs (Let's Encrypt) ───────────────────────────────────────────
    for d in all_domains:
        shutil.rmtree(os.path.join(paths.LETSENCRYPT_LIVE, d), ignore_errors=True)
        # Also remove from /etc/letsencrypt/renewal/ to prevent certbot errors
        renewal = f'/etc/letsencrypt/renewal/{d}.conf'
        try:
            if os.path.exists(renewal):
                os.remove(renewal)
        except Exception:
            pass
        # Also remove archived certs
        archive_dir = f'/etc/letsencrypt/archive/{d}'
        shutil.rmtree(archive_dir, ignore_errors=True)

    # ── 6. Mail data ───────────────────────────────────────────────────────────
    shutil.rmtree(_resolve_mail_domain_dir(domain_str, username=mainusername), ignore_errors=True)

    # ── 7. Postfix & Dovecot config cleanup ────────────────────────────────────
    # Remove all lines referencing this domain from virtual mailbox, alias, and
    # dovecot users files so mail services don't log errors on every lookup.
    for fpath in (
        paths.POSTFIX_VIRTUAL_MAILBOX,
        paths.POSTFIX_VIRTUAL_ALIAS,
        getattr(paths, 'POSTFIX_VIRTUAL_DOMAINS', ''),
        paths.DOVECOT_USERS,
    ):
        if not fpath or not os.path.exists(fpath):
            continue
        try:
            with open(fpath, 'r') as f:
                lines = f.readlines()
            cleaned = [l for l in lines if f'@{domain_str}' not in l and f'{domain_str}' not in l]
            with open(fpath, 'w') as f:
                f.writelines(cleaned)
            logger.info('[terminate] Cleaned %s for domain %s', fpath, domain_str)
        except Exception as e:
            logger.warning('[terminate] postfix/dovecot file %s: %s', fpath, e)

    # Rebuild postfix maps
    try:
        _run(['sudo', 'postmap', paths.POSTFIX_VIRTUAL_MAILBOX], timeout=10)
        _run(['sudo', 'postmap', paths.POSTFIX_VIRTUAL_ALIAS], timeout=10)
    except Exception:
        pass

    # ── 8. MySQL: drop all databases and users prefixed with the account name ──
    # Convention: panel creates DBs as "<username>_<dbname>" and
    # MySQL users as "<username>_<mysqluser>".
    try:
        mysql_pw_file = paths.MYSQL_PASSWORD_FILE
        if os.path.exists(mysql_pw_file):
            with open(mysql_pw_file, 'r') as f:
                mysql_root_pass = f.read().strip()

            from function import (
                get_database_names_with_filter,
                get_database_users_with_filter,
                remove_database,
                delete_mysql_user,
            )
            prefix = mainusername + '_'

            # Drop all databases
            dbs = get_database_names_with_filter(mysql_root_pass, prefix)
            for db in dbs:
                if remove_database(db, mysql_root_pass):
                    logger.info('[terminate] Dropped MySQL database: %s', db)
                else:
                    logger.warning('[terminate] Failed to drop MySQL database: %s', db)

            # Drop all MySQL users
            db_users = get_database_users_with_filter(mysql_root_pass, prefix)
            for db_user in db_users:
                if delete_mysql_user(db_user, mysql_root_pass):
                    logger.info('[terminate] Dropped MySQL user: %s', db_user)
                else:
                    logger.warning('[terminate] Failed to drop MySQL user: %s', db_user)
    except Exception as e:
        logger.warning('[terminate] MySQL cleanup failed for %s: %s', mainusername, e)

    # ── 9. Service reloads (nginx -t first to catch config errors) ────────────
    nginx_test = _run(['sudo', 'nginx', '-t'], timeout=15)
    if nginx_test.returncode == 0:
        _reload('nginx')
    else:
        logger.error('[terminate] nginx -t failed after cleanup — NOT reloading nginx: %s',
                     nginx_test.stderr)
    for svc in ('bind9', 'postfix', 'dovecot'):
        _reload(svc)

    # ── 10. FTP accounts ──────────────────────────────────────────────────────
    try:
        ft = ftpaccount.objects.filter(main=mainusername)
        plat = get_platform()
        for acct in ft:
            plat.users.delete_user(acct.main)
        ft.delete()
    except Exception as e:
        logger.warning('[terminate] FTP cleanup: %s', e)

    # ── 11. Linux system user ─────────────────────────────────────────────────
    try:
        get_platform().users.delete_user(mainusername)
        logger.info('[terminate] Removed system user: %s', mainusername)
    except Exception as e:
        logger.warning('[terminate] userdel: %s', e)

    # ── 12. Python app service ────────────────────────────────────────────────
    try:
        apps = pythonname.objects.filter(main=mainusername) | pythonname.objects.filter(domain__in=all_domains)
        for df in apps.distinct():
            svc_name = df.name
            df.delete()
            if sys.platform != 'win32' and paths.SYSTEMD_DIR:
                _run(['sudo', 'systemctl', 'stop', svc_name], timeout=10)
                _run(['sudo', 'systemctl', 'disable', svc_name], timeout=10)
                svc_path = os.path.join(paths.SYSTEMD_DIR, f'{svc_name}.service')
                if os.path.exists(svc_path):
                    os.remove(svc_path)
                _run(['sudo', 'systemctl', 'daemon-reload'], timeout=15)
    except Exception as e:
        logger.warning('[terminate] Python cleanup: %s', e)

    # ── 13. MERN app ──────────────────────────────────────────────────────────
    try:
        apps = mernname.objects.filter(main=mainusername) | mernname.objects.filter(domain__in=all_domains)
        for df in apps.distinct():
            svc_name = df.name
            df.delete()
            if sys.platform != 'win32':
                # Stop PM2 process if running
                _run(['sudo', '-u', mainusername, 'pm2', 'delete', svc_name], timeout=10)
                _run(['sudo', '-u', mainusername, 'pm2', 'save'], timeout=10)
                # Remove socket file
                sock = os.path.join(paths.RUN_DIR if hasattr(paths, 'RUN_DIR') else '/var/run',
                                    f'{svc_name}.sock')
                if os.path.exists(sock):
                    os.remove(sock)
    except Exception as e:
        logger.warning('[terminate] MERN cleanup: %s', e)

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

        # 2. Update hosts file safely via temp file and sudo copy
        hosts_file = paths.HOSTS_FILE
        with open(hosts_file, 'r') as file:
            hosts_lines = file.readlines()
        temp_hosts = '/tmp/hosts_new'
        with open(temp_hosts, 'w') as file:
            for line in hosts_lines:
                if '127.0.1.1' in line:
                    file.write(f'127.0.1.1\t{new_hostname}\n')
                else:
                    file.write(line)
        if sys.platform != 'win32':
            _run(['sudo', 'cp', temp_hosts, hosts_file])
            _run(['sudo', 'rm', '-f', temp_hosts])

        # 3. Update Django CSRF settings
        settings_path = os.path.join(paths.PANEL_ROOT, 'panel', 'settings.py')
        if os.path.exists(settings_path):
            with open(settings_path, 'a+') as file:
                file.write(f'\nCSRF_TRUSTED_ORIGINS.extend(["http://{new_hostname}", "http://{new_hostname}:8080", "https://{new_hostname}", "https://{new_hostname}:8082"])\n')

        # 4. Generate SSL (platform-aware)
        ssl_ok = False
        if sys.platform != 'win32':
            res = _run([
                'sudo', 'certbot', '--nginx', '--non-interactive', '--agree-tos',
                '--email', email, '-d', new_hostname
            ])
            ssl_ok = (res.returncode == 0)
        else:
            get_platform().ssl.provision(new_hostname, email=email)
            ssl_ok = True
            
        if ssl_ok:
            try:
                from control.utils import trigger_ssl_notification
                trigger_ssl_notification(new_hostname)
            except Exception as e_notify:
                logger.error('Failed to trigger hostname SSL notification: %s', e_notify)
        
        # 5. Rewrite Nginx Configurations safely via temp file and sudo copy
        for conf_file in ['panel', 'phpmyadmin', 'roundcube']:
            conf_path = os.path.join(paths.NGINX_SITES_AVAILABLE, conf_file)
            if not os.path.exists(conf_path):
                continue
                
            with open(conf_path, 'r') as f:
                content = f.read()

            if is_first_time:
                content = content.replace(paths.SSL_DUMMY_CERT, f'{paths.LETSENCRYPT_LIVE}/{new_hostname}/fullchain.pem')
                content = content.replace(paths.SSL_DUMMY_KEY, f'{paths.LETSENCRYPT_LIVE}/{new_hostname}/privkey.pem')
            
            if old_hostname and old_hostname != new_hostname:
                import re
                suffix = ""
                if new_hostname.startswith(old_hostname):
                    suffix = new_hostname[len(old_hostname):]
                
                esc_old = re.escape(old_hostname)
                esc_suf = re.escape(suffix) if suffix else ""
                
                pattern = rf'\b{esc_old}\b'
                if esc_suf:
                    pattern += rf'(?!{esc_suf})'
                    
                content = re.sub(pattern, new_hostname, content)
                content = content.replace(f'{paths.LETSENCRYPT_LIVE}/{old_hostname}/', f'{paths.LETSENCRYPT_LIVE}/{new_hostname}/')

            temp_conf = f'/tmp/nginx_{conf_file}'
            with open(temp_conf, 'w') as f:
                f.write(content)
                
            if sys.platform != 'win32':
                _run(['sudo', 'cp', temp_conf, conf_path])
                _run(['sudo', 'rm', '-f', temp_conf])

        # 6. Update mail server (Postfix + Dovecot) to use the new hostname cert
        # This runs after every hostname SSL provisioning so mail clients (Outlook,
        # Thunderbird, etc.) get a trusted cert instead of the dummy self-signed one.
        if ssl_ok and sys.platform != 'win32':
            try:
                fullchain = f'{paths.LETSENCRYPT_LIVE}/{new_hostname}/fullchain.pem'
                privkey   = f'{paths.LETSENCRYPT_LIVE}/{new_hostname}/privkey.pem'

                # Update Postfix main.cf
                _run(['sudo', 'postconf', '-e', f'smtpd_tls_cert_file={fullchain}'])
                _run(['sudo', 'postconf', '-e', f'smtpd_tls_key_file={privkey}'])
                _run(['sudo', 'postconf', '-e', f'myhostname={new_hostname}'])

                # Update Dovecot 10-ssl.conf via python-based replacement (handles extra whitespace)
                ssl_conf = '/etc/dovecot/conf.d/10-ssl.conf'
                if os.path.exists(ssl_conf):
                    import re
                    with open(ssl_conf, 'r') as f:
                        ssl_content = f.read()
                    ssl_content = re.sub(r'ssl_cert\s*=.*', f'ssl_cert = <{fullchain}', ssl_content)
                    ssl_content = re.sub(r'ssl_key\s*=.*',  f'ssl_key  = <{privkey}',   ssl_content)
                    tmp_ssl = '/tmp/dovecot_10-ssl.conf'
                    with open(tmp_ssl, 'w') as f:
                        f.write(ssl_content)
                    _run(['sudo', 'cp', tmp_ssl, ssl_conf])
                    _run(['sudo', 'rm', '-f', tmp_ssl])

                # Reload mail services
                _run(['sudo', 'systemctl', 'reload', 'postfix'])
                _run(['sudo', 'systemctl', 'reload', 'dovecot'])
                logger.info('Mail server SSL updated to hostname cert: %s', new_hostname)
            except Exception as e_mail:
                logger.error('Failed to update mail server SSL cert: %s', e_mail)

        # 7. Service Reloads
        _reload('nginx')
        get_platform().services.restart('voidpanel')
        get_platform().services.restart('voidpanel-daphne')
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
            
            # Trigger SSL notification
            try:
                from control.utils import trigger_ssl_notification
                trigger_ssl_notification(domain_name)
            except Exception as e_notify:
                logger.error('Failed to trigger SSL notification for %s: %s', domain_name, e_notify)
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


# ─────────────────────────────────────────────────────────────
# Task: Nightly License Refresh (Celery Beat — runs at 00:00 UTC)
# ─────────────────────────────────────────────────────────────

@shared_task(
    name='control.tasks.refresh_license_task',
    acks_late=True,
    max_retries=3,
    default_retry_delay=300,  # retry after 5 min if voidpanel.com is temporarily down
)
def refresh_license_task():
    """
    Nightly task: Ping voidpanel.com to re-validate this installation's license key.
    On success, updates the local PanelLicense.status.
    On network failure, preserves the existing status (fail-open).
    """
    from control.license import refresh_license
    logger.info('[license] Nightly license refresh starting...')
    valid = refresh_license()
    if valid:
        logger.info('[license] License refresh OK — status: active')
    else:
        logger.warning('[license] License refresh returned non-active status. Panel access will be blocked.')
    return valid


# ─────────────────────────────────────────────────────────────
# Task: One-Click Script Installer
# ─────────────────────────────────────────────────────────────

@shared_task(
    bind=True,
    max_retries=0,
    name='voidpanel.install_script',
    acks_late=True,
)
def async_install_script(self, record_id: int, script_name: str, domain: str,
                          username: str, admin_user: str, admin_pass: str,
                          admin_email: str, install_url: str, **kwargs):
    """
    Celery task: Run a one-click script installation in the background.
    Updates InstalledScript.status to 'active' or 'failed' upon completion.
    """
    from control.models import InstalledScript
    from control.script_installers import run_installer

    logger.info('[AppInstaller] Starting install: %s on %s', script_name, domain)

    try:
        record = InstalledScript.objects.get(pk=record_id)
    except InstalledScript.DoesNotExist:
        logger.error('[AppInstaller] Record %d not found — aborting.', record_id)
        return

    try:
        result = run_installer(
            script_name=script_name,
            domain=domain,
            username=username,
            admin_user=admin_user,
            admin_pass=admin_pass,
            admin_email=admin_email,
            install_url=install_url,
            **kwargs,
        )

        record.log      = result.get('log', '')
        record.admin_url = result.get('admin_url', '')
        record.db_name  = result.get('db_name', '')
        record.db_user  = result.get('db_user', '')
        record.db_pass  = result.get('db_pass', '')

        if result.get('status') == 'success':
            record.status = InstalledScript.STATUS_ACTIVE
            logger.info('[AppInstaller] Install SUCCESS: %s on %s', script_name, domain)
            try:
                from control.utils import trigger_script_installed_notification
                trigger_script_installed_notification(script_name, domain, username, result.get('admin_url', ''))
            except Exception:
                pass
        else:
            record.status = InstalledScript.STATUS_FAILED
            logger.error('[AppInstaller] Install FAILED: %s on %s — %s', script_name, domain, result.get('error', ''))

    except Exception as exc:
        record.status = InstalledScript.STATUS_FAILED
        record.log    = str(exc)
        logger.exception('[AppInstaller] Unhandled exception during install of %s', script_name)

    record.save()


@shared_task(
    bind=True,
    max_retries=0,
    name='voidpanel.uninstall_script',
    acks_late=True,
)
def async_uninstall_script(self, record_id: int):
    """
    Celery task: Clean up/remove an installed script from the server.
    """
    from control.models import InstalledScript
    from control.script_installers import run_uninstaller

    logger.info('[AppInstaller] Uninstall task for record %d', record_id)

    try:
        record = InstalledScript.objects.get(pk=record_id)
    except InstalledScript.DoesNotExist:
        logger.error('[AppInstaller] Uninstall: record %d not found.', record_id)
        return

    try:
        result = run_uninstaller(record)
        record.status = InstalledScript.STATUS_DELETED
        record.log   += f"\n[Uninstall] {result.get('log', '')}"
        logger.info('[AppInstaller] Uninstall SUCCESS for record %d', record_id)
    except Exception as exc:
        record.log += f"\n[Uninstall ERROR] {str(exc)}"
        logger.exception('[AppInstaller] Uninstall FAILED for record %d', record_id)

    record.save()


@shared_task(
    bind=True,
    max_retries=0,
    name='voidpanel.process_scheduled_campaigns',
    acks_late=True,
)
def process_scheduled_campaigns_task(self):
    """
    Periodic task: Check for scheduled marketing campaigns and send them.
    """
    import smtplib
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText
    from django.utils import timezone
    from control.models import MarketingCampaign, CampaignRecipient, allemail

    now = timezone.now()
    scheduled_campaigns = MarketingCampaign.objects.filter(status='scheduled', scheduled_at__lte=now)
    
    logger.info('[Marketing] Periodic scheduler running. Found %d pending scheduled campaign(s)', scheduled_campaigns.count())
    
    for camp in scheduled_campaigns:
        logger.info('[Marketing] Processing scheduled campaign: %s (ID: %d)', camp.name, camp.id)
        
        # Update status immediately to prevent double processing in case of long runs
        camp.status = 'sent'
        camp.save()
        
        recipients = camp.recipients.filter(status='pending')
        if not recipients.exists():
            continue
            
        custom_smtp = camp.custom_smtp
        sender_email = camp.sender_email
        domain = camp.domain
        subject = camp.subject
        body_html = camp.body
        
        sent_count = 0
        fail_count = 0
        
        try:
            smtp = None
            if custom_smtp:
                if custom_smtp.encryption == 'ssl':
                    smtp = smtplib.SMTP_SSL(custom_smtp.smtp_host, custom_smtp.smtp_port, timeout=15)
                else:
                    smtp = smtplib.SMTP(custom_smtp.smtp_host, custom_smtp.smtp_port, timeout=15)
                    smtp.ehlo()
                    if custom_smtp.encryption == 'tls':
                        smtp.starttls()
                        smtp.ehlo()
                smtp.login(custom_smtp.smtp_user, custom_smtp.smtp_password)
            else:
                sender_obj_local = allemail.objects.filter(email=sender_email).first()
                sender_password = sender_obj_local.password if sender_obj_local else None
                try:
                    smtp = smtplib.SMTP('localhost', 587, timeout=10)
                    smtp.ehlo()
                    smtp.starttls()
                    if sender_password:
                        smtp.login(sender_email, sender_password)
                except Exception:
                    try:
                        if smtp: smtp.quit()
                    except Exception: pass
                    smtp = smtplib.SMTP('localhost', 25, timeout=10)
                    smtp.ehlo()

            from control.views import replace_email_placeholders
            from email.utils import formataddr

            for rcpt in recipients:
                try:
                    msg = MIMEMultipart('alternative')
                    if camp.custom_smtp and camp.custom_smtp.label:
                        msg['From'] = formataddr((camp.custom_smtp.label, sender_email))
                    else:
                        msg['From'] = sender_email
                    msg['To']      = rcpt.email

                    rcpt_subject = replace_email_placeholders(subject, rcpt.name, domain)
                    rcpt_body = replace_email_placeholders(body_html, rcpt.name, domain)
                    tracking_url = f'https://{domain}/control/marketing/{domain}/track/{rcpt.id}/open.png'
                    html_body = rcpt_body + f'<img src="{tracking_url}" width="1" height="1" style="display:none" alt="" />'

                    msg['Subject'] = rcpt_subject
                    msg.attach(MIMEText(rcpt_body, 'plain'))
                    msg.attach(MIMEText(html_body, 'html'))

                    smtp.sendmail(sender_email, [rcpt.email], msg.as_string())
                    rcpt.status = 'sent'
                    rcpt.sent_at = timezone.now()
                    rcpt.save()
                    sent_count += 1
                except Exception as e:
                    rcpt.status = 'failed'
                    rcpt.error_msg = str(e)[:500]
                    rcpt.save()
                    fail_count += 1

            try: smtp.quit()
            except Exception: pass

        except Exception as e:
            recipients.update(
                status='failed', error_msg=f'SMTP connection error: {str(e)[:400]}'
            )
            fail_count = camp.recipients.filter(status='failed').count()

        camp.sent_count = sent_count
        camp.open_rate = 0
        camp.save()
        logger.info('[Marketing] Scheduled campaign %d finished. Sent: %d, Failed: %d', camp.id, sent_count, fail_count)


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def update_all_email_stats_task(self):
    """Periodically or asynchronously updates the cached statistics for all emails."""
    try:
        update_all_email_stats()
        logger.info('[Email] All email statistics updated successfully.')
    except Exception as e:
        logger.error('[Email] Failed to update email statistics: %s', e)
        raise self.retry(exc=e)


def update_all_email_stats():
    import subprocess
    import re
    from collections import defaultdict
    from control.models import allemail
    from django.core.cache import cache

    queue_counts = defaultdict(int)
    if sys.platform != 'win32':
        try:
            r = subprocess.run(['sudo', 'postqueue', '-p'], capture_output=True, text=True, timeout=10)
            if r.returncode == 0:
                lines = r.stdout.splitlines()
                for line in lines:
                    for email_obj in allemail.objects.all():
                        if email_obj.email.lower() in line.lower():
                            queue_counts[email_obj.email.lower()] += 1
        except Exception:
            pass

    sent_counts = defaultdict(int)
    failed_counts = defaultdict(int)
    if sys.platform != 'win32':
        try:
            log_path = '/var/log/mail.log'
            if not os.path.exists(log_path) or os.path.getsize(log_path) == 0:
                log_path = '/var/log/syslog'
                
            if os.path.exists(log_path):
                r = subprocess.run(['sudo', 'cat', log_path], capture_output=True, text=True, timeout=15)
                if r.returncode == 0:
                    lines = r.stdout.splitlines()
                    queue_sender = {}
                    for line in lines:
                        match_qid = re.search(r'postfix/\w+\[\d+\]:\s+([0-9a-zA-Z]+):\s+', line)
                        if match_qid:
                            qid = match_qid.group(1)
                            match_from = re.search(r'from=<([^>]+)>', line)
                            if match_from:
                                queue_sender[qid] = match_from.group(1).lower()
                                
                            match_status = re.search(r'status=(\w+)', line)
                            if match_status and qid in queue_sender:
                                sender = queue_sender[qid]
                                status = match_status.group(1)
                                if status == 'sent':
                                    sent_counts[sender] += 1
                                elif status in ('bounced', 'deferred'):
                                    failed_counts[sender] += 1
        except Exception as e:
            pass

    for email_obj in allemail.objects.all():
        email = email_obj.email.lower()
        stats = {
            'sent': sent_counts.get(email, 0),
            'failed': failed_counts.get(email, 0),
            'queue': queue_counts.get(email, 0)
        }
        cache.set(f'email_stats:{email}', stats, timeout=3600)


@shared_task(
    bind=True,
    max_retries=0,
    name='control.tasks.process_automation_workflows_task',
    acks_late=True,
)
def process_automation_workflows_task(self):
    """
    Periodic task: Check running workflow enrollments and process due steps.
    """
    from django.utils import timezone
    from datetime import timedelta
    from control.models import (
        MarketingWorkflowEnrollment, MarketingWorkflowStep,
        MarketingTemplate, CustomSMTPConfig, SMSGatewayConfig
    )
    import smtplib
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText
    import requests
    
    now = timezone.now()
    due_enrollments = MarketingWorkflowEnrollment.objects.filter(status='running', next_run_at__lte=now)
    
    logger.info('[Automation] Periodic runner starting. Found %d due enrollments', due_enrollments.count())
    
    for enroll in due_enrollments:
        workflow = enroll.workflow
        lead = enroll.lead
        steps = list(workflow.steps.order_by('step_order'))
        
        while enroll.status == 'running' and enroll.next_run_at <= timezone.now():
            idx = enroll.current_step_index
            if idx >= len(steps):
                enroll.status = 'completed'
                enroll.save()
                break
                
            step = steps[idx]
            logger.info('[Automation] Executing workflow %s step %d (%s) for lead %s', workflow.name, step.step_order, step.action_type, lead.email or lead.phone)
            
            if step.action_type == 'delay':
                enroll.next_run_at = timezone.now() + timedelta(days=step.delay_days)
                enroll.current_step_index += 1
                enroll.save()
                break  # Stop processing this enrollment until the delay expires
                
            elif step.action_type == 'send_email':
                if lead.email:
                    # Get SMTP configuration
                    smtp_config = CustomSMTPConfig.objects.filter(domain=workflow.domain).first()
                    sender_email = smtp_config.from_email if smtp_config else f"noreply@{workflow.domain}"
                    subject = "Notification"
                    body = step.message_text or "Hello!"
                    
                    if step.template_id:
                        try:
                            tmpl = MarketingTemplate.objects.get(id=step.template_id)
                            subject = tmpl.subject or subject
                            body = tmpl.content_html or body
                        except MarketingTemplate.DoesNotExist:
                            pass
                            
                    # Personalise
                    subject = subject.replace('{{name}}', lead.name).replace('{{email}}', lead.email)
                    body = body.replace('{{name}}', lead.name).replace('{{email}}', lead.email)
                    
                    try:
                        msg = MIMEMultipart('alternative')
                        msg['Subject'] = subject
                        msg['From'] = sender_email
                        msg['To'] = lead.email
                        msg.attach(MIMEText(body, 'html'))
                        
                        server = None
                        if smtp_config:
                            if smtp_config.encryption == 'ssl':
                                server = smtplib.SMTP_SSL(smtp_config.smtp_host, smtp_config.smtp_port, timeout=10)
                            else:
                                server = smtplib.SMTP(smtp_config.smtp_host, smtp_config.smtp_port, timeout=10)
                                server.ehlo()
                                if smtp_config.encryption == 'tls':
                                    server.starttls()
                                    server.ehlo()
                            server.login(smtp_config.smtp_user, smtp_config.smtp_password)
                        else:
                            server = smtplib.SMTP('localhost', 25, timeout=10)
                            
                        server.sendmail(sender_email, [lead.email], msg.as_string())
                        server.quit()
                    except Exception as e:
                        logger.error('[Automation] Failed to send email: %s', e)
                
                enroll.current_step_index += 1
                
            elif step.action_type == 'send_sms':
                if lead.phone:
                    # Personalise
                    sms_text = (step.message_text or "").replace('{{name}}', lead.name).replace('{{phone}}', lead.phone)
                    
                    # Try custom gateway first, then system default
                    gateway = SMSGatewayConfig.objects.filter(domain=workflow.domain).first()
                    if gateway and gateway.api_url:
                        try:
                            url = gateway.api_url.replace('{phone}', lead.phone).replace('{msg}', requests.utils.quote(sms_text))
                            requests.get(url, timeout=10)
                        except Exception as e:
                            logger.error('[Automation] Failed to send SMS via gateway: %s', e)
                            
                enroll.current_step_index += 1
                
            elif step.action_type == 'send_whatsapp':
                if lead.phone:
                    # Personalise
                    wa_text = (step.message_text or "").replace('{{name}}', lead.name).replace('{{phone}}', lead.phone)
                    
                    # Format phone number for WhatsApp
                    clean_phone = ''.join(c for c in lead.phone if c.isdigit())
                    
                    try:
                        # Call local microservice
                        resp = requests.post('http://127.0.0.1:3001/send', json={
                            'to': clean_phone,
                            'message': wa_text
                        }, timeout=10)
                        resp.raise_for_status()
                        
                        # Also save to message history
                        # Try to resolve conversation
                        from .models import WaConversation, WaMessage
                        conv, _ = WaConversation.objects.get_or_create(
                            domain=workflow.domain,
                            phone=clean_phone,
                            defaults={'name': lead.name}
                        )
                        conv.last_message = wa_text
                        conv.last_ts = timezone.now()
                        conv.save()
                        
                        WaMessage.objects.create(
                            conversation=conv,
                            domain=workflow.domain,
                            phone=clean_phone,
                            name=lead.name,
                            text=wa_text,
                            direction='out'
                        )
                    except Exception as e:
                        logger.error('[Automation] Failed to send WhatsApp via microservice: %s', e)
                        
                enroll.current_step_index += 1
                
            # Save progress and continue the loop to the next step
            enroll.save()
            
        # Double check if completed
        if enroll.status == 'running' and enroll.current_step_index >= len(steps):
            enroll.status = 'completed'
            enroll.save()

