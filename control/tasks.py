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

from celery import shared_task

from panel.logger import get_logger

logger = get_logger(__name__)


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
        _run(['sudo', 'systemctl', 'reload', service], timeout=15)
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
        # Write PHP INI
        with open(inipath, 'w', encoding='utf-8') as f:
            f.write(php_ini_content)

        # Nginx / SSL / DNS setup (imported from views helpers)
        from panel.views import (
            generate_ssl_certificates, create_nginx_ssl_conf,
            generate_dkim_keys, create_bind_records, configure_opendkim,
        )
        file_path = f'/etc/nginx/sites-available/{domain12}.conf'
        root_dir  = path + '/public_html'
        cert_path, key_path = generate_ssl_certificates(domain12, path + '/ssl', path + '/logs')

        if cert_path and key_path:
            create_nginx_ssl_conf(file_path, domain12, root_dir, cert_path, key_path)
        else:
            raise RuntimeError(f'Cannot generate OpenSSL for domain {domain12}')

        key_dir        = f'/etc/opendkim/keys/{domain12}'
        zone_file_path = f'/etc/bind/db.{domain12}'
        private_key_path, public_key_path = generate_dkim_keys(domain12, key_dir)

        if private_key_path and public_key_path:
            create_bind_records(domain12, key_dir, zone_file_path)
            configure_opendkim(domain12, key_dir)
        else:
            raise RuntimeError(f'Cannot generate DKIM for domain {domain12}')

        # Atomic DB inserts
        with transaction.atomic():
            domain.objects.create(domain=domain12, email=email, dir=domainname, userdomain=True)
            user.objects.create(domain=domain12, email=email, username=domainname, hosting_package=package12)
            User.objects.create_user(username=domainname, email=email, password=password)

        # Create Unix user — parameterised (no shell injection)
        _run(['sudo', 'useradd', '-m', '-s', '/usr/sbin/nologin', domainname])

        passwd_proc = subprocess.Popen(
            ['sudo', 'chpasswd'],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, encoding='utf-8',
        )
        passwd_proc.communicate(input=f'{domainname}:{password}\n')

        _run(['sudo', 'chown', f'{domainname}:{domainname}', f'/home/{domainname}'])

        # Apply disk quota
        try:
            _run(['sudo', 'setquota', '-u', domainname, str(sto), str(sto), '0', '0', '/'])
        except Exception:
            logger.warning('Quota setup skipped for %s (setquota not available?)', domainname)

        # Zero-downtime reloads
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
            f'/etc/nginx/sites-enabled/{domain12}.conf',
            f'/etc/nginx/sites-available/{domain12}.conf',
            f'/var/mail/vhosts/{domain12}',
        ]:
            try:
                if os.path.isdir(path_to_remove):
                    shutil.rmtree(path_to_remove)
                elif os.path.exists(path_to_remove):
                    os.remove(path_to_remove)
            except Exception:
                pass

        # Unix user rollback
        _run(['sudo', 'userdel', '-r', domainname])

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
        shutil.rmtree(f'/home/{mainusername}', ignore_errors=True)
    except Exception as e:
        logger.warning('[terminate] home dir: %s', e)

    # Nginx configs (main + subdomains)
    for conf in [f'/etc/nginx/sites-enabled/{domain_str}.conf'] + \
                [f'/etc/nginx/sites-enabled/{s}.conf' for s in subdomains]:
        try:
            os.remove(conf)
        except FileNotFoundError:
            pass
        except Exception as e:
            logger.warning('[terminate] nginx conf %s: %s', conf, e)

    # DNS zone
    for path in [f'/etc/bind/db.{domain_str}']:
        try:
            os.remove(path)
        except Exception:
            pass
    try:
        from panel.views import remove_zone_from_file
        remove_zone_from_file('/etc/bind/named.conf', domain_str)
    except Exception:
        pass

    # DKIM keys
    for kpath in [f'/etc/opendkim/keys/{domain_str}'] + \
                 [f'/etc/opendkim/keys/{s}' for s in subdomains]:
        shutil.rmtree(kpath, ignore_errors=True)

    # SSL certs
    for spath in [f'/etc/letsencrypt/live/{domain_str}'] + \
                 [f'/etc/letsencrypt/live/{s}' for s in subdomains]:
        shutil.rmtree(spath, ignore_errors=True)

    # Mail data
    shutil.rmtree(f'/var/mail/vhosts/{domain_str}', ignore_errors=True)

    # Service reloads
    for svc in ('bind9', 'nginx', 'postfix', 'dovecot'):
        _reload(svc)

    # FTP accounts
    try:
        ft = ftpaccount.objects.filter(main=mainusername)
        for acct in ft:
            _run(['sudo', 'deluser', acct.main])
        ft.delete()
    except Exception as e:
        logger.warning('[terminate] FTP cleanup: %s', e)

    # Linux user
    try:
        _run(['sudo', 'userdel', '-r', mainusername])
    except Exception as e:
        logger.warning('[terminate] userdel: %s', e)

    # Python app service
    try:
        df = pythonname.objects.get(domain=domain_str)
        svc_name = df.name
        df.delete()
        os.remove(f'/etc/systemd/system/{svc_name}.service')
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
        for d in [path, f'{path}/public_html', f'{path}/ssl', f'{path}/logs', f'/var/mail/vhosts/{domain12}']:
            os.makedirs(d, exist_ok=True)

        # Copy default voidpanel index
        _run(['sudo', 'cp', '-r', '/var/www/panel/voidpanel/.', f'{path}/public_html/'])

        # Write PHP INI
        with open(inipath, 'w', encoding='utf-8') as f:
            f.write(php_ini_content)

        # Nginx & SSL
        file_path = f'/etc/nginx/sites-available/{domain12}.conf'
        root_dir = f'{path}/public_html'
        cert_path, key_path = generate_ssl_certificates(domain12, f'{path}/ssl', f'{path}/logs')
        
        if cert_path and key_path:
            create_nginx_ssl_conf(file_path, domain12, root_dir, cert_path, key_path)
            # Link to sites-enabled
            if not os.path.exists(f'/etc/nginx/sites-enabled/{domain12}.conf'):
                os.symlink(file_path, f'/etc/nginx/sites-enabled/{domain12}.conf')
        else:
            raise RuntimeError(f'SSL generation failed for {domain12}')

        # DKIM & DNS
        key_dir = f'/etc/opendkim/keys/{domain12}'
        zone_file_path = f'/etc/bind/db.{domain12}'
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
        for p in [f'/etc/nginx/sites-enabled/{domain12}.conf', f'/etc/nginx/sites-available/{domain12}.conf', f'/var/mail/vhosts/{domain12}']:
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
        _run(['sudo', 'hostnamectl', 'set-hostname', new_hostname])
        
        # 2. Update /etc/hosts safely
        with open('/etc/hosts', 'r') as file:
            hosts_lines = file.readlines()
        with open('/etc/hosts', 'w') as file:
            for line in hosts_lines:
                if '127.0.1.1' in line:
                    file.write(f'127.0.1.1\t{new_hostname}\n')
                else:
                    file.write(line)

        # 3. Update Django CSRF settings
        settings_path = '/var/www/panel/panel/settings.py'
        if os.path.exists(settings_path):
            with open(settings_path, 'a+') as file:
                file.write(f'\nCSRF_TRUSTED_ORIGINS.append("https://{new_hostname}:8082")\n')

        # 4. Generate SSL with certbot securely
        _run([
            'sudo', 'certbot', '--nginx', '--non-interactive', '--agree-tos',
            '--email', email, '-d', new_hostname
        ])
        
        # 5. Rewrite Nginx Configurations securely instead of using raw 'sed'
        for conf_file in ['panel', 'phpmyadmin', 'roundcube']:
            conf_path = f'/etc/nginx/sites-available/{conf_file}'
            if not os.path.exists(conf_path):
                continue
                
            with open(conf_path, 'r') as f:
                content = f.read()

            content = content.replace(old_hostname, new_hostname)

            if is_first_time:
                content = content.replace('/etc/nginx/dummy.crt', f'/etc/letsencrypt/live/{new_hostname}/fullchain.pem')
                content = content.replace('/etc/nginx/dummy.key', f'/etc/letsencrypt/live/{new_hostname}/privkey.pem')
            else:
                content = content.replace(f'/etc/letsencrypt/live/{old_hostname}/fullchain.pem', f'/etc/letsencrypt/live/{new_hostname}/fullchain.pem')
                content = content.replace(f'/etc/letsencrypt/live/{old_hostname}/privkey.pem', f'/etc/letsencrypt/live/{new_hostname}/privkey.pem')

            with open(conf_path, 'w') as f:
                f.write(content)

        # 6. Service Reloads
        _reload('nginx')
        _run(['sudo', 'systemctl', 'restart', 'uwsgi'])
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
            
        # 2. Create Unix user — parameterised (no shell injection)
        _run(['sudo', 'useradd', '-m', '-s', '/usr/sbin/nologin', dir_name])
        
        passwd_proc = subprocess.Popen(
            ['sudo', 'chpasswd'],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, encoding='utf-8',
        )
        passwd_proc.communicate(input=f'{dir_name}:{password}\n')
        
        _run(['sudo', 'chown', f'{dir_name}:{dir_name}', f'/home/{dir_name}'])
        
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
    
    logger.info('Auto SSL task started for domain: %s', domain_name)
    path = '/var/log/ssl.txt'
    
    command = [
        "sudo", "certbot", "--nginx",
        "-d", domain_name, "-d", f'www.{domain_name}',
        "--non-interactive", "--agree-tos",
        "--email", email, "--redirect", "--no-eff-email"
    ]
    
    try:
        # Run certbot securely
        _run(command, timeout=120)  # certbot can take a while to complete ACME challenge
        
        # Log success
        with open(path, 'a+', encoding='utf-8') as f:
            f.write(f"\nAutoSSl Completed for domain {domain_name}")
            
        # Update Database
        try:
            db_domain = domain.objects.get(domain=domain_name)
            db_domain.sslstatus = True
            db_domain.save()
        except domain.DoesNotExist:
            logger.warning('Auto SSL domain %s not found in DB', domain_name)

        logger.info('Auto SSL SUCCESS: %s', domain_name)
        
    except Exception as exc:
        with open(path, 'a+', encoding='utf-8') as f:
            f.write(f"\nError Occured during AutoSSL for domain {domain_name}")
        logger.error('Auto SSL FAILED for %s. Error: %s', domain_name, exc)
        raise
