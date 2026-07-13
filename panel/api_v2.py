import json
import logging
from functools import wraps

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import hmac

from control.models import APIToken, user as VUser, package, domain as DomainModel

logger = logging.getLogger('voidpanel')

def _json_error(msg, status=400):
    return JsonResponse({'status': 'error', 'message': msg}, status=status)

def _json_success(data=None, message='Success'):
    resp = {'status': 'success', 'message': message}
    if data:
        resp.update(data)
    return JsonResponse(resp)

def require_api_auth(required_scope):
    """
    Decorator for API v2 views.
    1. Extracts X-API-Token header.
    2. Looks up APIToken.
    3. Verifies token has `required_scope`.
    4. Attaches token to request.api_token for reseller checks.
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            auth_header = request.headers.get('X-API-Token', '').strip()
            if not auth_header:
                # Fallback to Authorization: Bearer
                auth_header = request.headers.get('Authorization', '')
                if auth_header.startswith('Bearer '):
                    auth_header = auth_header[7:].strip()

            if not auth_header:
                return _json_error('Missing authentication token', 401)

            # To prevent timing attacks, we should technically compare hashes, but since we 
            # lookup by key, we just query it.
            try:
                token = APIToken.objects.get(key=auth_header, is_active=True)
            except APIToken.DoesNotExist:
                return _json_error('Invalid or inactive token', 403)

            if not token.has_scope(required_scope):
                return _json_error(f'Token missing required scope: {required_scope}', 403)

            # Update last used
            token.touch()
            request.api_token = token
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator

def _verify_reseller_access(token, domain_name):
    """
    If token is owned by a reseller, verify they own the domain.
    Returns (True, None) if ok, or (False, ErrorResponse) if forbidden.
    """
    if token.owner_type == APIToken.OWNER_SUPERADMIN:
        return True, None
    
    if not token.reseller:
        return False, _json_error('Reseller token has no profile linked', 500)

    try:
        # Check if domain belongs to a user owned by this reseller
        vuser = VUser.objects.get(domain=domain_name)
        if vuser.reseller_id != token.reseller_id:
            return False, _json_error('Forbidden: Domain not in your reseller pool', 403)
        return True, None
    except VUser.DoesNotExist:
        return False, _json_error('Domain not found', 404)

# ── Ping ──────────────────────────────────────────────────────────────────────

@csrf_exempt
@require_http_methods(['GET'])
def api_ping(request):
    import socket
    return _json_success({
        'hostname': socket.gethostname(),
        'version': 'v2',
        'auth_required': False
    }, 'VoidPanel API v2 is online')

# ── Accounts ──────────────────────────────────────────────────────────────────

@csrf_exempt
@require_http_methods(['GET'])
@require_api_auth('accounts.list')
def accounts_list(request):
    qs = VUser.objects.all()
    if request.api_token.owner_type == APIToken.OWNER_RESELLER:
        qs = qs.filter(reseller=request.api_token.reseller)
    
    data = []
    for u in qs:
        data.append({
            'username': u.username,
            'domain': u.domain,
            'package': u.hosting_package,
            'is_active': u.is_active,
            'status': u.status
        })
    return _json_success({'accounts': data})

@csrf_exempt
@require_http_methods(['POST'])
@require_api_auth('accounts.create')
def accounts_create(request):
    try:
        data = json.loads(request.body)
    except Exception:
        return _json_error('Invalid JSON body')

    domain = data.get('domain', '').lower().strip()
    email = data.get('email', '').strip()
    pkg_name = data.get('package', 'default')

    if not domain or not email:
        return _json_error('domain and email are required')

    if DomainModel.objects.filter(domain=domain).exists():
        return _json_error(f"Domain '{domain}' already exists", 409)

    # Note: Full provisioning logic (Celery task, quota checks, etc.) should be called here.
    # For brevity in this file, we will import and trigger the background task.
    # If reseller, we must check quotas first.
    
    token = request.api_token
    if token.owner_type == APIToken.OWNER_RESELLER:
        prof = token.reseller
        if not prof.has_account_slot():
            return _json_error('Reseller account limit reached', 403)
        # Check storage quota
        try:
            pkg_obj = package.objects.get(name=pkg_name)
            sto = int(pkg_obj.storage)
        except:
            return _json_error('Invalid package')
        if not prof.has_storage_for(sto):
            return _json_error('Reseller storage quota exceeded', 403)

    import re, secrets, string
    from control.tasks import provision_user_task
    from voidplatform.config import paths
    import os

    alphabet = string.ascii_letters + string.digits
    password = data.get('password') or ''.join(secrets.choice(alphabet) for _ in range(16))
    
    directories = os.listdir(paths.HOME_BASE)
    base_name = re.sub(r'[^a-z0-9]', '', domain.split('.')[0].lower())[:16]
    domainname = base_name
    counter = 1
    while domainname in directories:
        suffix = str(counter)
        domainname = base_name[:16 - len(suffix)] + suffix
        counter += 1

    try:
        pkg_obj = package.objects.get(name=pkg_name)
        sto = int(pkg_obj.storage)
    except package.DoesNotExist:
        return _json_error('Package not found')

    acct_path = os.path.join(paths.HOME_BASE, domainname)
    inipath = acct_path + '/public_html/php.ini'
    php_ini_content = f'; PHP settings for {domain}\nopen_basedir = "{acct_path}/public_html:/tmp"\n'

    task = provision_user_task.delay(
        domain, domainname, email, password, pkg_name,
        acct_path, sto, inipath, php_ini_content,
    )

    # Tag reseller if applicable
    if token.owner_type == APIToken.OWNER_RESELLER:
        import threading, time
        def _tag(dname, prof):
            time.sleep(20)
            try:
                u = VUser.objects.get(username=dname)
                u.reseller = prof
                u.save(update_fields=['reseller'])
            except: pass
        threading.Thread(target=_tag, args=(domainname, prof), daemon=True).start()

    return _json_success({
        'task_id': str(task.id),
        'username': domainname,
        'password': password
    }, 'Account provisioning started')

@csrf_exempt
@require_http_methods(['POST'])
@require_api_auth('accounts.suspend')
def accounts_suspend(request):
    try: data = json.loads(request.body)
    except: return _json_error('Invalid JSON body')
    domain = data.get('domain')
    if not domain: return _json_error('domain required')
    
    ok, err = _verify_reseller_access(request.api_token, domain)
    if not ok: return err

    try:
        from control.tasks import suspend_user_task
        u = VUser.objects.get(domain=domain)
        suspend_user_task.delay(u.username, domain)
        return _json_success(message=f'Account {domain} suspended')
    except Exception as e:
        return _json_error(str(e))

@csrf_exempt
@require_http_methods(['POST'])
@require_api_auth('accounts.unsuspend')
def accounts_unsuspend(request):
    try: data = json.loads(request.body)
    except: return _json_error('Invalid JSON body')
    domain = data.get('domain')
    if not domain: return _json_error('domain required')
    
    ok, err = _verify_reseller_access(request.api_token, domain)
    if not ok: return err

    try:
        from control.tasks import unsuspend_user_task
        u = VUser.objects.get(domain=domain)
        unsuspend_user_task.delay(u.username, domain)
        return _json_success(message=f'Account {domain} unsuspended')
    except Exception as e:
        return _json_error(str(e))

@csrf_exempt
@require_http_methods(['POST'])
@require_api_auth('accounts.terminate')
def accounts_terminate(request):
    try: data = json.loads(request.body)
    except: return _json_error('Invalid JSON body')
    domain_name = data.get('domain')
    if not domain_name: return _json_error('domain required')

    ok, err = _verify_reseller_access(request.api_token, domain_name)
    if not ok: return err

    try:
        from control.tasks import terminate_user_task
        from control.models import subdomainname
        u = VUser.objects.get(domain=domain_name)
        sub_domains = list(subdomainname.objects.filter(domain=domain_name).values_list('subdomain', flat=True))
        terminate_user_task.delay(domain_name, u.username, sub_domains)
        
        DomainModel.objects.filter(domain=domain_name).delete()
        VUser.objects.filter(username=u.username).delete()
        from django.contrib.auth.models import User as AuthUser
        AuthUser.objects.filter(username=u.username).delete()
        
        return _json_success(message=f'Account {domain_name} termination started')
    except Exception as e:
        return _json_error(str(e))


# ── DNS ───────────────────────────────────────────────────────────────────────

@csrf_exempt
@require_http_methods(['GET'])
@require_api_auth('dns.list')
def dns_list(request):
    domain = request.GET.get('domain')
    if not domain: return _json_error('domain required')
    ok, err = _verify_reseller_access(request.api_token, domain)
    if not ok: return err

    from control.models import subdomainname
    subs = list(subdomainname.objects.filter(domain=domain).values('subdomain', 'name', 'sslstatus'))
    return _json_success({'subdomains': subs})

@csrf_exempt
@require_http_methods(['POST'])
@require_api_auth('dns.create')
def dns_create(request):
    try: data = json.loads(request.body)
    except: return _json_error('Invalid JSON body')
    domain = data.get('domain')
    record_type = data.get('type')
    name = data.get('name')
    value = data.get('value')
    if not all([domain, record_type, name, value]): return _json_error('Missing required fields')
    
    ok, err = _verify_reseller_access(request.api_token, domain)
    if not ok: return err

    import os
    cmd = f'sudo voiddns add {domain} {record_type} {name} {value}'
    os.system(cmd)
    return _json_success(message='DNS record added')

# ── Email ─────────────────────────────────────────────────────────────────────

@csrf_exempt
@require_http_methods(['GET'])
@require_api_auth('email.list')
def email_list(request):
    domain = request.GET.get('domain')
    if not domain: return _json_error('domain required')
    # For superadmin tokens (used by voidpanel.com), skip hosting-account domain check
    # so email-only domains (no hosting account) are supported.
    if request.api_token.owner_type != APIToken.OWNER_SUPERADMIN:
        ok, err = _verify_reseller_access(request.api_token, domain)
        if not ok: return err

    from control.models import allemail
    emails = list(allemail.objects.filter(domain=domain).values('email'))
    return _json_success({'data': {'emails': list(allemail.objects.filter(domain=domain).values('email'))}})

@csrf_exempt
@require_http_methods(['POST'])
@require_api_auth('email.create')
def email_create(request):
    try: data = json.loads(request.body)
    except: return _json_error('Invalid JSON body')
    domain = data.get('domain')
    email = data.get('email')
    password = data.get('password')
    if not all([domain, email, password]): return _json_error('Missing required fields')

    # Superadmin tokens can create email for any domain (including email-only, no hosting account)
    if request.api_token.owner_type != APIToken.OWNER_SUPERADMIN:
        ok, err = _verify_reseller_access(request.api_token, domain)
        if not ok: return err

    from control.models import allemail
    import os
    if not allemail.objects.filter(email=email).exists():
        allemail.objects.create(email=email, password=password, domain=domain)
        os.system(f"sudo voidemail add {email} '{password}'")
        return _json_success(message=f'Email {email} created')
    return _json_error('Email already exists', 409)

# ── Database ──────────────────────────────────────────────────────────────────

@csrf_exempt
@require_http_methods(['GET'])
@require_api_auth('databases.list')
def database_list(request):
    domain = request.GET.get('domain')
    if not domain: return _json_error('domain required')
    ok, err = _verify_reseller_access(request.api_token, domain)
    if not ok: return err

    try:
        u = VUser.objects.get(domain=domain)
        import subprocess
        dbs = subprocess.check_output(f"mysql -u root -e \\\"SHOW DATABASES LIKE '{u.username}_%';\\\"", shell=True).decode().split('\\n')[1:-1]
        return _json_success({'databases': dbs})
    except:
        return _json_success({'databases': []})

@csrf_exempt
@require_http_methods(['POST'])
@require_api_auth('databases.create')
def database_create(request):
    try: data = json.loads(request.body)
    except: return _json_error('Invalid JSON body')
    domain = data.get('domain')
    dbname = data.get('database')
    dbuser = data.get('user')
    dbpass = data.get('password')
    if not all([domain, dbname, dbuser, dbpass]): return _json_error('Missing required fields')
    
    ok, err = _verify_reseller_access(request.api_token, domain)
    if not ok: return err

    try:
        u = VUser.objects.get(domain=domain)
        full_db = f"{u.username}_{dbname}"
        full_user = f"{u.username}_{dbuser}"
        import os
        os.system(f"mysql -u root -e \\\"CREATE DATABASE {full_db}; CREATE USER '{full_user}'@'localhost' IDENTIFIED BY '{dbpass}'; GRANT ALL PRIVILEGES ON {full_db}.* TO '{full_user}'@'localhost'; FLUSH PRIVILEGES;\\\"")
        return _json_success(message=f'Database {full_db} created')
    except Exception as e:
        return _json_error(str(e))

# ── SSL ───────────────────────────────────────────────────────────────────────

@csrf_exempt
@require_http_methods(['GET'])
@require_api_auth('ssl.list')
def ssl_status(request):
    domain = request.GET.get('domain')
    if not domain: return _json_error('domain required')
    ok, err = _verify_reseller_access(request.api_token, domain)
    if not ok: return err

    import os
    ssl_file = f'/usr/local/lsws/conf/cert/{domain}/fullchain.cer'
    status = 'active' if os.path.exists(ssl_file) else 'inactive'
    return _json_success({'ssl_status': status})

# ── Packages & Server ─────────────────────────────────────────────────────────

@csrf_exempt
@require_http_methods(['GET'])
@require_api_auth('packages.list')
def packages_list(request):
    pkgs = list(package.objects.values('name', 'storage', 'bandwidth', 'email_accounts', 'subdomains', 'databases'))
    return _json_success({'packages': pkgs})

@csrf_exempt
@require_http_methods(['GET'])
@require_api_auth('server.status')
def server_status(request):
    import psutil, platform
    cpu = psutil.cpu_percent(interval=0.1)
    ram = psutil.virtual_memory().percent
    disk = psutil.disk_usage('/').percent
    return _json_success({
        'hostname': platform.node(),
        'os': platform.system(),
        'cpu_percent': cpu,
        'ram_percent': ram,
        'disk_percent': disk
    })

# ── Accounts: Change Package ───────────────────────────────────────────────────
@csrf_exempt
@require_http_methods(['POST'])
@require_api_auth('accounts.change_package')
def accounts_change_package(request):
    """POST /api/v2/accounts/change-package/  Body: {domain, package}"""
    try: data = json.loads(request.body)
    except: return _json_error('Invalid JSON body')
    domain   = data.get('domain')
    pkg_name = data.get('package')
    if not domain or not pkg_name: return _json_error('domain and package required')
    ok, err = _verify_reseller_access(request.api_token, domain)
    if not ok: return err
    try:
        pkg = package.objects.get(name=pkg_name)
        u = VUser.objects.get(domain=domain)
        u.hosting_package = pkg.name
        u.save(update_fields=['hosting_package'])
        # Apply new quota
        import os
        os.system(f"setquota -u {u.username} 0 {int(pkg.storage)*1024*1024} 0 0 /  2>/dev/null || true")
        return _json_success(message=f'Package for {domain} changed to {pkg_name}')
    except package.DoesNotExist:
        return _json_error('Package not found', 404)
    except VUser.DoesNotExist:
        return _json_error('Domain not found', 404)
    except Exception as e:
        return _json_error(str(e))


# ── Accounts: Change Password ──────────────────────────────────────────────────
@csrf_exempt
@require_http_methods(['POST'])
@require_api_auth('accounts.change_password')
def accounts_change_password(request):
    """POST /api/v2/accounts/change-password/  Body: {domain, password}"""
    try: data = json.loads(request.body)
    except: return _json_error('Invalid JSON body')
    domain   = data.get('domain')
    password = data.get('password')
    if not domain or not password: return _json_error('domain and password required')
    ok, err = _verify_reseller_access(request.api_token, domain)
    if not ok: return err
    try:
        u = VUser.objects.get(domain=domain)
        from django.contrib.auth.models import User as AuthUser
        try:
            auth_user = AuthUser.objects.get(username=u.username)
            auth_user.set_password(password)
            auth_user.save()
        except AuthUser.DoesNotExist:
            pass
        # Also update system user password
        import subprocess
        subprocess.run(f"echo '{u.username}:{password}' | chpasswd", shell=True)
        return _json_success(message=f'Password changed for {domain}')
    except VUser.DoesNotExist:
        return _json_error('Domain not found', 404)
    except Exception as e:
        return _json_error(str(e))


# ── Accounts: Get Info ─────────────────────────────────────────────────────────
@csrf_exempt
@require_http_methods(['GET'])
@require_api_auth('accounts.list')
def accounts_get(request):
    """GET /api/v2/accounts/get/?domain=example.com"""
    domain = request.GET.get('domain')
    if not domain: return _json_error('domain required')
    ok, err = _verify_reseller_access(request.api_token, domain)
    if not ok: return err
    try:
        u = VUser.objects.get(domain=domain)
        return _json_success({'account': {
            'username': u.username,
            'domain': u.domain,
            'email': u.email,
            'package': u.hosting_package,
            'is_active': u.is_active,
            'status': u.status,
        }})
    except VUser.DoesNotExist:
        return _json_error('Domain not found', 404)


# ── Email: Delete ─────────────────────────────────────────────────────────────
@csrf_exempt
@require_http_methods(['POST'])
@require_api_auth('email.delete')
def email_delete(request):
    """POST /api/v2/email/delete/  Body: {domain, email}"""
    try: data = json.loads(request.body)
    except: return _json_error('Invalid JSON body')
    domain = data.get('domain')
    email  = data.get('email')
    if not domain or not email: return _json_error('domain and email required')
    # Superadmin tokens can delete any email (including email-only domains)
    if request.api_token.owner_type != APIToken.OWNER_SUPERADMIN:
        ok, err = _verify_reseller_access(request.api_token, domain)
        if not ok: return err
    from control.models import allemail
    import os
    allemail.objects.filter(email=email, domain=domain).delete()
    os.system(f"sudo voidemail del '{email}' 2>/dev/null || true")
    return _json_success(message=f'Email {email} deleted')


# ── Email: Change Password ─────────────────────────────────────────────────────
@csrf_exempt
@require_http_methods(['POST'])
@require_api_auth('email.change_password')
def email_change_password(request):
    """POST /api/v2/email/change-password/  Body: {domain, email, password}"""
    try: data = json.loads(request.body)
    except: return _json_error('Invalid JSON body')
    domain   = data.get('domain')
    email    = data.get('email')
    password = data.get('password')
    if not all([domain, email, password]): return _json_error('domain, email and password required')
    # Superadmin tokens can change any email password (including email-only domains)
    if request.api_token.owner_type != APIToken.OWNER_SUPERADMIN:
        ok, err = _verify_reseller_access(request.api_token, domain)
        if not ok: return err
    from control.models import allemail
    import os
    obj = allemail.objects.filter(email=email, domain=domain).first()
    if not obj: return _json_error('Email not found', 404)
    obj.password = password
    obj.save()
    os.system(f"sudo voidemail chpass '{email}' '{password}' 2>/dev/null || true")
    return _json_success(message=f'Password changed for {email}')


# ── DNS: Delete Record ────────────────────────────────────────────────────────
@csrf_exempt
@require_http_methods(['POST'])
@require_api_auth('dns.delete')
def dns_delete(request):
    """POST /api/v2/dns/delete/  Body: {domain, type, name}"""
    try: data = json.loads(request.body)
    except: return _json_error('Invalid JSON body')
    domain = data.get('domain')
    rtype  = data.get('type')
    name   = data.get('name')
    if not all([domain, rtype, name]): return _json_error('domain, type and name required')
    ok, err = _verify_reseller_access(request.api_token, domain)
    if not ok: return err
    import os
    os.system(f'sudo voiddns del {domain} {rtype} {name} 2>/dev/null || true')
    return _json_success(message='DNS record deleted')


# ── Subdomains ────────────────────────────────────────────────────────────────
@csrf_exempt
@require_http_methods(['GET'])
@require_api_auth('subdomains.list')
def subdomains_list(request):
    """GET /api/v2/subdomains/list/?domain=example.com"""
    domain = request.GET.get('domain')
    if not domain: return _json_error('domain required')
    ok, err = _verify_reseller_access(request.api_token, domain)
    if not ok: return err
    from control.models import subdomainname
    subs = list(subdomainname.objects.filter(domain=domain).values('subdomain', 'name', 'sslstatus', 'php'))
    return _json_success({'subdomains': subs})


@csrf_exempt
@require_http_methods(['POST'])
@require_api_auth('subdomains.create')
def subdomains_create(request):
    """POST /api/v2/subdomains/create/  Body: {domain, subdomain}"""
    try: data = json.loads(request.body)
    except: return _json_error('Invalid JSON body')
    domain    = data.get('domain')
    subdomain = data.get('subdomain')
    if not domain or not subdomain: return _json_error('domain and subdomain required')
    ok, err = _verify_reseller_access(request.api_token, domain)
    if not ok: return err
    from control.models import subdomainname
    import os
    if subdomainname.objects.filter(subdomain=subdomain, domain=domain).exists():
        return _json_error('Subdomain already exists', 409)
    full = f'{subdomain}.{domain}'
    os.system(f'sudo voidsubdomain create {full} {domain} 2>/dev/null || true')
    subdomainname.objects.create(subdomain=subdomain, name=full, domain=domain)
    return _json_success(message=f'Subdomain {full} created')


@csrf_exempt
@require_http_methods(['POST'])
@require_api_auth('subdomains.delete')
def subdomains_delete(request):
    """POST /api/v2/subdomains/delete/  Body: {domain, subdomain}"""
    try: data = json.loads(request.body)
    except: return _json_error('Invalid JSON body')
    domain    = data.get('domain')
    subdomain = data.get('subdomain')
    if not domain or not subdomain: return _json_error('domain and subdomain required')
    ok, err = _verify_reseller_access(request.api_token, domain)
    if not ok: return err
    from control.models import subdomainname
    import os
    full = f'{subdomain}.{domain}'
    os.system(f'sudo voidsubdomain del {full} 2>/dev/null || true')
    subdomainname.objects.filter(subdomain=subdomain, domain=domain).delete()
    return _json_success(message=f'Subdomain {full} deleted')


# ── FTP ───────────────────────────────────────────────────────────────────────
@csrf_exempt
@require_http_methods(['GET'])
@require_api_auth('ftp.list')
def ftp_list(request):
    """GET /api/v2/ftp/list/?domain=example.com"""
    domain = request.GET.get('domain')
    if not domain: return _json_error('domain required')
    ok, err = _verify_reseller_access(request.api_token, domain)
    if not ok: return err
    try:
        u = VUser.objects.get(domain=domain)
        from control.models import ftpaccount
        accts = list(ftpaccount.objects.filter(main=u.username).values('username', 'storage'))
        return _json_success({'ftp_accounts': accts})
    except VUser.DoesNotExist:
        return _json_error('Domain not found', 404)


@csrf_exempt
@require_http_methods(['POST'])
@require_api_auth('ftp.create')
def ftp_create(request):
    """POST /api/v2/ftp/create/  Body: {domain, username, password, storage}"""
    try: data = json.loads(request.body)
    except: return _json_error('Invalid JSON body')
    domain   = data.get('domain')
    username = data.get('username')
    password = data.get('password')
    storage  = data.get('storage', '1024')
    if not all([domain, username, password]): return _json_error('domain, username and password required')
    ok, err = _verify_reseller_access(request.api_token, domain)
    if not ok: return err
    try:
        u = VUser.objects.get(domain=domain)
        from control.models import ftpaccount
        import os
        full_user = f'{u.username}_{username}'
        os.system(f"sudo voidftp add '{full_user}' '{password}' '{storage}' 2>/dev/null || true")
        ftpaccount.objects.create(main=u.username, username=full_user, password=password, storage=storage)
        return _json_success(message=f'FTP account {full_user} created')
    except VUser.DoesNotExist:
        return _json_error('Domain not found', 404)


@csrf_exempt
@require_http_methods(['POST'])
@require_api_auth('ftp.delete')
def ftp_delete(request):
    """POST /api/v2/ftp/delete/  Body: {domain, username}"""
    try: data = json.loads(request.body)
    except: return _json_error('Invalid JSON body')
    domain   = data.get('domain')
    username = data.get('username')
    if not domain or not username: return _json_error('domain and username required')
    ok, err = _verify_reseller_access(request.api_token, domain)
    if not ok: return err
    from control.models import ftpaccount
    import os
    os.system(f"sudo voidftp del '{username}' 2>/dev/null || true")
    ftpaccount.objects.filter(username=username).delete()
    return _json_success(message=f'FTP account {username} deleted')


# ── Cron ──────────────────────────────────────────────────────────────────────
@csrf_exempt
@require_http_methods(['GET'])
@require_api_auth('cron.list')
def cron_list(request):
    """GET /api/v2/cron/list/?domain=example.com"""
    domain = request.GET.get('domain')
    if not domain: return _json_error('domain required')
    ok, err = _verify_reseller_access(request.api_token, domain)
    if not ok: return err
    from control.models import cron as CronModel
    jobs = list(CronModel.objects.filter(domain=domain).values('id', 'duratioin', 'path'))
    return _json_success({'cron_jobs': jobs})


@csrf_exempt
@require_http_methods(['POST'])
@require_api_auth('cron.create')
def cron_create(request):
    """POST /api/v2/cron/create/  Body: {domain, schedule, command}"""
    try: data = json.loads(request.body)
    except: return _json_error('Invalid JSON body')
    domain   = data.get('domain')
    schedule = data.get('schedule')
    command  = data.get('command')
    if not all([domain, schedule, command]): return _json_error('domain, schedule and command required')
    ok, err = _verify_reseller_access(request.api_token, domain)
    if not ok: return err
    from control.models import cron as CronModel
    import os
    CronModel.objects.create(domain=domain, duratioin=schedule, path=command)
    os.system(f"(crontab -u {domain.split('.')[0]} -l 2>/dev/null; echo '{schedule} {command}') | crontab -u {domain.split('.')[0]} - 2>/dev/null || true")
    return _json_success(message='Cron job created')


@csrf_exempt
@require_http_methods(['POST'])
@require_api_auth('cron.delete')
def cron_delete(request):
    """POST /api/v2/cron/delete/  Body: {domain, cron_id}"""
    try: data = json.loads(request.body)
    except: return _json_error('Invalid JSON body')
    domain  = data.get('domain')
    cron_id = data.get('cron_id')
    if not domain or not cron_id: return _json_error('domain and cron_id required')
    ok, err = _verify_reseller_access(request.api_token, domain)
    if not ok: return err
    from control.models import cron as CronModel
    CronModel.objects.filter(id=cron_id, domain=domain).delete()
    return _json_success(message='Cron job deleted')


# ── Backups ───────────────────────────────────────────────────────────────────
@csrf_exempt
@require_http_methods(['GET'])
@require_api_auth('backups.list')
def backups_list(request):
    """GET /api/v2/backups/list/?domain=example.com"""
    domain = request.GET.get('domain')
    if not domain: return _json_error('domain required')
    ok, err = _verify_reseller_access(request.api_token, domain)
    if not ok: return err
    import os, glob
    try:
        u = VUser.objects.get(domain=domain)
        backup_dir = f'/home/{u.username}/backups/'
        backups = []
        for f in sorted(glob.glob(f'{backup_dir}*.zip'), reverse=True)[:20]:
            stat = os.stat(f)
            backups.append({
                'filename': os.path.basename(f),
                'size_mb': round(stat.st_size / 1048576, 2),
                'created': stat.st_mtime,
            })
        return _json_success({'backups': backups})
    except VUser.DoesNotExist:
        return _json_error('Domain not found', 404)


@csrf_exempt
@require_http_methods(['POST'])
@require_api_auth('backups.create')
def backups_create(request):
    """POST /api/v2/backups/create/  Body: {domain}"""
    try: data = json.loads(request.body)
    except: return _json_error('Invalid JSON body')
    domain = data.get('domain')
    if not domain: return _json_error('domain required')
    ok, err = _verify_reseller_access(request.api_token, domain)
    if not ok: return err
    try:
        u = VUser.objects.get(domain=domain)
        from control.tasks import backup_user_task
        task = backup_user_task.delay(u.username, domain)
        return _json_success({'task_id': str(task.id)}, 'Backup started')
    except VUser.DoesNotExist:
        return _json_error('Domain not found', 404)
    except Exception as e:
        return _json_error(str(e))


# ── PHP ───────────────────────────────────────────────────────────────────────
@csrf_exempt
@require_http_methods(['GET'])
@require_api_auth('php.get')
def php_get(request):
    """GET /api/v2/php/get/?domain=example.com"""
    domain = request.GET.get('domain')
    if not domain: return _json_error('domain required')
    ok, err = _verify_reseller_access(request.api_token, domain)
    if not ok: return err
    try:
        dom = DomainModel.objects.get(domain=domain)
        return _json_success({'domain': domain, 'php_version': dom.php})
    except DomainModel.DoesNotExist:
        return _json_error('Domain not found', 404)


@csrf_exempt
@require_http_methods(['POST'])
@require_api_auth('php.set')
def php_set(request):
    """POST /api/v2/php/set/  Body: {domain, version}  e.g. version: '8.3'"""
    try: data = json.loads(request.body)
    except: return _json_error('Invalid JSON body')
    domain  = data.get('domain')
    version = data.get('version')
    if not domain or not version: return _json_error('domain and version required')
    ok, err = _verify_reseller_access(request.api_token, domain)
    if not ok: return err
    try:
        dom = DomainModel.objects.get(domain=domain)
        dom.php = version
        dom.save(update_fields=['php'])
        import os
        os.system(f'sudo voidphp set {domain} {version} 2>/dev/null || true')
        return _json_success(message=f'PHP version for {domain} set to {version}')
    except DomainModel.DoesNotExist:
        return _json_error('Domain not found', 404)


# ── SSL: Issue ────────────────────────────────────────────────────────────────
@csrf_exempt
@require_http_methods(['POST'])
@require_api_auth('ssl.issue')
def ssl_issue(request):
    """POST /api/v2/ssl/issue/  Body: {domain}"""
    try: data = json.loads(request.body)
    except: return _json_error('Invalid JSON body')
    domain = data.get('domain')
    if not domain: return _json_error('domain required')
    ok, err = _verify_reseller_access(request.api_token, domain)
    if not ok: return err
    import os
    os.system(f'sudo certbot --nginx -d {domain} --non-interactive --agree-tos -m admin@{domain} 2>/dev/null || true')
    return _json_success(message=f'SSL issuance started for {domain}')


# ── SSL: Download ─────────────────────────────────────────────────────────────
@csrf_exempt
@require_http_methods(['POST', 'GET'])
@require_api_auth('ssl.status')
def ssl_download(request):
    """POST/GET /api/v2/ssl/download/  Body/Params: {domain}"""
    try: data = json.loads(request.body)
    except:
        data = request.GET.dict() or request.POST.dict()
    domain = data.get('domain')
    if not domain: return _json_error('domain required')
    ok, err = _verify_reseller_access(request.api_token, domain)
    if not ok: return err
    import os
    cert_dir = f'/etc/letsencrypt/live/{domain}'
    if not os.path.exists(cert_dir):
        return _json_error('SSL certificate files do not exist on the server', 404)
    try:
        files = {}
        for fname in ('cert.pem', 'privkey.pem', 'fullchain.pem', 'chain.pem'):
            fpath = os.path.join(cert_dir, fname)
            if os.path.exists(fpath):
                with open(fpath, 'r') as f:
                    files[fname] = f.read()
            else:
                files[fname] = None
        return _json_success(data=files)
    except Exception as exc:
        return _json_error(str(exc))


# ── WordPress App Installer ───────────────────────────────────────────────────

def _wp_path(domain_name):
    """Returns the document root for a domain.
    Tries: domain.dir → user.username → /var/www/{domain}
    """
    import os as _os
    try:
        # Primary: use the 'domain' model which has a 'dir' field (system username)
        from control.models import domain as DomainModel
        d = DomainModel.objects.get(domain=domain_name)
        if d.dir:
            path = f'/home/{d.dir}/public_html'
            return path
    except Exception:
        pass
    try:
        # Secondary: use 'VUser' if it exists (newer installations)
        from control.models import VUser
        u = VUser.objects.get(domain=domain_name)
        return f'/home/{u.username}/public_html'
    except Exception:
        pass
    # Fallback
    return f'/var/www/{domain_name}'


def _wp_config_path(domain):
    return f'{_wp_path(domain)}/wp-config.php'


def _wp_is_installed(domain):
    import os
    return os.path.exists(_wp_config_path(domain))


@csrf_exempt
@require_http_methods(['GET'])
@require_api_auth('wordpress.status')
def wordpress_status(request):
    """GET /api/v2/wordpress/status/?domain=example.com"""
    domain = request.GET.get('domain')
    if not domain:
        return _json_error('domain required')
    ok, err = _verify_reseller_access(request.api_token, domain)
    if not ok:
        return err

    installed = _wp_is_installed(domain)
    if not installed:
        return _json_success({
            'domain': domain,
            'installed': False,
            'wp_admin_url': None,
            'wp_version': None,
        })

    # Try to read WP version from wp-includes/version.php
    version = 'Unknown'
    try:
        import subprocess
        result = subprocess.run(
            ['php', '-r',
             f"define('ABSPATH','{_wp_path(domain)}/');require('{_wp_path(domain)}/wp-includes/version.php');echo $wp_version;"],
            capture_output=True, text=True, timeout=8
        )
        if result.returncode == 0 and result.stdout.strip():
            version = result.stdout.strip()
    except Exception:
        pass

    # SSL status
    import os
    cert_paths = [
        f'/etc/letsencrypt/live/{domain}/fullchain.pem',
        f'/usr/local/lsws/conf/cert/{domain}/fullchain.cer',
    ]
    ssl_active = any(os.path.exists(p) for p in cert_paths)

    return _json_success({
        'domain': domain,
        'installed': True,
        'wp_admin_url': f'https://{domain}/wp-admin/' if ssl_active else f'http://{domain}/wp-admin/',
        'wp_version': version,
        'ssl_active': ssl_active,
    })


@csrf_exempt
@require_http_methods(['POST'])
@require_api_auth('wordpress.install')
def wordpress_install(request):
    """
    POST /api/v2/wordpress/install/
    Body: {domain, wp_admin_user, wp_admin_email, wp_admin_password, site_title}
    Downloads and installs WordPress in the domain's document root via WP-CLI.
    """
    try:
        data = json.loads(request.body)
    except Exception:
        return _json_error('Invalid JSON body')

    domain        = data.get('domain', '').strip()
    admin_user    = data.get('wp_admin_user', 'admin').strip()
    admin_email   = data.get('wp_admin_email', '').strip()
    admin_pass    = data.get('wp_admin_password', '').strip()
    site_title    = data.get('site_title', f'{domain} — Powered by WordPress').strip()

    if not domain or not admin_email or not admin_pass:
        return _json_error('domain, wp_admin_email, and wp_admin_password are required')

    ok, err = _verify_reseller_access(request.api_token, domain)
    if not ok:
        return err

    if _wp_is_installed(domain):
        return _json_error('WordPress is already installed for this domain', status=409)

    doc_root = _wp_path(domain)
    import os, subprocess

    # Ensure doc root exists — use sudo to handle permission issues
    if not os.path.exists(doc_root):
        result = subprocess.run(
            f'sudo mkdir -p "{doc_root}"',
            shell=True, capture_output=True, text=True
        )
        if result.returncode != 0:
            return _json_error(f'Cannot create document root: {result.stderr.strip() or doc_root}')

    # Resolve system username for this domain
    try:
        from control.models import domain as DomainModel
        d = DomainModel.objects.get(domain=domain)
        sys_user = d.dir if d.dir else 'www-data'
    except Exception:
        try:
            from control.models import VUser
            vuser = VUser.objects.get(domain=domain)
            sys_user = vuser.username
        except Exception:
            sys_user = 'www-data'

    # Sanitise sys_user for safe use in MySQL identifiers (max 16 chars for user)
    safe_user = sys_user[:10].replace('-', '_')
    db_name = f'{safe_user}_wp'
    db_user = f'{safe_user}_wp'
    db_pass = admin_pass

    site_url = f'http://{domain}'

    # ── Step 1: Create MySQL DB and user via root (before WP-CLI) ────────────
    sql = (
        f"CREATE DATABASE IF NOT EXISTS `{db_name}`; "
        f"DROP USER IF EXISTS '{db_user}'@'localhost'; "
        f"CREATE USER '{db_user}'@'localhost' IDENTIFIED BY '{db_pass}'; "
        f"GRANT ALL PRIVILEGES ON `{db_name}`.* TO '{db_user}'@'localhost'; "
        f"FLUSH PRIVILEGES;"
    )

    # Try multiple MySQL authentication methods in order
    mysql_cmds = [
        ['sudo', 'mysql', '-e', sql],
        ['mysql', '-u', 'root', '-e', sql],
        ['mysql', '--defaults-file=/root/.my.cnf', '-e', sql],
    ]
    # Also try with DB password from Django settings if available
    try:
        from django.conf import settings
        db_cfg = settings.DATABASES.get('default', {})
        if db_cfg.get('PASSWORD'):
            mysql_cmds.append(['mysql', '-u', 'root', f'-p{db_cfg["PASSWORD"]}', '-e', sql])
    except Exception:
        pass

    db_ok = False
    db_err_msg = ''
    for mcmd in mysql_cmds:
        db_result = subprocess.run(mcmd, capture_output=True, text=True, timeout=30)
        if db_result.returncode == 0:
            db_ok = True
            break
        db_err_msg = (db_result.stderr or db_result.stdout or '').strip()

    if not db_ok:
        import logging
        logging.getLogger('voidpanel').error('WP DB create failed all methods: %s', db_err_msg[:400])
        return _json_error(f'MySQL database setup failed: {db_err_msg[:200] or "Permission denied — check MySQL root access on the server"}')


    # ── Step 2: Install WP files and configure ────────────────────────────────
    wpcli_paths = ['/usr/local/bin/wp', '/usr/bin/wp', '/home/wp-cli/wp']
    wpcli = next((p for p in wpcli_paths if os.path.exists(p)), None)

    if wpcli:
        from control.script_installers import _get_wp_php
        wp_php = _get_wp_php()
        cmds = [
            f'{wp_php} {wpcli} core download --path={doc_root} --allow-root --quiet',
            (f'{wp_php} {wpcli} config create --path={doc_root} --allow-root '
             f'--dbname={db_name} --dbuser={db_user} --dbpass={db_pass} '
             f'--dbhost=localhost --quiet --force'),
            (f'{wp_php} {wpcli} core install --path={doc_root} --allow-root '
             f'--url="{site_url}" --title="{site_title}" '
             f'--admin_user="{admin_user}" --admin_email="{admin_email}" '
             f'--admin_password="{admin_pass}" --skip-email'),
        ]
        # Prepend sudo so WP-CLI runs with write access to domain directories
        cmds = ['sudo ' + c for c in cmds]
        step_names = ['core download', 'config create', 'core install']
        for step_name, cmd in zip(step_names, cmds):
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=180)
            combined = (result.stderr + result.stdout).lower()
            if result.returncode != 0 and 'already' not in combined:
                err_detail = (result.stderr or result.stdout or '').strip()[:300]
                import logging
                logging.getLogger('voidpanel').error('WP-CLI [%s] failed: %s', step_name, err_detail)
                return _json_error(f'WP install failed at [{step_name}]: {err_detail or "Unknown — check server logs"}')
    else:
        # ── Fallback: download + write wp-config.php + run PHP installer ──
        dl = subprocess.run(
            f'cd "{doc_root}" && curl -sL https://wordpress.org/latest.tar.gz | tar -xz --strip-components=1',
            shell=True, capture_output=True, timeout=180
        )
        if dl.returncode != 0:
            return _json_error('Failed to download WordPress — check server internet access')

        # Check wp-load.php exists (confirms files are extracted)
        if not os.path.exists(f'{doc_root}/wp-load.php'):
            return _json_error('WordPress files could not be extracted to the document root')

        salt      = secrets.token_hex(32)
        secret_key2  = secrets.token_hex(32)
        auth_salt = secrets.token_hex(32)
        config_content = (
            "<?php\n"
            f"define('DB_NAME', '{db_name}');\n"
            f"define('DB_USER', '{db_user}');\n"
            f"define('DB_PASSWORD', '{db_pass}');\n"
            "define('DB_HOST', 'localhost');\n"
            "define('DB_CHARSET', 'utf8mb4');\n"
            "define('DB_COLLATE', '');\n"
            f"define('AUTH_KEY', '{salt}');\n"
            f"define('SECURE_AUTH_KEY', '{secret_key2}');\n"
            f"define('AUTH_SALT', '{auth_salt}');\n"
            f"define('SECURE_AUTH_SALT', '{secrets.token_hex(32)}');\n"
            f"define('LOGGED_IN_KEY', '{secrets.token_hex(32)}');\n"
            f"define('NONCE_KEY', '{secrets.token_hex(32)}');\n"
            f"define('LOGGED_IN_SALT', '{secrets.token_hex(32)}');\n"
            f"define('NONCE_SALT', '{secrets.token_hex(32)}');\n"
            "$table_prefix = 'wp_';\n"
            "define('WP_DEBUG', false);\n"
            "define('ABSPATH', __DIR__ . '/');\n"
            "require_once ABSPATH . 'wp-settings.php';\n"
        )
        with open(f'{doc_root}/wp-config.php', 'w') as f:
            f.write(config_content)

        # ── Run WordPress database installer via PHP CLI ──────────────────
        # This is equivalent to visiting /wp-admin/install.php?step=2 in a browser
        escaped_pass  = admin_pass.replace("'", "\\'")
        escaped_title = site_title.replace("'", "\\'")
        php_install = (
            f"define('ABSPATH', '{doc_root}/'); "
            f"define('WPINC', 'wp-includes'); "
            f"$_SERVER['HTTP_HOST'] = '{domain}'; "
            f"$_SERVER['REQUEST_URI'] = '/'; "
            f"require('{doc_root}/wp-load.php'); "
            f"require('{doc_root}/wp-admin/includes/upgrade.php'); "
            f"wp_install('{escaped_title}', '{admin_user}', '{admin_email}', 1, '', '{escaped_pass}', 'en_US');"
        )
        install_r = subprocess.run(
            ['php', '-r', php_install],
            capture_output=True, text=True, timeout=60
        )
        import logging as _log
        if install_r.returncode != 0:
            _log.getLogger('voidpanel').error(
                'WP PHP-installer failed for %s: stdout=%s stderr=%s',
                domain, install_r.stdout[:300], install_r.stderr[:300]
            )
            # Non-fatal: config is written, user can visit /wp-admin/install.php manually
            # but we still return success so the status record is created
        else:
            _log.getLogger('voidpanel').info('WP PHP-installer OK for %s', domain)

    # Fix ownership
    subprocess.run(
        f'chown -R {sys_user}:{sys_user} "{doc_root}" 2>/dev/null || chown -R www-data:www-data "{doc_root}"',
        shell=True, capture_output=True
    )

    return _json_success({
        'domain': domain,
        'wp_admin_url': f'{site_url}/wp-admin/',
        'wp_admin_user': admin_user,
        'message': f'WordPress installed successfully for {domain}',
    })


@csrf_exempt
@require_http_methods(['POST'])
@require_api_auth('wordpress.uninstall')
def wordpress_uninstall(request):
    """
    POST /api/v2/wordpress/uninstall/
    Body: {domain}
    Removes WordPress files and drops the WP database.
    """
    try:
        data = json.loads(request.body)
    except Exception:
        return _json_error('Invalid JSON body')

    domain = data.get('domain', '').strip()
    if not domain:
        return _json_error('domain required')

    ok, err = _verify_reseller_access(request.api_token, domain)
    if not ok:
        return err

    if not _wp_is_installed(domain):
        return _json_error('WordPress is not installed for this domain', status=404)

    import os, subprocess
    doc_root = _wp_path(domain)

    # Read DB credentials from wp-config.php before deleting
    db_name, db_user = None, None
    try:
        with open(f'{doc_root}/wp-config.php') as f:
            cfg = f.read()
        import re
        m_name = re.search(r"define\s*\(\s*['\"]DB_NAME['\"]\s*,\s*['\"]([^'\"]+)['\"]", cfg)
        m_user = re.search(r"define\s*\(\s*['\"]DB_USER['\"]\s*,\s*['\"]([^'\"]+)['\"]", cfg)
        if m_name:
            db_name = m_name.group(1)
        if m_user:
            db_user = m_user.group(1)
    except Exception:
        pass

    # Remove WP core files (keep non-WP files)
    wp_dirs = ['wp-admin', 'wp-includes']
    wp_files = ['wp-config.php', 'wp-login.php', 'wp-cron.php', 'wp-blog-header.php',
                'wp-comments-post.php', 'wp-links-opml.php', 'wp-load.php',
                'wp-mail.php', 'wp-settings.php', 'wp-signup.php', 'wp-trackback.php',
                'xmlrpc.php', 'index.php', 'readme.html', 'license.txt']
    for d in wp_dirs:
        subprocess.run(f'rm -rf "{doc_root}/{d}"', shell=True, capture_output=True)
    for f in wp_files:
        try:
            os.remove(f'{doc_root}/{f}')
        except Exception:
            pass

    # Drop database
    if db_name:
        drop_sql = f"DROP DATABASE IF EXISTS `{db_name}`; DROP USER IF EXISTS '{db_user}'@'localhost';"
        subprocess.run(['mysql', '-u', 'root', '-e', drop_sql], capture_output=True, timeout=15)

    return _json_success(message=f'WordPress uninstalled from {domain}')


@csrf_exempt
@require_http_methods(['POST'])
@require_api_auth('wordpress.reset_password')
def wordpress_reset_password(request):
    """
    POST /api/v2/wordpress/reset-password/
    Body: {domain, new_password, wp_admin_user}
    """
    try:
        data = json.loads(request.body)
    except Exception:
        return _json_error('Invalid JSON body')

    domain    = data.get('domain', '').strip()
    new_pass  = data.get('new_password', '').strip()
    wp_user   = data.get('wp_admin_user', 'admin').strip()

    if not domain or not new_pass:
        return _json_error('domain and new_password are required')

    ok, err = _verify_reseller_access(request.api_token, domain)
    if not ok:
        return err

    if not _wp_is_installed(domain):
        return _json_error('WordPress is not installed for this domain', status=404)

    import os, subprocess
    doc_root = _wp_path(domain)

    # Use WP-CLI if available
    wpcli_paths = ['/usr/local/bin/wp', '/usr/bin/wp']
    wpcli = next((p for p in wpcli_paths if os.path.exists(p)), None)
    if wpcli:
        from control.script_installers import _get_wp_php
        wp_php = _get_wp_php()
        r = subprocess.run(
            f'sudo {wp_php} {wpcli} user update {wp_user} --user_pass="{new_pass}" --path={doc_root} --allow-root',
            shell=True, capture_output=True, text=True, timeout=30
        )
        if r.returncode == 0:
            return _json_success(message=f'WordPress admin password updated for {domain}')
        return _json_error(f'WP-CLI error: {(r.stderr or r.stdout or "").strip()[:200]}')

    # Fallback: direct DB update via wp-config credentials
    try:
        with open(f'{doc_root}/wp-config.php') as f:
            cfg = f.read()
        import re, hashlib
        m_db   = re.search(r"define\s*\(\s*['\"]DB_NAME['\"]\s*,\s*['\"]([^'\"]+)['\"]", cfg)
        m_user = re.search(r"define\s*\(\s*['\"]DB_USER['\"]\s*,\s*['\"]([^'\"]+)['\"]", cfg)
        m_pass = re.search(r"define\s*\(\s*['\"]DB_PASSWORD['\"]\s*,\s*['\"]([^'\"]+)['\"]", cfg)
        if m_db and m_user and m_pass:
            db_name = m_db.group(1)
            db_user = m_user.group(1)
            db_pass = m_pass.group(1)
            # WordPress uses phpass — use PHP to hash
            php_script = (
                f"$pw='{new_pass}';"
                "require_once '/usr/share/wordpress/wp-includes/class-phpass.php' "
                "?? require_once '{doc_root}/wp-includes/class-phpass.php';"
                "$h=new PasswordHash(8,true);echo $h->HashPassword($pw);"
            )
            # simpler: use WP's own PHP
            hash_r = subprocess.run(
                f'php -r "require(\'{doc_root}/wp-load.php\');wp_set_password(\'{new_pass}\',1);"',
                shell=True, capture_output=True, text=True, timeout=20
            )
            if hash_r.returncode == 0:
                return _json_success(message='WordPress admin password updated')
    except Exception as exc:
        return _json_error(f'Failed to update password: {exc}')

    return _json_error('Could not update password — WP-CLI not available and fallback failed')
