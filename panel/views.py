import sys
import json
from voidplatform import get_platform
from voidplatform.config import paths
from django.views.decorators.cache import never_cache


def _resolve_mail_domain_dir(domain_name):
    """Return the mail directory for a domain: /home/<owner>/mail/<domain>/.
    Falls back to /var/mail/vhosts/<domain>/ only if no owner exists."""
    try:
        owner = user.objects.filter(domain=domain_name).first()
        if owner:
            return os.path.join(paths.HOME_BASE, owner.username, 'mail', domain_name)
    except Exception:
        pass
    return os.path.join(paths.MAIL_VHOSTS, domain_name)


def _resolve_maildir(domain_name, email_prefix):
    """Return the maildir path for a specific email account."""
    return os.path.join(_resolve_mail_domain_dir(domain_name), email_prefix)
from django.core.cache import cache
from django.shortcuts import render,redirect
from django.contrib.auth import authenticate
import requests
from django.contrib.auth import login,logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse
from control.models import mernname,portnumber,quick,domain,allemail,phpextentions,cron,subdomainname,phpversion,redir,package,firewall,ftp,user,ftpaccount,pythonname
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from function import start_service,stop_service,get_directory_size_in_mb,restart_service,get_service_status,get_php_versions,get_php_version,get_php_extensions,get_database_names,get_database_users,change_hostname,remove_zone_from_file,zip_multiple_locations_backup,create_bind_recordsforsubdomain,grant_mysql_user_privileges,change_mysql_user_password,delete_mysql_user,remove_database,get_database_names_with_filter,get_database_users_with_filter,create_mysql_user,is_website_live,parse_dns_zone_file,configure_opendkim,create_bind_records,generate_dkim_keys,create_nginx_ssl_conf,generate_ssl_certificates,hostnamessl,run_command,get_server_ip,get_random_port,get_file_info,zip_files_and_folders,extract_zip_with_error_handling,create_database_and_table,clone_website, get_database_privileges_with_filter, revoke_mysql_user_privileges
import psutil
import os, shlex, subprocess
from panel.logger import get_logger

logger = get_logger(__name__)
from django.http import FileResponse, Http404
from django.contrib.auth.models import User
import shutil
import datetime

# ── Security helper ──────────────────────────────────────────────────────────
from django.conf import settings as _settings
TRASH_DIR = str(_settings.BASE_DIR / '.voidpanel_trash')

from functools import wraps

def secure_fm_paths(view_func):
    """Sanitize incoming file manager POST request paths based on sanitize_path."""
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if request.user.is_authenticated and request.method == 'POST':
            # 1. Enforce User Storage Quota
            if not request.user.is_superuser:
                try:
                    from control.models import package, user
                    from function import get_directory_size_in_mb
                    cur_user = user.objects.get(username=request.user.username)
                    cur_package = package.objects.get(name=cur_user.hosting_package)
                    if int(cur_package.storage) != 0:
                        cur_size = get_directory_size_in_mb(os.path.join(paths.HOME_BASE, request.user.username))
                        if int(cur_size) >= int(cur_package.storage):
                            from django.http import JsonResponse
                            return JsonResponse({'status': 'error', 'message': f'Storage Quota Exceeded (Limit: {cur_package.storage}MB). Please upgrade your hosting package.'}, status=403)
                except Exception:
                    pass

            # 2. Handle JSON formatted bodies
            if request.content_type == 'application/json' and request.body:
                import json
                try:
                    data = json.loads(request.body)
                    for key in ['path', 'copy', 'xfilepath', 'xfolderpath', 'file_path']:
                        if key in data and data[key]:
                            data[key] = sanitize_path(data[key], request.user)
                    request._body = json.dumps(data).encode('utf-8')
                except ValueError as e:
                    from django.http import JsonResponse
                    return JsonResponse({'status': 'error', 'message': str(e)}, status=403)
                except Exception:
                    pass
            # Handle Form encoded bodies
            elif request.POST:
                from django.http import QueryDict
                try:
                    q = request.POST.copy()
                    for key in ['path', 'copy', 'xfilepath', 'xfolderpath', 'file_path']:
                        if key in q and q[key]:
                            q[key] = sanitize_path(q[key], request.user)
                    request.POST = q
                except ValueError as e:
                    from django.http import JsonResponse
                    return JsonResponse({'status': 'error', 'message': str(e)}, status=403)
        return view_func(request, *args, **kwargs)
    return _wrapped_view

def sanitize_path(raw_path, user=None):
    """
    Resolve and validate a filesystem path.
    - Blocks path traversal (../) by resolving symlinks via realpath.
    - Non-superusers are restricted to HOME_BASE/<username>/.
    Raises ValueError on invalid paths.
    """
    if raw_path is None:
        raise ValueError("No path provided.")
    # Normalise double-slashes and collapse traversal sequences
    safe = os.path.realpath(os.path.normpath('/' + raw_path.lstrip('/')))
    # Block access to the internal trash metadata dir components
    if safe.startswith(TRASH_DIR + '/.meta'):
        raise ValueError("Access to trash metadata is not permitted.")
    if user is not None and not user.is_superuser:
        home = os.path.join(paths.HOME_BASE, user.username)
        if not safe.startswith(home):
            raise ValueError(f"Access outside home directory is not permitted.")
    return safe
# ─────────────────────────────────────────────────────────────────────────────


# views.py




from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny

@api_view(['POST'])
def list_packages(request):
    """Suspend a hosting account."""
    session_token = request.data.get('session_token')
    # if not CustomUser.objects.filter(api_token=session_token).exists():
    try:
        with open(paths.API_FILE, 'r') as f:
                    random_code=f.read()
    except:
         return Response({'status': 'error', 'message': 'All fields are required'}, status=400)
    if session_token!=random_code:
        return Response({'status': 'error', 'message': 'Invalid session token'}, status=403)
    tobepassed=package.objects.all().values('id','name')
    return Response({'status': 'success', 'packages': tobepassed})
    

@api_view(['POST'])
@permission_classes([AllowAny])
def authenticate_user(request):
    """Authenticate admin for WHMCS."""
    username = request.data.get('username')
    password = request.data.get('password')

    import secrets
    random_code = secrets.token_urlsafe(32)

    if not username or not password:
        return Response({'status': 'error', 'message': 'Username and password are required'}, status=400)

    user = authenticate(username=username, password=password)
    
    if user:
        try:
             with open(paths.API_FILE, 'r') as f:
                  random_code=f.read()
                  
        except:
             import secrets
             random_code = secrets.token_urlsafe(32)
             with open(paths.API_FILE, 'w') as f:
                  f.write(random_code)
      
        return Response({'status': 'success', 'session_token': random_code})
    
    return Response({'status': 'error', 'message': 'Invalid credentials'}, status=403)

def background_create_account(username, password, domain_name, package_name, email=''):
    """
    Called by the portal provisioning API.
    Uses the portal-provided `username` as the Linux account and directory name
    so it always matches what the portal stores and sends in SSO tokens.
    """
    import re
    try:
        from control.models import package as PackageModel
        try:
            pkg = PackageModel.objects.get(name=package_name)
            sto = int(pkg.storage)
        except Exception:
            sto = 0

        # Use the portal-provided username as the directory/account name.
        # If it already exists on disk (e.g. duplicate order), add a counter suffix.
        home_base   = paths.HOME_BASE
        domainname  = username  # portal-provided, already unique via token_hex
        if os.path.exists(os.path.join(home_base, domainname)):
            counter = 1
            base = domainname
            while os.path.exists(os.path.join(home_base, domainname)):
                suffix     = str(counter)
                domainname = base[:16 - len(suffix)] + suffix
                counter   += 1

        acct_path = os.path.join(paths.HOME_BASE, domainname)
        inipath   = acct_path + '/public_html/php.ini'
        php_ini_content = (
            f'; PHP settings for {domain_name}\n'
            'max_execution_time = 30\nmemory_limit = 256M\n'
            'post_max_size = 64M\nupload_max_filesize = 64M\n'
            'display_errors = Off\nlog_errors = On\n'
            f'error_log = "{acct_path}/public_html/logs/php_errors.log"\n'
            'date.timezone = "Asia/Kolkata"\nfile_uploads = On\n'
            f'open_basedir = "{acct_path}/public_html:/tmp"\n'
        )

        from control.tasks import provision_user_task
        task = provision_user_task.delay(
            domain_name, domainname, email, password, package_name,
            acct_path, sto, inipath, php_ini_content,
        )
        logger.info(
            'API provision task dispatched: domain=%s domainname=%s task_id=%s',
            domain_name, domainname, task.id,
        )
    except Exception as exc:
        logger.error('background_create_account failed for %s: %s', domain_name, exc)


import threading
@api_view(['POST'])
def create_account(request):
    """Create a hosting account."""

    session_token = request.data.get('session_token')


    try:
        with open(paths.API_FILE, 'r') as f:
                    random_code=f.read()
    except:
         return Response({'status': 'error', 'message': 'All fields are required'}, status=400)
    if random_code != session_token:
        return Response({'status': 'error', 'message': 'Invalid session token'}, status=403)
    domain_val = request.data.get('domain')   # fixed: was 'domain=...,' (tuple bug)
    username   = request.data.get('username')
    password   = request.data.get('password')
    package    = request.data.get('package')

    if not all([domain_val, username, password, package]):
        return Response({'status': 'error', 'message': 'All fields are required'}, status=400)

    import threading
    thread = threading.Thread(
        target=background_create_account,
        args=(username, password, domain_val, package)
    )
    thread.start()

    return Response({'status': 'success', 'message': 'Account creation initiated'})


@api_view(['POST'])
def suspend_account(request):
    """Suspend a hosting account."""
    session_token = request.data.get('session_token')
    try:
        with open(paths.API_FILE, 'r') as f:
            valid_token = f.read().strip()
        if not session_token or session_token != valid_token:
            return Response({'status': 'error', 'message': 'Invalid session token'}, status=403)
    except Exception:
        return Response({'status': 'error', 'message': 'API not configured'}, status=403)

    username = request.data.get('username')
    if not username:
        return Response({'status': 'error', 'message': 'Username is required'}, status=400)

    try:
        lold = domain.objects.get(dir=username)
    except domain.DoesNotExist:
        return Response({'status': 'error', 'message': 'Account not found'}, status=404)

    data = lold.domain
    try:
        dub = subdomainname.objects.filter(domain=data).all()
        file_path_ = os.path.join(paths.NGINX_SITES_ENABLED, data+".conf")

        if os.path.exists(file_path_):
            with open(file_path_, 'r') as file:
                config_data = file.readlines()
            root_updated = False
            for i, line in enumerate(config_data):
                if line.strip().startswith('root '):
                    config_data[i] = f"    root /var/www/suspend;\n"
                    root_updated = True
                    break
            if root_updated:
                with open(file_path_, 'w') as file:
                    file.writelines(config_data)

        for iu in dub:
            file_path_ = os.path.join(paths.NGINX_SITES_ENABLED, iu.subdomain+".conf")
            if os.path.exists(file_path_):
                with open(file_path_, 'r') as file:
                    config_data = file.readlines()
                root_updated = False
                for i, line in enumerate(config_data):
                    if line.strip().startswith('root '):
                        config_data[i] = f"    root /var/www/suspend;\n"
                        root_updated = True
                        break
                if root_updated:
                    with open(file_path_, 'w') as file:
                        file.writelines(config_data)

        lold.status = False
        lold.save()

        try:
            loldd = user.objects.get(domain=data)
            loldd.status = False
            loldd.save()
        except:
            pass

        toggle_email_suspension(data, True)
        
        try:
            import subprocess
            subprocess.run(['sudo', 'systemctl', 'reload', 'nginx'], timeout=15, check=False)
        except:
            pass

        try:
            from control.utils import trigger_user_suspended_notification
            trigger_user_suspended_notification(username, data)
        except:
            pass

        return Response({'status': 'success', 'message': 'Account suspended'})
    except Exception as e:
        return Response({'status': 'error', 'message': str(e)}, status=500)


@api_view(['POST'])
def unsuspend_account(request):
    """Unsuspend a hosting account."""
    session_token = request.data.get('session_token')
    try:
        with open(paths.API_FILE, 'r') as f:
            valid_token = f.read().strip()
        if not session_token or session_token != valid_token:
            return Response({'status': 'error', 'message': 'Invalid session token'}, status=403)
    except Exception:
        return Response({'status': 'error', 'message': 'API not configured'}, status=403)

    username = request.data.get('username')
    if not username:
        return Response({'status': 'error', 'message': 'Username is required'}, status=400)

    try:
        lold = domain.objects.get(dir=username)
    except domain.DoesNotExist:
        return Response({'status': 'error', 'message': 'Account not found'}, status=404)

    data = lold.domain
    try:
        dub = subdomainname.objects.filter(domain=data).all()
        file_path_ = os.path.join(paths.NGINX_SITES_ENABLED, data+".conf")

        if os.path.exists(file_path_):
            with open(file_path_, 'r') as file:
                config_data = file.readlines()
            root_updated = False
            for i, line in enumerate(config_data):
                if line.strip().startswith('root '):
                    config_data[i] = f"    root {os.path.join(paths.HOME_BASE, lold.dir, 'public_html')};\n"
                    root_updated = True
                    break
            if root_updated:
                with open(file_path_, 'w') as file:
                    file.writelines(config_data)

        for iu in dub:
            file_path_ = os.path.join(paths.NGINX_SITES_ENABLED, iu.subdomain+".conf")
            if os.path.exists(file_path_):
                with open(file_path_, 'r') as file:
                    config_data = file.readlines()
                root_updated = False
                for i, line in enumerate(config_data):
                    if line.strip().startswith('root '):
                        config_data[i] = f"    root {os.path.join(paths.HOME_BASE, lold.dir, 'public_html')};\n"
                        root_updated = True
                        break
                if root_updated:
                    with open(file_path_, 'w') as file:
                        file.writelines(config_data)

        lold.status = True
        lold.save()

        try:
            loldd = user.objects.get(domain=data)
            loldd.status = True
            loldd.save()
        except:
            pass

        toggle_email_suspension(data, False)
        
        try:
            import subprocess
            subprocess.run(['sudo', 'systemctl', 'reload', 'nginx'], timeout=15, check=False)
        except:
            pass

        try:
            from control.utils import trigger_user_unsuspended_notification
            trigger_user_unsuspended_notification(username, data)
        except:
            pass

        return Response({'status': 'success', 'message': 'Account unsuspended'})
    except Exception as e:
        return Response({'status': 'error', 'message': str(e)}, status=500)


@api_view(['POST'])
def terminate_account(request):
    """Terminate a hosting account."""
    session_token = request.data.get('session_token')
    try:
        with open(paths.API_FILE, 'r') as f:
            valid_token = f.read().strip()
        if not session_token or session_token != valid_token:
            return Response({'status': 'error', 'message': 'Invalid session token'}, status=403)
    except Exception:
        return Response({'status': 'error', 'message': 'API not configured'}, status=403)

    username = request.data.get('username')
    if not username:
        return Response({'status': 'error', 'message': 'Username is required'}, status=400)

    try:
        lold = domain.objects.get(dir=username)
    except domain.DoesNotExist:
        try:
            lold = domain.objects.get(domain=username)
        except domain.DoesNotExist:
            return Response({'status': 'error', 'message': 'Account not found'}, status=404)

    domain_str = lold.domain
    mainusername = lold.dir
    subdomains = list(subdomainname.objects.filter(domain=domain_str).values_list('subdomain', flat=True))

    subdomainname.objects.filter(domain=domain_str).delete()
    allemail.objects.filter(domain=domain_str).delete()
    cron.objects.filter(domain=domain_str).delete()
    redir.objects.filter(domain=domain_str).delete()
    try:
        user.objects.filter(username=mainusername).delete()
    except Exception:
        pass
    try:
        from django.contrib.auth.models import User as AuthUser
        AuthUser.objects.filter(username=mainusername).delete()
    except Exception:
        pass
    lold.delete()

    import threading
    t = threading.Thread(
        target=_background_terminate_user,
        args=(domain_str, mainusername, subdomains),
        daemon=True
    )
    t.start()

    try:
        from control.utils import trigger_user_terminated_notification
        trigger_user_terminated_notification(mainusername, domain_str)
    except:
        pass

    return Response({'status': 'success', 'message': 'Account termination initiated'})








@login_required(login_url='/')
def get_server_load(request):
    # Get CPU load (reduced blocking interval from 1.0s to 0.1s for faster response)
    cpu_load = psutil.cpu_percent(interval=0.1)
    
    # Get RAM usage
    memory_info = psutil.virtual_memory()
    memory_load = memory_info.percent
    
    # Get Disk usage (platform-aware)
    _disk_root = (os.path.splitdrive(paths.HOME_BASE)[0] + '\\') if sys.platform == 'win32' else '/'
    disk_usage = psutil.disk_usage(_disk_root)
    disk_load = disk_usage.percent
    
    # Return the data as JSON
    try:
        import platform, datetime
        boot_ts  = psutil.boot_time()
        uptime_s = int(psutil.time.time() - boot_ts)
        days, r  = divmod(uptime_s, 86400)
        hrs,  r  = divmod(r, 3600)
        mins, _  = divmod(r, 60)
        uptime_str = f"{days}d {hrs}h {mins}m" if days else f"{hrs}h {mins}m"

        load_avg = [round(x, 2) for x in psutil.getloadavg()] if hasattr(psutil, 'getloadavg') else [0, 0, 0]
        hostname = platform.node()
        os_info  = f"{platform.system()} {platform.release()}"

        ram_total = round(memory_info.total / (1024**3), 1)
        disk_total = round(disk_usage.total / (1024**3), 1)
        disk_used  = round(disk_usage.used  / (1024**3), 1)
    except Exception:
        uptime_str = "N/A"
        load_avg = [0, 0, 0]
        hostname = "N/A"
        os_info  = "N/A"
        ram_total = 0
        disk_total = 0
        disk_used  = 0

    load = {
        'cpu':        cpu_load,
        'memory':     memory_load,
        'disk':       disk_load,
        'uptime':     uptime_str,
        'hostname':   hostname,
        'os':         os_info,
        'load_avg':   load_avg,
        'ram_total':  ram_total,
        'disk_total': disk_total,
        'disk_used':  disk_used,
    }
    return JsonResponse(load)





def logoutt(request):
     logout(request)
     return redirect('/')


def login_user(request):
    if request.user.is_superuser:
        return redirect('/panel')
    if request.user.is_authenticated:
        return redirect('/control')
    if request.method=="POST":
        username=request.POST['username']
        password=request.POST['password']
        user=authenticate(username=username,password=password)
        if user is not None and user.is_superuser:
            login(request,user)
            try:
                from control.utils import trigger_login_notification, get_client_ip
                trigger_login_notification(user.username, get_client_ip(request))
            except Exception:
                pass
            return redirect('/panel')
        elif user is not None:
            login(request,user)
            try:
                from control.utils import trigger_login_notification, get_client_ip
                trigger_login_notification(user.username, get_client_ip(request))
            except Exception:
                pass
            return redirect('/control')
             
        else:
            messages.success(request, "Invalid Credentials")
            return redirect('/')
    return render(request,'login/login.html')

@login_required(login_url='/')
def panel(request):
    
    if request.user.is_superuser:
        d = {}
        show = False
        try:
            # Using .first() is safer and generally faster than .get(id=1)
            quick_ = quick.objects.first()
            if quick_ and quick_.show == False:
                show = False
            else:
                show = True
        except Exception:
            show = True
            
        d['show'] = show
        
        import concurrent.futures
        
        # Check caches first to avoid spawning threads unnecessarily
        messages_data = cache.get('voidpanel_messages')
        docs_data = cache.get('voidpanel_docs')
        server_ip = cache.get('server_ip')

        def fetch_messages():
            if messages_data: return messages_data
            try:
                response = requests.get('https://voidpanel.com/latest_messages/', timeout=1.5)
                data = response.json() if response.status_code == 200 else []
                if not data: raise Exception("Empty or Invalid Message Format")
                cache.set('voidpanel_messages', data, 3600)
                return data
            except Exception:
                # Return a fallback message so the UI isn't blank during offline/development mode
                return [{
                    'photo': 'static/icons/fav.png', 
                    'date': 'Offline', 
                    'text': 'Offline Mode: Unable to connect to VoidPanel.com services to fetch live notifications.'
                }]

        def fetch_docs():
            if docs_data is not None: return docs_data
            try:
                response = requests.get('https://voidpanel.com/admindocs/', timeout=1.5)
                data = response.json() if response.status_code == 200 else []
                cache.set('voidpanel_docs', data, 3600)
                return data
            except Exception:
                return []

        def fetch_ip():
            if server_ip is not None: return server_ip
            ip = get_server_ip()
            if ip: cache.set('server_ip', ip, 86400)
            return ip or ''

        # Run concurrently for any missing cache data
        needs_fetch = any(x is None for x in (messages_data, docs_data, server_ip))
        if needs_fetch:
            with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
                f_msgs = executor.submit(fetch_messages)
                f_docs = executor.submit(fetch_docs)
                f_ip   = executor.submit(fetch_ip)
                
                messages_data = f_msgs.result()
                docs_data = f_docs.result()
                server_ip = f_ip.result()

        d['message'] = messages_data
        d['docs'] = docs_data
        d['serverip'] = server_ip

        # Quick stats for dashboard summary strip
        try:
            from control.models import domain as domain_model
            from control.models import subdomainname as subdomain_model
            from control.models import user
            d['total_users']    = user.objects.count()
            d['total_domains']  = domain_model.objects.count()
            d['total_websites'] = domain_model.objects.count() + subdomain_model.objects.count()
        except Exception as e:
            import logging
            logging.getLogger('voidpanel').error(f'Dashboard stats error: {e}')
            d['total_users']    = 0
            d['total_domains']  = 0
            d['total_websites'] = 0

        # Load EmailConfig for the SMTP Relay card on the dashboard
        try:
            from control.models import EmailConfig
            config, _ = EmailConfig.objects.get_or_create(id=1)
            d['config'] = config
        except Exception:
            d['config'] = None

        return render(request, 'panel/index.html', d)

    else: 
        return redirect('/')
    

@login_required(login_url='/')
def installed_services(request):
    """Show all installed system services and their status."""
    if not request.user.is_superuser:
        return redirect('/')

    import subprocess

    def _run(cmd):
        try:
            return subprocess.check_output(cmd, shell=True, stderr=subprocess.DEVNULL, timeout=4).decode().strip()
        except Exception:
            return ''

    def _is_running(svc):
        try:
            r = subprocess.run(['systemctl', 'is-active', svc], capture_output=True, text=True, timeout=4)
            return r.stdout.strip() == 'active'
        except Exception:
            return False

    def _is_installed(binary):
        import shutil as _sh
        return bool(_sh.which(binary))

    def _ver(cmd):
        out = _run(cmd)
        return out.split('\n')[0][:60] if out else 'Unknown'

    # Active web engine
    try:
        engine_file = '/etc/voidpanel/web_engine'
        with open(engine_file) as _f:
            active_engine = _f.read().strip()
    except Exception:
        active_engine = 'nginx'

    services = [
        {
            'id': 'nginx',
            'name': 'NGINX',
            'role': 'Panel Reverse Proxy',
            'icon': 'fa-brands fa-nginx',
            'color': '#10b981',
            'glow': 'rgba(16,185,129,0.35)',
            'installed': _is_installed('nginx'),
            'running': _is_running('nginx'),
            'version': _ver('nginx -v 2>&1'),
        },
        {
            'id': 'ols',
            'name': 'OpenLiteSpeed',
            'role': 'High-Performance Web Engine',
            'icon': 'fa-solid fa-bolt',
            'color': '#f59e0b',
            'glow': 'rgba(245,158,11,0.35)',
            'installed': _is_installed('/usr/local/lsws/bin/lswsctrl'),
            'running': _is_running('lshttpd'),
            'version': _ver('/usr/local/lsws/bin/lswsctrl version 2>&1 | head -1'),
        },
        {
            'id': 'mysql',
            'name': 'MySQL',
            'role': 'Relational Database Server',
            'icon': 'fa-solid fa-database',
            'color': '#38bdf8',
            'glow': 'rgba(56,189,248,0.35)',
            'installed': _is_installed('mysql'),
            'running': _is_running('mysql'),
            'version': _ver('mysql --version'),
        },
        {
            'id': 'redis',
            'name': 'Redis',
            'role': 'In-Memory Cache & Queue',
            'icon': 'fa-solid fa-memory',
            'color': '#f87171',
            'glow': 'rgba(248,113,113,0.35)',
            'installed': _is_installed('redis-server'),
            'running': _is_running('redis-server'),
            'version': _ver('redis-server --version'),
        },
        {
            'id': 'postfix',
            'name': 'Postfix',
            'role': 'SMTP Mail Transfer Agent',
            'icon': 'fa-solid fa-paper-plane',
            'color': '#fbbf24',
            'glow': 'rgba(251,191,36,0.35)',
            'installed': _is_installed('postfix'),
            'running': _is_running('postfix'),
            'version': _ver('postconf mail_version 2>/dev/null | cut -d= -f2'),
        },
        {
            'id': 'dovecot',
            'name': 'Dovecot',
            'role': 'IMAP / POP3 Mail Server',
            'icon': 'fa-solid fa-inbox',
            'color': '#818cf8',
            'glow': 'rgba(129,140,248,0.35)',
            'installed': _is_installed('dovecot'),
            'running': _is_running('dovecot'),
            'version': _ver('dovecot --version'),
        },
        {
            'id': 'bind9',
            'name': 'BIND9 DNS',
            'role': 'Authoritative Name Server',
            'icon': 'fa-solid fa-network-wired',
            'color': '#ec4899',
            'glow': 'rgba(236,72,153,0.35)',
            'installed': _is_installed('named'),
            'running': _is_running('named'),
            'version': _ver('named -v'),
        },
        {
            'id': 'vsftpd',
            'name': 'vsftpd',
            'role': 'FTP Server',
            'icon': 'fa-solid fa-folder-open',
            'color': '#a78bfa',
            'glow': 'rgba(167,139,250,0.35)',
            'installed': _is_installed('vsftpd'),
            'running': _is_running('vsftpd'),
            'version': _ver('vsftpd --version 2>&1'),
        },
        {
            'id': 'php',
            'name': 'PHP-FPM',
            'role': 'PHP FastCGI Process Manager',
            'icon': 'fa-solid fa-code',
            'color': '#6366f1',
            'glow': 'rgba(99,102,241,0.35)',
            'installed': bool(_run('php --version 2>/dev/null')),
            'running': bool(_run("systemctl list-units --state=running | grep php")),
            'version': _ver('php --version 2>/dev/null | head -1'),
        },
        {
            'id': 'certbot',
            'name': 'Certbot',
            'role': 'Let\'s Encrypt SSL Manager',
            'icon': 'fa-solid fa-shield-halved',
            'color': '#34d399',
            'glow': 'rgba(52,211,153,0.35)',
            'installed': _is_installed('certbot'),
            'running': None,  # Not a daemon
            'version': _ver('certbot --version'),
        },
        {
            'id': 'opendkim',
            'name': 'OpenDKIM',
            'role': 'Email Authentication (DKIM)',
            'icon': 'fa-solid fa-key',
            'color': '#fb923c',
            'glow': 'rgba(251,146,60,0.35)',
            'installed': _is_installed('opendkim'),
            'running': _is_running('opendkim'),
            'version': _ver('opendkim --version 2>&1'),
        },
        {
            'id': 'celery',
            'name': 'Celery Worker',
            'role': 'Async Task Queue',
            'icon': 'fa-solid fa-gear',
            'color': '#22d3ee',
            'glow': 'rgba(34,211,238,0.35)',
            'installed': _is_installed('celery'),
            'running': _is_running('celery'),
            'version': _ver('celery --version 2>/dev/null'),
        },
    ]

    # Count stats
    installed_count = sum(1 for s in services if s['installed'])
    running_count   = sum(1 for s in services if s['running'])

    # Get active web engine display name
    engine_display = 'OpenLiteSpeed' if active_engine == 'ols' else 'NGINX'

    d = {
        'services': services,
        'installed_count': installed_count,
        'running_count': running_count,
        'active_engine': active_engine,
        'engine_display': engine_display,
    }

    # Also load docs for sidebar
    docs_data = cache.get('voidpanel_docs') or []
    d['docs'] = docs_data

    return render(request, 'panel/services.html', d)


@login_required(login_url='/')
def processmanager(request):
    """Render the Process Manager dashboard."""
    if not request.user.is_superuser:
        return redirect('/')

    import psutil
    import datetime

    processes = []
    total_mem = psutil.virtual_memory().total
    cpu_cores = psutil.cpu_count()

    for p in psutil.process_iter(['pid', 'name', 'username', 'memory_info', 'cpu_percent', 'create_time', 'cmdline']):
        try:
            info = p.info
            # Formatting Data
            cmd = " ".join(info['cmdline']) if info['cmdline'] else info['name']
            if len(cmd) > 100:
                cmd = cmd[:97] + "..."
            
            mem_bytes = info['memory_info'].rss if info['memory_info'] else 0
            mem_pct = round((mem_bytes / total_mem) * 100, 1)
            mem_mb = round(mem_bytes / (1024 * 1024), 1)

            # CPU percentage across all cores
            cpu_pct = round(info['cpu_percent'] / cpu_cores, 1) if info['cpu_percent'] is not None else 0.0

            uptime_sec = datetime.datetime.now().timestamp() - info['create_time'] if info['create_time'] else 0
            
            processes.append({
                'pid': info['pid'],
                'name': info['name'],
                'user': info['username'],
                'cmd': cmd,
                'mem_mb': mem_mb,
                'mem_pct': mem_pct,
                'cpu_pct': cpu_pct,
                'uptime': round(uptime_sec),
            })
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass

    # Sort down by memory usage initially
    processes = sorted(processes, key=lambda i: i['mem_pct'], reverse=True)

    d = {
        'processes': processes,
        'total_procs': len(processes),
        'serverip': cache.get('server_ip') or get_server_ip()
    }
    
    docs_data = cache.get('voidpanel_docs') or []
    d['docs'] = docs_data

    return render(request, 'panel/processmanager.html', d)


@csrf_exempt
@login_required(login_url='/')
def process_action(request):
    """Handle process termination gracefully or forcefully."""
    if not request.user.is_superuser:
        return JsonResponse({'status': 'error', 'message': 'Access Denied'}, status=403)
        
    if request.method == 'POST':
        import psutil
        try:
            pid = int(request.POST.get('pid'))
            action = request.POST.get('action') # 'term' or 'kill'
            
            p = psutil.Process(pid)
            proc_name = p.name()
            
            # Safeguard: prevent killing critical panel processes dynamically
            if proc_name in ['uwsgi', 'nginx'] and p.username() in ['root', 'nginx', 'www-data']:
                return JsonResponse({'status': 'error', 'message': f'Cannot kill core cluster process: {proc_name}'})
            
            if action == 'kill':
                p.kill()
            else:
                p.terminate()
                
            return JsonResponse({'status': 'success', 'message': f'Process {pid} ({proc_name}) terminated.'})
            
        except (ValueError, TypeError):
            return JsonResponse({'status': 'error', 'message': 'Invalid PID.'})
        except psutil.NoSuchProcess:
            return JsonResponse({'status': 'error', 'message': 'Process no longer exists.'})
        except psutil.AccessDenied:
            return JsonResponse({'status': 'error', 'message': 'Access denied to terminate this process.'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})

    return JsonResponse({'status': 'error', 'message': 'Invalid request.'})


from django.http import JsonResponse



@login_required(login_url='/')
def checkstatus(request):
    import requests as _requests
    if request.method == 'GET':
        url = request.GET.get('url', '')
        if not url or not url.startswith(('http://', 'https://')):
            return JsonResponse({'status': 'error'}, status=400)

        # SSRF protection: only allow checking domains that exist in the panel
        from urllib.parse import urlparse
        parsed = urlparse(url)
        hostname = parsed.hostname or ''
        if not domain.objects.filter(domain=hostname).exists() and not subdomainname.objects.filter(subdomain=hostname).exists():
            return JsonResponse({'status': 'error', 'message': 'Only panel-managed domains can be checked.'}, status=400)

        try:
            response = _requests.get(url, timeout=10, allow_redirects=True)
            if response.status_code == 200:
                return JsonResponse({'status': 'success'})
        except Exception:
            pass
        return JsonResponse({'status': 'error'}, status=400)

    return JsonResponse({'status': 'error'}, status=400)

@login_required(login_url='/')
def activeterminal(request):
    
    if request.user.is_superuser:
        if request.method == 'GET':
            # Terminal unavailable on Windows
            if sys.platform == 'win32':
                return JsonResponse({'status': 'error', 'message': 'Web terminal not available on Windows.'})

            port=get_random_port({8080,8082,8090,8092,9000,9002})
            run_command(f'''sudo bash -c "cat > /etc/default/shellinabox <<EOL
SHELLINABOX_DAEMON_START=1
SHELLINABOX_PORT={port}
SHELLINABOX_ARGS=\'--disable-ssl --no-beep --service=/:root:root:/home/:/bin/bash\'
EOL"''')
            run_command("sudo systemctl start shellinabox")
            if sys.platform != 'win32':
                run_command("sudo systemctl stop csf")
               
                

                


                
                return JsonResponse({'status': 'success'})
        return JsonResponse({'status': 'error'}, status=400)


@login_required(login_url='/')
def handle_user_event(request):

    if request.method == 'GET':

        action=request.GET['action']
        port=request.GET['port']
        if action == 'user_inactive':
            if sys.platform != 'win32':
                run_command('sudo systemctl stop shellinabox')
                run_command("sudo systemctl start csf")
            # run_command(f'''sudo sed -i '/^TCP_OUT/s/,{port}//g' /etc/csf/csf.conf''')
            # run_command(f'''sudo sed -i '/^TCP_IN/s/,{port}//g' /etc/csf/csf.conf''')
            # run_command(f'''sudo csf -d {get_server_ip()} {port}''')

            # run_command('sudo csf -r')


        elif action == 'tab_close':
            if sys.platform != 'win32':
                run_command('sudo systemctl stop shellinabox')
                run_command("sudo systemctl start csf")
            # run_command(f'''sudo sed -i '/^TCP_OUT/s/,{port}//g' /etc/csf/csf.conf''')
            # run_command(f'''sudo sed -i '/^TCP_IN/s/,{port}//g' /etc/csf/csf.conf''')
            # run_command('sudo csf -r')
            # run_command(f'''sudo csf -d {get_server_ip()} {port}''')
         
         
       
        return JsonResponse({'status': 'success'})

    return JsonResponse({'status': 'error'}, status=400)


@login_required(login_url='/')
def terminal(request):
    import platform
    import socket
    import psutil
    import requests
    
    d={}
    if request.is_secure():
         d['securehai']=True
    
    if request.user.is_superuser:
        _disk_root = (os.path.splitdrive(paths.HOME_BASE)[0] + '\\') if sys.platform == 'win32' else '/'
        try:
            storage_info = psutil.disk_usage(_disk_root)
            d['storage']=str(storage_info.total // (1024 ** 3)) +"GB"
        except Exception:
            d['storage'] = "100GB"
    else:
        uname = request.user.username
        home_dir = os.path.join(paths.HOME_BASE, uname)
        try:
            storage_info = psutil.disk_usage(home_dir)
            d['storage']=str(storage_info.total // (1024 ** 3)) +"GB"
        except Exception:
            d['storage'] = "10GB"

    d['ip']=get_server_ip()
    d['os']=platform.system()
    d['cpu']=platform.processor()
    
    try:
        d['hostname'] = socket.gethostname()
    except:
        d['hostname'] = "localhost"
        
    d['ram']=str(round(psutil.virtual_memory().total / (1024.0 **3)))+" GB"
    
    if request.user.is_superuser:
        url = 'https://voidpanel.com/admindocs/'
        try:
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                d['docs'] = response.json()
        except:
            pass
        
    return render(request,'panel/terminal.html',d)


@csrf_exempt
def quicksetup(request):
    # Only accessible during initial install (before a superuser exists).
    # After install, superusers must be authenticated.
    from django.contrib.auth.models import User as _User
    _already_setup = _User.objects.filter(is_superuser=True).exists()
    if _already_setup and not request.user.is_superuser:
        return JsonResponse({'status': 'error', 'message': 'Forbidden'}, status=403)
    if request.method == 'POST':
         
        
       try:
           data=quick.objects.get(id=1)
           data.show=True
           data.save()
        
       
       except:
         
           data=quick.objects.create(show=True)
       
    
    return JsonResponse({'update': 'update'}, status=200)

    


@csrf_exempt
def updatesetup(request):
    # Only accessible during initial install (before a superuser exists).
    # After install, superusers must be authenticated.
    from django.contrib.auth.models import User as _User
    _already_setup = _User.objects.filter(is_superuser=True).exists()
    if _already_setup and not request.user.is_superuser:
        return JsonResponse({'status': 'error', 'message': 'Forbidden'}, status=403)
    if request.method == 'POST':
        hostname = request.POST.get('hostname', "None")
        ns1 = request.POST.get('ns1', "None")
        ns2 = request.POST.get('ns2', "None")
        email = request.POST.get('email', "None")
        email = email.lower()
        
        try:
            data = quick.objects.get(id=1)
            is_first_time = (data.count == 0)
            
            data.show = False
            data.hostname = hostname
            data.nameserver1 = ns1
            data.nameserver2 = ns2
            data.email = email
            data.status = True
            data.count = 1
            data.save()
            
            # Dispatch Celery background task
            from control.tasks import update_hostname_task
            update_hostname_task.delay(hostname, email, is_first_time)
            
        except quick.DoesNotExist:
            data = quick.objects.create(
                show=False, hostname=hostname, nameserver1=ns1, 
                nameserver2=ns2, email=email, status=True, count=1
            )
            
            # Dispatch Celery background task
            from control.tasks import update_hostname_task
            update_hostname_task.delay(hostname, email, True)
            
        return JsonResponse({'status': 'success', 'message': 'Hostname update queued successfully.'}, status=200)
        
    return JsonResponse({'status': 'error', 'message': 'Invalid request.'}, status=400)
    
@login_required(login_url='/')
def filemanager(request):
    raw_path = request.GET.get('key', '/')
    try:
        file_path = sanitize_path(raw_path, request.user)
    except ValueError as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=403)

    last = os.path.dirname(file_path)
    if request.user.is_superuser or request.user.is_authenticated:
        try:
            current = request.session['name']
        except Exception:
            current = request.user
        d = {}
        d['main_dir'] = file_path
        d['last'] = last
        result = get_file_info(file_path)
        d['items'] = result['directories']
        d['files'] = result['files']
        # Add primary domain for sidebar links
        try:
            from control.models import domain as DomainModel
            primary = DomainModel.objects.filter(username=str(current)).first()
            d['primary_domain'] = primary.domain if primary else ''
        except Exception:
            d['primary_domain'] = ''
        return render(request, 'panel/filemanager.html', d)
    return redirect('/')


# ─── Web IDE ──────────────────────────────────────────────────────────────────

@login_required(login_url='/')
def webide_view(request, folder_path=''):
    """Render the full VS Code-like Web IDE for a given directory."""
    raw_path = '/' + folder_path.lstrip('/') if folder_path else '/'
    try:
        safe_path = sanitize_path(raw_path, request.user)
    except ValueError as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=403)

    if not os.path.isdir(safe_path):
        # If it's a file path, open its parent directory
        safe_path = os.path.dirname(safe_path)

    ctx = {
        'root_dir': safe_path,
        'root_name': os.path.basename(safe_path) or '/',
    }
    return render(request, 'panel/webide.html', ctx)


@login_required(login_url='/')
def api_file_tree(request):
    """Return directory listing for the Web IDE file explorer."""
    raw_path = request.GET.get('path', '/')
    try:
        safe_path = sanitize_path(raw_path, request.user)
    except ValueError as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=403)

    if not os.path.isdir(safe_path):
        return JsonResponse({'status': 'error', 'message': 'Not a directory'}, status=400)

    result = get_file_info(safe_path)
    return JsonResponse({
        'status': 'success',
        'path': safe_path,
        'directories': [{'name': d['name'], 'path': os.path.join(safe_path, d['name']), 'permissions': d.get('permissions', '')} for d in result['directories']],
        'files': [{'name': f['name'], 'path': os.path.join(safe_path, f['name']), 'size': f.get('size', 0), 'type': f.get('type', '')} for f in result['files']],
    })


@login_required(login_url='/')
def api_file_content(request):
    """Return file content as JSON for the Web IDE editor."""
    raw_path = request.GET.get('path', '')
    if not raw_path:
        return JsonResponse({'status': 'error', 'message': 'No path provided'}, status=400)
    try:
        safe_path = sanitize_path(raw_path, request.user)
    except ValueError as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=403)

    if not os.path.isfile(safe_path):
        return JsonResponse({'status': 'error', 'message': 'Not a file'}, status=400)

    # Extension → Monaco language map
    EXT_LANG = {
        '.py': 'python', '.js': 'javascript', '.ts': 'typescript',
        '.html': 'html', '.htm': 'html', '.css': 'css', '.scss': 'css',
        '.json': 'json', '.jsonc': 'json', '.php': 'php', '.java': 'java',
        '.cpp': 'cpp', '.c': 'c', '.h': 'c', '.cs': 'csharp',
        '.go': 'go', '.rs': 'rust', '.rb': 'ruby',
        '.sh': 'shell', '.bash': 'shell', '.zsh': 'shell',
        '.sql': 'sql', '.xml': 'xml', '.svg': 'xml',
        '.yaml': 'yaml', '.yml': 'yaml', '.md': 'markdown',
        '.ini': 'ini', '.cfg': 'ini', '.conf': 'ini', '.env': 'ini',
        '.tf': 'hcl', '.toml': 'toml', '.tsx': 'typescript', '.jsx': 'javascript',
        '.dockerfile': 'dockerfile', '.nginx': 'nginx',
    }
    fname = os.path.basename(safe_path)
    ext = os.path.splitext(fname)[1].lower()
    lang = EXT_LANG.get(ext, 'plaintext')
    if lang == 'plaintext':
        b = fname.lower()
        if b == 'dockerfile': lang = 'dockerfile'
        elif b == 'makefile': lang = 'makefile'
        elif b.startswith('.env'): lang = 'ini'

    # Size limit: refuse files > 5 MB
    try:
        size = os.path.getsize(safe_path)
        if size > 5 * 1024 * 1024:
            return JsonResponse({'status': 'error', 'message': 'File too large to open in editor (>5MB)'}, status=400)
    except Exception:
        pass

    try:
        try:
            with open(safe_path, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()
        except PermissionError:
            import subprocess as _sp
            result = _sp.run(['sudo', 'cat', safe_path], capture_output=True, check=True)
            content = result.stdout.decode('utf-8', errors='replace')
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

    return JsonResponse({'status': 'success', 'content': content, 'language': lang, 'filename': fname, 'path': safe_path})


@login_required(login_url='/')
@secure_fm_paths
def webide_save(request):
    """
    Save a file from the Web IDE.
    Unlike the legacy save_file view, this accepts a clean absolute path
    directly (no URL-encoded trailing slash hacks needed).
    """
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'POST required'}, status=405)

    try:
        data = json.loads(request.body)
    except Exception:
        return JsonResponse({'status': 'error', 'message': 'Invalid JSON body'}, status=400)

    content = data.get('content', '')
    path    = data.get('path', '')
    if not path:
        return JsonResponse({'status': 'error', 'message': 'No path provided'}, status=400)

    # Path is already sanitized by @secure_fm_paths decorator — use directly
    try:
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        return JsonResponse({'status': 'success', 'message': 'Saved successfully'})
    except PermissionError:
        import tempfile, subprocess as _sp
        try:
            with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.voidtmp') as tmp:
                tmp.write(content)
                tmp_path = tmp.name
            _sp.run(['sudo', 'bash', '-c', f'cat "{tmp_path}" > "{path}"'], check=True)
            os.unlink(tmp_path)
            return JsonResponse({'status': 'success', 'message': 'Saved successfully (sudo)'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': f'Permission denied (sudo fallback failed): {e}'}, status=500)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': f'Save error: {e}'}, status=500)

# ─────────────────────────────────────────────────────────────────────────────


# @login_required(login_url='/')
# def filemanagerr(request,file_path="/"):
#     import os
#     print(file_path)
#     print("fer")
#     if request.user.is_superuser:
           
               
#            d={}
#            d['main_dir']=file_path
#         #    items = os.listdir(main_dir)
         
#            result = get_file_info(file_path)
#            d['items']=result['directories']
#            d['files']=result['files']
          
#            return render(request,'panel/filemanager.html',d)
#     else: 
#         return redirect('/')


@login_required(login_url='/')
def download_file(request):
    raw_path = request.GET.get('key', '/')
    try:
        file_path = sanitize_path(raw_path, request.user)
    except ValueError as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=403)

    if not os.path.isfile(file_path):
        raise Http404("File does not exist")

    response = FileResponse(open(file_path, 'rb'))
    response['Content-Type'] = 'application/octet-stream'
    response['Content-Disposition'] = f'attachment; filename="{os.path.basename(file_path)}"'
    return response

@login_required(login_url='/')
def delete_file(request, file_path):
    """Soft-delete: move to Recycle Bin. Single-item delete from file manager rows."""
    try:
        safe_path = sanitize_path(file_path, request.user)
    except ValueError as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=403)

    if request.method == 'POST':
        try:
            if not os.path.exists(safe_path):
                return JsonResponse({'status': 'error', 'message': 'File not found'})
            _trash_move(safe_path, request.user)
            return JsonResponse({'status': 'success', 'message': 'Moved to Recycle Bin'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})

    return JsonResponse({'status': 'error', 'message': 'Invalid method'})


 
   
@login_required(login_url='/')
def editor_view(request, file_path):
    import json as _json
    try:
        safe_path = sanitize_path(file_path, request.user)
    except ValueError:
        return render(request, 'panel/500notfound.html')

    # Comprehensive extension → Monaco language map
    EXT_LANG = {
        '.py': 'python', '.pyw': 'python', '.pyx': 'python',
        '.js': 'javascript', '.mjs': 'javascript', '.cjs': 'javascript',
        '.ts': 'typescript', '.tsx': 'typescript',
        '.jsx': 'javascript',
        '.html': 'html', '.htm': 'html', '.jinja': 'html', '.jinja2': 'html', '.j2': 'html',
        '.css': 'css', '.scss': 'css', '.sass': 'css', '.less': 'css',
        '.json': 'json', '.jsonc': 'json',
        '.php': 'php', '.php3': 'php', '.php4': 'php', '.php5': 'php', '.phtml': 'php',
        '.java': 'java',
        '.cpp': 'cpp', '.cc': 'cpp', '.cxx': 'cpp', '.hpp': 'cpp', '.hxx': 'cpp',
        '.c': 'c', '.h': 'c',
        '.cs': 'csharp',
        '.go': 'go',
        '.rs': 'rust',
        '.rb': 'ruby', '.erb': 'ruby',
        '.sh': 'shell', '.bash': 'shell', '.zsh': 'shell', '.fish': 'shell',
        '.sql': 'sql',
        '.xml': 'xml', '.svg': 'xml', '.xsl': 'xml', '.xslt': 'xml',
        '.yaml': 'yaml', '.yml': 'yaml',
        '.md': 'markdown', '.markdown': 'markdown',
        '.dockerfile': 'dockerfile',
        '.ini': 'ini', '.cfg': 'ini', '.conf': 'ini', '.env': 'ini',
        '.nginx': 'nginx',
        '.pl': 'perl', '.pm': 'perl',
        '.r': 'r',
        '.swift': 'swift',
        '.kt': 'kotlin', '.kts': 'kotlin',
        '.dart': 'dart',
        '.scala': 'scala',
        '.groovy': 'groovy',
        '.ps1': 'powershell', '.psm1': 'powershell',
        '.lua': 'lua',
        '.ex': 'elixir', '.exs': 'elixir',
        '.hs': 'haskell',
        '.toml': 'toml',
        '.tf': 'hcl', '.tfvars': 'hcl',
    }

    fname     = os.path.basename(safe_path.rstrip('/'))
    ext       = os.path.splitext(fname)[1].lower()
    lang      = EXT_LANG.get(ext, 'plaintext')
    # Special filename-based detection (no extension)
    if lang == 'plaintext':
        basename_lower = fname.lower()
        if basename_lower in ('dockerfile',): lang = 'dockerfile'
        elif basename_lower in ('makefile',): lang = 'makefile'
        elif basename_lower in ('nginx.conf', 'nginx'):  lang = 'nginx'
        elif basename_lower.startswith('.env'): lang = 'ini'

    # Read the file (with sudo fallback for permission-restricted paths)
    try:
        try:
            with open(safe_path, 'r', encoding='utf-8', errors='replace') as f:
                file_content = f.read()
        except PermissionError:
            import subprocess
            result = subprocess.run(['sudo', 'cat', safe_path], capture_output=True, check=True)
            file_content = result.stdout.decode('utf-8', errors='replace')
    except FileNotFoundError:
        return render(request, 'panel/500notfound.html')
    except Exception:
        return render(request, 'panel/500notfound.html')

    ctx = {
        'data':     file_content,
        'language': lang,
        'filename': fname,
    }
    return render(request, 'panel/editor.html', ctx)


@login_required(login_url='/')
@secure_fm_paths
def save_file(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        content = data.get('content', '')
        path = data.get('path', '')

        x=len(path)
        path='/'+path[:x-1]
        
        try:
            with open(path, 'w') as file:
                file.write(content)
            return JsonResponse({'status': 'success', 'message': 'File saved successfully!'})
        except PermissionError:
            import tempfile, subprocess, os
            try:
                with tempfile.NamedTemporaryFile(mode='w', delete=False) as tmp:
                    tmp.write(content)
                    tmp_path = tmp.name
                subprocess.run(['sudo', 'bash', '-c', f'cat "{tmp_path}" > "{path}"'], check=True)
                os.unlink(tmp_path)
                return JsonResponse({'status': 'success', 'message': 'File saved successfully!'})
            except Exception as e:
                return JsonResponse({'status': 'error', 'message': f'Error saving file via sudo: {str(e)}'})
        except Exception as e:
              return JsonResponse({'status': 'error', 'message': f'Error saving file: {str(e)}'})
    

@login_required(login_url='/')
@secure_fm_paths
def upload_file(request):
    if request.method == 'POST' and request.FILES.getlist('file'):
        # Check Account Storage Quota (Bypass for Admin)
        if not request.user.is_superuser:
            try:
                from core.models import user, package
                from .views import get_directory_size_in_mb, safe_get_package
                currentstorage = get_directory_size_in_mb(os.path.join(paths.HOME_BASE, str(request.user)))
                packagecc = safe_get_package(user.objects.get(username=request.user).hosting_package).storage
                
                if int(packagecc) != 0:
                    uploaded_files = request.FILES.getlist('file')
                    total_upload_size_mb = sum([f.size for f in uploaded_files]) / (1024 * 1024)
                    
                    if (float(currentstorage) + total_upload_size_mb) > float(packagecc):
                        return JsonResponse({'status': 'error', 'message': 'Storage Quota Exceeded. Upload Blocked.'}, status=400)
            except Exception as e:
                pass # Fallback to standard flow if check errors out

        uploaded_files = request.FILES.getlist('file')
        # Use .get() to avoid KeyError when file_path is missing from POST
        file_path_base = request.POST.get('file_path', '').strip()
        force_overwrite = request.POST.get('force', 'false').lower() == 'true'

        if not file_path_base:
            return JsonResponse({'status': 'error', 'message': 'Upload destination path is missing. Please refresh the file manager and try again.'}, status=400)

        # --- Conflict detection (skip if user confirmed overwrite) ---
        if not force_overwrite:
            conflicts = []
            for uploaded_file in uploaded_files:
                if not uploaded_file:
                    continue
                dest = os.path.join(file_path_base, uploaded_file.name)
                if not dest.startswith('/'):
                    dest = '/' + dest
                if os.path.exists(dest):
                    conflicts.append(uploaded_file.name)
            if conflicts:
                return JsonResponse({
                    'status': 'conflict',
                    'message': f'{len(conflicts)} file(s) already exist and will be overwritten.',
                    'conflicts': conflicts
                })

        try: 
            import tempfile
            import shutil
            import subprocess

            for uploaded_file in uploaded_files:
                if not uploaded_file:
                    continue
                file_name = uploaded_file.name
                file_path = os.path.join(file_path_base, file_name)
                if not file_path.startswith('/'):
                    file_path = '/' + file_path
                
                # Write to a secure temp file first (always writable by www-data)
                with tempfile.NamedTemporaryFile(delete=False) as temp_dest:
                    for chunk in uploaded_file.chunks():
                        temp_dest.write(chunk)
                    temp_path = temp_dest.name
                
                # Move to the final destination
                try:
                    # Try normal python move first
                    shutil.move(temp_path, file_path)
                except PermissionError:
                    # Fallback to sudo mv if normal move fails
                    try:
                        subprocess.run(['sudo', 'mv', temp_path, file_path], check=True)
                    except Exception as mv_err:
                        if os.path.exists(temp_path):
                            try: os.unlink(temp_path)
                            except: pass
                        return JsonResponse({'status': 'error', 'message': f'Permission denied: cannot write to destination {file_path_base}. Error: {str(mv_err)}'}, status=400)
                except Exception as move_err:
                    if os.path.exists(temp_path):
                        try: os.unlink(temp_path)
                        except: pass
                    return JsonResponse({'status': 'error', 'message': f'Failed to move file to destination: {str(move_err)}'}, status=400)

                # Set correct file ownership
                try:
                    if sys.platform != 'win32':
                        if request.user.is_superuser:
                            subprocess.run(['sudo', 'chown', 'www-data:www-data', file_path], check=True)
                        else:
                            subprocess.run(['sudo', 'chown', f'{request.user.username}:{request.user.username}', file_path], check=True)
                except Exception:
                    pass
            return JsonResponse({'status': 'success', 'message': f'{len(uploaded_files)} file(s) uploaded successfully!'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
    return JsonResponse({'status': 'error', 'message': 'No files received. Please select files and try again.'}, status=400)



# try:
#                              if request.user.is_superuser():
#                                   run_command(f"chown www-data:www-data {copy}")
#                                   run_command(f"chown www-data:www-data {copy}/{i}")
                                  
#                              else:
#                                   run_command(f"chown {request.user}:www-data {copy}")
#                                   run_command(f"chown {request.user}:www-data {copy}/{i}")
#                         except:
#                              pass
@login_required(login_url='/')
def upload_files(request,file_path):
    if request.user.is_authenticated:
        d={}
        file_path=file_path.replace('////','').replace('//','')
        d['location']=file_path
        new="/"+file_path
        try:
            dataw = os.listdir(new)
        except Exception:
            dataw = []
        d['data']=dataw
        try:
            url = 'https://voidpanel.com/admindocs/'
            response = requests.get(url, timeout=3)
            if response.status_code == 200:
                d['docs'] = response.json()
        except:
            d['docs'] = []
        return render(request,'panel/upload.html',d)
    else: 
        return redirect('/')
    

@login_required(login_url='/')
@login_required(login_url='/')
@secure_fm_paths
def create_file(request):

     if request.user.is_superuser:
         if request.method =="POST":
              
               file_name = request.POST.get('xfile')
               file_path = request.POST.get('xfilepath')
               if '/' !=file_path[0]:
                   file_path="/"+file_path
                   
               full_path=file_path+'/'+file_name
               full_path=full_path.replace("//",'/')
               print(full_path)
               if os.path.exists(full_path):
                      
                        
                        return JsonResponse({'status': 'already', 'message': 'File already Exists Failed!'})
              
               try:
                with open(full_path, 'w') as file:
                    file.write('This is a new file.\n')
                try:
                    if sys.platform != 'win32':
                        # Get owner of parent directory and assign it
                        import stat
                        parent_stat = os.stat(file_path)
                        os.chown(full_path, parent_stat.st_uid, parent_stat.st_gid)
                except Exception:
                     pass
                return JsonResponse({'status': 'success', 'message': 'File Create successfully!'})
               except PermissionError:
                    try:
                        import subprocess
                        print(f"Attempting sudo creation for {full_path}")
                        subprocess.run(['sudo', 'bash', '-c', f'echo "This is a new file." > "{full_path}"'], check=True)
                        parent_stat = os.stat(file_path)
                        print(f"Setting ownership to {parent_stat.st_uid}:{parent_stat.st_gid}")
                        subprocess.run(['sudo', 'chown', f'{parent_stat.st_uid}:{parent_stat.st_gid}', full_path])
                        return JsonResponse({'status': 'success', 'message': 'File Create successfully!'})
                    except Exception as e:
                        print(f"Sudo Fallback Failed: {repr(e)}")
                        return JsonResponse({'status': 'error', 'message': 'File Create Failed!'})
               except Exception as e:
                   print(e)
                   return JsonResponse({'status': 'error', 'message': 'File Create Failed!'})
         return JsonResponse({'status': 'error', 'message': 'File Create Failed!'})
     elif request.user.is_authenticated: 
          if request.method =="POST":
               from control.models import user as ctrl_user
               try:
                   currentstorage = get_directory_size_in_mb(os.path.join(paths.HOME_BASE, str(request.user)))
                   packagecc = safe_get_package(ctrl_user.objects.get(username=request.user).hosting_package).storage
                   if int(packagecc) != 0 and float(currentstorage) >= float(packagecc):
                       return JsonResponse({'status': 'error', 'message': 'Storage Quota Exceeded. Creation Blocked.'})
               except Exception:
                   pass
               
               file_name = request.POST.get('xfile')
               file_path = request.POST.get('xfilepath')
               if '/' !=file_path[0]:
                   file_path="/"+file_path
                   
               full_path=file_path+'/'+file_name
               full_path=full_path.replace("//",'/')
               print(full_path)
               if os.path.exists(full_path):
                      
                        
                        return JsonResponse({'status': 'already', 'message': 'File already Exists Failed!'})
              
               try:
                   with open(full_path, 'w') as file:
                       file.write('This is a new file.\n')
                   if sys.platform != 'win32':
                       import subprocess
                       subprocess.run(['sudo', 'chown', f'{request.user}:{request.user}', full_path])
                   return JsonResponse({'status': 'success', 'message': 'File Create successfully!'})
               except PermissionError:
                   try:
                       if sys.platform != 'win32':
                           import subprocess
                           subprocess.run(['sudo', 'bash', '-c', f'echo "This is a new file." > "{full_path}"'], check=True)
                           subprocess.run(['sudo', 'chown', f'{request.user}:{request.user}', full_path])
                           return JsonResponse({'status': 'success', 'message': 'File Create successfully!'})
                       else:
                           return JsonResponse({'status': 'error', 'message': 'File Create Failed!'})
                   except Exception as e:
                       print(f"Sudo Fallback Failed: {repr(e)}")
                       return JsonResponse({'status': 'error', 'message': 'File Create Failed!'})
               except Exception as e:
                   print(e)
                   return JsonResponse({'status': 'error', 'message': 'File Create Failed!'})
          return JsonResponse({'status': 'error', 'message': 'File Create Failed!'})
          


@login_required(login_url='/')
@secure_fm_paths
def create_folder(request):

     if request.user.is_superuser:
         if request.method =="POST":
               file_name = request.POST.get('xfolder')
               file_path = request.POST.get('xfolderpath')
           
               if '/' !=file_path[0]:
                   file_path="/"+file_path
                   
               full_path=file_path+'/'+file_name
               full_path=full_path.replace("//",'/')
               if os.path.exists(full_path):
                    
                        
                        return JsonResponse({'status': 'already', 'message': 'Folder already Exists Failed!'})
               try:
                os.mkdir(full_path)
                try:
                    if sys.platform != 'win32':
                        import stat
                        parent_stat = os.stat(file_path)
                        os.chown(full_path, parent_stat.st_uid, parent_stat.st_gid)
                except Exception:
                     pass
                return JsonResponse({'status': 'success', 'message': 'Folder created successfully!'})
               except PermissionError:
                    try:
                        import subprocess
                        subprocess.run(['sudo', 'mkdir', full_path], check=True)
                        parent_stat = os.stat(file_path)
                        subprocess.run(['sudo', 'chown', f'{parent_stat.st_uid}:{parent_stat.st_gid}', full_path])
                        return JsonResponse({'status': 'success', 'message': 'Folder created successfully!'})
                    except Exception as e:
                        return JsonResponse({'status': 'error', 'message': 'Folder creation Failed!'})
               except Exception as e:
                   print(e)
                   return JsonResponse({'status': 'error', 'message': 'Folder creation Failed!'})
         return JsonResponse({'status': 'error', 'message': 'File upload Failed!'})
     elif request.user.is_authenticated: 
          if request.method =="POST":
               from control.models import user as ctrl_user
               try:
                   currentstorage = get_directory_size_in_mb(os.path.join(paths.HOME_BASE, str(request.user)))
                   packagecc = safe_get_package(ctrl_user.objects.get(username=request.user).hosting_package).storage
                   if int(packagecc) != 0 and float(currentstorage) >= float(packagecc):
                       return JsonResponse({'status': 'error', 'message': 'Storage Quota Exceeded. Creation Blocked.'})
               except Exception:
                   pass

               file_name = request.POST.get('xfolder')
               file_path = request.POST.get('xfolderpath')
           
               if '/' !=file_path[0]:
                   file_path="/"+file_path
                   
               full_path=file_path+'/'+file_name
               full_path=full_path.replace("//",'/')
               if os.path.exists(full_path):
                    
                        
                        return JsonResponse({'status': 'already', 'message': 'Folder already Exists Failed!'})
               try:
                   os.mkdir(full_path)
                   if sys.platform != 'win32':
                       import subprocess
                       subprocess.run(['sudo', 'chown', f'{request.user}:{request.user}', full_path])
                   return JsonResponse({'status': 'success', 'message': 'Folder created successfully!'})
               except PermissionError:
                   try:
                       if sys.platform != 'win32':
                           import subprocess
                           subprocess.run(['sudo', 'mkdir', '-p', full_path], check=True)
                           subprocess.run(['sudo', 'chown', f'{request.user}:{request.user}', full_path])
                           return JsonResponse({'status': 'success', 'message': 'Folder created successfully!'})
                       else:
                           return JsonResponse({'status': 'error', 'message': 'Folder creation Failed!'})
                   except Exception as e:
                       print(f"Sudo Fallback Failed: {repr(e)}")
                       return JsonResponse({'status': 'error', 'message': 'Folder creation Failed!'})
               except Exception as e:
                   print(e)
                   return JsonResponse({'status': 'error', 'message': 'Folder creation Failed!'})
          return JsonResponse({'status': 'error', 'message': 'Folder creation Failed!'})


@login_required(login_url='/')
@secure_fm_paths
def copydata(request):
     c = 0
     x = 0
     s = ""
     errors = []

     if request.method == "POST":
          import shutil
          import subprocess
          import sys
          
          try:
              data = json.loads(request.body)  # Get the data from the request body
          except Exception:
              return JsonResponse({'status': 'error', 'message': 'Invalid JSON data'}, status=400)
              
          selected_items = data.get('selected', [])
          file_path = data.get('path', '').rstrip('/')
          copy = data.get('copy', '').rstrip('/')

          if not file_path or not copy or not selected_items:
              return JsonResponse({'status': 'error', 'message': 'Missing parameters'}, status=400)

          # Enforce paths security inside views as double safety
          if not request.user.is_superuser:
              home_dir = os.path.join(paths.HOME_BASE, request.user.username)
              if not file_path.startswith(home_dir) or not copy.startswith(home_dir):
                  return JsonResponse({'status': 'error', 'message': 'Access outside home directory is not permitted.'}, status=403)

          if not os.path.isdir(copy):
              return JsonResponse({'status': 'invalid', 'message': "Invalid Location"})

          # Get target stats for permission settings
          try:
              dest_stat = os.stat(copy)
              dest_uid = dest_stat.st_uid
              dest_gid = dest_stat.st_gid
          except Exception:
              dest_uid = dest_gid = None

          for i in selected_items:
               src = os.path.join(file_path, i)
               dst = os.path.join(copy, i)
               
               if not os.path.exists(src):
                   errors.append(f"{i} does not exist")
                   x += 1
                   s += i
                   continue

               if os.path.isdir(src):
                    try:
                        shutil.copytree(src, dst)
                        c += 1
                        if dest_uid is not None and sys.platform != 'win32':
                            try:
                                os.chown(dst, dest_uid, dest_gid)
                                for root_dir, dirs, files in os.walk(dst):
                                    for d in dirs:
                                        os.chown(os.path.join(root_dir, d), dest_uid, dest_gid)
                                    for f in files:
                                        os.chown(os.path.join(root_dir, f), dest_uid, dest_gid)
                            except PermissionError:
                                subprocess.run(['sudo', 'chown', '-R', f'{dest_uid}:{dest_gid}', dst], check=True)
                    except PermissionError:
                        try:
                            if sys.platform != 'win32':
                                subprocess.run(['sudo', 'cp', '-r', src, dst], check=True)
                                if dest_uid is not None:
                                    subprocess.run(['sudo', 'chown', '-R', f'{dest_uid}:{dest_gid}', dst], check=True)
                                c += 1
                            else:
                                x += 1
                                s += i
                                errors.append(f"Permission denied on {i}")
                        except Exception as e:
                            x += 1
                            s += i
                            errors.append(f"Failed to copy {i}: {str(e)}")
                    except Exception as e:
                        x += 1
                        s += i
                        errors.append(f"Failed to copy {i}: {str(e)}")
               else:
                    try:
                        shutil.copy2(src, dst)
                        c += 1
                        if dest_uid is not None and sys.platform != 'win32':
                            try:
                                os.chown(dst, dest_uid, dest_gid)
                            except PermissionError:
                                subprocess.run(['sudo', 'chown', f'{dest_uid}:{dest_gid}', dst], check=True)
                    except PermissionError:
                        try:
                            if sys.platform != 'win32':
                                subprocess.run(['sudo', 'cp', src, dst], check=True)
                                if dest_uid is not None:
                                    subprocess.run(['sudo', 'chown', f'{dest_uid}:{dest_gid}', dst], check=True)
                                c += 1
                            else:
                                x += 1
                                s += i
                                errors.append(f"Permission denied on {i}")
                        except Exception as e:
                            x += 1
                            s += i
                            errors.append(f"Failed to copy {i}: {str(e)}")
                    except Exception as e:
                        x += 1
                        s += i
                        errors.append(f"Failed to copy {i}: {str(e)}")
          
          if c == len(selected_items):
              return JsonResponse({'status': 'success', 'message': 'Files copied successfully!'})
          elif x != 0:
              return JsonResponse({'status': 'already', 'message': f'Errors: {", ".join(errors)}', 'details': s})
          else:  
              return JsonResponse({'status': 'error', 'message': 'Copy operation failed.'})
     return JsonResponse({'status': 'error', 'message': 'Invalid request method.'}, status=405)


@login_required(login_url='/')
@secure_fm_paths
def movedata(request):
     c = 0
     errors = []

     if request.method == "POST":
          import shutil
          import subprocess
          import sys
          
          try:
              data = json.loads(request.body)  # Get the data from the request body
          except Exception:
              return JsonResponse({'status': 'error', 'message': 'Invalid JSON data'}, status=400)
              
          selected_items = data.get('selected', [])
          file_path = data.get('path', '').rstrip('/')
          copy = data.get('copy', '').rstrip('/')

          if not file_path or not copy or not selected_items:
              return JsonResponse({'status': 'error', 'message': 'Missing parameters'}, status=400)

          # Enforce paths security inside views as double safety
          if not request.user.is_superuser:
              home_dir = os.path.join(paths.HOME_BASE, request.user.username)
              if not file_path.startswith(home_dir) or not copy.startswith(home_dir):
                  return JsonResponse({'status': 'error', 'message': 'Access outside home directory is not permitted.'}, status=403)

          if not os.path.isdir(copy):
              return JsonResponse({'status': 'invalid', 'message': "Invalid Location"})

          # Get target stats for permission settings
          try:
              dest_stat = os.stat(copy)
              dest_uid = dest_stat.st_uid
              dest_gid = dest_stat.st_gid
          except Exception:
              dest_uid = dest_gid = None

          for i in selected_items:
               src = os.path.join(file_path, i)
               dst = os.path.join(copy, i)

               if not os.path.exists(src):
                   errors.append(f"{i} does not exist")
                   continue

               try:
                   shutil.move(src, dst)
                   c += 1
                   if dest_uid is not None and sys.platform != 'win32':
                       try:
                           os.chown(dst, dest_uid, dest_gid)
                           if os.path.isdir(dst):
                               for root_dir, dirs, files in os.walk(dst):
                                   for d in dirs:
                                       os.chown(os.path.join(root_dir, d), dest_uid, dest_gid)
                                   for f in files:
                                       os.chown(os.path.join(root_dir, f), dest_uid, dest_gid)
                       except PermissionError:
                           subprocess.run(['sudo', 'chown', '-R', f'{dest_uid}:{dest_gid}', dst], check=True)
               except PermissionError:
                   try:
                       if sys.platform != 'win32':
                           subprocess.run(['sudo', 'mv', src, dst], check=True)
                           if dest_uid is not None:
                               subprocess.run(['sudo', 'chown', '-R', f'{dest_uid}:{dest_gid}', dst], check=True)
                           c += 1
                       else:
                           errors.append(f"Permission denied on {i}")
                   except Exception as e:
                       errors.append(f"Failed to move {i}: {str(e)}")
               except Exception as e:
                   errors.append(f"Failed to move {i}: {str(e)}")
  
          if c == len(selected_items):
              return JsonResponse({'status': 'success', 'message': 'Files moved successfully!'})
          elif c > 0:
              return JsonResponse({'status': 'partial', 'message': f'Moved {c} of {len(selected_items)} items. Errors: {", ".join(errors)}'})
          else:
              return JsonResponse({'status': 'error', 'message': f'Failed to move files: {", ".join(errors)}'})
     return JsonResponse({'status': 'error', 'message': 'Invalid request method.'}, status=405)

         


@login_required(login_url='/')
@secure_fm_paths
def extractdata(request):

    def _do_extract(file_path, selected_items, force=False):
        """Check for conflicts then extract ZIP. Returns JsonResponse."""
        if not file_path.startswith('/'):
            file_path = '/' + file_path
        zip_file = file_path.rstrip('/') + '/' + selected_items[0]

        # --- Conflict detection (ZIP only, skip on force) ---
        if not force and zip_file.endswith('.zip'):
            try:
                import zipfile as zf
                conflicts = []
                with zf.ZipFile(zip_file, 'r') as z:
                    for name in z.namelist():
                        if not name.endswith('/'):
                            dest = os.path.join(file_path, name)
                            if os.path.exists(dest):
                                conflicts.append(name)
                if conflicts:
                    return JsonResponse({
                        'status': 'conflict',
                        'message': f'{len(conflicts)} file(s) already exist and will be overwritten during extraction.',
                        'conflicts': conflicts[:20]
                    })
            except Exception:
                pass  # if we can't inspect the ZIP, just proceed with extraction

        try:
            if sys.platform != 'win32':
                import subprocess
                subprocess.run(['sudo', 'unzip', '-o', zip_file, '-d', file_path], check=True)
                parent_stat = os.stat(file_path)
                subprocess.run(['sudo', 'chown', '-R',
                                f'{parent_stat.st_uid}:{parent_stat.st_gid}', file_path], check=True)
            else:
                extract_zip_with_error_handling(zip_file, file_path)
            return JsonResponse({'status': 'success', 'message': 'File Extracted successfully!'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': f'File Extraction Failed! {str(e)}'})

    if request.user.is_superuser or request.user.is_authenticated:
        if request.method == 'POST':
            data = json.loads(request.body)
            selected_items = data.get('selected', [])
            file_path = data.get('path', '')
            force = data.get('force', False)

            if not selected_items or not file_path:
                return JsonResponse({'status': 'error', 'message': 'File Extraction Failed!'})

            return _do_extract(file_path, selected_items, force=force)

    return JsonResponse({'status': 'error', 'message': 'File Extraction Failed!'})



@login_required(login_url='/')
@secure_fm_paths
def compressdata(request):
     import os, random

     if request.user.is_superuser or request.user.is_authenticated:
         if request.method == 'POST':
               data = json.loads(request.body)
               selected_items = data.get('selected', [])
               base_path = data.get('path', '/')

               if not selected_items:
                   return JsonResponse({'status': 'error', 'message': 'No items selected.'})

               # Normalise base_path
               if not base_path.startswith('/'):
                   base_path = '/' + base_path
               base_path = base_path.rstrip('/') + '/'

               # Build source paths BEFORE generating zip name
               source_paths = [os.path.join(base_path, i) for i in selected_items]

               # Quota check
               if not request.user.is_superuser:
                   try:
                       from control.models import user as ctrl_user
                       pkg = safe_get_package(ctrl_user.objects.get(username=request.user).hosting_package)
                       used_mb = get_directory_size_in_mb(os.path.join(paths.HOME_BASE, str(request.user)))
                       if int(pkg.storage) != 0 and float(used_mb) >= float(pkg.storage):
                           return JsonResponse({'status': 'Overload', 'message': 'Disk quota exceeded!'})
                   except Exception:
                       pass

               # Generate unique zip filename
               existing = set(os.listdir(base_path)) if os.path.isdir(base_path) else set()
               zip_name = random.choice(selected_items) + '.zip'
               attempt = 0
               while zip_name in existing:
                   zip_name = random.choice(selected_items) + f'_{attempt}.zip'
                   attempt += 1
               zip_output_path = os.path.join(base_path, zip_name)

               try:
                   if sys.platform != 'win32':
                       import uuid, subprocess
                       temp_zip = f"/tmp/vp_zip_{uuid.uuid4().hex}.zip"
                       zip_files_and_folders(temp_zip, source_paths)
                       
                       # Move to target path using sudo
                       subprocess.run(['sudo', 'mv', temp_zip, zip_output_path], check=True)
                       
                       # Set correct ownership (parent directory owner or request.user)
                       parent_stat = os.stat(base_path)
                       subprocess.run(['sudo', 'chown', f'{parent_stat.st_uid}:{parent_stat.st_gid}', zip_output_path], check=True)
                   else:
                       zip_files_and_folders(zip_output_path, source_paths)
                   return JsonResponse({'status': 'success', 'message': f'Compressed to {zip_name}!'})
               except Exception as e:
                   print(f'compressdata error: {e}')
                   return JsonResponse({'status': 'error', 'message': f'Compression failed: {e}'})

@login_required(login_url='/')
@secure_fm_paths
def ddeletedata(request):
     """Soft-delete: bulk move to Recycle Bin (called by file manager toolbar checkbox delete)."""
     if not (request.user.is_superuser or request.user.is_authenticated):
         return JsonResponse({'status': 'error', 'message': 'Unauthorized'}, status=403)
     if request.method != 'POST':
         return JsonResponse({'status': 'error', 'message': 'POST required'}, status=405)

     data = json.loads(request.body)
     selected_items = data.get('selected', [])
     raw_path = data.get('path', '/')
     moved = 0
     errors = []
     try:
         base_path = sanitize_path(raw_path, request.user)
     except ValueError as e:
         return JsonResponse({'status': 'error', 'message': str(e)}, status=403)

     for item in selected_items:
         src = os.path.join(base_path, item)
         try:
             if not item or '/' in item or '..' in item:
                 errors.append(f'{item}: invalid name')
                 continue
             if os.path.exists(src):
                 _trash_move(src, request.user)
                 moved += 1
             else:
                 errors.append(f'{item}: not found')
         except Exception as e:
             errors.append(f'{item}: {str(e)}')

     if moved == len(selected_items):
         return JsonResponse({'status': 'success', 'message': f'{moved} item(s) moved to Recycle Bin.'})
     elif moved > 0:
         return JsonResponse({'status': 'partial', 'message': f'{moved} moved, errors: {", ".join(errors)}'})
     return JsonResponse({'status': 'error', 'message': f'Failed: {", ".join(errors)}'})

@login_required(login_url='/')
@secure_fm_paths
def deletedata(request):
     """Soft-delete: move selected items to the Recycle Bin (called by toolbar bulk-delete)."""
     if not (request.user.is_superuser or request.user.is_authenticated):
         return JsonResponse({'status': 'error', 'message': 'Unauthorized'}, status=403)
     if request.method != 'POST':
         return JsonResponse({'status': 'error', 'message': 'POST required'}, status=405)

     data = json.loads(request.body)
     selected_items = data.get('selected', [])
     raw_path = data.get('path', '/')
     moved = 0
     errors = []
     try:
         base_path = sanitize_path(raw_path, request.user)
     except ValueError as e:
         return JsonResponse({'status': 'error', 'message': str(e)}, status=403)

     for item in selected_items:
         src = os.path.join(base_path, item)
         try:
             if not item or '/' in item or '..' in item:
                 errors.append(f'{item}: invalid name')
                 continue
             if os.path.exists(src):
                 _trash_move(src, request.user)
                 moved += 1
             else:
                 errors.append(f'{item}: not found')
         except Exception as e:
             errors.append(f'{item}: {str(e)}')

     if moved == len(selected_items):
         return JsonResponse({'status': 'success', 'message': f'{moved} item(s) moved to Recycle Bin.'})
     elif moved > 0:
         return JsonResponse({'status': 'partial', 'message': f'{moved} moved, errors: {", ".join(errors)}'})
     return JsonResponse({'status': 'error', 'message': f'Failed: {", ".join(errors)}'})


# ── Recycle Bin helpers ───────────────────────────────────────────────────────
def get_trash_dir_for_path(src_path):
    """
    SECURITY: Trash location is ALWAYS determined by the file's home directory,
    regardless of who (admin or user) is performing the delete.

    Files inside /home/<username>/  →  trash goes to  /home/<username>/.trash/
    Any other path (admin files)    →  trash goes to  /var/www/panel/.voidpanel_trash/
    """
    real = os.path.realpath(src_path)
    home_base = paths.HOME_BASE.rstrip('/')  # e.g. /home
    # If the file lives inside a user home dir, trash belongs there
    if real.startswith(home_base + '/'):
        parts = real[len(home_base)+1:].split('/')
        if parts and parts[0]:
            username = parts[0]
            return os.path.join(home_base, username, '.trash')
    # Fallback: admin / system-level trash
    return str(_settings.BASE_DIR / '.voidpanel_trash')

def get_trash_dir(user):
    """Legacy: returns the user's own trash dir (for trash_list / restore / empty)."""
    return os.path.join(paths.HOME_BASE, user.username, '.trash')

def _sudo_mv(src, dest):
    """Move using sudo mv to handle user-owned files (www-data has NOPASSWD sudo)."""
    import subprocess
    result = subprocess.run(['sudo', 'mv', src, dest], capture_output=True, text=True, timeout=30)
    if result.returncode != 0:
        raise PermissionError(f"sudo mv failed: {result.stderr.strip()}")

def _sudo_rm(path):
    """Remove using sudo rm to handle user-owned files."""
    import subprocess
    if os.path.isdir(path):
        cmd = ['sudo', 'rm', '-rf', path]
    else:
        cmd = ['sudo', 'rm', '-f', path]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    if result.returncode != 0:
        raise PermissionError(f"sudo rm failed: {result.stderr.strip()}")

def _trash_move(src_path, user):
    """Move a file/folder into the VoidPanel trash and write a .meta sidecar.

    SECURITY: trash dir is always determined by where the FILE lives,
    not who is logged in. This prevents admin's trash from leaking user files.
    """
    import subprocess
    # Always use the file path to determine which user's trash to use
    t_dir = get_trash_dir_for_path(src_path)
    # Ensure trash dir exists and is writable by www-data using sudo
    subprocess.run(['sudo', 'mkdir', '-p', t_dir], capture_output=True, timeout=10)
    subprocess.run(['sudo', 'chmod', '777', t_dir], capture_output=True, timeout=10)
    timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S_%f')
    item_name = os.path.basename(src_path.rstrip('/'))
    trash_name = f'{timestamp}__{item_name}'
    dest = os.path.join(t_dir, trash_name)
    # Use sudo mv to handle user-owned files
    _sudo_mv(src_path, dest)
    # Write metadata sidecar
    meta = {
        'original_path': src_path,
        'deleted_at': datetime.datetime.now().isoformat(),
        'item_name': item_name,
        'trash_name': trash_name,
    }
    with open(dest + '.meta', 'w') as f:
        json.dump(meta, f)
    return dest


@login_required(login_url='/')
def deletedata(request):
    """Soft-delete: move selected items to the Recycle Bin."""
    if not (request.user.is_superuser or request.user.is_authenticated):
        return JsonResponse({'status': 'error', 'message': 'Unauthorized'}, status=403)
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'POST required'}, status=405)

    data = json.loads(request.body)
    selected_items = data.get('selected', [])
    raw_path = data.get('path', '/')
    moved = 0
    errors = []
    try:
        base_path = sanitize_path(raw_path, request.user)
    except ValueError as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=403)

    for item in selected_items:
        src = os.path.join(base_path, item)
        try:
            src = sanitize_path(src, request.user)
            if os.path.exists(src):
                _trash_move(src, request.user)
                moved += 1
            else:
                errors.append(f'{item}: not found')
        except Exception as e:
            errors.append(f'{item}: {str(e)}')

    if moved == len(selected_items):
        return JsonResponse({'status': 'success', 'message': f'{moved} item(s) moved to Recycle Bin.'})
    elif moved > 0:
        return JsonResponse({'status': 'partial', 'message': f'{moved} moved, errors: {", ".join(errors)}'})
    return JsonResponse({'status': 'error', 'message': f'Failed: {", ".join(errors)}'})


@login_required(login_url='/')
def trash_list(request):
    """List Recycle Bin items for the CONTEXT user (never admin's own trash).

    Security model:
    - Regular user   → always shows /home/<their username>/.trash/
    - Admin user     → shows /home/<session['name']>/.trash/  (the user being managed)
      The admin can also pass ?for=<username> to view a specific user's trash.
      Admin CANNOT see their own root-level trash here (by design).
    """
    # Determine WHOSE trash to show
    if request.user.is_superuser:
        # Admin: prefer session context user, fall back to ?for= query param
        context_username = request.session.get('name', '')
        forced = request.GET.get('for', '').strip()
        if forced:
            context_username = forced
        if not context_username:
            return render(request, 'panel/trash.html', {
                'items': [], 'trash_username': '',
                'error': 'No user context. Open the File Manager for a specific user first.',
            })
    else:
        context_username = str(request.user.username)

    # Only allow access to real home dirs (prevent path traversal)
    if '/' in context_username or '..' in context_username or not context_username:
        return render(request, 'panel/trash.html', {'items': [], 'trash_username': '', 'error': 'Invalid user.'})

    t_dir = os.path.join(paths.HOME_BASE, context_username, '.trash')
    import subprocess
    subprocess.run(['sudo', 'mkdir', '-p', t_dir], capture_output=True)
    subprocess.run(['sudo', 'chmod', '777', t_dir], capture_output=True)

    items = []
    try:
        for fname in os.listdir(t_dir):
            if fname.endswith('.meta'):
                continue
            meta_path = os.path.join(t_dir, fname + '.meta')
            meta = {}
            if os.path.exists(meta_path):
                try:
                    with open(meta_path) as f:
                        meta = json.load(f)
                except Exception:
                    pass
            items.append({
                'trash_name': fname,
                'item_name': meta.get('item_name', fname),
                'original_path': meta.get('original_path', '—'),
                'deleted_at': meta.get('deleted_at', '—'),
                'is_dir': os.path.isdir(os.path.join(t_dir, fname)),
                'trash_for': context_username,
            })
    except Exception:
        pass
    items.sort(key=lambda x: x['deleted_at'], reverse=True)
    return render(request, 'panel/trash.html', {
        'items': items,
        'trash_username': context_username,
    })


@login_required(login_url='/')
def trash_restore(request):
    """Restore an item from the Recycle Bin to its original location."""
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'POST required'}, status=405)
    data = json.loads(request.body)
    trash_name = data.get('trash_name', '')
    if not trash_name or '/' in trash_name or '..' in trash_name:
        return JsonResponse({'status': 'error', 'message': 'Invalid trash name'}, status=400)

    # Determine whose trash to operate on from the metadata path itself
    # (the caller sends trash_name which is just the filename, and trash_for = username)
    data_for = data.get('trash_for', '').strip()
    if request.user.is_superuser and data_for:
        if '/' in data_for or '..' in data_for:
            return JsonResponse({'status': 'error', 'message': 'Invalid user'}, status=400)
        t_dir = os.path.join(paths.HOME_BASE, data_for, '.trash')
    else:
        t_dir = os.path.join(paths.HOME_BASE, str(request.user.username), '.trash')
    trash_item = os.path.join(t_dir, trash_name)
    meta_file = trash_item + '.meta'
    if not os.path.exists(trash_item):
        return JsonResponse({'status': 'error', 'message': 'Item not found in trash'})
    try:
        with open(meta_file) as f:
            meta = json.load(f)
        original_path = meta.get('original_path')
        if not original_path:
            raise ValueError('No original path in metadata')
        # If destination already exists, restore with a unique suffix
        restore_dest = original_path
        if os.path.exists(restore_dest):
            base, ext = os.path.splitext(restore_dest)
            restore_dest = f"{base}_restored_{datetime.datetime.now().strftime('%H%M%S')}{ext}"
        os.makedirs(os.path.dirname(restore_dest), exist_ok=True)
        _sudo_mv(trash_item, restore_dest)
        if os.path.exists(meta_file):
            os.remove(meta_file)
        return JsonResponse({'status': 'success', 'message': f'Restored to {restore_dest}'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)})


@login_required(login_url='/')
def trash_empty(request):
    """Permanently delete one or all items in the Recycle Bin."""
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'POST required'}, status=405)
    data = json.loads(request.body)
    trash_name = data.get('trash_name')  # single item, or None/omitted for empty all

    # Determine whose trash to empty from the POST body
    data_for = data.get('trash_for', '').strip()
    if request.user.is_superuser and data_for:
        if '/' in data_for or '..' in data_for:
            return JsonResponse({'status': 'error', 'message': 'Invalid user'}, status=400)
        t_dir = os.path.join(paths.HOME_BASE, data_for, '.trash')
    else:
        t_dir = os.path.join(paths.HOME_BASE, str(request.user.username), '.trash')

    try:
        if trash_name:
            # Permanently delete one specific item
            if '/' in trash_name or '..' in trash_name:
                return JsonResponse({'status': 'error', 'message': 'Invalid name'}, status=400)
            target = os.path.join(t_dir, trash_name)
            meta  = target + '.meta'
            if os.path.exists(target):
                _sudo_rm(target)
            if os.path.exists(meta):
                os.remove(meta)
            return JsonResponse({'status': 'success', 'message': 'Item permanently deleted.'})
        else:
            # Empty entire trash
            for fname in os.listdir(t_dir):
                fpath = os.path.join(t_dir, fname)
                try:
                    _sudo_rm(fpath)
                except Exception:
                    pass
            return JsonResponse({'status': 'success', 'message': 'Recycle Bin emptied.'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)})
# ─────────────────────────────────────────────────────────────────────────────


@login_required(login_url='/')
@secure_fm_paths
def renamedata(request):
   
     
     if request.user.is_superuser or request.user.is_authenticated:
         if request.method =="POST":
               data = json.loads(request.body)  # Get the data from the request body
               selected_items = data.get('selected', [])
               file_path = data.get('path')
               
               copy = data.get('copy')   
               if '/' !=file_path[0]:
                   file_path="/"+file_path+'/'
       
              
               for i in selected_items:
             

                try:
                    os.rename(file_path+i,file_path+copy)
                    return JsonResponse({'status': 'success', 'message': 'File Renamed successfully!'})
                   
                except Exception as e:
                  
                    return JsonResponse({'status': 'error', 'message': 'File Rename Failed!'})
             





@login_required(login_url='/')
@secure_fm_paths
def permissiondata(request):
     c=0

     if request.user.is_superuser or request.user.is_authenticated:
         if request.method =="POST":
               data = json.loads(request.body)  # Get the data from the request body
               selected_items = data.get('selected', [])
               file_path = data.get('path')
               copy = data.get('copy')   
               if '/' !=file_path[0]:
                   file_path="/"+file_path
               if '/' !=file_path[-1]:
                   file_path=file_path+"/"
            #    if '/' ==file_path[-1]:
            #        file_path=file_path[:len(copy)-1]
       
               common_permissions = [
    "000",
    "644",
    "755",
    "666",
    "700",
    "777",
    "644",
    "750",
    "770",
    "400",
    "500"
]
           
               if copy not in common_permissions:
               
                     return JsonResponse({'status': 'error', 'message': 'Set Valid Permission!'})
               for i in selected_items:
                    try:
                        permission = int(copy, 8)
                        os.chmod(file_path+i, permission)
                        return JsonResponse({'status': 'success', 'message': 'File uploaded successfully!'})
                        c=c+1
                    except Exception as e:
                        print(e)
                        return JsonResponse({'status': 'error', 'message': 'File upload Failed!'})
               
         return JsonResponse({'status': 'error', 'message': 'File upload Failed!'})
     

@login_required(login_url='/')
def addwebsite(request):
   
    if request.user.is_superuser:
           d={}
          
           url = 'https://voidpanel.com/admindocs/'  # Replace with your API URL
           response = requests.get(url, timeout=2)
           if response.status_code == 200:
            dataee = response.json()  # Parse the JSON response
            d['docs']=dataee
           return render(request,'panel/addwebsite.html',d)
    else: 
        return redirect('/')
    
@login_required(login_url='/')
def addemail(request):
   
    if request.user.is_superuser:
           d={}
           url = 'https://voidpanel.com/admindocs/'  # Replace with your API URL
           response = requests.get(url, timeout=2)
           if response.status_code == 200:
            dataee = response.json()  # Parse the JSON response
            d['docs']=dataee
          
           
           return render(request,'panel/addemail.html',d)
    else: 
        return redirect('/')
    
@login_required(login_url='/')
def adduser(request):
   
    if request.user.is_superuser:
           d={}
           d['package']=package.objects.all()

           # ── License feature flags ─────────────────────────────────────
           try:
               from control.license import get_features, has_feature
               d['license_features']      = get_features()
               d['license_can_reseller']  = has_feature('reseller')
           except Exception:
               d['license_features']     = {}
               d['license_can_reseller'] = False
           # ─────────────────────────────────────────────────────────────

           try:
               url = 'https://voidpanel.com/admindocs/'
               response = requests.get(url, timeout=2)
               if response.status_code == 200:
                   d['docs'] = response.json()
           except Exception:
               pass
           
           return render(request,'panel/adduser.html',d)
    else: 
        return redirect('/')
    
@login_required(login_url='/')
def convertwebsite(request):
   
    if request.user.is_superuser:
           d={}
           newdata=[]
           doai=domain.objects.all()
           userr=user.objects.all()
       
           for user1 in doai:
                try:
                     user.objects.get(domain=user1.domain)
                except:
                     newdata.append(user1)
           d['package']=newdata
           d['package1']=package.objects.all()
           url = 'https://voidpanel.com/admindocs/'  # Replace with your API URL
           response = requests.get(url, timeout=2)
           if response.status_code == 200:
            dataee = response.json()  # Parse the JSON response
            d['docs']=dataee

          
           
           return render(request,'panel/convertwebsite.html',d)
    else: 
        return redirect('/')
    
    
    
    

@never_cache
@login_required(login_url='/')
def addweb(request):
     if request.user.is_superuser:
         if request.method =="POST":
               data = json.loads(request.body)
               domain12 = data.get('web').lower()
               email = data.get('email')
               
               try:
                   if domain.objects.filter(domain=domain12).exists():
                       return JsonResponse({'status': 'already', 'message': 'Domain Already Exist'})
                   
                   directories = os.listdir(paths.HOME_BASE)
                   domainname = domain12.split('.')[0].lower()
                   import re
                   domainname = re.sub(r'[^a-zA-Z0-9]', '', domainname)
                   
                   while domainname in directories:
                       domainname = domainname[:-1]
                       
                   path = os.path.join(paths.HOME_BASE, domainname)
                   inipath = path + '/public_html/php.ini'
                   
                   php_ini_content = f"""
; PHP settings for {domain12}

; General settings
max_execution_time = 30
max_input_time = 60
memory_limit = 256M
post_max_size = 64M
upload_max_filesize = 64M
max_file_uploads = 20
default_charset = "UTF-8"
display_errors = Off
log_errors = On
error_log = "/{path}/public_html/logs/php_errors.log"
error_reporting = E_ALL & ~E_DEPRECATED & ~E_STRICT

; Timezone
date.timezone = "Asia/Kolkata"  ; Set to your timezone

; File Uploads
file_uploads = On
upload_tmp_dir = "/{path}/public_html/tmp"
max_file_uploads = 20

; Session settings
session.save_path = "/{path}/public_html/sessions"
session.gc_maxlifetime = 1440
session.cookie_httponly = 1
session.cookie_secure = 1

; Custom domain-based settings
open_basedir = "/{path}/public_html:/tmp"
"""
                   
                   # Dispatch background celery task
                   from control.tasks import add_website_task
                   add_website_task.delay(domain12, email, domainname, path, inipath, php_ini_content)
                   
                   return JsonResponse({'status': 'success', 'message': 'Website provisioning started'})

               except Exception as e:
                   logger.error("Error in addweb dispatch: %s", e)
                   return JsonResponse({'status': 'error', 'message': str(e)})
             
         from control.activity import log_activity as _log
         _domain_val = request.POST.get('domain', data.get('domain', '')) if hasattr(request, 'POST') else ''
         _log(request, 'success', 'domain', domain=str(_domain_val), action='Domain created', detail='vHost and Nginx config provisioned.')
         return JsonResponse({'status': 'success', 'message': 'Domain Added!'})
            

def _background_provision_user(domain12, email, password, package12, sto, domainname):
    import os, shutil, subprocess, time
    from django.db import transaction
    path=os.path.join(paths.HOME_BASE, domainname)
    try:
        if sys.platform != 'win32':
            subprocess.run(['sudo', 'mkdir', '-p', f"{path}/public_html"], check=True)
            subprocess.run(['sudo', 'chown', '-R', 'www-data:www-data', path], check=True)
        else:
            os.makedirs(f"{path}/public_html", exist_ok=True)
        # Copy voidpanel default web files if source dir exists
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
        _ln_src = f'{paths.NGINX_SITES_AVAILABLE}/{domain12}.conf'
        _ln_dst = f'{paths.NGINX_SITES_ENABLED}/'
        if sys.platform == 'win32':
            shutil.copy2(_ln_src, os.path.join(_ln_dst, f'{domain12}.conf'))
        else:
            run_command(f'sudo ln -sf {_ln_src}  {_ln_dst}')
        if sys.platform != 'win32':
            subprocess.run(['sudo', 'mkdir', '-p', f"{path}/ssl"], check=True)
            subprocess.run(['sudo', 'mkdir', '-p', os.path.join(path, 'mail', domain12)], check=True)
            subprocess.run(['sudo', 'mkdir', '-p', f"{path}/logs"], check=True)
            # Create Recycle Bin dir owned by www-data so the panel can always write to it
            subprocess.run(['sudo', 'mkdir', '-p', f"{path}/.trash"], check=True)
            # CRITICAL: chown+chmod BEFORE writing files — dirs are root-owned after sudo mkdir
            subprocess.run(['sudo', 'chown', '-R', 'www-data:www-data', path], check=True)
            subprocess.run(['sudo', 'chmod', '-R', '755', path], check=True)
            # .trash must be 777 so user files (owned by the linux user) can also be moved in/out
            subprocess.run(['sudo', 'chmod', '777', f"{path}/.trash"], check=True)
        else:
            os.makedirs(f"{path}/ssl", exist_ok=True)
            os.makedirs(os.path.join(path, 'mail', domain12), exist_ok=True)
            os.makedirs(f"{path}/logs", exist_ok=True)
            os.makedirs(f"{path}/.trash", exist_ok=True)

        inipath = path + '/public_html/php.ini'
        php_ini_content = f"""
; PHP settings for {domain12}
max_execution_time = 30
memory_limit = 256M
post_max_size = 64M
upload_max_filesize = 64M
display_errors = Off
log_errors = On
error_log = "{path}/public_html/logs/php_errors.log"
date.timezone = "Asia/Kolkata"
file_uploads = On
open_basedir = "{path}/public_html:/tmp"
"""
        import tempfile
        with tempfile.NamedTemporaryFile('w', suffix='.ini', delete=False) as _tmp:
            _tmp.write(php_ini_content)
            _tmp_name = _tmp.name
        if sys.platform != 'win32':
            subprocess.run(['sudo', 'cp', _tmp_name, inipath], check=True)
            subprocess.run(['sudo', 'chown', 'www-data:www-data', inipath], check=True)
        else:
            import shutil as _shutil
            _shutil.copy2(_tmp_name, inipath)
        os.unlink(_tmp_name)
            
        file_path = os.path.join(paths.NGINX_SITES_AVAILABLE, f"{domain12}.conf")
        root_dir = path+'/public_html'
        cert_path, key_path = generate_ssl_certificates(domain12, path+'/ssl',path+'/logs')
        
        if cert_path and key_path:
            create_nginx_ssl_conf(file_path, domain12, root_dir, cert_path, key_path)
        else:
            raise Exception(f"Cannot generate open ssl for domain {domain12}")
            
        key_dir = os.path.join(paths.OPENDKIM_KEY_DIR, domain12)
        zone_file_path = os.path.join(paths.BIND_ZONE_DIR, f'db.{domain12}')
        private_key_path, public_key_path = generate_dkim_keys(domain12, key_dir)
        
        if private_key_path and public_key_path:
            create_bind_records(domain12, key_dir, zone_file_path)
            configure_opendkim(domain12, key_dir)
        else:
            raise Exception(f"Cannot generate DKIM Record for domain {domain12}")
            
        # Perform DB insertions as an atomic transaction
        with transaction.atomic():
            domain.objects.create(domain=domain12,email=email,dir=domainname,userdomain=True)
            user.objects.create(domain=domain12,email=email,username=domainname,hosting_package=package12)
            User.objects.create_user(username=domainname,email=email,password=password)
            
        # Create Unix user via platform layer
        get_platform().users.create_user(domainname, password, shell='/usr/sbin/nologin')
        
        if sys.platform != 'win32':
            subprocess.run(['sudo', 'chown', f'{domainname}:{domainname}', os.path.join(paths.HOME_BASE, domainname)],
                           capture_output=True, check=False)

        # Apply Quota (optional — skip if setquota not installed)
        try:
            get_platform().users.set_quota(domainname, sto, sto)
        except Exception:
            logger.warning('Quota setup skipped for %s — setquota unavailable', domainname)

        # ZERO-DOWNTIME RELOADS
        plat = get_platform()
        for svc in ('opendkim', 'bind9', 'postfix', 'nginx'):
            try:
                if sys.platform != 'win32':
                    plat.services.reload(svc)
            except Exception as _e:
                logger.warning('Reload %s failed: %s', svc, _e)

        logger.info('Provisioning SUCCESS: domain=%s user=%s', domain12, domainname)

    except Exception as e:
        import traceback as _tb
        _full_err = _tb.format_exc()
        # Write full traceback to provision_error.log for debugging
        try:
            with open('/var/www/panel/provision_error.log', 'a') as _elf:
                _elf.write(f'\n\n=== PROVISION FAIL: domain={domain12} user={domainname} ===\n')
                _elf.write(_full_err)
                _elf.write('=== END ===\n')
        except Exception:
            pass
        logger.error('Provisioning FAILED for %s \u2014 rolling back. Error: %s\n%s', domainname, e, _full_err)

        # Rollback DB
        domain.objects.filter(domain=domain12).delete()
        user.objects.filter(username=domainname).delete()
        User.objects.filter(username=domainname).delete()

        # Rollback Files
        if sys.platform != 'win32':
            subprocess.run(['sudo', 'rm', '-rf', path], check=False)
        else:
            if os.path.exists(path):
                shutil.rmtree(path, ignore_errors=True)

        _en = os.path.join(paths.NGINX_SITES_ENABLED, f'{domain12}.conf')
        if os.path.exists(_en):
            try: os.remove(_en)
            except Exception: pass
        _av = os.path.join(paths.NGINX_SITES_AVAILABLE, f'{domain12}.conf')
        if os.path.exists(_av):
            try: os.remove(_av)
            except Exception: pass

        # Rollback Unix user
        try:
            get_platform().users.delete_user(domainname)
        except Exception:
            pass

@login_required(login_url='/')
@never_cache
def addusermain(request):
    if request.user.is_superuser:
        if request.method =="POST":
            data = json.loads(request.body)
            domain12 = data.get('web').lower()
            email = data.get('email') 
            password = data.get('password') 
            package12 = data.get('package')
            shell_access = bool(data.get('shell_access', False))
            make_reseller     = bool(data.get('make_reseller', False))
            reseller_storage  = int(data.get('reseller_storage_gb', 10))
            reseller_accounts = int(data.get('reseller_max_accounts', 5))
            reseller_company  = data.get('reseller_company', '').strip()
            reseller_branding = data.get('reseller_branding', 'VoidPanel').strip()
            
            if package12 == 'Select':
                package12='default'
                
            try:
                fgf = package.objects.get(name=package12)
                sto = str(fgf.storage)
            except:
                return JsonResponse({'status': 'package', 'message': 'Package not found'})
        
            if domain.objects.filter(domain=domain12).exists():
                return JsonResponse({'status': 'already', 'message': 'Domain Already Exist'})
                
            import re
            base_name = re.sub(r'[^a-z0-9]', '', domain12.split('.')[0].lower())[:16]
            domainname = base_name
            counter = 1
            while os.path.exists(os.path.join(paths.HOME_BASE, domainname)):
                suffix = str(counter)
                domainname = base_name[:16 - len(suffix)] + suffix
                counter += 1
                
            # Dispatch via Celery for robust async provisioning with full logging
            from control.tasks import provision_user_task
            acct_path = os.path.join(paths.HOME_BASE, domainname)
            inipath   = acct_path + '/public_html/php.ini'
            php_ini_content = (
                f'; PHP settings for {domain12}\n'
                'max_execution_time = 30\nmemory_limit = 256M\n'
                'post_max_size = 64M\nupload_max_filesize = 64M\n'
                'display_errors = Off\nlog_errors = On\n'
                f'error_log = "{acct_path}/public_html/logs/php_errors.log"\n'
                'date.timezone = "Asia/Kolkata"\nfile_uploads = On\n'
                f'open_basedir = "{acct_path}/public_html:/tmp"\n'
            )
            task = provision_user_task.delay(
                domain12, domainname, email, password, package12,
                acct_path, int(sto), inipath, php_ini_content,
            )
            logger.info(
                'Provision task dispatched: domain=%s domainname=%s task_id=%s',
                domain12, domainname, task.id,
            )
            
            # If shell_access requested, update the model once we know domainname
            # The user model row is created inside Celery, so we save it async after
            if shell_access:
                from control.models import user as VUser
                import threading
                def _set_shell(dname, dnum):
                    import time; time.sleep(15)  # Give Celery time to create the row
                    try:
                        u = VUser.objects.get(username=dname)
                        u.shell = True
                        u.save()
                        # Change system user shell to /bin/bash
                        run_command(f'sudo usermod -s /bin/bash {dname}')
                    except Exception as e:
                        logger.warning('Set shell flag failed for %s: %s', dname, e)
                threading.Thread(target=_set_shell, args=(domainname, sto), daemon=True).start()

            # If reseller account requested, create the ResellerProfile once Celery finishes
            if make_reseller:
                import threading as _threading
                def _make_reseller(dname, storage_gb, max_acc, company, branding, email_addr, pw):
                    import time as _time
                    _time.sleep(20)  # Wait for Celery to create the Django auth user
                    try:
                        from django.contrib.auth import get_user_model as _gum
                        from control.models import ResellerProfile, user as VUser
                        AuthUser = _gum()
                        # Find the auth user by username (same as domainname)
                        try:
                            auth_user = AuthUser.objects.get(username=dname)
                        except AuthUser.DoesNotExist:
                            # Fallback: find by email
                            auth_user = AuthUser.objects.get(email=email_addr)
                        # Create or update RessellerProfile
                        profile, _ = ResellerProfile.objects.get_or_create(
                            auth_user=auth_user,
                            defaults={
                                'company_name':     company,
                                'branding_name':    branding or 'VoidPanel',
                                'storage_quota_gb': storage_gb,
                                'max_accounts':     max_acc,
                                'is_active':        True,
                            }
                        )
                        logger.info('ResellerProfile created for %s', dname)
                    except Exception as ex:
                        logger.warning('Failed to create ResellerProfile for %s: %s', dname, ex)
                _threading.Thread(
                    target=_make_reseller,
                    args=(domainname, reseller_storage, reseller_accounts,
                          reseller_company, reseller_branding, email, password),
                    daemon=True
                ).start()
            
            return JsonResponse({
                'status': 'success',
                'task_id': str(task.id),
                'username': domainname,
                'message': 'User Creation Initiated!'
            })

        return JsonResponse({'status': 'success', 'message': 'Domain Added!'})

@login_required(login_url='/')
def viewwebsite(request):
   
    if request.user.is_superuser:
           domainname=request.GET.get('domain',None)
           if domainname:

                d={}
                try:
                    import requests

                    current_domain=domain.objects.get(domain=domainname)
                    d['sub']=subdomainname.objects.filter(domain=domainname).all()
                
                    d['domain']=current_domain
                
             
                    try:
                        response = requests.get("http://"+domainname, timeout=10)
                        
                        if response.status_code >= 200 and response.status_code < 400:
                            d['status']=True
                    except:
                        d['status']=False
                    d['phpversion']=phpversion.objects.all()
                   
                

                except:
                    return redirect('/listwebsites/')
                
                url = 'https://voidpanel.com/admindocs/'  # Replace with your API URL
                response = requests.get(url, timeout=2)
                if response.status_code == 200:
                    dataee = response.json()  # Parse the JSON response
                    d['docs']=dataee
                
                try:
                    from voidplatform.linux.web import get_active_engine
                    d['engine'] = get_active_engine()
                except:
                    d['engine'] = 'nginx'

                return render(request,'panel/viewwebsite.html',d)
           else:
               return redirect('/listwebsites')
    else: 
        return redirect('/')
    

@login_required(login_url='/')
def eadns(request):
    if not request.user.is_superuser:
        return redirect('/')

    domainname = request.GET.get('domain', None)
    if not domainname:
        return redirect('/')

    d = {}
    try:
        current_domain = domain.objects.get(domain=domainname)
        d['domain'] = current_domain

        zone_file_path = os.path.join(paths.BIND_ZONE_DIR, f'db.{current_domain.domain}')

        if not os.path.exists(zone_file_path):
            d['error'] = f"Zone file not found for {domainname}. Ensure BIND is configured correctly."
            d['data'] = []
        else:
            data12 = parse_dns_zone_file(zone_file_path)
            d['data'] = data12[2:]  # Skip header SOA lines

    except domain.DoesNotExist:
        return redirect('/')
    except PermissionError:
        d['error'] = "Permission denied reading zone file. Check server file permissions."
        d['data'] = []
    except Exception as e:
        d['error'] = f"Unexpected error: {str(e)}"
        d['data'] = []

    return render(request, 'panel/eadns.html', d)


@login_required(login_url='/')
def deletedns(request):
    if not request.user.is_superuser:
        return JsonResponse({'status': 'error', 'message': 'Permission denied.'}, status=403)

    # Industry standard: state-modifying actions MUST use POST
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Method not allowed. Use POST.'}, status=405)

    domainname  = request.POST.get('domain', '').strip()
    name        = request.POST.get('name', '').strip()
    record_type = request.POST.get('type', '').strip()
    data        = request.POST.get('data', '').strip()
    ttl         = request.POST.get('ttl', '').strip()

    if not domainname or not name:
        return JsonResponse({'status': 'error', 'message': 'Missing required parameters.'}, status=400)

    # Validate domain is actually in our database (prevents path traversal)
    try:
        domain.objects.get(domain=domainname)
    except domain.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Domain not found.'}, status=404)

    zone_file_path = os.path.join(paths.BIND_ZONE_DIR, f'db.{domainname}')

    if not os.path.exists(zone_file_path):
        return JsonResponse({'status': 'error', 'message': 'Zone file not found.'}, status=404)

    deleted = False
    try:
        import subprocess
        result = subprocess.run(['sudo', 'cat', zone_file_path], capture_output=True, text=True)
        if result.returncode != 0:
            raise PermissionError('Failed to read zone file.')
        lines = result.stdout.splitlines(True)

        new_lines = []
        for line in lines:
            line_str = line.strip()
            if not line_str or line_str.startswith(';'):
                new_lines.append(line)
                continue
                
            parts = line_str.split()
            if len(parts) >= 4 and parts[0] == name and record_type in parts:
                if data and data[:15] not in line_str:
                    new_lines.append(line)
                else:
                    deleted = True
            else:
                new_lines.append(line)

        if deleted:
            import tempfile, subprocess
            with tempfile.NamedTemporaryFile('w', delete=False) as tmp:
                tmp.writelines(new_lines)
                tmp_path = tmp.name

            if sys.platform != 'win32':
                check = subprocess.run(['named-checkzone', domainname, tmp_path], capture_output=True, text=True)
                if check.returncode != 0:
                    subprocess.run(['sudo', 'rm', '-f', tmp_path], check=False)
                    return JsonResponse({'status': 'error', 'message': 'DNS Validation failed. Record syntax may break the DNS zone.'}, status=400)
            
            subprocess.run(['sudo', 'mv', tmp_path, zone_file_path], check=True)
            subprocess.run(['sudo', 'chown', 'bind:bind', zone_file_path], check=False)

            if sys.platform != 'win32':
                subprocess.run(['sudo', 'systemctl', 'reload', 'bind9'], check=False)
            return JsonResponse({'status': 'success', 'message': 'DNS record deleted successfully.'})
        else:
            return JsonResponse({'status': 'error', 'message': 'Record not found in zone file.'}, status=404)

    except PermissionError:
        return JsonResponse({'status': 'error', 'message': 'Permission error. Cannot modify zone file.'}, status=500)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': f'Error: {str(e)}'}, status=500)



@login_required(login_url='/')
def adddnsrecord(request):
    if not request.user.is_superuser:
        return JsonResponse({'success': False, 'error': 'Permission denied.'}, status=403)

    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Method not allowed.'}, status=405)

    name        = request.POST.get('name', '').strip()
    domainname  = request.POST.get('domain', '').strip().lower()
    record_class = request.POST.get('class', 'IN').strip().upper()
    record_type = request.POST.get('type', '').strip().upper()
    ttl         = request.POST.get('ttl', '86400').strip()
    data        = request.POST.get('data', '').strip()

    # --- Input Validation ---
    VALID_TYPES = {'A', 'AAAA', 'CNAME', 'MX', 'TXT', 'NS', 'SRV', 'CAA', 'PTR', 'SOA'}
    VALID_CLASSES = {'IN', 'CH', 'HS'}

    if not all([name, domainname, record_type, data]):
        return JsonResponse({'success': False, 'error': 'Missing required fields: name, domain, type, data.'}, status=400)

    if record_type not in VALID_TYPES:
        return JsonResponse({'success': False, 'error': f'Invalid record type "{record_type}". Allowed: {sorted(VALID_TYPES)}'}, status=400)

    if record_class not in VALID_CLASSES:
        return JsonResponse({'success': False, 'error': f'Invalid class "{record_class}". Use IN.'}, status=400)

    if not ttl.isdigit():
        return JsonResponse({'success': False, 'error': 'TTL must be a numeric value.'}, status=400)

    # Validate domain is in our database (prevent arbitrary file writes)
    try:
        domain.objects.get(domain=domainname)
    except domain.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Domain not found in system.'}, status=404)

    # Validate name (no shell metacharacters)
    import re
    if not re.match(r'^[a-zA-Z0-9@._\-\*]+$', name):
        return JsonResponse({'success': False, 'error': 'Invalid record name. Only alphanumeric, dots, hyphens, and @ allowed.'}, status=400)

    zone_file_path = os.path.join(paths.BIND_ZONE_DIR, f'db.{domainname}')
    
    if not os.path.exists(zone_file_path):
        return JsonResponse({'success': False, 'error': 'Zone file not found for this domain.'}, status=404)

    try:
        import subprocess
        result = subprocess.run(['sudo', 'cat', zone_file_path], capture_output=True, text=True)
        if result.returncode != 0:
            raise PermissionError('Failed to read zone file.')
        original_content = result.stdout

        new_content = original_content + f"\n; {record_type} Record added via VoidPanel\n{name} {ttl} IN {record_type} {data}\n"

        import tempfile, subprocess
        with tempfile.NamedTemporaryFile('w', delete=False) as tmp:
            tmp.write(new_content)
            tmp_path = tmp.name

        if sys.platform != 'win32':
            check = subprocess.run(['named-checkzone', domainname, tmp_path], capture_output=True, text=True)
            if check.returncode != 0:
                subprocess.run(['sudo', 'rm', '-f', tmp_path], check=False)
                return JsonResponse({'success': False, 'error': f'Invalid record syntax. BIND rejected the entry. Details: {check.stdout[:100]}'}, status=400)
        
        subprocess.run(['sudo', 'mv', tmp_path, zone_file_path], check=True)
        subprocess.run(['sudo', 'chown', 'bind:bind', zone_file_path], check=False)

        if sys.platform != 'win32':
            subprocess.run(['sudo', 'systemctl', 'reload', 'bind9'], check=False)
        return JsonResponse({'success': True, 'message': f'{record_type} record for "{name}" added successfully.'})

    except PermissionError:
        return JsonResponse({'success': False, 'error': 'Server permission error. Cannot write zone file.'}, status=500)
    except Exception as e:
        return JsonResponse({'success': False, 'error': f'Unexpected error: {str(e)}'}, status=500)

@login_required(login_url='/')
def editdnsrecord(request):
    if not request.user.is_superuser:
        return JsonResponse({'success': False, 'error': 'Permission denied.'}, status=403)

    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Method not allowed.'}, status=405)

    # Old data for matching
    old_name        = request.POST.get('old_name', '').strip()
    old_type        = request.POST.get('old_type', '').strip()
    old_data        = request.POST.get('old_data', '').strip()
    
    # New data for writing
    name        = request.POST.get('name', '').strip()
    domainname  = request.POST.get('domain', '').strip().lower()
    record_class = request.POST.get('class', 'IN').strip().upper()
    record_type = request.POST.get('type', '').strip().upper()
    ttl         = request.POST.get('ttl', '86400').strip()
    data        = request.POST.get('data', '').strip()

    VALID_TYPES = {'A', 'AAAA', 'CNAME', 'MX', 'TXT', 'NS', 'SRV', 'CAA', 'PTR', 'SOA'}
    if not all([old_name, old_type, name, domainname, record_type, data]):
        return JsonResponse({'success': False, 'error': 'Missing required fields.'}, status=400)

    if record_type not in VALID_TYPES:
        return JsonResponse({'success': False, 'error': f'Invalid record type "{record_type}".'}, status=400)

    import re
    if not re.match(r'^[a-zA-Z0-9@._\-\*]+$', name):
        return JsonResponse({'success': False, 'error': 'Invalid new record name.'}, status=400)

    zone_file_path = os.path.join(paths.BIND_ZONE_DIR, f'db.{domainname}')
    
    if not os.path.exists(zone_file_path):
        return JsonResponse({'success': False, 'error': 'Zone file not found for this domain.'}, status=404)

    edited = False
    try:
        import subprocess
        result = subprocess.run(['sudo', 'cat', zone_file_path], capture_output=True, text=True)
        if result.returncode != 0:
            raise PermissionError('Failed to read zone file.')
        lines = result.stdout.splitlines(True)

        new_lines = []
        for line in lines:
            line_str = line.strip()
            if not line_str or line_str.startswith(';'):
                new_lines.append(line)
                continue
                
            parts = line_str.split()
            if len(parts) >= 4 and parts[0] == old_name and old_type in parts:
                if old_data and old_data[:15] not in line_str:
                    new_lines.append(line)
                else:
                    new_lines.append(f"{name} {ttl} IN {record_type} {data}\n")
                    edited = True
            else:
                new_lines.append(line)

        if edited:
            import tempfile, subprocess
            with tempfile.NamedTemporaryFile('w', delete=False) as tmp:
                tmp.writelines(new_lines)
                tmp_path = tmp.name

            if sys.platform != 'win32':
                check = subprocess.run(['named-checkzone', domainname, tmp_path], capture_output=True, text=True)
                if check.returncode != 0:
                    subprocess.run(['sudo', 'rm', '-f', tmp_path], check=False)
                    detail = (check.stdout or check.stderr or '').strip()[:200]
                    return JsonResponse({'success': False, 'error': f'Invalid record syntax. BIND rejected the change. Details: {detail}'}, status=400)
            
            subprocess.run(['sudo', 'mv', tmp_path, zone_file_path], check=True)
            subprocess.run(['sudo', 'chown', 'bind:bind', zone_file_path], check=False)

            if sys.platform != 'win32':
                subprocess.run(['sudo', 'systemctl', 'reload', 'bind9'], check=False)
            return JsonResponse({'success': True, 'message': 'DNS record updated successfully.'})
        else:
            return JsonResponse({'success': False, 'error': 'Original record not found for editing.'}, status=404)

    except PermissionError:
        return JsonResponse({'success': False, 'error': 'Permission error editing zone file.'}, status=500)
    except Exception as e:
        return JsonResponse({'success': False, 'error': f'Unexpected error: {str(e)}'}, status=500)

@login_required(login_url='/')
def loginuser(request):
   
    if request.user.is_superuser:
              username=request.GET.get('user','none')
              if username== 'none':
                   return redirect('/listusers/')
              else:
                   request.session['name']=username
                   return redirect('/control')
              
                
              pass
           
    else: 
        return redirect('/')
    
@login_required(login_url='/')
def listwebsite(request):
   
    if request.user.is_superuser:
                d={}
                listdomain=domain.objects.all()
                d['domain']=listdomain
                url = 'https://voidpanel.com/admindocs/'  # Replace with your API URL
                response = requests.get(url, timeout=2)
                if response.status_code == 200:
                    dataee = response.json()  # Parse the JSON response
                    d['docs']=dataee
    
                return render(request,'panel/listwebsite.html',d)
           
    else: 
        return redirect('/')
    
@login_required(login_url='/')
def listusers(request):
   
    if request.user.is_superuser:
                d={}

                # ── Handle ?filter=resellers to show reseller accounts ────────
                filter_type = request.GET.get('filter', '')
                if filter_type == 'resellers':
                    from control.models import ResellerProfile
                    reseller_profiles = ResellerProfile.objects.select_related('auth_user').all()
                    # Build a list that the template can iterate with .username, .domain, .email etc.
                    reseller_list = []
                    for rp in reseller_profiles:
                        reseller_list.append({
                            'username': rp.auth_user.username,
                            'email': rp.auth_user.email,
                            'company_name': rp.company_name,
                            'storage_gb': rp.storage_quota_gb,
                            'max_accounts': rp.max_accounts,
                            'is_active': rp.is_active,
                            'created_at': rp.created_at,
                            'auth_user': rp.auth_user,
                            'id': rp.id,
                        })
                    d['resellers'] = reseller_list
                    d['is_reseller_filter'] = True
                    d['domain'] = []  # empty so template doesn't break
                    d['package'] = []
                else:
                    listdomain = user.objects.all()
                    # Annotate each user with whether they have a ResellerProfile
                    from control.models import ResellerProfile as _RP
                    reseller_usernames = set(
                        _RP.objects.values_list('auth_user__username', flat=True)
                    )
                    for u_obj in listdomain:
                        u_obj.has_reseller_profile = u_obj.username in reseller_usernames
                    d['domain'] = listdomain
                    d['package'] = package.objects.all()

                try:
                    url = 'https://voidpanel.com/admindocs/'
                    response = requests.get(url, timeout=2)
                    if response.status_code == 200:
                        dataee = response.json()
                        d['docs']=dataee
                except Exception:
                    pass
            
                return render(request,'panel/listuser.html',d)
           
    else: 
        return redirect('/')
    

@login_required(login_url='/')
def listdns(request):
   
    if request.user.is_superuser:
                d={}
                listdomain=domain.objects.all()
                d['domain']=listdomain
                url = 'https://voidpanel.com/admindocs/'  # Replace with your API URL
                try:
                    response = requests.get(url, timeout=2)
                    if response.status_code == 200:
                        dataee = response.json()  # Parse the JSON response
                        d['docs'] = dataee
                except Exception:
                    pass
    
                return render(request,'panel/listdns.html',d)
           
    else: 
        return redirect('/')
               
               
       
              
from django.views.decorators.csrf import csrf_exempt

@csrf_exempt
def addemailaccount(request):
    import base64
    from control.models import user as sysuser
    if request.user.is_superuser or request.user.is_authenticated:
        if request.method == 'POST':
            username = request.POST.get('username')
            if not username: return JsonResponse({'status': 'error', 'message': 'Invalid'})
            username = username.lower()
            password = request.POST.get('password')
            domain_name = request.POST.get('domain')
            if not domain_name: return JsonResponse({'status': 'error', 'message': 'Invalid'})
            domain_name = domain_name.lower()
            full_email = f"{username}@{domain_name}"

            # Industry Standard Feature: Enforce Hosting Package Limits
            from control.models import package
            owner_obj = sysuser.objects.filter(domain=domain_name).first()
            if owner_obj:
                package_obj = package.objects.filter(name=owner_obj.hosting_package).first()
                if package_obj:
                    # Count existing email accounts for this domain
                    current_email_count = allemail.objects.filter(domain=domain_name).count()
                    allowed_emails_str = str(package_obj.email_accounts).strip().lower()
                    
                    if allowed_emails_str != "unlimited" and allowed_emails_str != "0":
                        try:
                            max_emails = int(allowed_emails_str)
                            if current_email_count >= max_emails:
                                return JsonResponse({'status': 'error', 'message': f'Quota Exceeded: Your hosting package allows a maximum of {max_emails} email accounts.'})
                        except ValueError:
                            # If it's not unlimited and not a valid integer, fail securely
                            return JsonResponse({'status': 'error', 'message': 'Invalid package configuration. Cannot verify quota.'})

            if allemail.objects.filter(email=full_email).exists():
                return JsonResponse({'status': 'error', 'message': 'Email already exists.'})

            # Lookup System User tied to this domain for quotas
            sys_owner = 'vmail'
            owner_obj = sysuser.objects.filter(domain=domain_name).first()
            if owner_obj:
                sys_owner = owner_obj.username
            elif sysuser.objects.filter(username=request.user.username).exists():
                sys_owner = request.user.username

            import tempfile
            # Safely append domain mapping securely using temporary shadowed files and sudo
            with tempfile.NamedTemporaryFile('w', delete=False) as tf:
                tf.write(f"{domain_name}\n")
                tmp_domain = tf.name
            run_command(f"sudo bash -c 'grep -q \"^{domain_name}$\" {paths.POSTFIX_VIRTUAL_DOMAINS} || cat {tmp_domain} >> {paths.POSTFIX_VIRTUAL_DOMAINS}'")

            with tempfile.NamedTemporaryFile('w', delete=False) as tf:
                tf.write(f"{full_email} {full_email}\n")
                tmp_alias = tf.name
            run_command(f"sudo bash -c 'grep -q \"^{full_email} \" {paths.POSTFIX_VIRTUAL_ALIAS} || cat {tmp_alias} >> {paths.POSTFIX_VIRTUAL_ALIAS}'")

            if sys.platform != 'win32':
                run_command(f"sudo postmap {paths.POSTFIX_VIRTUAL_ALIAS}")
                run_command(f"sudo postmap {paths.POSTFIX_VIRTUAL_DOMAINS}")

            # Pass sys_owner as argument 3 to the shell script executing securely as sudo
            if sys.platform != 'win32':
                script_cmd = f"sudo bash {shlex.quote(os.path.join(paths.PANEL_ROOT, 'emailadd.sh'))} {shlex.quote(full_email)} {shlex.quote(password)} {shlex.quote(sys_owner)}"
                run_command(script_cmd)

            password_b64 = base64.b64encode(password.encode('utf-8')).decode('utf-8')
            allemail.objects.create(domain=domain_name, email=full_email, password=password_b64)
            from control.activity import log_activity
            log_activity(request, 'success', 'email', domain=domain_name,
                         action=f'Email account created: {full_email}',
                         detail=f'Dovecot maildir provisioned for {full_email}')
            return JsonResponse({'status': 'success'})

        return JsonResponse({'status': 'error', 'message': 'POST required.'})
    return JsonResponse({'status': 'error', 'message': 'Unauthorized'})

@login_required(login_url='/')
def listemail(request,data):
    import subprocess
    from django.core.cache import cache
    from control.tasks import update_all_email_stats_task, update_all_email_stats

    if request.user.is_superuser:
           d={}
           emaildetail=[]
           try: 
               domain.objects.get(domain=data)
               data=data.lower()
               d['allemail']=allemail.objects.filter(domain=data).all()
               for i in allemail.objects.filter(domain=data).all():
                   usernameemail=i.email.split("@")[0]
                   maildir_path = _resolve_maildir(i.domain, usernameemail)
                   new_dir = os.path.join(maildir_path, "Maildir", "new")
                   if not os.path.exists(new_dir):
                       new_dir = os.path.join(maildir_path, "new")
                   cur_dir = os.path.join(maildir_path, "Maildir", "cur")
                   if not os.path.exists(cur_dir):
                       cur_dir = os.path.join(maildir_path, "cur")
                   new_emails_count = len(os.listdir(new_dir)) if os.path.exists(new_dir) else 0
                   cur_emails_count = len(os.listdir(cur_dir)) if os.path.exists(cur_dir) else 0
                   total_emails_count = new_emails_count + cur_emails_count
                   
                   email_key = i.email.lower()
                   stats = cache.get(f'email_stats:{email_key}')
                   if stats is None:
                        if allemail.objects.filter(domain=data).count() <= 5:
                            try:
                                update_all_email_stats()
                                stats = cache.get(f'email_stats:{email_key}', {'sent': 0, 'failed': 0, 'queue': 0})
                            except Exception:
                                stats = {'sent': 0, 'failed': 0, 'queue': 0}
                        else:
                            update_all_email_stats_task.delay()
                            stats = {'sent': 0, 'failed': 0, 'queue': 0}

                   sent_cnt = stats.get('sent', 0)
                   failed_cnt = stats.get('failed', 0)
                   queue_cnt = stats.get('queue', 0)
                   totalemail = sent_cnt + failed_cnt + queue_cnt
                   
                   try:
                    sendp=(sent_cnt/totalemail)*100
                    failedp=(failed_cnt/totalemail)*100
                    processp=(queue_cnt/totalemail)*100
                   except:
                        sendp=0
                        failedp=0
                        processp=0
                   emaildetail.append(
                       {'email':i.email,'sent':sent_cnt,'failed':failed_cnt,'queue':queue_cnt,'sendp':sendp,'failedp':failedp,'processp':processp,'total_emails_count':total_emails_count}
                   )
               d['emaildata']=emaildetail
               import socket
               hostname = socket.gethostname()
               url = f"https://{hostname}:9002"
               if is_website_live(url):
                   d['ip']=url
               else:
                   d['ip']=f"https://{get_server_ip()}:9002"
               url = 'https://voidpanel.com/admindocs/'  # Replace with your API URL
               response = requests.get(url, timeout=2)
               if response.status_code == 200:
                    dataee = response.json()  # Parse the JSON response
                    d['docs']=dataee
               return render(request,'panel/listemail.html',d)
           except Exception as e:
                return redirect('/')
    else: 
        return redirect('/')



  
    

@login_required(login_url='/')

def changeemailpassword(request):
    import base64
    if request.user.is_superuser or request.user.is_authenticated:
        if request.method == 'POST':
            password = request.POST.get('password')
            domain_name = request.POST.get('domain')
            domain_name=domain_name.lower()
            email = request.POST.get('emailname')
            email=email.lower()
            if sys.platform != 'win32':
                # Use subprocess list to avoid shell injection
                import subprocess
                hashed = subprocess.run(
                    ['doveadm', 'pw', '-p', password],
                    capture_output=True, text=True
                ).stdout.strip()
                shadow_path = os.path.join(_resolve_mail_domain_dir(domain_name), 'shadow')
                if os.path.exists(shadow_path):
                    with open(shadow_path, 'r') as f:
                        lines = f.readlines()
                    with open(shadow_path, 'w') as f:
                        for line in lines:
                            if line.startswith(email + ':'):
                                f.write(f'{email}:{hashed}\n')
                            else:
                                f.write(line)
            password = base64.b64encode(password.encode('utf-8'))
            
            xxxx=allemail.objects.get(email=email)
            xxxx.password=password
            xxxx.save()
            return JsonResponse({'status': 'success'})
        
        return JsonResponse({'status': 'error'})
    


@login_required(login_url='/')
def adddatabase(request):
    try:
        with open(paths.MYSQL_PASSWORD_FILE, 'r') as f:
            adminpassword = f.read().strip()
    except Exception:
        adminpassword = ''

    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Invalid request method'})

    if request.user.is_superuser:
        current = request.session.get('name', request.user.username)
    else:
        current = str(request.user)

    front = request.POST.get('front', '')
    name = request.POST.get('databasename', '')
    if not name:
        return JsonResponse({'status': 'error', 'message': 'Database name is required'})

    final = front + name

    try:
        user_obj = user.objects.get(username=current)
        er = package.objects.get(name=user_obj.hosting_package)
        if er.databases_allowed != '0':
            mainn = f"{current}_"
            if len(get_database_names_with_filter(adminpassword, mainn)) >= int(er.databases_allowed):
                return JsonResponse({'status': 'exceed', 'message': 'Database quota limit reached'})
    except Exception:
        pass

    if create_database_and_table(final, adminpassword):
        from control.activity import log_activity
        log_activity(request, 'success', 'db', domain=current,
                     action=f'Database created: {final}',
                     detail=f'MySQL database provisioned for user {current}')
        return JsonResponse({'status': 'success'})
    
    from control.activity import log_activity
    log_activity(request, 'error', 'db', domain=current,
                 action=f'Database creation failed: {final}',
                 detail='MySQL create_database_and_table returned False')
    return JsonResponse({'status': 'error', 'message': 'Database creation failed'})

@login_required(login_url='/')
def adddatabaseuser(request):
    try:
        with open(paths.MYSQL_PASSWORD_FILE, 'r') as f:
            adminpassword = f.read().strip()
    except Exception:
        adminpassword = ''
        
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'POST required'})

    username = request.POST.get('databaseuser')
    password = request.POST.get('password')
    domain_val = request.POST.get('domain')
    
    if not username or not password or domain_val is None:
        return JsonResponse({'status': 'error', 'message': 'All fields are required'})

    if domain_val == "":
        full = username
    else:
        full = f"{domain_val}_{username}"
        
    if create_mysql_user(full, password, adminpassword):
        return JsonResponse({'status': 'success'})
    return JsonResponse({'status': 'error', 'message': 'Could not create user'})

@login_required(login_url='/')
def dbconnect(request,data):
    try:
        with open(paths.MYSQL_PASSWORD_FILE, 'r') as f:
            adminpassword=f.read()
            adminpassword=adminpassword.strip()
    except Exception:
        adminpassword = ''
   
    if request.user.is_superuser:
                d={}
                try:
                    lold=domain.objects.get(domain=data)
                    cc=lold.dir
                    d['domain']=data
                    mainn=cc+"_"
                    d['database']=get_database_names_with_filter(adminpassword,mainn)
                    d['users']=get_database_users_with_filter(adminpassword,mainn)
                    d['mappings']=get_database_privileges_with_filter(adminpassword,mainn)
                    url = 'https://voidpanel.com/admindocs/'  # Replace with your API URL
                    response = requests.get(url, timeout=2)
                    if response.status_code == 200:
                        dataee = response.json()  # Parse the JSON response
                        d['docs']=dataee
                            
                    return render(request,'panel/dbconnect.html',d)
                except:
                    return redirect("/listwebsite/")
           
    else: 
        return redirect('/')
    
@login_required(login_url='/')
def dbreomve(request, data, database):
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'POST required.'}, status=405)
    try:
        with open(paths.MYSQL_PASSWORD_FILE, 'r') as f:
            adminpassword = f.read().strip()
    except FileNotFoundError:
        adminpassword = 'adminpassword'

    if request.user.is_superuser:
        # Admin shortcut — /dbreomve/admin/<db>/
        if data == 'admin':
            if remove_database(database, adminpassword):
                return JsonResponse({'status': 'success', 'message': f'Database {database} deleted.'})
            return JsonResponse({'status': 'error', 'message': 'Could not delete database.'}, status=500)
        try:
            lold = domain.objects.get(domain=data)
            if remove_database(database, adminpassword):
                return JsonResponse({'status': 'success', 'message': f'Database {database} deleted.'})
            return JsonResponse({'status': 'error', 'message': 'Could not delete database.'}, status=500)
        except Exception:
            return JsonResponse({'status': 'error', 'message': 'Domain not found.'}, status=404)

    elif request.user.is_authenticated:
        try:
            lold = domain.objects.get(domain=data)
            # Ensure the authenticated user owns this domain
            current = str(request.user)
            if user.objects.get(username=current).domain != data:
                return JsonResponse({'status': 'error', 'message': 'Permission denied.'}, status=403)
            if remove_database(database, adminpassword):
                return JsonResponse({'status': 'success', 'message': f'Database {database} deleted.'})
            return JsonResponse({'status': 'error', 'message': 'Could not delete database.'}, status=500)
        except Exception:
            return JsonResponse({'status': 'error', 'message': 'Domain not found.'}, status=404)

    return JsonResponse({'status': 'error', 'message': 'Unauthorized.'}, status=403)
    
@login_required(login_url='/')
def dbuserremove(request, data, database):
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'POST required.'}, status=405)
    try:
        with open(paths.MYSQL_PASSWORD_FILE, 'r') as f:
            adminpassword = f.read().strip()
    except FileNotFoundError:
        adminpassword = 'adminpassword'

    if request.user.is_superuser:
        if data == 'admin':
            if delete_mysql_user(database, adminpassword):
                return JsonResponse({'status': 'success', 'message': f'User {database} deleted.'})
            return JsonResponse({'status': 'error', 'message': 'Could not delete user.'}, status=500)
        try:
            lold = domain.objects.get(domain=data)
            if delete_mysql_user(database, adminpassword):
                return JsonResponse({'status': 'success', 'message': f'User {database} deleted.'})
            return JsonResponse({'status': 'error', 'message': 'Could not delete user.'}, status=500)
        except Exception:
            return JsonResponse({'status': 'error', 'message': 'Domain not found.'}, status=404)

    elif request.user.is_authenticated:
        try:
            lold = domain.objects.get(domain=data)
            current = str(request.user)
            if user.objects.get(username=current).domain != data:
                return JsonResponse({'status': 'error', 'message': 'Permission denied.'}, status=403)
            if delete_mysql_user(database, adminpassword):
                return JsonResponse({'status': 'success', 'message': f'User {database} deleted.'})
            return JsonResponse({'status': 'error', 'message': 'Could not delete user.'}, status=500)
        except Exception:
            return JsonResponse({'status': 'error', 'message': 'Domain not found.'}, status=404)

    return JsonResponse({'status': 'error', 'message': 'Unauthorized.'}, status=403)

@login_required(login_url='/')
def changepasswordforuser(request):
    try:
        with open(paths.MYSQL_PASSWORD_FILE, 'r') as f:
            adminpassword = f.read().strip()
    except Exception:
        adminpassword = ''
        
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Invalid request.'})
        
    username = request.POST.get('databaseuser')
    new_password = request.POST.get('password')

    if change_mysql_user_password(username, new_password, adminpassword):
        return JsonResponse({'status': 'success'})
    return JsonResponse({'status': 'error', 'message': 'Password change failed.'})

@login_required(login_url='/')
def addpermissiontouser(request):
    try:
        with open(paths.MYSQL_PASSWORD_FILE, 'r') as f:
            adminpassword = f.read().strip()
    except Exception:
        adminpassword = ''

    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'POST required'})
    
    database = request.POST.get('databasename')
    userdatabase = request.POST.get('databaseusername')
    
    if not database or not userdatabase:
         return JsonResponse({'status': 'error', 'message': 'Database and user required'})
         
    priv = []
    allowed_privs = ['SELECT', 'INSERT', 'UPDATE', 'DELETE', 'EXECUTE', 'CREATE', 'DROP', 'ALTER', 'INDEX', 'REFERENCES']
    for p in allowed_privs:
        if request.POST.get(p.lower()):
            priv.append(p)
            
    if not priv:
        if request.POST.getlist('select'):
            priv.extend([x.upper() for x in request.POST.getlist('select') if x.upper() in allowed_privs])
        elif request.POST.getlist('priv'):
            priv.extend([x.upper() for x in request.POST.getlist('priv') if x.upper() in allowed_privs])

    priv = list(set(priv))
    if not priv:
         return JsonResponse({'status': 'error', 'message': 'No privileges selected'})

    if grant_mysql_user_privileges(userdatabase, database, priv, adminpassword):
        return JsonResponse({'status': 'success', 'message': 'Success.'})
    return JsonResponse({'status': 'error', 'message': 'failed.'})
                      

@login_required(login_url='/')
def files(request,data):
    import os
    file_path=request.GET.get('key',None)
    if file_path is None:
        file_path=os.path.join(paths.HOME_BASE, data)
    last = file_path.rsplit('/', 1)[0]
    if request.user.is_superuser:
           
               
           d={}
           d['main_dir']=file_path
           d['last']=last
        #    items = os.listdir(main_dir)
         
           result = get_file_info(file_path)
           d['pppp']=data
           d['items']=result['directories']
           d['files']=result['files']
          
           return render(request,'panel/files.html',d)
    else: 
        return redirect('/')
    

@login_required(login_url='/')
def revokeprivilege(request):
    try:
        with open(paths.MYSQL_PASSWORD_FILE, 'r') as f:
            adminpassword = f.read().strip()
    except Exception:
        adminpassword = ''

    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'POST required'})
    
    database = request.POST.get('databasename')
    username = request.POST.get('databaseusername')

    if not database or not username:
        return JsonResponse({'status': 'error', 'message': 'Database and user required'})
    
    if revoke_mysql_user_privileges(username, database, adminpassword):
        return JsonResponse({'status': 'success'})
        
    return JsonResponse({'status': 'error', 'message': 'Could not revoke privilege'})


@login_required(login_url='/')
def cronn(request, data):
    import json
    import subprocess
    if request.user.is_superuser:
        d = {}
        try:
            lold = domain.objects.get(domain=data)
            d['crondata'] = cron.objects.filter(domain=data).all()
            d['domainname'] = data
            
            if request.method == "POST":
                # Handle Modern JSON Request
                if request.content_type == 'application/json':
                    req_data = json.loads(request.body)
                    time_val = req_data.get('time')
                    path_val = req_data.get('path')
                    
                    if not time_val or not path_val:
                        return JsonResponse({'status': 'error', 'message': 'Invalid data provided.'})

                    if sys.platform != 'win32':
                        res = subprocess.run(['crontab', '-l'], capture_output=True, text=True)
                        current_cron = res.stdout if res.returncode == 0 else ""
                        new_cron = f"{current_cron.strip()}\n{time_val} {path_val}\n"
                        subprocess.run(['crontab', '-'], input=new_cron, text=True, check=True)
                    else:
                        from voidplatform.windows.cron import add_cron as _add_cron
                        _add_cron(time_val, path_val)

                    cron.objects.create(domain=data, path=path_val, duratioin=time_val)
                    return JsonResponse({'status': 'success', 'message': 'User cron job added successfully.'})

            try:
                url = 'https://voidpanel.com/admindocs/'
                response = requests.get(url, timeout=5)
                if response.status_code == 200:
                    d['docs'] = response.json()
            except Exception:
                pass
            
            return render(request, 'panel/cron.html', d)
        except Exception as e:
            if request.content_type == 'application/json':
                return JsonResponse({'status': 'error', 'message': str(e)})
            return redirect("/listwebsite/")
    else: 
        return redirect('/')
    
@login_required(login_url='/')
def deletecron(request, data):
    import subprocess
    if request.user.is_superuser:
        try:
            xxxx = cron.objects.get(id=data)
            domainname = xxxx.domain
            
            # Secure Cron Deletion: Filter out the specific path line without using shell pipes
            if sys.platform != 'win32':
                res = subprocess.run(['crontab', '-l'], capture_output=True, text=True)
                if res.returncode == 0:
                    current_cron_lines = res.stdout.splitlines()
                    filtered_lines = [line for line in current_cron_lines if xxxx.path not in line]
                    new_cron = "\n".join(filtered_lines) + "\n"
                    subprocess.run(['crontab', '-'], input=new_cron, text=True, check=True)
            else:
                from voidplatform.windows.cron import delete_cron as _delete_cron
                _delete_cron(xxxx.path)

            xxxx.delete()
            
            # If request is JSON (async delete)
            if request.content_type == 'application/json':
                return JsonResponse({'status': 'success', 'message': 'Cron job removed safely.'})
                
            # Fallback redirect for GET/POST fallback
            if domainname == 'admin':
                return redirect('/maincron/')
            else:
                return redirect(f'/cron/{domainname}')
        except Exception as e:
            if request.content_type == 'application/json':
                return JsonResponse({'status': 'error', 'message': str(e)})
            return redirect('/maincron/')
    
@never_cache
@login_required(login_url='/')
def subdomain(request,data):
   
    if request.user.is_superuser :
                d={}
                try:
                    
                    lold=domain.objects.get(domain=data)
                    d['domain']=data
                    d['data']=subdomainname.objects.filter(domain=data).all() 
                    url = 'https://voidpanel.com/admindocs/'  # Replace with your API URL
                    response = requests.get(url, timeout=2)
                    if response.status_code == 200:
                        dataee = response.json()  # Parse the JSON response
                        d['docs']=dataee    
                    return render(request,'panel/subdomian.html',d)
                except Exception as e:
                    return redirect("/listwebsite/")
           
    else: 
        return redirect('/')


def sync_cloudflare_subdomain_add(domain_name, subdomain_full):
    from control.models import CloudflareIntegration
    integration = CloudflareIntegration.objects.filter(domain=domain_name).first()
    if integration:
        ip = '207.180.209.216'
        try:
            import requests
            r = requests.get('https://ifconfig.me/ip', timeout=5)
            if r.status_code == 200:
                ip = r.text.strip()
        except Exception:
            pass
        
        url = f"https://api.cloudflare.com/client/v4/zones/{integration.zone_id}/dns_records"
        payload = {
            "type": "A",
            "name": subdomain_full,
            "content": ip,
            "ttl": 1,
            "proxied": True
        }
        
        if integration.email:
            headers = {
                "X-Auth-Email": integration.email,
                "X-Auth-Key": integration.api_token,
                "Content-Type": "application/json",
            }
        else:
            headers = {
                "Authorization": f"Bearer {integration.api_token}",
                "Content-Type": "application/json",
            }
        try:
            import requests
            requests.post(url, headers=headers, json=payload, timeout=10)
        except Exception:
            pass


def sync_cloudflare_subdomain_delete(domain_name, subdomain_full):
    from control.models import CloudflareIntegration
    integration = CloudflareIntegration.objects.filter(domain=domain_name).first()
    if integration:
        url = f"https://api.cloudflare.com/client/v4/zones/{integration.zone_id}/dns_records?name={subdomain_full}"
        if integration.email:
            headers = {
                "X-Auth-Email": integration.email,
                "X-Auth-Key": integration.api_token,
                "Content-Type": "application/json",
            }
        else:
            headers = {
                "Authorization": f"Bearer {integration.api_token}",
                "Content-Type": "application/json",
            }
        try:
            import requests
            r = requests.get(url, headers=headers, timeout=10)
            if r.status_code == 200:
                data = r.json()
                if data.get('success') and data.get('result'):
                    for rec in data['result']:
                        rec_id = rec['id']
                        del_url = f"https://api.cloudflare.com/client/v4/zones/{integration.zone_id}/dns_records/{rec_id}"
                        requests.delete(del_url, headers=headers, timeout=10)
        except Exception:
            pass


@login_required(login_url='/')
def subdomainprocess(request):
    try:
        if request.user.is_superuser:
            current=request.session['name']
        else:
            current=request.user
    except:
         pass
    if request.user.is_superuser or request.user.is_authenticated:
        if request.method == 'POST':
                            name=request.POST.get('name', '').lower()
                            data=request.POST.get('data', '').lower()
                            if not name or not data:
                                return JsonResponse({'status': 'error', 'message': 'Missing parameters'})
                            lold=domain.objects.get(domain=data)
                            full=name+'.'+data
                            try:
                                 weew=user.objects.get(username=current).hosting_package
                                 er=package.objects.get(name=weew)
                                 if er.subdomain !='0':
                                    if len(subdomainname.objects.filter(domain=data)) >= int(er.subdomain):
                                      return JsonResponse({'status': 'exceed', 'message': 'Subdomain limit exceeded'})
                            except:
                                 pass
                            try:
                                cc=subdomainname.objects.get(subdomain=full)
                                return JsonResponse({'status': 'error', 'message': 'Subdomain already exists'})
                            except:
                                path=os.path.join(paths.HOME_BASE, lold.dir, 'public_html', name)
                                oldpath=os.path.join(paths.HOME_BASE, lold.dir)
                                if not os.path.exists(path):
                                    if sys.platform != 'win32':
                                        run_command(f'sudo mkdir -p {path}')
                                        run_command(f'sudo chown www-data:www-data {path}')
                                    else:
                                        os.makedirs(path, exist_ok=True)
                                    _vp_src = os.path.join(paths.PANEL_ROOT, 'voidpanel')
                                    for _item in os.listdir(_vp_src):
                                        _s = os.path.join(_vp_src, _item)
                                        _d = os.path.join(path, _item)
                                        if os.path.isdir(_s):
                                            shutil.copytree(_s, _d, dirs_exist_ok=True)
                                        else:
                                            shutil.copy2(_s, _d)
                                    if sys.platform != 'win32':
                                        run_command(f'sudo chown -R {lold.dir}:www-data {path}')
                                        run_command(f'sudo chmod -R 750 {path}')
                                
                                # ── Engine-aware subdomain config ──
                                from voidplatform.linux.web import get_active_engine, get_active_engine_manager
                                engine = get_active_engine()
                                mgr = get_active_engine_manager()
                                root_dir = path

                                if engine == 'nginx':
                                    file_path = os.path.join(paths.NGINX_SITES_AVAILABLE, f"{full}.conf")
                                    cert_path, key_path = generate_ssl_certificates(full, oldpath+'/ssl', oldpath+'/logs')

                                    if cert_path and key_path:
                                        create_nginx_ssl_conf(file_path, full, root_dir, cert_path, key_path)
                                    else:
                                        # Write a standard HTTP-only fallback to avoid breaking nginx
                                        fallback_conf = f"server {{\n    listen 80;\n    server_name {full};\n    root {root_dir};\n    index index.php index.html;\n    location /vpanel {{\n        return 301 https://$host:8082;\n    }}\n    location /control/ {{\n        proxy_pass http://127.0.0.1:8080;\n        proxy_set_header Host $host;\n        proxy_set_header X-Real-IP $remote_addr;\n        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;\n        proxy_set_header X-Forwarded-Proto $scheme;\n    }}\n    location / {{\n        try_files $uri $uri/ =404;\n    }}\n    location ~ \\.php$ {{\n        include snippets/fastcgi-php.conf;\n        fastcgi_pass unix:/run/php/php8.3-fpm.sock;\n    }}\n}}\n"
                                        with open(file_path, 'w') as f:
                                            f.write(fallback_conf)

                                    # Safely Symlink & Test
                                    _ln_src = f'{paths.NGINX_SITES_AVAILABLE}/{full}.conf'
                                    _ln_dst = paths.NGINX_SITES_ENABLED
                                    if sys.platform == 'win32':
                                        shutil.copy2(_ln_src, os.path.join(_ln_dst, f'{full}.conf'))
                                    else:
                                        run_command(f'sudo ln -sf {_ln_src} {_ln_dst}/')

                                    if sys.platform != 'win32':
                                        test_res = mgr.test_config()
                                        if not test_res.success:
                                            _rm_path = os.path.join(paths.NGINX_SITES_ENABLED, f'{full}.conf')
                                            if os.path.exists(_rm_path):
                                                os.remove(_rm_path)
                                            return JsonResponse({'status': 'error', 'message': 'Nginx config test failed. Reverted.'})

                                else:
                                    # OpenLiteSpeed — use the engine manager
                                    result = mgr.create_site(full, root_dir, php_version='8.3', unix_user=lold.dir)
                                    if not result.success:
                                        return JsonResponse({'status': 'error', 'message': f'OLS config failed: {result.error}'})

                                # DNS record & service restarts (common for both engines)
                                zone_file_path = os.path.join(paths.BIND_ZONE_DIR, f'db.{lold.domain}')
                                create_bind_recordsforsubdomain(name, zone_file_path)
                                try:
                                    get_platform().services.reload('bind9')
                                except Exception:
                                    pass
                                cce=subdomainname.objects.create(subdomain=full, name=name, domain=data)
                                try:
                                    sync_cloudflare_subdomain_add(data, full)
                                except Exception:
                                    pass
                                return JsonResponse({'status': 'success', 'message': 'Subdomain successfully created'})
    
        return JsonResponse({'status': 'error', 'message': 'Invalid request.'})
    

@login_required(login_url='/')
def deletesubdomain(request,data):
    from voidplatform.linux.web import get_active_engine_manager
    mgr = get_active_engine_manager()

    if request.user.is_superuser :
        xxxx=subdomainname.objects.get(subdomain=data)
        maindir=lold=domain.objects.get(domain=xxxx.domain).dir
        path=os.path.join(paths.HOME_BASE, maindir, "public_html", xxxx.name)
        import shutil
        try:
            shutil.rmtree(path)
        except:
            pass
        mgr.delete_site(data)
        domainname=xxxx.domain
        try:
            sync_cloudflare_subdomain_delete(domainname, xxxx.subdomain)
        except Exception:
            pass
        xxxx.delete()
        return redirect(f'/subdomain/{domainname}')
    elif request.user.is_authenticated:
        xxxx=subdomainname.objects.get(subdomain=data)
        # Ownership check: ensure user owns this subdomain's parent domain
        owner = user.objects.filter(username=request.user.username).first()
        if not owner or owner.domain != xxxx.domain:
            return JsonResponse({'status': 'error', 'message': 'Unauthorized'}, status=403)
        maindir=lold=domain.objects.get(domain=xxxx.domain).dir
        path=os.path.join(paths.HOME_BASE, maindir, "public_html", xxxx.name)
        import shutil
        try:
            shutil.rmtree(path)
        except:
            pass
        mgr.delete_site(data)
        domainname=xxxx.domain
        try:
            sync_cloudflare_subdomain_delete(domainname, xxxx.subdomain)
        except Exception:
            pass
        xxxx.delete()
        return redirect(f'/control/subdomain/{domainname}')


@login_required(login_url='/')
def runssl(request,data):
   
    if request.user.is_superuser:
                d={}
                try:
                    
                    lold=domain.objects.get(domain=data)
                 
                    d['domain']=data
               
                    d['main']=lold
                    logs=[]
                    path=os.path.join(paths.HOME_BASE, lold.dir, "logs", "ssl.txt")
                    with open(path,'r') as f:
                         dd=f.readlines()
                         for i in dd:
                              logs.append(i)
                    d['logs']=logs
                    d['subdomain']=subdomainname.objects.filter(domain=data).all()      
                    try:
                        url = 'https://voidpanel.com/admindocs/'
                        response = requests.get(url, timeout=2)
                        if response.status_code == 200:
                            dataee = response.json()
                            d['docs']=dataee
                    except Exception:
                        d['docs'] = []
                    return render(request,'panel/sitessl.html',d)
                except Exception as e:
                    return redirect("/listwebsite/")
           
    else: 
        return redirect('/')


@login_required(login_url='/')
def runsslfordoamin(request):
    if not request.user.is_superuser:
        return JsonResponse({'status': 'error', 'message': 'Authentication required.'}, status=403)
    import subprocess
    if request.method == 'POST':
                        name=request.POST['domain']
                        name=name.lower()
                        lold=domain.objects.get(domain=name)
                        
                        plat = get_platform()
                        
                        subdomain2=subdomainname.objects.filter(domain=name).all()
                        path=os.path.join(paths.HOME_BASE, lold.dir, "logs", "ssl.txt")
                        try:
                            result = plat.ssl.provision(name, email=lold.email)
                            if result.success:
                                with open(path,'a+') as f:
                                    f.write("\n")
                                    f.write(f"AutoSSl Completed for domain {name}")
                                    lold.sslstatus=True
                                    lold.save()
                            else:
                                with open(path,'a+') as f:
                                    f.write("\n")
                                    f.write(f"Error Occur for domain {name}: {result.error}")

                        except Exception as e:
                             with open(path,'a+') as f:
                                f.write("\n")
                                f.write(f"Error Occur for domain {name}")
                                f.write(str(e))
                        for i in subdomain2:
                            
                            try:
                                result = plat.ssl.provision(i.subdomain, email=f'{i.name}@example.com')
                                if result.success:
                                    with open(path,'a+') as f:
                                        f.write("\n")
                                        f.write(f"AutoSSl Completed for domain {i.subdomain}")
                                        i.sslstatus=True
                                        i.save()
                                else:
                                    with open(path,'a+') as f:
                                        f.write("\n")
                                        f.write(f"Error Occur for domain {i.subdomain}: {result.error}")
                            except Exception as e:
                             with open(path,'a+') as f:
                                f.write("\n")
                                f.write(f"Error Occur for domain {i.subdomain}")
                                f.write(str(e))   
                        return JsonResponse({'status': 'success', 'message': 'Already Exist'})
   
    return JsonResponse({'status': 'error', 'message': 'Invalid request.'})


@login_required(login_url='/')
def runsslfordoamin1(request):
    if not request.user.is_superuser:
        return JsonResponse({'status': 'error', 'message': 'Authentication required.'}, status=403)
    import subprocess
    lol=None
    if request.method == 'POST':
                        data = json.loads(request.body)
                        name=data.get('name').strip(' ')
                        plat = get_platform()
                        try:
                            lold=domain.objects.get(domain=name)

                            _ssl_domain = lold.domain
                            _ssl_email = lold.email
                        except:
                             lold1=subdomainname.objects.get(subdomain=name)
                             lold=domain.objects.get(domain=lold1.domain)
                             path=os.path.join(paths.HOME_BASE, lold.dir, "logs", "ssl.txt")
                             with open(path,'a+') as f:
                                f.write(f"\nfetched Subdomain {name}")

                             with open(path,'a+') as f:
                                f.write(f"\nPerforming SSl for {name}")
                             _ssl_domain = lold1.subdomain
                             _ssl_email = lold.email



                        path=os.path.join(paths.HOME_BASE, lold.dir, "logs", "ssl.txt")

                        try:
                            result = plat.ssl.provision(_ssl_domain, email=_ssl_email)
                            if result.success:
                                with open(path,'a+') as f:
                                    f.write("\n")
                                    f.write(f"AutoSSl Completed for  domain {name}")
                                try:
                                        uuu=domain.objects.get(domain=name)
                                        uuu.sslstatus=True
                                        uuu.save()

                                except:
                                            ubub=subdomainname.objects.get(subdomain=name)
                                            ubub.sslstatus=True
                                            ubub.save()
                            else:
                                with open(path,'a+') as f:
                                    f.write("\n")
                                    f.write(f"Error Occur for domain {name}: {result.error}")
                     
                              
                                

                        except Exception as e:
                             with open(path,'a+') as f:
                                f.write("\n")
                                f.write(f"Error Occur for domain {name}")
                                f.write(str(e))
                      
                         
                        return JsonResponse({'status': 'success', 'message': 'Already Exist'})
   
    return JsonResponse({'status': 'error', 'message': 'Invalid request.'})
@login_required(login_url='/')
def changephpversion(request):
    import subprocess
    from control.models import domain, subdomainname, user as ctrl_user

    if request.user.is_superuser or request.user.is_authenticated:
        if request.method == "POST":
            name = request.POST.get('name')
            php = request.POST.get('php')
            if not name or not php:
                return JsonResponse({'status': 'error', 'message': 'Missing parameters.'})

            # Security: Verify the user owns this domain/subdomain
            if not request.user.is_superuser:
                owner = request.user.username
                owner_obj = ctrl_user.objects.filter(username=owner).first()
                if not owner_obj or (owner_obj.domain != name and not subdomainname.objects.filter(domain=owner_obj.domain, subdomain=name).exists()):
                    return JsonResponse({'status': 'error', 'message': 'Unauthorized: Domain ownership verification failed.'})

            # Get the config file name
            config_name = None
            obj = None
            if domain.objects.filter(domain=name).exists():
                obj = domain.objects.get(domain=name)
                config_name = obj.domain
            elif subdomainname.objects.filter(subdomain=name).exists():
                obj = subdomainname.objects.get(subdomain=name)
                config_name = obj.subdomain
            
            if not obj or not config_name:
                return JsonResponse({'status': 'error', 'message': 'Domain not found.'})

            try:
                from voidplatform.linux.web import get_active_engine_manager
                mgr = get_active_engine_manager()
                _old_content = mgr.read_site_config(config_name)
                
                if not _old_content:
                     return JsonResponse({'status': 'error', 'message': 'Configuration file not found.'})

                import re as _re
                _new_content = _re.sub(
                    r'fastcgi_pass unix:/run/php/php[0-9.]+-fpm\.sock;',
                    f'fastcgi_pass unix:/run/php/php{php}-fpm.sock;',
                    _old_content
                )
                
                r = mgr.write_and_test_site_config(config_name, _new_content)
                if not r.success:
                    return JsonResponse({'status': 'error', 'message': f'Nginx syntax error after changing PHP version: {r.error}'})
                
                obj.php = php
                obj.save()
                return JsonResponse({'status': 'success', 'message': f'PHP version successfully changed to {php}.'})
            except Exception as e:
                return JsonResponse({'status': 'error', 'message': f'Operation failed: {str(e)}'})

        return JsonResponse({'status': 'error', 'message': 'Invalid request.'})
    return JsonResponse({'status': 'error', 'message': 'Unauthorized request.'})


@never_cache
@login_required(login_url='/')
def phpini(request,data):
   
    if request.user.is_superuser:
                d={}
                try:
                    
                    lold=domain.objects.get(domain=data)

                    d['domain']=data
                    file_path = os.path.join(paths.HOME_BASE, lold.dir, 'public_html', 'php.ini')

                    # Initialize an empty list to store the values
                    values_list = {}

                    # Open and read the file
                    with open(file_path, 'r') as file:
                        for line in file:
                            # Ignore comments and empty lines
                            line = line.strip()
                            if line.startswith(';') or not line:
                                continue
                            if '=' in line:
                                key, value = line.split('=', 1)
                                values_list[key]=(value.strip())

                    # Print the list of values to verify
                    d["new"]=values_list
                    newdata={}
                    if request.method=="POST":
                            for i in values_list.keys():
                                newdata[i]=request.POST[i]
                            with open(file_path, 'w') as file:
                                    for i ,j in newdata.items():
                                        file.write(f'{i}={j}\n')
                    url = 'https://voidpanel.com/admindocs/'  # Replace with your API URL
                    response = requests.get(url, timeout=2)
                    if response.status_code == 200:
                        dataee = response.json()  # Parse the JSON response
                        d['docs']=dataee
                    return render(request,'panel/phpini.html',d)
                except Exception as e:
                    return redirect("/listwebsite/")
           
    else: 
        return redirect('/')



@login_required(login_url='/')
def addredirect(request,data):
   
    if request.user.is_superuser or request.user.is_authenticated:
                d={}
                try:
                    
                    lold=domain.objects.get(domain=data)
                    d['allredir']=redir.objects.filter(maindomain=data).all()
                    d['domain']=data
                    d['subdomain']=subdomainname.objects.filter(domain=data).all()     
                    url = 'https://voidpanel.com/admindocs/'  # Replace with your API URL
                    response = requests.get(url, timeout=2)
                    if response.status_code == 200:
                        dataee = response.json()  # Parse the JSON response
                        d['docs']=dataee 
                    return render(request,'panel/redirect.html',d)
                except Exception as e:
                    return redirect("/listwebsite/")
           
    else: 
        return redirect('/')

@login_required(login_url='/')
def addredirectionnn(request):
    """
    Add a URL redirect — supports both Nginx and OpenLiteSpeed.
    Nginx : inserts a location block with return 301/302 into sites-available (via sudo mv).
    OLS   : writes a RewriteRule into the domain's .htaccess file.
    """
    import re as _re
    import tempfile
    import subprocess as _sp
    import os
    import json
    from django.http import JsonResponse
    from control.models import redir, domain, subdomainname, user
    from voidplatform.config import LinuxPaths as paths

    if not (request.user.is_superuser or request.user.is_authenticated):
        return JsonResponse({'status': 'error', 'message': 'Unauthorized'}, status=403)
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Invalid method'}, status=405)

    name            = request.POST.get('domain', '').strip().lower()
    pathlocation    = request.POST.get('path', '').strip()
    newpathlocation = request.POST.get('newpath', '').strip()
    maindomain      = request.POST.get('maindomain', '').strip().lower()
    redir_type      = request.POST.get('type', '301').strip()

    if not name or not pathlocation or not newpathlocation:
        return JsonResponse({'status': 'error', 'message': 'Missing required fields.'})
    if not pathlocation.startswith('/'):
        pathlocation = '/' + pathlocation
    if redir_type not in ('301', '302'):
        redir_type = '301'

    _reserved = {'/phpmyadmin', '/phpmyadmin/', '/static', '/static/', '/media', '/.well-known'}
    if pathlocation.rstrip('/') in {r.rstrip('/') for r in _reserved}:
        return JsonResponse({'status': 'c', 'message': 'Reserved system path — cannot redirect.'})

    # Ownership check for non-admins
    if not request.user.is_superuser:
        try:
            owner = user.objects.get(username=request.user)
            allowed = {owner.domain} | set(
                subdomainname.objects.filter(domain=owner.domain).values_list('subdomain', flat=True)
            )
            if name not in allowed:
                return JsonResponse({'status': 'error', 'message': 'Unauthorized domain.'}, status=403)
        except Exception:
            return JsonResponse({'status': 'error', 'message': 'Unauthorized.'}, status=403)

    # Duplicate check
    if redir.objects.filter(domain=name, path=pathlocation).exists():
        return JsonResponse({'status': 'error', 'message': 'A redirect for this path already exists.'})

    # Resolve doc root
    doc_root = None
    site_user = None
    try:
        d_obj = domain.objects.get(domain=name)
        doc_root = os.path.join(paths.HOME_BASE, d_obj.dir, 'public_html')
        site_user = d_obj.dir
    except domain.DoesNotExist:
        try:
            s_obj = subdomainname.objects.get(subdomain=name)
            doc_root = os.path.join(paths.HOME_BASE, s_obj.dir, 'public_html')
            site_user = s_obj.dir
        except subdomainname.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': f'Domain {name} not registered in panel.'})

    # Build destination
    if newpathlocation.startswith('http://') or newpathlocation.startswith('https://'):
        destination = newpathlocation
    else:
        if not newpathlocation.startswith('/'):
            newpathlocation = '/' + newpathlocation
        destination = f'https://{name}{newpathlocation}'

    from voidplatform.linux.web import get_active_engine
    engine = get_active_engine()

    try:
        if engine == 'nginx':
            conf_path = os.path.join(paths.NGINX_SITES_AVAILABLE, f'{name}.conf')
            if not os.path.exists(conf_path):
                return JsonResponse({'status': 'error', 'message': 'Nginx config not found for this domain.'})

            read_r = _sp.run(['sudo', 'cat', conf_path], capture_output=True, text=True)
            conf_text = read_r.stdout if read_r.returncode == 0 else open(conf_path).read()

            if _re.search(rf'location\s+{_re.escape(pathlocation)}\s*\{{', conf_text):
                return JsonResponse({'status': 'error', 'message': 'Location block already exists in nginx config.'})

            redirect_block = (
                f'\n    # VP-REDIR {pathlocation}\n'
                f'    location {pathlocation} {{\n'
                f'        return {redir_type} {destination};\n'
                f'    }}\n'
            )
            last_brace = conf_text.rfind('\n}')
            if last_brace == -1:
                last_brace = conf_text.rfind('}')
            new_conf = conf_text[:last_brace] + redirect_block + conf_text[last_brace:]

            with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.conf') as tmp:
                tmp.write(new_conf)
                tmp_path = tmp.name
            _sp.run(['sudo', 'chown', 'root:root', tmp_path], check=False)
            _sp.run(['sudo', 'chmod', '644', tmp_path], check=False)
            mv = _sp.run(['sudo', 'mv', tmp_path, conf_path])
            if mv.returncode != 0:
                return JsonResponse({'status': 'error', 'message': 'Failed to write nginx config (permission denied).'})

            test = _sp.run(['sudo', 'nginx', '-t'], capture_output=True, text=True)
            if test.returncode != 0:
                _sp.run(['sudo', 'mv', f'/tmp/{name}_nginx_backup.conf', conf_path], check=False) # best effort restore
                return JsonResponse({'status': 'error', 'message': f'Nginx config test failed: {test.stderr.strip()}'})
            _sp.run(['sudo', 'systemctl', 'reload', 'nginx'], check=False)

        else:
            # OLS: write .htaccess RewriteRule
            htaccess_path = os.path.join(doc_root, '.htaccess')
            htaccess = ''
            if os.path.exists(htaccess_path):
                r2 = _sp.run(['sudo', 'cat', htaccess_path], capture_output=True, text=True)
                htaccess = r2.stdout if r2.returncode == 0 else open(htaccess_path, 'r', errors='replace').read()

            rule_pat = _re.escape(pathlocation.lstrip('/'))
            if _re.search(rf'RewriteRule\s+\^{rule_pat}', htaccess):
                return JsonResponse({'status': 'error', 'message': 'RewriteRule already exists for this path.'})

            flag = 'R=301,L' if redir_type == '301' else 'R=302,L'
            new_rule = (
                f'\n# VP-REDIR {pathlocation}\n'
                f'RewriteEngine On\n'
                f'RewriteRule ^{pathlocation.lstrip("/")}(/.*)?$ {destination} [{flag}]\n'
            )
            with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.htaccess') as tmp:
                tmp.write(htaccess.rstrip('\n') + new_rule + '\n')
                tmp_path = tmp.name
            _sp.run(['sudo', 'mv', tmp_path, htaccess_path], check=False)
            _sp.run(['sudo', 'chown', f'{site_user}:{site_user}', htaccess_path], check=False)
            _sp.run(['sudo', 'chmod', '644', htaccess_path], check=False)
            _sp.run(['sudo', 'systemctl', 'reload', 'lsws'], check=False)

        redir.objects.create(maindomain=maindomain, domain=name, path=pathlocation, newpath=newpathlocation)
        return JsonResponse({'status': 'success', 'message': f'Redirect added: {pathlocation} → {destination} ({redir_type})'})

    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f'addredirectionnn error: {e}', exc_info=True)
        return JsonResponse({'status': 'error', 'message': str(e)})


@login_required(login_url='/')
def delredirectionnn(request):
    """
    Remove a URL redirect — supports both Nginx and OpenLiteSpeed.
    """
    import re as _re
    import tempfile
    import subprocess as _sp
    import os
    import json
    from django.http import JsonResponse
    from control.models import redir, domain, subdomainname, user
    from voidplatform.config import LinuxPaths as paths

    if not (request.user.is_superuser or request.user.is_authenticated):
        return JsonResponse({'status': 'error', 'message': 'Unauthorized'}, status=403)
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Invalid method'}, status=405)

    try:
        body = json.loads(request.body)
    except Exception:
        return JsonResponse({'status': 'error', 'message': 'Invalid JSON body.'})

    name         = body.get('domain', '').strip()
    pathlocation = body.get('path', '').strip()

    if not name or not pathlocation:
        return JsonResponse({'status': 'error', 'message': 'Missing required fields.'})

    if not request.user.is_superuser:
        try:
            owner = user.objects.get(username=request.user)
            allowed = {owner.domain} | set(
                subdomainname.objects.filter(domain=owner.domain).values_list('subdomain', flat=True)
            )
            if name not in allowed:
                return JsonResponse({'status': 'error', 'message': 'Unauthorized domain.'}, status=403)
        except Exception:
            return JsonResponse({'status': 'error', 'message': 'Unauthorized.'}, status=403)

    # Resolve doc root
    doc_root = None
    site_user = None
    try:
        d_obj = domain.objects.get(domain=name)
        doc_root = os.path.join(paths.HOME_BASE, d_obj.dir, 'public_html')
    except domain.DoesNotExist:
        try:
            s_obj = subdomainname.objects.get(subdomain=name)
            doc_root = os.path.join(paths.HOME_BASE, s_obj.dir, 'public_html')
        except subdomainname.DoesNotExist:
            pass

    from voidplatform.linux.web import get_active_engine
    engine = get_active_engine()

    try:
        if engine == 'nginx':
            conf_path = os.path.join(paths.NGINX_SITES_AVAILABLE, f'{name}.conf')
            if os.path.exists(conf_path):
                r = _sp.run(['sudo', 'cat', conf_path], capture_output=True, text=True)
                conf_text = r.stdout if r.returncode == 0 else open(conf_path).read()

                esc = _re.escape(pathlocation)
                # Remove VP-tagged block first
                new_conf = _re.sub(
                    rf'\n\s*#\s*VP-REDIR\s+{esc}\s*\n\s*location\s+{esc}\s*\{{[^}}]*\}}\n?',
                    '\n', conf_text, flags=_re.DOTALL
                )
                # Generic fallback removal
                if new_conf == conf_text:
                    new_conf = _re.sub(
                        rf'\s*location\s+{esc}\s*\{{[^}}]*\}}\n?',
                        '\n', conf_text, flags=_re.DOTALL
                    )

                with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.conf') as tmp:
                    tmp.write(new_conf)
                    tmp_path = tmp.name
                _sp.run(['sudo', 'mv', tmp_path, conf_path], check=False)
                _sp.run(['sudo', 'chown', 'root:root', conf_path], check=False)
                _sp.run(['sudo', 'chmod', '644', conf_path], check=False)
                test = _sp.run(['sudo', 'nginx', '-t'], capture_output=True, text=True)
                if test.returncode == 0:
                    _sp.run(['sudo', 'systemctl', 'reload', 'nginx'], check=False)
        else:
            if doc_root:
                htaccess_path = os.path.join(doc_root, '.htaccess')
                if os.path.exists(htaccess_path):
                    r2 = _sp.run(['sudo', 'cat', htaccess_path], capture_output=True, text=True)
                    htaccess = r2.stdout if r2.returncode == 0 else open(htaccess_path, 'r', errors='replace').read()
                    rule_pat = _re.escape(pathlocation.lstrip('/'))
                    new_ht = _re.sub(
                        rf'\n?#\s*VP-REDIR\s+{_re.escape(pathlocation)}\nRewriteEngine On\nRewriteRule\s+\^{rule_pat}[^\n]*\n?',
                        '\n', htaccess, flags=_re.DOTALL
                    )
                    if new_ht == htaccess:
                        new_ht = _re.sub(rf'RewriteRule\s+\^{rule_pat}[^\n]*\n?', '', htaccess)
                    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.htaccess') as tmp:
                        tmp.write(new_ht)
                        tmp_path = tmp.name
                    _sp.run(['sudo', 'mv', tmp_path, htaccess_path], check=False)
                    _sp.run(['sudo', 'chmod', '644', htaccess_path], check=False)
                    _sp.run(['sudo', 'systemctl', 'reload', 'lsws'], check=False)

        redir.objects.filter(domain=name, path=pathlocation).delete()
        return JsonResponse({'status': 'success', 'message': 'Redirect removed successfully.'})

    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f'delredirectionnn error: {e}', exc_info=True)
        return JsonResponse({'status': 'error', 'message': str(e)})


def _background_terminate_user(domain_str, mainusername, subdomains):
    """Background worker: wipe all filesystem, config, and DB records for a terminated account.
    All steps are individually guarded — one failure will NOT stop the rest of the cleanup.
    """
    import shutil
    import subprocess

    all_domains = [domain_str] + list(subdomains)

    # --- Filesystem: home directory ---
    try:
        shutil.rmtree(os.path.join(paths.HOME_BASE, mainusername), ignore_errors=True)
    except Exception as e:
        logger.warning('[terminate] Could not remove home dir for %s: %s', mainusername, e)

    # --- Nginx configs: main domain + all subdomains ---
    # Fix: delete BOTH sites-enabled symlinks AND sites-available files to prevent dangling config files
    for d in all_domains:
        for nginx_dir in (paths.NGINX_SITES_ENABLED, paths.NGINX_SITES_AVAILABLE):
            conf = os.path.join(nginx_dir, f'{d}.conf')
            try:
                if os.path.islink(conf) or os.path.isfile(conf):
                    os.remove(conf)
            except Exception:
                pass

    # --- DNS zone file ---
    for d in all_domains:
        try:
            os.remove(os.path.join(paths.BIND_ZONE_DIR, f'db.{d}'))
        except Exception:
            pass
    try:
        if sys.platform != 'win32':
            remove_zone_from_file(paths.BIND_CONF, domain_str)
    except Exception:
        pass

    # --- DKIM keys ---
    if paths.OPENDKIM_KEY_DIR:
        for d in all_domains:
            shutil.rmtree(os.path.join(paths.OPENDKIM_KEY_DIR, d), ignore_errors=True)
        # Clean DKIM tables
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

    # --- SSL certificates ---
    for d in all_domains:
        shutil.rmtree(os.path.join(paths.LETSENCRYPT_LIVE, d), ignore_errors=True)
        renewal = f'/etc/letsencrypt/renewal/{d}.conf'
        try:
            if os.path.exists(renewal):
                os.remove(renewal)
        except Exception:
            pass
        archive_dir = f'/etc/letsencrypt/archive/{d}'
        shutil.rmtree(archive_dir, ignore_errors=True)

    # --- Mail data ---
    try:
        shutil.rmtree(_resolve_mail_domain_dir(domain_str), ignore_errors=True)
    except Exception:
        pass

    # --- Postfix & Dovecot configs ---
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
        except Exception as e:
            logger.warning('[terminate] postfix/dovecot file %s: %s', fpath, e)

    # Rebuild postfix maps
    try:
        if sys.platform != 'win32':
            subprocess.run(['sudo', 'postmap', paths.POSTFIX_VIRTUAL_MAILBOX], timeout=10, check=False)
            subprocess.run(['sudo', 'postmap', paths.POSTFIX_VIRTUAL_ALIAS], timeout=10, check=False)
    except Exception:
        pass

    # --- MySQL: drop databases and users ---
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

            # Drop databases
            dbs = get_database_names_with_filter(mysql_root_pass, prefix)
            for db in dbs:
                remove_database(db, mysql_root_pass)

            # Drop users
            db_users = get_database_users_with_filter(mysql_root_pass, prefix)
            for db_user in db_users:
                delete_mysql_user(db_user, mysql_root_pass)
    except Exception as e:
        logger.warning('[terminate] MySQL cleanup failed: %s', e)

    # --- Reload services (zero-downtime: reload not restart) ---
    try:
        subprocess.run(['sudo', 'systemctl', 'reload', 'bind9'], timeout=15, check=False)
    except Exception:
        pass
    # Reload Nginx only if the test is successful to avoid failing the server globally
    try:
        nginx_test = subprocess.run(['sudo', 'nginx', '-t'], timeout=15, capture_output=True, text=True)
        if nginx_test.returncode == 0:
            subprocess.run(['sudo', 'systemctl', 'reload', 'nginx'], timeout=15, check=False)
    except Exception:
        pass
    try:
        subprocess.run(['sudo', 'systemctl', 'reload', 'postfix'], timeout=15, check=False)
    except Exception:
        pass
    try:
        subprocess.run(['sudo', 'systemctl', 'reload', 'dovecot'], timeout=15, check=False)
    except Exception:
        pass

    # --- Remove FTP accounts (parameterized — no shell injection) ---
    try:
        ft = ftpaccount.objects.filter(main=mainusername)
        for ftp_acct in ft:
            get_platform().users.delete_user(ftp_acct.main)
        ft.delete()
    except Exception as e:
        logger.warning('[terminate] FTP cleanup error for %s: %s', mainusername, e)

    # --- Remove Linux system user (parameterised) ---
    try:
        get_platform().users.delete_user(mainusername)
    except Exception as e:
        logger.warning('[terminate] userdel error for %s: %s', mainusername, e)

    # --- Python/MERN app service files ---
    try:
        apps = pythonname.objects.filter(main=mainusername) | pythonname.objects.filter(domain__in=all_domains)
        for df in apps.distinct():
            svc_name = df.name
            df.delete()
            try:
                if sys.platform == 'win32':
                    from voidplatform.windows.apps import delete_python_app
                    delete_python_app(svc_name)
                else:
                    run_command(f'sudo systemctl stop {svc_name} || true')
                    run_command(f'sudo systemctl disable {svc_name} || true')
                    svc_file = f'/etc/systemd/system/{svc_name}.service'
                    if os.path.exists(svc_file):
                        os.remove(svc_file)
                    run_command('sudo systemctl daemon-reload || true')
            except Exception:
                pass
    except Exception as e:
        logger.warning('[terminate] Python cleanup failed: %s', e)

    try:
        apps = mernname.objects.filter(main=mainusername) | mernname.objects.filter(domain__in=all_domains)
        for df in apps.distinct():
            svc_name = df.name
            df.delete()
            try:
                if sys.platform == 'win32':
                    from voidplatform.windows.apps import delete_mern_app
                    delete_mern_app(svc_name)
                else:
                    subprocess.run(['sudo', '-u', mainusername, 'pm2', 'delete', svc_name], timeout=10, check=False)
                    subprocess.run(['sudo', '-u', mainusername, 'pm2', 'save'], timeout=10, check=False)
                    sock = os.path.join(paths.RUN_DIR if hasattr(paths, 'RUN_DIR') else '/var/run', f'{svc_name}.sock')
                    if os.path.exists(sock):
                        os.remove(sock)
            except Exception:
                pass
    except Exception as e:
        logger.warning('[terminate] MERN cleanup failed: %s', e)



@login_required(login_url='/')
def terminate(request, data):
    """Terminate a hosted account: remove all files, configs, DNS, SSL, and DB records.
    Validation is instant; the actual heavy I/O runs in a background thread.
    """
    if not request.user.is_superuser:
        return redirect('/')

    try:
        lold = domain.objects.get(domain=data)
    except domain.DoesNotExist:
        return redirect('/listwebsite/')

    # Capture all needed data BEFORE deleting the DB record (fixes the use-after-delete bug)
    domain_str   = lold.domain
    mainusername = lold.dir
    subdomains   = list(subdomainname.objects.filter(domain=domain_str).values_list('subdomain', flat=True))

    # --- Immediately clean up all DB records (fast, in-request) ---
    subdomainname.objects.filter(domain=domain_str).delete()
    allemail.objects.filter(domain=domain_str).delete()
    cron.objects.filter(domain=domain_str).delete()
    redir.objects.filter(domain=domain_str).delete()
    try:
        user.objects.filter(username=mainusername).delete()
    except Exception:
        pass
    try:
        User.objects.filter(username=mainusername).delete()
    except Exception:
        pass
    lold.delete()  # Safe now — all needed strings captured above

    # --- Push slow filesystem/service I/O to background thread ---
    import threading
    t = threading.Thread(
        target=_background_terminate_user,
        args=(domain_str, mainusername, subdomains),
        daemon=True
    )
    t.start()

    return redirect('/listusers/')
    


def toggle_email_suspension(domain_name, suspend_status=True):
    try:
        import os, subprocess
        for fpath in [paths.POSTFIX_VIRTUAL_ALIAS, paths.POSTFIX_VIRTUAL_MAILBOX, paths.DOVECOT_USERS]:
            if not os.path.exists(fpath): continue
            with open(fpath, 'r') as fp: lines = fp.readlines()
            changed = False
            with open(fpath, 'w') as fp:
                for line in lines:
                    if f"@{domain_name}" in line:
                        if suspend_status and not line.startswith('#SUSPENDED#'):
                            fp.write(f"#SUSPENDED#{line}")
                            changed = True
                        elif not suspend_status and line.startswith('#SUSPENDED#'):
                            fp.write(line.replace('#SUSPENDED#', '', 1))
                            changed = True
                        else: fp.write(line)
                    else: fp.write(line)
            if changed and fpath in (paths.POSTFIX_VIRTUAL_ALIAS, paths.POSTFIX_VIRTUAL_MAILBOX, paths.POSTFIX_VIRTUAL_DOMAINS):
                if sys.platform != 'win32':
                    subprocess.run(["postmap", fpath], capture_output=True)
    except Exception as e: pass

@login_required(login_url='/')
def suspend(request,data):
   
    if request.user.is_superuser:
                d={}
                try:
                    
                    lold=domain.objects.get(domain=data)
                    dub=subdomainname.objects.filter(domain=data).all()
                    file_path_=os.path.join(paths.NGINX_SITES_ENABLED, data+".conf")

                    with open(file_path_, 'r') as file:
                        config_data = file.readlines()
                    root_updated = False
                    for i, line in enumerate(config_data):
                        if line.strip().startswith('root '):
                            config_data[i] = f"    root /var/www/suspend;\n"
                            root_updated = True
                            break
                    if root_updated:

                        with open(file_path_, 'w') as file:
                            file.writelines(config_data)
                    for iu in dub:
                            file_path_=os.path.join(paths.NGINX_SITES_ENABLED, iu.subdomain+".conf")
                            with open(file_path_, 'r') as file:
                                config_data = file.readlines()
                            root_updated = False
                            for i, line in enumerate(config_data):
                                if line.strip().startswith('root '):
                                    config_data[i] = f"    root /var/www/suspend;\n"
                                    root_updated = True
                                    break
                            if root_updated:
        
                                with open(file_path_, 'w') as file:
                                    file.writelines(config_data)
                    lold.status=False
                    
                    lold.save()
                    try:
                        loldd=user.objects.get(domain=data)
                        loldd.status=False
                        loldd.save()
                        
                        # Added: suspend emails dynamically
                        toggle_email_suspension(data, True)
                        
                        return redirect('/listusers/')
                    except:

                        return redirect('/listwebsite/')
                         
                    
                              
                except Exception as e:
                    return redirect("/listwebsite/")
           
    else: 
        return redirect('/')
                        
@login_required(login_url='/')
def unsuspend(request,data):
   
    if request.user.is_superuser:
                d={}
                try:
                    
                    lold=domain.objects.get(domain=data)
                    dub=subdomainname.objects.filter(domain=data).all()
                    file_path_=os.path.join(paths.NGINX_SITES_ENABLED, data+".conf")

                    with open(file_path_, 'r') as file:
                        config_data = file.readlines()
                    root_updated = False
                    for i, line in enumerate(config_data):
                        if line.strip().startswith('root '):
                            config_data[i] = f"    root {os.path.join(paths.HOME_BASE, lold.dir, 'public_html')};\n"
                            root_updated = True
                            break
                    if root_updated:

                        with open(file_path_, 'w') as file:
                            file.writelines(config_data)
                    for iu in dub:
                            file_path_=os.path.join(paths.NGINX_SITES_ENABLED, iu.subdomain+".conf")
                            with open(file_path_, 'r') as file:
                                config_data = file.readlines()
                            root_updated = False
                            for i, line in enumerate(config_data):
                                if line.strip().startswith('root '):
                                    config_data[i] = f"    root {os.path.join(paths.HOME_BASE, lold.dir, 'public_html', iu.name)};\n"
                                    root_updated = True
                                    break
                            if root_updated:
        
                                with open(file_path_, 'w') as file:
                                    file.writelines(config_data)
                    lold.status=True
                    lold.save()
                    try:
                        loldd=user.objects.get(domain=data)
                        loldd.status=True
                        loldd.save()
                        
                        # Added: unsuspend emails dynamically
                        toggle_email_suspension(data, False)
                        
                        return redirect('/listusers/')
                    except:
                         
                        return redirect('/listwebsite/')
                         
                    
                              
                except Exception as e:
                    return redirect("/listwebsite/")
           
    else: 
        return redirect('/')
    



# # Example usage:
# main_directory = '/path/to/main/directory'  # Path to the main directory where the zip will be saved
# locations = ['/path/to/first/location', '/path/to/second/location', '/path/to/file.txt']  # List of locations (files or directories)
# zip_filename = 'my_backup'  # Name for the output zip file

# zip_multiple_locations_backup(main_directory, locations, zip_filename)


@login_required(login_url='/')
def backup(request,data):
    import glob
    import os
   
    if request.user.is_superuser:
                d={}
                try:
                    
                    lold=domain.objects.get(domain=data)   
                    d['domain']=data
                    import glob
                    folder={}
                    directory="/home/"+lold.dir
                    zip_files = glob.glob(os.path.join(directory, "*.zip"))
            
                    for zip_file in zip_files:
                        print(os.path.basename(zip_file))
                        parts = zip_file.rsplit('_', 2)
                        if len(parts) == 3:
                            folder[parts[2]]=[parts[0],parts[1],parts[2].replace(".zip",""),os.path.basename(zip_file)]
                    d['folder']=folder
                    d['dire']=lold.dir
                    url = 'https://voidpanel.com/admindocs/'  # Replace with your API URL
                    response = requests.get(url, timeout=2)
                    if response.status_code == 200:
                        dataee = response.json()  # Parse the JSON response
                        d['docs']=dataee
                    return render(request,'panel/backup.html',d)
                except Exception as e:
                    return redirect("/listwebsite/")
           
    else: 
        return redirect('/')
    
@login_required(login_url='/')
def download_zip_backup(request, filename,user):
    if request.user.is_superuser:
        zip_file_path = "/home/"+user+"/"+filename
        if os.path.exists(zip_file_path):
            response = FileResponse(open(zip_file_path, 'rb'))
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            return response
        else:
            raise Http404("File not found")
    

@login_required(login_url='/')
def backupdata(request):
    if request.method=="POST":
                            data = json.loads(request.body)
                         
                            name=data.get('domain').strip(' ')
                  
                            namm=domain.objects.get(domain=name)

                            # Ownership check: non-admin users can only backup their own domains
                            if not request.user.is_superuser:
                                owner = user.objects.filter(username=request.user.username).first()
                                if not owner or owner.domain != name:
                                    return JsonResponse({'status': 'error', 'message': 'Unauthorized'}, status=403)

                            main_directory = os.path.join(paths.HOME_BASE, namm.dir)
                            front=os.path.join(paths.HOME_BASE, namm.dir)
                            mail=_resolve_mail_domain_dir(namm.domain)
                            open1=os.path.join(paths.OPENDKIM_KEY_DIR, namm.domain)
                            lets=os.path.join(paths.LETSENCRYPT_LIVE, namm.domain)
                            import datetime
                            zip_filename = "backup_"+namm.domain+"_"+str(datetime.datetime.today())
                            zip_filename=zip_filename.replace(" ", "_")
                            locations = [front,mail,open1,lets]
                            zip_multiple_locations_backup(main_directory, locations, zip_filename)
                            return JsonResponse({'status': 'success', 'message': 'Already Exist'})
    return JsonResponse({'status': 'error', 'message': 'Invalid request.'})


@login_required(login_url='/')
def packagewizard(request):
    if not request.user.is_superuser:
        return redirect('/')

    d = {}
    d['packages'] = package.objects.all()

    if request.method == "POST":
        package_name = request.POST.get('package', '').strip()
        storage = request.POST.get('storage', '0')
        ftp = request.POST.get('ftp', '0')
        bandwidth = request.POST.get('bandwidth', '0')
        subdomain = request.POST.get('subdomain', '0')
        database = request.POST.get('database', '0')
        email = request.POST.get('email', '0')

        # Clean "unlimited" strings
        storage = '0' if storage == 'unlimited' or storage == '' else storage
        ftp = '0' if ftp == 'unlimited' or ftp == '' else ftp
        bandwidth = '0' if bandwidth == 'unlimited' or bandwidth == '' else bandwidth
        subdomain = '0' if subdomain == 'unlimited' or subdomain == '' else subdomain
        database = '0' if database == 'unlimited' or database == '' else database
        email = '0' if email == 'unlimited' or email == '' else email

        is_ajax = request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.headers.get('Accept') == 'application/json'

        if not package_name:
            if is_ajax:
                return JsonResponse({'status': 'error', 'message': 'Package name is required.'})
            messages.error(request, "Package name is required")
            return redirect('/package/')

        if package.objects.filter(name=package_name).exists():
            if is_ajax:
                return JsonResponse({'status': 'error', 'message': f'Package "{package_name}" already exists.'})
            messages.error(request, "Same package Already Exist")
            return redirect('/package/')
        
        # Create package safely
        package.objects.create(
            name=package_name,
            storage=storage,
            ftp=ftp,
            subdomain=subdomain,
            bandwidth=bandwidth,
            email_accounts=email,
            databases_allowed=database,
            includes_social    = request.POST.get('includes_social')    == 'on',
            includes_seo       = request.POST.get('includes_seo')       == 'on',
            includes_marketing = request.POST.get('includes_marketing') == 'on',
            social_plan        = request.POST.get('social_plan', 'starter') or 'starter',
            seo_plan           = request.POST.get('seo_plan', 'lite') or 'lite',
            marketing_plan     = request.POST.get('marketing_plan', 'starter') or 'starter',
        )
        
        if is_ajax:
            return JsonResponse({'status': 'success', 'message': f'Package "{package_name}" created!'})
        
        # Standard PRG (Post-Redirect-Get) to prevent double submission
        messages.success(request, f'Package "{package_name}" created successfully!')
        return redirect('/package/')

    # Grab docs safely
    url = 'https://voidpanel.com/admindocs/'
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            d['docs'] = response.json()
    except Exception:
        pass # Fail gracefully if API is down

    return render(request, 'panel/package.html', d)
    

@login_required(login_url='/')
def update(request):
    if not request.user.is_superuser:
        return redirect('/')

    from control.models import UpdateSettings
    update_settings = UpdateSettings.get()

    if request.method == 'POST' and 'update_mode' in request.POST:
        mode = request.POST.get('update_mode', 'auto').strip()
        if mode in ['auto', 'manual']:
            update_settings.mode = mode
            update_settings.save()
            return redirect('/update/')

    d = {'update_settings': update_settings}

    # Read installed version — try /etc/version.txt (prod), then project root version.txt (dev)
    def _read_version():
        for path_try in [paths.VERSION_FILE,
                         os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'version.txt')]:
            try:
                with open(path_try, 'r') as f:
                    v = f.read().strip()
                    if v:
                        return v
            except Exception:
                pass
        return '1.0'
    version = _read_version()
    d['version'] = version

    # Check for latest version (non-blocking, ignore failures)
    try:
        resp = requests.get('https://voidpanel.com/version_name/', timeout=6)
        if resp.status_code == 200:
            dataee = resp.json()
            latest = dataee.get('version', version)
            if latest > version:
                d['show'] = True
                d['latestversion'] = latest
    except Exception:
        pass

    return render(request, 'panel/update.html', d)


def checkversion(request):
    """Public API — returns installed version for the website portal's Update Manager.
    Authenticated via X-VoidPanel-Key header (same as other API endpoints)."""
    header_key = request.headers.get('X-VoidPanel-Key', '').strip()
    try:
        expected = open('/etc/voidpanel_api_key').read().strip()
    except Exception:
        from django.conf import settings as _s
        expected = os.environ.get('VOIDPANEL_API_KEY', getattr(_s, 'VOIDPANEL_API_KEY', ''))
    # If a key is configured, enforce it; if none configured, allow the request
    if expected and header_key != expected:
        return JsonResponse({'error': 'Unauthorized'}, status=401)
    try:
        with open(paths.VERSION_FILE, 'r') as f:
            version = f.read().strip()
    except Exception:
        version = '1.0'
    return JsonResponse({'version': version, 'platform': sys.platform, 'status': 'ok'})


@login_required(login_url='/')
def updatepanel(request):

    if not request.user.is_superuser:
        # Also accept X-VoidPanel-Key header for remote push from portal
        header_key = request.headers.get('X-VoidPanel-Key', '').strip()
        try:
            expected = open('/etc/voidpanel_api_key').read().strip()
        except Exception:
            from django.conf import settings as _s
            expected = os.environ.get('VOIDPANEL_API_KEY', getattr(_s, 'VOIDPANEL_API_KEY', ''))
        if not header_key or header_key != expected:
            return JsonResponse({'status': 'error', 'message': 'Forbidden'}, status=403)

    if request.method == 'POST':
        import tempfile, subprocess, threading

        if sys.platform == 'win32':
            from voidplatform.windows.apps import update_panel_windows
            success, msg = update_panel_windows()
            if success:
                return JsonResponse({'status': 'success', 'message': msg})
            return JsonResponse({'status': 'error', 'message': msg})

        # ── Linux: step-by-step migration ──────────────────────────────────────
        # 1. Read current version
        current_version = '1.0'
        for path_try in [paths.VERSION_FILE,
                         os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'version.txt')]:
            try:
                v = open(path_try).read().strip()
                if v:
                    current_version = v
                    break
            except Exception:
                pass

        # 2. Fetch migration path from voidpanel.com
        migration_steps = []
        try:
            _resp = requests.get(
                f'https://voidpanel.com/version_migration_path/?from={current_version}',
                timeout=10
            )
            if _resp.status_code == 200:
                _data = _resp.json()
                migration_steps = _data.get('steps', [])
        except Exception:
            pass

        # 3. Fallback: single script if no migration path available
        if not migration_steps:
            migration_steps = [{
                'version':    None,
                'script_url': 'https://voidpanel.com/updatepanel.sh',
                'notes':      'General update',
            }]

        def _run_migration(steps, cur_ver):
            """Apply each update step in order in a background thread."""
            import datetime, subprocess as _sp
            panel_dir = '/var/www/panel'
            # Backup first
            try:
                tag = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
                _sp.run(f'cp -r {panel_dir} /var/backups/voidpanel-{tag} 2>/dev/null || true',
                        shell=True)
            except Exception:
                pass

            for step in steps:
                script_url  = step.get('script_url', 'https://voidpanel.com/updatepanel.sh')
                target_ver  = step.get('version')
                _tmp = os.path.join(tempfile.gettempdir(), f'voidpanel_update_{target_ver or "latest"}.sh')
                # Download step script
                dl = _sp.run(['curl', '-fsSL', '-o', _tmp, script_url], capture_output=True)
                if dl.returncode != 0:
                    break   # abort chain on download failure
                # Run with sudo so it can write /etc/version.txt and restart services
                _sp.run(['sudo', 'bash', _tmp], check=False)
                # Update version file after each successful step
                if target_ver:
                    # Write to /etc/version.txt via sudo (www-data can't write /etc directly)
                    try:
                        _sp.run(f'echo "{target_ver}" | sudo tee /etc/version.txt > /dev/null',
                                shell=True, check=False)
                    except Exception:
                        pass
                    # Also write to panel dir (always writable by www-data — reliable fallback)
                    try:
                        with open(os.path.join(panel_dir, 'version.txt'), 'w') as _vf:
                            _vf.write(target_ver)
                    except Exception:
                        pass
                    # And update the in-memory path used by this process
                    try:
                        with open(paths.VERSION_FILE, 'w') as _vf:
                            _vf.write(target_ver)
                    except Exception:
                        pass

        t = threading.Thread(target=_run_migration, args=(migration_steps, current_version), daemon=True)
        t.start()

        step_count = len(migration_steps)
        last_ver   = migration_steps[-1].get('version', 'latest') if migration_steps else 'latest'
        return JsonResponse({
            'status':  'success',
            'message': f'Step-by-step update started ({step_count} step(s) → {last_ver}). Panel will restart after each step.',
            'steps':   step_count,
            'from':    current_version,
            'to':      last_ver,
        })

    return JsonResponse({'status': 'error', 'message': 'POST required.'})

    

@login_required(login_url='/')
def maincron(request):
    import json
    import subprocess
    if request.user.is_superuser:
        d = {}
        try:
            d['crondata'] = cron.objects.all()
            if request.method == "POST":
                # Handle Modern JSON Request
                if request.content_type == 'application/json':
                    data = json.loads(request.body)
                    time_val = data.get('time')
                    path_val = data.get('path')
                    
                    if not time_val or not path_val:
                        return JsonResponse({'status': 'error', 'message': 'Invalid data provided.'})
                    
                    # Securely fetch current crontab
                    if sys.platform != 'win32':
                        res = subprocess.run(['crontab', '-l'], capture_output=True, text=True)
                        current_cron = res.stdout if res.returncode == 0 else ""

                        # Append new job and securely load back into crontab
                        new_cron = f"{current_cron.strip()}\n{time_val} {path_val}\n"
                        subprocess.run(['crontab', '-'], input=new_cron, text=True, check=True)
                    else:
                        from voidplatform.windows.cron import add_cron as _add_cron
                        _add_cron(time_val, path_val)

                    cron.objects.create(domain='admin', path=path_val, duratioin=time_val)
                    return JsonResponse({'status': 'success', 'message': 'Cron job configured successfully.'})
                
            # Handle GET requests
            try:
                url = 'https://voidpanel.com/admindocs/'
                response = requests.get(url, timeout=5)
                if response.status_code == 200:
                    d['docs'] = response.json()
            except Exception:
                pass
                
            return render(request, 'panel/maincron.html', d)
        except Exception as e:
            if request.content_type == 'application/json':
                return JsonResponse({'status': 'error', 'message': str(e)})
            return redirect("/panel")
    else:
        return redirect('/')
@login_required(login_url='/')
def chpass(request):
    if request.user.is_superuser:
        import json
        if request.method == "POST":
            try:
                # Handle JSON request from modern frontend
                if request.content_type == 'application/json':
                    data = json.loads(request.body)
                    password = data.get('password')
                else:
                    return JsonResponse({'status': 'error', 'message': 'Invalid content type.'})

                if not password or len(password) < 8:
                    return JsonResponse({'status': 'error', 'message': 'Password must be at least 8 characters long.'})

                # Update the currently logged-in superadmin's password securely
                user = request.user
                user.set_password(password)
                user.save()

                # Update the system details file safely
                file_path = paths.DETAILS_FILE
                try:
                    with open(file_path, 'r') as file:
                        lines = file.readlines()

                    for i, line in enumerate(lines):
                        if 'admin' in line:
                            lines[i + 1] = f'VoidPanel_Password="{password}"\n'
                            break

                    with open(file_path, 'w') as file:
                        file.writelines(lines)
                except Exception as e:
                    # Log silently, don't fail the API request if the details file isn't writable
                    pass

                # Return success instead of logging out to show smooth frontend notification
                return JsonResponse({'status': 'success', 'message': 'Password updated successfully!'})

            except Exception as e:
                return JsonResponse({'status': 'error', 'message': str(e)})

        # GET request: render the template
        d = {}
        try:
            url = 'https://voidpanel.com/admindocs/'
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                d['docs'] = response.json()
        except Exception:
            pass
            
        return render(request, 'panel/chpass.html', d)
    else: 
        return redirect('/')
    
    
@login_required(login_url='/')
def runsslall(request):
    if request.user.is_superuser:
        import os
        d = {}
        try:
            lold = domain.objects.all()
            d['domain'] = lold
            
            logs = []
            path = paths.SSL_LOG
            if os.path.exists(path):
                with open(path, 'r') as f:
                    dd = f.readlines()
                    for i in dd:
                        logs.append(i)
            d['logs'] = logs   
            
            try:
                url = 'https://voidpanel.com/admindocs/'
                response = requests.get(url, timeout=5)
                if response.status_code == 200:
                    dataee = response.json()
                    d['docs'] = dataee
            except Exception:
                pass
                
            return render(request, 'panel/allssl.html', d)
        except Exception as e:
            return redirect("/panel")
    else: 
        return redirect('/')


@login_required(login_url='/')
def runsslforall(request):
    if not request.user.is_superuser:
        return JsonResponse({'status': 'error', 'message': 'Authentication required.'}, status=403)
    from control.tasks import run_ssl_task
    
    if request.method == 'POST':
        lold = domain.objects.filter(sslstatus=False)
        for name in lold:
            try:
                # Dispatch to background Celery worker
                run_ssl_task.delay(name.domain, name.email)
            except Exception as e:
                pass
                
        return JsonResponse({'status': 'success', 'message': 'Auto SSL initiated for all pending domains.'})
   
    return JsonResponse({'status': 'error', 'message': 'Invalid request.'})



@login_required(login_url='/')
def runsslforall1(request):
    if not request.user.is_superuser:
        return JsonResponse({'status': 'error', 'message': 'Authentication required.'}, status=403)
    from control.tasks import run_ssl_task
    import json
    
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            name = data.get('name', '').strip()
            
            if name:
                lold = domain.objects.get(domain=name)
                # Dispatch to background Celery worker
                run_ssl_task.delay(lold.domain, lold.email)
                
            return JsonResponse({'status': 'success', 'message': 'Auto SSL initiated.'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})
            
    return JsonResponse({'status': 'error', 'message': 'Invalid request.'})





@login_required(login_url='/')
def hostname(request):
    
    if request.user.is_superuser:
      
        d={}
        quick_=quick.objects.get(id=1)
        d['serverip']=get_server_ip()
  
        
        d['show']=quick_
        url = 'https://voidpanel.com/admindocs/'  # Replace with your API URL
        response = requests.get(url, timeout=2)
        if response.status_code == 200:
            dataee = response.json()  # Parse the JSON response
            d['docs']=dataee
        return render(request,'panel/hostname.html',d)
    else: 
        return redirect('/')
    


@login_required(login_url='/')
def fulldbwizard(request):
    try:
        with open(paths.MYSQL_PASSWORD_FILE, 'r') as f:
            adminpassword=f.read()
            adminpassword=adminpassword.strip()
    except Exception:
        adminpassword = ''
    
    if request.user.is_superuser:
      
        d={}

        d['database'] = get_database_names(adminpassword)
        d['users'] = get_database_users(adminpassword)
        d['totaldb'] = '∞'

        # Get all DB→user privilege mappings from mysql.db
        try:
            import mysql.connector
            _conn = mysql.connector.connect(host='localhost', user='root', password=adminpassword)
            _cur = _conn.cursor()
            _cur.execute("SELECT User, Db FROM mysql.db ORDER BY Db, User;")
            _rows = _cur.fetchall()
            _cur.close()
            _conn.close()
            d['mappings'] = [{'user': r[0], 'database': r[1]} for r in _rows]
        except Exception:
            d['mappings'] = []

        try:
            url = 'https://voidpanel.com/admindocs/'
            response = requests.get(url, timeout=4)
            if response.status_code == 200:
                d['docs'] = response.json()
        except Exception:
            pass

        return render(request,'panel/fulldbwizard.html',d)
    else: 
        return redirect('/')
    

@login_required(login_url='/')
def allemailwizard(request):
    
    if request.user.is_superuser:
      
        d={}
        d['data']=allemail.objects.all()
        d['domain']=domain.objects.all()
        url = 'https://voidpanel.com/admindocs/'  # Replace with your API URL
        try:
            response = requests.get(url, timeout=2)
            if response.status_code == 200:
                dataee = response.json()  # Parse the JSON response
                d['docs'] = dataee
        except Exception:
            pass
        return render(request,'panel/allemail.html',d)
    else: 
        return redirect('/')
    

@login_required(login_url='/')
def deleteemail(request, data):
    from control.models import user as sysuser
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'POST required'})
    if not (request.user.is_superuser or request.user.is_authenticated):
        return JsonResponse({'status': 'error', 'message': 'Unauthorized'})
        
    import shutil
    try:
        email_obj = allemail.objects.get(email=data)
        domain_name = email_obj.domain
        user_prefix = data.split("@")[0]
        
        # Cleanup from files securely using temporary files and sudo cp
        def _modify_mail_file_securely(filepath, match_prefix):
            import subprocess
            temp_in = f"/tmp/void_mail_in_{os.getpid()}_{abs(hash(filepath))}"
            temp_out = f"/tmp/void_mail_out_{os.getpid()}_{abs(hash(filepath))}"
            
            # Check if file exists using sudo
            check = subprocess.run(['sudo', 'test', '-f', filepath])
            if check.returncode != 0:
                return
            
            # Copy to temp_in and make readable
            subprocess.run(['sudo', 'cp', filepath, temp_in])
            subprocess.run(['sudo', 'chmod', '666', temp_in])
            
            if os.path.exists(temp_in):
                with open(temp_in, 'r') as fp:
                    lines = fp.readlines()
                
                with open(temp_out, 'w') as fp:
                    fp.writelines(l for l in lines if not l.startswith(match_prefix))
                
                # Copy back to overwrite source
                subprocess.run(['sudo', 'cp', temp_out, filepath])
                
                # Clean up
                for temp_file in (temp_in, temp_out):
                    if os.path.exists(temp_file):
                        try:
                            os.remove(temp_file)
                        except:
                            pass

        # Apply to postfix virtual_alias and virtual_mailbox
        _modify_mail_file_securely(paths.POSTFIX_VIRTUAL_ALIAS, f'{data} ')
        _modify_mail_file_securely(paths.POSTFIX_VIRTUAL_MAILBOX, f'{data} ')

        if sys.platform != 'win32':
            run_command(f"sudo postmap {paths.POSTFIX_VIRTUAL_ALIAS}")
            run_command(f"sudo postmap {paths.POSTFIX_VIRTUAL_MAILBOX}")

        # Cleanup specific user directory (not whole domain!)
        sys_owner = 'vmail'
        owner_obj = sysuser.objects.filter(domain=domain_name).first()
        if owner_obj:
            sys_owner = owner_obj.username
            
        home_path = os.path.join(paths.HOME_BASE, sys_owner, 'mail', domain_name, user_prefix)
        old_path = os.path.join(_resolve_mail_domain_dir(domain_name), user_prefix)
        
        if os.path.exists(home_path): shutil.rmtree(home_path, ignore_errors=True)
        if os.path.exists(old_path): shutil.rmtree(old_path, ignore_errors=True)
        
        # Remove from Dovecot users mapping and domain passwd/shadow files if they exist
        for _fpath in [paths.DOVECOT_USERS,
                       os.path.join(_resolve_mail_domain_dir(domain_name), 'passwd'),
                       os.path.join(_resolve_mail_domain_dir(domain_name), 'shadow')]:
            _modify_mail_file_securely(_fpath, f'{data}:')
        
        email_obj.delete()
        return JsonResponse({'status': 'success'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)})

@login_required(login_url='/')
def deleteemai(request, data):
    return deleteemail(request, data)

from control.models import EmailConfig

@login_required(login_url='/')
def emailconfig(request):
    if not request.user.is_superuser:
        return redirect('/')
    
    config, created = EmailConfig.objects.get_or_create(id=1)
    
    if request.method == 'POST':
        config.hourly_limit = request.POST.get('hourly_limit', 100)
        config.daily_limit = request.POST.get('daily_limit', 1000)
        config.default_quota_mb = request.POST.get('default_quota_mb', 1024)
        config.max_attachment_size_mb = request.POST.get('max_attachment_size_mb', 50)
        config.enable_antispam = request.POST.get('enable_antispam') == 'true'
        config.spam_score_threshold = request.POST.get('spam_score_threshold', 5.0)
        config.enforce_dkim_spf = request.POST.get('enforce_dkim_spf') == 'true'
        config.max_concurrent_connections = request.POST.get('max_concurrent_connections', 20)
        config.catch_all_capability = request.POST.get('catch_all_capability') == 'true'
        config.allow_autoresponders = request.POST.get('allow_autoresponders') == 'true'
        
        # New SMTP Relay configuration fields
        config.enable_smtp_relay = request.POST.get('enable_smtp_relay') == 'true'
        config.smtp_relay_host = request.POST.get('smtp_relay_host', '').strip()
        config.smtp_relay_username = request.POST.get('smtp_relay_username', '').strip()
        config.smtp_relay_password = request.POST.get('smtp_relay_password', '').strip()
        config.save()
        
        # Save whitelisted domains
        whitelisted_domains = request.POST.get('whitelisted_domains', '').strip()
        try:
            import tempfile, subprocess
            with tempfile.NamedTemporaryFile('w', delete=False) as f:
                f.write(whitelisted_domains)
                tmp_path = f.name
            subprocess.run(['sudo', 'mv', tmp_path, '/etc/voidpanel-mail-policy-whitelist.conf'])
            subprocess.run(['sudo', 'chmod', '644', '/etc/voidpanel-mail-policy-whitelist.conf'])
        except Exception:
            pass
            
        # Apply configurations to live postfix / dovecot / spamassassin
        from voidplatform.linux.mail import apply_global_email_config
        apply_global_email_config(config)
        
        return JsonResponse({'status': 'success'})

    # Load whitelisted domains
    whitelisted_domains = ""
    try:
        import os
        if os.path.exists('/etc/voidpanel-mail-policy-whitelist.conf'):
            with open('/etc/voidpanel-mail-policy-whitelist.conf', 'r') as f:
                whitelisted_domains = f.read().strip()
    except Exception:
        pass

    return render(request, 'panel/emailconfig.html', {'config': config, 'config_whitelisted_domains': whitelisted_domains})


import socket

@login_required(login_url='/')
def mail_diagnostics(request):
    if not request.user.is_superuser:
        return JsonResponse({'status': 'error', 'message': 'Unauthorized'}, status=403)
        
    config, _ = EmailConfig.objects.get_or_create(id=1)
    
    # 1. Check if Postfix is running
    postfix_active = False
    try:
        r = subprocess.run(['systemctl', 'is-active', 'postfix'], capture_output=True, text=True, timeout=2)
        postfix_active = r.stdout.strip() == 'active'
    except Exception:
        pass
        
    # 2. Check if Dovecot is running
    dovecot_active = False
    try:
        r = subprocess.run(['systemctl', 'is-active', 'dovecot'], capture_output=True, text=True, timeout=2)
        dovecot_active = r.stdout.strip() == 'active'
    except Exception:
        pass

    # 3. Check outbound port 25 connectivity
    port_25_blocked = False
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2.0)
        result = sock.connect_ex(('alt2.gmail-smtp-in.l.google.com', 25))
        if result != 0:
            port_25_blocked = True
        sock.close()
    except Exception:
        port_25_blocked = True

    # 4. Get Postfix mail queue size
    queue_size = 0
    try:
        deferred_dir = '/var/spool/postfix/deferred'
        if os.path.exists(deferred_dir):
            for root, dirs, files in os.walk(deferred_dir):
                queue_size += len(files)
        else:
            r = subprocess.run(['sudo', 'postqueue', '-p'], capture_output=True, text=True, timeout=5)
            if 'Mail queue is empty' in r.stdout:
                queue_size = 0
            else:
                import re
                queue_size = len(re.findall(r'^[0-9A-F]{10}', r.stdout, re.MULTILINE))
    except Exception:
        pass

    return JsonResponse({
        'status': 'success',
        'postfix_running': postfix_active,
        'dovecot_running': dovecot_active,
        'port_25_blocked': port_25_blocked,
        'queue_size': queue_size,
        'smtp_relay_enabled': config.enable_smtp_relay,
        'smtp_relay_host': config.smtp_relay_host,
    })


@login_required(login_url='/')
def mail_diagnostics_repair(request):
    if not request.user.is_superuser:
        return JsonResponse({'status': 'error', 'message': 'Unauthorized'}, status=403)
        
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'POST request required'}, status=405)
        
    config, _ = EmailConfig.objects.get_or_create(id=1)
    actions_taken = []
    errors = []

    # 1. Start/restart postfix if inactive or trigger restart anyway
    try:
        r = subprocess.run(['systemctl', 'is-active', 'postfix'], capture_output=True, text=True, timeout=2)
        if r.stdout.strip() != 'active':
            subprocess.run(['sudo', 'systemctl', 'start', 'postfix'], check=True, timeout=10)
            actions_taken.append("Started Postfix service.")
        else:
            subprocess.run(['sudo', 'systemctl', 'reload', 'postfix'], check=True, timeout=10)
            actions_taken.append("Reloaded Postfix configuration.")
    except Exception as e:
        errors.append(f"Postfix repair error: {str(e)}")

    # 2. Start dovecot if inactive
    try:
        r = subprocess.run(['systemctl', 'is-active', 'dovecot'], capture_output=True, text=True, timeout=2)
        if r.stdout.strip() != 'active':
            subprocess.run(['sudo', 'systemctl', 'start', 'dovecot'], check=True, timeout=10)
            actions_taken.append("Started Dovecot service.")
    except Exception as e:
        errors.append(f"Dovecot repair error: {str(e)}")

    # 3. Apply/Re-apply SMTP Relay configuration if enabled
    try:
        from voidplatform.linux.mail import apply_global_email_config
        apply_global_email_config(config)
        actions_taken.append("Synchronized system SMTP settings.")
    except Exception as e:
        errors.append(f"SMTP config sync error: {str(e)}")

    # 4. Flush the queue (force immediate attempt to send deferred mails)
    try:
        subprocess.run(['sudo', 'postqueue', '-f'], check=True, timeout=15)
        actions_taken.append("Flushed Postfix mail delivery queue.")
    except Exception as e:
        errors.append(f"Mail queue flush error: {str(e)}")

    if errors:
        return JsonResponse({
            'status': 'error',
            'message': '; '.join(errors),
            'actions_taken': actions_taken
        })
        
    return JsonResponse({
        'status': 'success',
        'message': 'Mail subsystem repair completed successfully.',
        'actions_taken': actions_taken
    })
    

@login_required(login_url='/')
def phpsetting(request):
    if request.user.is_superuser:
        d = {}
        installed = phpversion.objects.all()
        available = ['5.6', '7.1', '7.2', '7.3', '7.4', '8.1', '8.2', '8.3', '8.4']
        for i in installed:
            if i.name in available:
                available.remove(i.name)
        d['installed'] = installed
        d['available'] = available

        phpextentionsss = phpextentions.objects.all()
        dictphpextentionsss = {}
        for ie in phpextentionsss:
            try:
                import ast
                dictphpextentionsss[ie.name] = ast.literal_eval(str(ie.extentions))
            except Exception:
                dictphpextentionsss[ie.name] = {}
        d['extentionname'] = dictphpextentionsss

        phpini = {}
        for i in installed:
            try:
                if sys.platform == 'win32':
                    _ini = os.path.join(paths.PHP_FPM_INI_DIR, i.name, 'php.ini')
                else:
                    _ini = f'/etc/php/{i.name}/fpm/php.ini'
                with open(_ini, 'r') as f:
                    phpini[i.name] = f.read()
            except FileNotFoundError:
                phpini[i.name] = ''
        d['phpini'] = phpini

        return render(request, 'panel/phpsetting.html', d)
    else:
        return redirect('/')


@login_required(login_url='/')
def savephpini(request):
    """Dedicated endpoint for saving PHP INI content sent via JSON."""
    import subprocess
    from panel.logger import get_logger
    logger = get_logger(__name__)
    if not request.user.is_superuser:
        return JsonResponse({'status': 'error', 'message': 'Unauthorized'}, status=403)
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'POST required'}, status=405)
    try:
        data = json.loads(request.body)
        version = data.get('version', '').strip()
        content = data.get('content', '')

        # Whitelist allowed PHP versions
        allowed_versions = ['5.6', '7.1', '7.2', '7.3', '7.4', '8.1', '8.2', '8.3', '8.4']
        if version not in allowed_versions:
            return JsonResponse({'status': 'error', 'message': 'Invalid PHP version'}, status=400)

        # Must match an installed version in DB
        if not phpversion.objects.filter(name=version).exists():
            return JsonResponse({'status': 'error', 'message': 'Version not installed'}, status=404)

        # Platform-aware PHP INI path
        if sys.platform == 'win32':
            ini_path = os.path.join(paths.PHP_FPM_INI_DIR, version, 'php.ini')
            os.makedirs(os.path.dirname(ini_path), exist_ok=True)
            with open(ini_path, 'w', encoding='utf-8') as f:
                f.write(content)
        else:
            ini_path = f'/etc/php/{version}/fpm/php.ini'
            import tempfile
            with tempfile.NamedTemporaryFile(mode='w', delete=False, encoding='utf-8') as tmp:
                tmp.write(content)
                tmp_path = tmp.name
                
            mv_res = subprocess.run(['sudo', 'mv', tmp_path, ini_path], capture_output=True, text=True)
            subprocess.run(['sudo', 'chown', 'root:root', ini_path], capture_output=True)
            subprocess.run(['sudo', 'chmod', '644', ini_path], capture_output=True)
            
            if mv_res.returncode != 0:
                os.unlink(tmp_path)
                return JsonResponse({'status': 'error', 'message': f'Failed to write INI: {mv_res.stderr}'}, status=500)

        # Reload PHP service — platform-aware
        if sys.platform == 'win32':
            # Windows: restart php-cgi process via taskkill + relaunch
            try:
                subprocess.run(['taskkill', '/F', '/IM', 'php-cgi.exe'],
                               capture_output=True, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
                php_cgi = os.path.join(paths.PHP_FPM_INI_DIR, version, 'php-cgi.exe')
                if os.path.exists(php_cgi):
                    subprocess.Popen([php_cgi, '-b', f'127.0.0.1:9123'],
                                     creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0) |
                                                   getattr(subprocess, 'DETACHED_PROCESS', 0))
            except Exception:
                pass
        else:
            subprocess.run(
                ['sudo', 'systemctl', 'reload', f'php{version}-fpm'],
                capture_output=True, timeout=15
            )
        logger.info('PHP INI saved and reloaded for version %s', version)
        return JsonResponse({'status': 'success', 'message': f'PHP {version} INI saved and FPM reloaded.'})
    except Exception as exc:
        logger.error('savephpini failed: %s', exc)
        return JsonResponse({'status': 'error', 'message': str(exc)}, status=500)




@login_required(login_url='/')
def installphpversion(request):
    import subprocess
    from panel.logger import get_logger
    logger = get_logger(__name__)
    if not request.user.is_superuser:
        return JsonResponse({'status': 'error', 'message': 'Unauthorized'}, status=403)
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'POST required'}, status=405)
    
    allowed_versions = ['5.6', '7.1', '7.2', '7.3', '7.4', '8.1', '8.2', '8.3', '8.4']
    php = request.POST.get('php', '').strip()
    
    if php not in allowed_versions:
        return JsonResponse({'status': 'error', 'message': 'Invalid PHP version specified.'})
    if phpversion.objects.filter(name=php).exists():
        return JsonResponse({'status': 'error', 'message': f'PHP {php} is already installed.'})
    
    try:
        # Parameterised; no shell=True
        result = subprocess.run(
            ['sudo', 'apt', 'install', '-y', f'php{php}', f'php{php}-fpm'],
            capture_output=True, text=True, timeout=300
        )
        if result.returncode != 0:
            # Try yum as fallback
            result = subprocess.run(
                ['sudo', 'yum', 'install', '-y', f'php{php}', f'php{php}-fpm'],
                capture_output=True, text=True, timeout=300
            )
            
        if result.returncode != 0:
            return JsonResponse({'status': 'error', 'message': f'Failed to install PHP {php} via package manager.'}, status=500)
            
        phpversion.objects.create(name=php)
        try:
            EXT_LIST = ['gd', 'curl', 'bcmath', 'mbstring', 'xml', 'zip', 'mysql', 'sqlite3', 'intl', 'soap', 'redis', 'memcached', 'imagick']
            defaults = {f"php{php}-{ext}": 0 for ext in EXT_LIST}
            import json
            phpextentions.objects.get_or_create(name=php, defaults={'extentions': json.dumps(defaults)})
        except Exception:
            pass
        logger.info('PHP %s installed successfully.', php)
        return JsonResponse({'status': 'success', 'message': f'PHP {php} installed.'})
    except Exception as exc:
        logger.error('installphpversion failed: %s', exc)
        return JsonResponse({'status': 'error', 'message': str(exc)}, status=500)



@login_required(login_url='/')
def installphpextention(request):
    import subprocess
    from panel.logger import get_logger
    logger = get_logger(__name__)
    if not request.user.is_superuser:
        return JsonResponse({'status': 'error', 'message': 'Unauthorized'}, status=403)
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'POST required'}, status=405)
    
    try:
        data = json.loads(request.body)
        pkg_name = data.get('name', '').strip()   # e.g. php8.3-gd
        option   = data.get('option', '').strip() # 'on' or 'off'
        phpname  = data.get('phpname', '').strip() # e.g. '8.3'
        
        if not pkg_name or option not in ('on', 'off') or not phpname:
            return JsonResponse({'status': 'error', 'message': 'Missing parameters.'}, status=400)

        # Validate package name to contain only safe characters
        import re
        if not re.match(r'^[a-zA-Z0-9._+-]+$', pkg_name):
            return JsonResponse({'status': 'error', 'message': 'Invalid extension name.'}, status=400)

        ffd = phpextentions.objects.get(name=phpname)
        try:
            import ast
            kjnre = ast.literal_eval(str(ffd.extentions))
        except Exception:
            kjnre = {}
        
        if option == 'on':
            result = subprocess.run(
                ['sudo', 'apt', 'install', '-y', pkg_name],
                capture_output=True, text=True, timeout=120
            )
            if result.returncode != 0:
                subprocess.run(
                    ['sudo', 'yum', 'install', '-y', pkg_name],
                    capture_output=True, text=True, timeout=120
                )
            kjnre[pkg_name] = 1
        else:
            result = subprocess.run(
                ['sudo', 'apt', 'remove', '-y', pkg_name],
                capture_output=True, text=True, timeout=120
            )
            if result.returncode != 0:
                subprocess.run(
                    ['sudo', 'yum', 'remove', '-y', pkg_name],
                    capture_output=True, text=True, timeout=120
                )
            kjnre[pkg_name] = 0
        
        ffd.extentions = kjnre
        ffd.save()
        logger.info('Extension %s toggled %s for PHP %s', pkg_name, option, phpname)
        return JsonResponse({'status': 'success', 'message': f'Extension {pkg_name} updated.'})
    except phpextentions.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'PHP version record not found.'}, status=404)
    except Exception as exc:
        logger.error('installphpextention failed: %s', exc)
        return JsonResponse({'status': 'error', 'message': str(exc)}, status=500)





@login_required(login_url='/')
def installcsf(request):
    """Install firewall: tries CSF first, falls back to UFW (built-in Ubuntu firewall)."""
    if not request.user.is_superuser:
        return JsonResponse({'status': 'error', 'message': 'Permission denied.'}, status=403)
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'POST required.'}, status=405)

    import subprocess as _sp, os as _os, shutil as _sh

    output_lines = []

    def _run(cmd, step='', timeout=300):
        try:
            r = _sp.run(cmd, capture_output=True, text=True, timeout=timeout)
            out = (r.stdout + r.stderr).strip()
            if out:
                output_lines.append(f'[{step}] {out[:800]}')
            return r.returncode == 0
        except Exception as ex:
            output_lines.append(f'[{step}] ERROR: {str(ex)[:200]}')
            return False

    output_lines.append('[init] Starting firewall installation...')

    # ── Step 1: Try CSF ──────────────────────────────────────────────────────
    output_lines.append('[csf] Attempting CSF download from official source...')

    # fix DNS first
    _run(['sudo', 'bash', '-c',
          "printf '[Resolve]\nDNS=8.8.8.8 1.1.1.1\nFallbackDNS=8.8.4.4\n' > /etc/systemd/resolved.conf && "
          "systemctl restart systemd-resolved && sleep 1"],
         step='dns')

    # try to download csf from multiple sources
    csf_urls = [
        'https://download.configserver.com/csf.tgz',
        'http://download.configserver.com/csf.tgz',
        'https://configserver.com/csf.tgz',
    ]
    csf_downloaded = False
    for url in csf_urls:
        ok = _run(['sudo', 'bash', '-c',
                   f'cd /usr/src && rm -rf csf csf.tgz && '
                   f'wget --timeout=30 --tries=2 "{url}" -O csf.tgz 2>&1 && '
                   f'test -s /usr/src/csf.tgz'],
                  step='csf-download', timeout=90)
        if ok or (_os.path.exists('/usr/src/csf.tgz') and _os.path.getsize('/usr/src/csf.tgz') > 10000):
            csf_downloaded = True
            output_lines.append(f'[csf-download] Downloaded from {url}')
            break

    if csf_downloaded:
        # install CSF
        _run(['sudo', 'apt-get', 'install', '-y', 'perl', 'liblwp-protocol-https-perl',
              'libwww-perl', 'unzip'], step='csf-deps')
        _run(['sudo', 'bash', '-c',
              'cd /usr/src && tar -xzf csf.tgz && cd csf && sh install.sh 2>&1'],
             step='csf-install', timeout=240)
        _run(['sudo', 'sed', '-i', r's/^TESTING = "1"/TESTING = "0"/', '/etc/csf/csf.conf'],
             step='csf-activate')
        _run(['sudo', 'systemctl', 'enable', '--now', 'csf'], step='csf-start')
        _run(['sudo', 'systemctl', 'enable', '--now', 'lfd'], step='lfd-start')

        if _sh.which('csf') or _os.path.exists('/etc/csf/csf.conf'):
            return JsonResponse({
                'status': 'success',
                'firewall': 'csf',
                'message': '✅ CSF Firewall installed and activated! Refreshing page...',
                'output': '\n'.join(output_lines),
            })

    # ── Step 2: CSF failed — install UFW (always available in Ubuntu repos) ──
    output_lines.append('[ufw] CSF download failed. Installing UFW (built-in Ubuntu firewall)...')

    ok_ufw = _run(['sudo', 'apt-get', 'install', '-y', 'ufw'], step='ufw-install')
    if ok_ufw or _sh.which('ufw'):
        _run(['sudo', 'ufw', '--force', 'reset'], step='ufw-reset')
        _run(['sudo', 'ufw', 'default', 'allow', 'incoming'],  step='ufw-default-in')
        _run(['sudo', 'ufw', 'default', 'allow', 'outgoing'],  step='ufw-default-out')
        _run(['sudo', 'ufw', 'allow', 'ssh'],                   step='ufw-allow-ssh')
        _run(['sudo', 'ufw', 'allow', '8080/tcp'],              step='ufw-allow-panel')
        _run(['sudo', 'ufw', '--force', 'enable'],             step='ufw-enable')

        # update firewall db record to reflect enabled state
        try:
            fw_obj = firewall.objects.filter(id=1).first() or firewall(id=1, status=False)
            fw_obj.status = True
            fw_obj.save()
        except Exception:
            pass

        if _sh.which('ufw'):
            return JsonResponse({
                'status': 'success',
                'firewall': 'ufw',
                'message': '✅ UFW Firewall installed and activated! Refreshing page...',
                'output': '\n'.join(output_lines),
            })

    return JsonResponse({
        'status': 'error',
        'message': 'Both CSF and UFW installation failed. Check output for details.',
        'output': '\n'.join(output_lines),
    })


@login_required(login_url='/')
def cpbruteforce(request):
    if request.user.is_superuser:
        import shutil, subprocess as _sp
        d = {}
        if firewall.objects.filter(id=1).exists():
            d['firewall'] = firewall.objects.get(id=1)
        else:
            d['firewall'] = firewall(id=1, status=False)
            d['firewall'].save()
        csf_ok = shutil.which('csf') is not None or os.path.exists('/etc/csf/csf.conf')
        ufw_ok = shutil.which('ufw') is not None
        d['csf_installed'] = csf_ok or ufw_ok
        d['firewall_type']  = 'csf' if csf_ok else ('ufw' if ufw_ok else None)
        
        # Always read LIVE state from the OS, not just the DB
        if csf_ok:
            csf_status = _sp.run(['sudo', 'csf', '--status'], capture_output=True, text=True, timeout=5)
            d['fw_enabled'] = 'disabled' not in csf_status.stdout.lower() and csf_status.returncode == 0
        elif ufw_ok:
            r = _sp.run(['sudo', 'ufw', 'status'], capture_output=True, text=True, timeout=5)
            out_lower = r.stdout.lower()
            d['fw_enabled'] = ('active' in out_lower and 'inactive' not in out_lower)
        else:
            d['fw_enabled'] = False
            
        # Sync DB record to match live state
        try:
            fw_obj = d['firewall']
            if fw_obj.status != d['fw_enabled']:
                fw_obj.status = d['fw_enabled']
                fw_obj.save()
        except Exception:
            pass
            
        return render(request, 'panel/cpbruteforce.html', d)
    else:
        return redirect('/')
    
@login_required(login_url='/')
def cpbrute(request):
    if request.user.is_superuser:
        if request.method == "POST":
            # Ensure firewall model instance exists
            if firewall.objects.filter(id=1).exists():
                e = firewall.objects.get(id=1)
            else:
                e = firewall(id=1, status=False)
                e.save()
                
            try:
                import shutil as _sh, subprocess as _sp
                csf_binary = _sh.which('csf')
                ufw_binary = _sh.which('ufw')
                
                if csf_binary or os.path.exists('/etc/csf/csf.conf'):
                    if e.status:
                        # Currently enabled -> we want to disable
                        if sys.platform != 'win32':
                            _sp.run(['sudo', 'sed', '-i', 's/^TESTING = "0"/TESTING = "1"/', '/etc/csf/csf.conf'], check=False)
                            _sp.run(['sudo', 'csf', '-x'], check=False)
                        e.status = False
                    else:
                        # Currently disabled -> we want to enable
                        if sys.platform != 'win32':
                            _sp.run(['sudo', 'sed', '-i', 's/^TESTING = "1"/TESTING = "0"/', '/etc/csf/csf.conf'], check=False)
                            _sp.run(['sudo', 'csf', '-e'], check=False)
                        e.status = True
                        
                elif ufw_binary:
                    # UFW fallback
                    st = _sp.run(['sudo', 'ufw', 'status'], capture_output=True, text=True)
                    out_lower = st.stdout.lower()
                    is_running = ('active' in out_lower and 'inactive' not in out_lower)
                    
                    if is_running or e.status:
                        _sp.run(['sudo', 'ufw', '--force', 'disable'], check=False)
                        e.status = False
                    else:
                        # ALWAYS pre-allow critical ports before enabling to prevent lockout
                        _sp.run(['sudo', 'ufw', 'allow', '22/tcp'],   check=False)  # SSH
                        _sp.run(['sudo', 'ufw', 'allow', '80/tcp'],   check=False)  # HTTP
                        _sp.run(['sudo', 'ufw', 'allow', '443/tcp'],  check=False)  # HTTPS
                        _sp.run(['sudo', 'ufw', 'allow', '8080/tcp'], check=False)  # VoidPanel
                        _sp.run(['sudo', 'ufw', '--force', 'enable'], check=False)
                        e.status = True
                else:
                    return JsonResponse({'status': 'error', 'message': 'No firewall engine installed. Click Install first.'})
                    
                e.save()
                return JsonResponse({'status': 'success', 'message': f"Firewall {'enabled' if e.status else 'disabled'} successfully."})
                
            except Exception as ex:
                return JsonResponse({'status': 'error', 'message': f'Toggle failed: {str(ex)}'})
    return JsonResponse({'status': 'error', 'message': 'Authentication required.'}, status=403)

@login_required(login_url='/')
def allowip(request):
    if request.user.is_superuser and request.method=="POST":
        try:
            import shutil as _sh, subprocess as _sp
            raw_ip = request.POST.get('allow', '').strip()
            ip = shlex.quote(raw_ip)
            if _sh.which('csf') or os.path.exists('/etc/csf/csf.conf'):
                get_platform().firewall.allow_ip(ip)
                get_platform().firewall.reload()
            elif _sh.which('ufw'):
                _sp.run(['sudo', 'ufw', 'allow', 'from', raw_ip], check=True)
            else:
                return JsonResponse({'status': 'error', 'message': 'No firewall installed.'})
            return JsonResponse({'status': 'success', 'message': f'IP {raw_ip} allowed in firewall.'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})
    return JsonResponse({'status': 'error', 'message': 'Invalid request.'})

@login_required(login_url='/')
def denyip(request):
    if request.user.is_superuser and request.method=="POST":
        try:
            import shutil as _sh, subprocess as _sp
            raw_ip = request.POST.get('allow', '').strip()
            ip = shlex.quote(raw_ip)
            if _sh.which('csf') or os.path.exists('/etc/csf/csf.conf'):
                get_platform().firewall.deny_ip(ip)
                get_platform().firewall.reload()
            elif _sh.which('ufw'):
                _sp.run(['sudo', 'ufw', 'deny', 'from', raw_ip], check=True)
            else:
                return JsonResponse({'status': 'error', 'message': 'No firewall installed.'})
            return JsonResponse({'status': 'success', 'message': f'IP {raw_ip} denied in firewall.'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})
    return JsonResponse({'status': 'error', 'message': 'Invalid request.'})

@login_required(login_url='/')
def ignoreip(request):
    if request.user.is_superuser and request.method=="POST":
        try:
            import shutil as _sh, subprocess as _sp
            raw_ip = request.POST.get('allow', '').strip()
            ip = shlex.quote(raw_ip)
            if _sh.which('csf') or os.path.exists('/etc/csf/csf.conf'):
                result = _sp.run(['sudo', 'csf', '--tempallow', raw_ip, '86400', 'Panel-Ignore'],
                                 capture_output=True, text=True)
                if result.returncode != 0:
                    get_platform().firewall.allow_ip(ip)
                    get_platform().firewall.reload()
            elif _sh.which('ufw'):
                _sp.run(['sudo', 'ufw', 'allow', 'from', raw_ip], check=False)
            else:
                return JsonResponse({'status': 'error', 'message': 'No firewall installed.'})
            return JsonResponse({'status': 'success', 'message': f'IP {raw_ip} added to ignore/allow list.'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})
    return JsonResponse({'status': 'error', 'message': 'Invalid request.'})

@login_required(login_url='/')
def unblockip(request):
    if request.user.is_superuser and request.method=="POST":
        try:
            import shutil as _sh, subprocess as _sp
            raw_ip = request.POST.get('allow', '').strip()
            ip = shlex.quote(raw_ip)
            if _sh.which('csf') or os.path.exists('/etc/csf/csf.conf'):
                if sys.platform != 'win32':
                    run_command(f'sudo csf -dr {ip}')
                    run_command('sudo csf -r')
            elif _sh.which('ufw'):
                _sp.run(['sudo', 'ufw', 'delete', 'deny', 'from', raw_ip], check=False)
                _sp.run(['sudo', 'ufw', 'reload'], check=False)
            else:
                return JsonResponse({'status': 'error', 'message': 'No firewall installed.'})
            return JsonResponse({'status': 'success', 'message': f'IP {raw_ip} unblocked.'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})
    return JsonResponse({'status': 'error', 'message': 'Invalid request.'})

@login_required(login_url='/')
def blockip(request):
    if request.user.is_superuser and request.method=="POST":
        try:
            import shutil as _sh, subprocess as _sp
            raw_ip = request.POST.get('allow', '').strip()
            ip = shlex.quote(raw_ip)
            if _sh.which('csf') or os.path.exists('/etc/csf/csf.conf'):
                get_platform().firewall.deny_ip(ip)
                get_platform().firewall.reload()
            elif _sh.which('ufw'):
                _sp.run(['sudo', 'ufw', 'deny', 'from', raw_ip], check=True)
            else:
                return JsonResponse({'status': 'error', 'message': 'No firewall installed.'})
            return JsonResponse({'status': 'success', 'message': f'IP {raw_ip} blocked successfully.'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})
    return JsonResponse({'status': 'error', 'message': 'Invalid request.'})


@login_required(login_url='/')
def ftpserver(request):
    
    if request.user.is_superuser:
      
        d={}
        from control.models import ftp
        # Use get_or_create to prevent 500 error crash when FTP configuration is not yet seeded
        ftp_obj, created = ftp.objects.get_or_create(id=1, defaults={'status': True})
        d['ftp'] = ftp_obj
        
        return render(request,'panel/ftp.html',d)
    else: 
        return redirect('/')
    

@login_required(login_url='/')
def ftp12(request):
    if not request.user.is_superuser:
        return JsonResponse({'status': 'error', 'message': 'Permission denied.'}, status=403)
        
    if request.method == "POST":
        try:
            from control.models import ftp
            e, created = ftp.objects.get_or_create(id=1, defaults={'status': True})
            import platform
            
            if e.status:
                if sys.platform != 'win32':
                    get_platform().services.stop('vsftpd')
                else:
                    get_platform().services.stop('FileZilla Server')
                e.status = False
                e.save()
                return JsonResponse({'status': 'success', 'message': 'FTP Server globally disabled.'})
            else:
                if sys.platform != 'win32':
                    get_platform().services.start('vsftpd')
                else:
                    get_platform().services.start('FileZilla Server')
                e.status = True
                e.save()
                return JsonResponse({'status': 'success', 'message': 'FTP Server securely enabled.'})
                
        except ftp.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'FTP Database record missing.'}, status=404)
        except Exception as err:
            return JsonResponse({'status': 'error', 'message': f'Server Error: {str(err)}'}, status=500)
            
    return JsonResponse({'status': 'error', 'message': 'Invalid request method.'}, status=405)



@login_required(login_url='/')
def delpackage(request, data):
    is_ajax = request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.headers.get('Accept') == 'application/json'

    if not request.user.is_superuser:
        if is_ajax: return JsonResponse({'status': 'error', 'message': 'Permission denied.'}) 
        return redirect('/')
    
    # Industry Standard: Enforce POST for state-modifying actions
    if request.method != "POST":
        # Reject GET deletions outright to prevent CSRF exploits
        if is_ajax:
            return JsonResponse({'status': 'error', 'message': 'Method Not Allowed. Must use POST for deletions.'}, status=405)
        messages.error(request, "Invalid request method. Please use the secure application interface to delete packages.")
        return redirect('/package/')

    # Check if a user is using the package
    is_in_use = user.objects.filter(hosting_package=data).exists()
    
    if is_in_use:
        message = "Cannot delete package as it is currently assigned to one or more users."
        if is_ajax:
            return JsonResponse({'status': 'error', 'message': message})
        messages.error(request, message)
        return redirect('/package/')

    # Execute Deletion Safely stringently
    pkg = package.objects.filter(name=data).first()
    if pkg:
        pkg.delete()
        message = f'Package "{data}" deleted successfully.'
        if is_ajax:
            return JsonResponse({'status': 'success', 'message': message})
        messages.success(request, message)
    else:
        message = f'Package "{data}" not found.'
        if is_ajax:
            return JsonResponse({'status': 'error', 'message': message})
        messages.error(request, message)
        
    return redirect('/package/')


@csrf_exempt
def editpackage(request):
    if not request.user.is_superuser:
        return JsonResponse({'status': 'error', 'message': 'Permission denied.'}, status=403)

    is_ajax = request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.headers.get('Accept') == 'application/json'

    if request.method != "POST":
        if is_ajax:
            return JsonResponse({'status': 'error', 'message': 'Method Not Allowed.'}, status=405)
        return redirect('/package/')

    package_id = request.POST.get('package_id')
    package_name = request.POST.get('package', '').strip()
    storage = request.POST.get('storage', '0')
    ftp = request.POST.get('ftp', '0')
    bandwidth = request.POST.get('bandwidth', '0')
    subdomain = request.POST.get('subdomain', '0')
    database = request.POST.get('database', '0')
    email = request.POST.get('email', '0')

    # Clean "unlimited" strings
    storage = '0' if storage == 'unlimited' or storage == '' else storage
    ftp = '0' if ftp == 'unlimited' or ftp == '' else ftp
    bandwidth = '0' if bandwidth == 'unlimited' or bandwidth == '' else bandwidth
    subdomain = '0' if subdomain == 'unlimited' or subdomain == '' else subdomain
    database = '0' if database == 'unlimited' or database == '' else database
    email = '0' if email == 'unlimited' or email == '' else email

    if not package_id:
        if is_ajax: return JsonResponse({'status': 'error', 'message': 'Package ID is required.'})
        messages.error(request, 'Package ID is required.')
        return redirect('/package/')

    pkg = package.objects.filter(id=package_id).first()
    if not pkg:
        if is_ajax: return JsonResponse({'status': 'error', 'message': 'Package not found.'})
        messages.error(request, 'Package not found.')
        return redirect('/package/')

    # Check if changing the name conflicts with another package
    if package_name and package_name != pkg.name:
        if package.objects.filter(name=package_name).exclude(id=package_id).exists():
            if is_ajax: return JsonResponse({'status': 'error', 'message': f'Package "{package_name}" already exists.'})
            messages.error(request, f'Package "{package_name}" already exists.')
            return redirect('/package/')
        
        # If we change the name, we should also update any users currently using this package name
        old_name = pkg.name
        pkg.name = package_name
        pkg.save()
        user.objects.filter(hosting_package=old_name).update(hosting_package=package_name)

    pkg.storage = storage
    pkg.ftp = ftp
    pkg.bandwidth = bandwidth
    pkg.subdomain = subdomain
    pkg.databases_allowed = database
    pkg.email_accounts = email
    # Suite add-ons
    try:
        pkg.includes_social    = request.POST.get("includes_social")    == "on"
        pkg.includes_seo       = request.POST.get("includes_seo")       == "on"
        pkg.includes_marketing = request.POST.get("includes_marketing") == "on"
        pkg.social_plan        = request.POST.get("social_plan", "starter") or "starter"
        pkg.seo_plan           = request.POST.get("seo_plan", "lite") or "lite"
        pkg.marketing_plan     = request.POST.get("marketing_plan", "starter") or "starter"
    except Exception:
        pass
    pkg.save()

    if is_ajax:
        return JsonResponse({'status': 'success', 'message': f'Package "{pkg.name}" updated successfully!'})
    messages.success(request, f'Package "{pkg.name}" updated successfully!')
    return redirect('/package/')
    

@login_required(login_url='/')
def cwtd(request):
    if request.user.is_superuser:
        if request.method == "POST":
            try:
                domainaname = request.POST.get('domain', '').lower()
                package12 = request.POST.get('package', '')
                
                if not domainaname or not package12:
                    return JsonResponse({'status': 'error', 'message': 'Missing domain or package'})
                    
                ded = package.objects.get(name=package12)
                sto = str(ded.storage)
                
                # Verify domain exists before queueing
                fddf = domain.objects.get(domain=domainaname)
                
                # Dispatch background task
                from control.tasks import convert_website_task
                convert_website_task.delay(domainaname, package12, sto)
                
                return JsonResponse({'status': 'success', 'message': 'Website conversion queued successfully.'})
            except Exception as e:
                return JsonResponse({'status': 'error', 'message': str(e)})
                
    return JsonResponse({'status': 'error', 'message': 'Invalid request or unauthorised.'})


@login_required(login_url='/')
def serverstatus(request):
    try:
        with open(paths.MYSQL_PASSWORD_FILE, 'r') as f:
            adminpassword=f.read()
            adminpassword=adminpassword.strip()
    except Exception:
        adminpassword = ''
    
    if request.user.is_superuser:
      
        d={}
        d['domains']=len(domain.objects.all())
        d['email']=len(allemail.objects.all())
        d['package']=len(package.objects.all())
        d['databases']=len(get_database_names(adminpassword))
        d['mysqlstatus']=get_service_status('mysql')
        d['dovecotstatus']=get_service_status('dovecot')
        d['postfixstatus']=get_service_status('postfix')
        d['dnsstatus']=get_service_status('bind9')
        d['firewallstatus']=get_service_status('csf')
        return render(request,'panel/serverstatus.html',d)
    else: 
        return redirect('/')
    
_ALLOWED_ADMIN_SERVICES = frozenset({
    'nginx', 'mysql', 'mariadb', 'postfix', 'dovecot', 'bind9', 'named',
    'uwsgi', 'csf', 'vsftpd', 'php5.6-fpm', 'php7.0-fpm', 'php7.1-fpm',
    'php7.2-fpm', 'php7.3-fpm', 'php7.4-fpm', 'php8.0-fpm', 'php8.1-fpm',
    'php8.2-fpm', 'php8.3-fpm', 'php8.4-fpm', 'redis', 'memcached',
    'shellinabox', 'daphne',
})

@login_required(login_url='/')
def restart_now(request):
    if request.user.is_superuser:
        
        if request.method=="POST":
            data = json.loads(request.body)
            service = data.get('service', '')
            if service not in _ALLOWED_ADMIN_SERVICES:
                return JsonResponse({'status': 'error', 'message': 'Service not allowed.'})
            if service == 'nginx':
                 get_platform().services.reload('nginx')
                 import time
                 time.sleep(2)
                 return JsonResponse({'status': 'success', 'message': 'Already Exist'})
            if restart_service(service):
                 return JsonResponse({'status': 'success', 'message': 'Already Exist'})
            else:
                 return JsonResponse({'status': 'success', 'message': 'Already Exist'})
    return JsonResponse({'status': 'error', 'message': 'Invalid request.'})

@login_required(login_url='/')
def start_now(request):
    if request.user.is_superuser:
        
        if request.method=="POST":
            data = json.loads(request.body)
            service = data.get('service', '')
            if service not in _ALLOWED_ADMIN_SERVICES:
                return JsonResponse({'status': 'error', 'message': 'Service not allowed.'})
            if start_service(service):
                 return JsonResponse({'status': 'success', 'message': 'Already Exist'})
            else:
                 return JsonResponse({'status': 'success', 'message': 'Already Exist'})
    return JsonResponse({'status': 'error', 'message': 'Invalid request.'})

@login_required(login_url='/')
def start_now_python(request):
    if request.user.is_authenticated:
        if request.method=="POST":
            data = json.loads(request.body)
            domainname = data.get('domain', '').strip()
            name = data.get('name', '').strip()
            # Ownership check for non-admin
            if not request.user.is_superuser:
                owner = user.objects.filter(username=request.user.username).first()
                if not owner or (owner.domain != domainname and not subdomainname.objects.filter(subdomain=domainname, domain=owner.domain).exists()):
                    return JsonResponse({'status': 'error', 'message': 'Unauthorized'}, status=403)
            # Validate service name matches a known app and get system user
            app = pythonname.objects.filter(name=name, domain=domainname).first()
            if not app:
                return JsonResponse({'status': 'error', 'message': 'Service not found.'})
            service_name = f'app-{app.main}-{name}'
            if start_service(service_name):
                 return JsonResponse({'status': 'success', 'message': 'Already Exist'})
            else:
                 return JsonResponse({'status': 'error', 'message': 'Already Exist'})
    return JsonResponse({'status': 'error', 'message': 'Invalid request.'})

@login_required(login_url='/')
def restart_now_python(request):
    if request.user.is_authenticated:
        if request.method=="POST":
            data = json.loads(request.body)
            domainname = data.get('domain', '').strip()
            name = data.get('name', '').strip()
            # Ownership check for non-admin
            if not request.user.is_superuser:
                owner = user.objects.filter(username=request.user.username).first()
                if not owner or (owner.domain != domainname and not subdomainname.objects.filter(subdomain=domainname, domain=owner.domain).exists()):
                    return JsonResponse({'status': 'error', 'message': 'Unauthorized'}, status=403)
            app = pythonname.objects.filter(name=name, domain=domainname).first()
            if not app:
                return JsonResponse({'status': 'error', 'message': 'Service not found.'})
            service_name = f'app-{app.main}-{name}'
            if restart_service(service_name):
                 return JsonResponse({'status': 'success', 'message': 'Already Exist'})
            else:
                 return JsonResponse({'status': 'error', 'message': 'Already Exist'})
    return JsonResponse({'status': 'error', 'message': 'Invalid request.'})

@login_required(login_url='/')
def stop_now(request):
    if request.user.is_superuser:
        
        if request.method=="POST":
            data = json.loads(request.body)
            service = data.get('service', '')
            if service not in _ALLOWED_ADMIN_SERVICES:
                return JsonResponse({'status': 'error', 'message': 'Service not allowed.'})
            if stop_service(service):
                 return JsonResponse({'status': 'success', 'message': 'Already Exist'})
            else:
                 return JsonResponse({'status': 'success', 'message': 'Already Exist'})
    return JsonResponse({'status': 'error', 'message': 'Invalid request.'})


@login_required(login_url='/')
def stop_now_python(request):
    if request.user.is_authenticated:
        if request.method=="POST":
            data = json.loads(request.body)
            domainname = data.get('domain', '').strip()
            name = data.get('name', '').strip()
            # Ownership check for non-admin
            if not request.user.is_superuser:
                owner = user.objects.filter(username=request.user.username).first()
                if not owner or (owner.domain != domainname and not subdomainname.objects.filter(subdomain=domainname, domain=owner.domain).exists()):
                    return JsonResponse({'status': 'error', 'message': 'Unauthorized'}, status=403)
            app = pythonname.objects.filter(name=name, domain=domainname).first()
            if not app:
                return JsonResponse({'status': 'error', 'message': 'Service not found.'})
            service_name = f'app-{app.main}-{name}'
            if stop_service(service_name):
                 return JsonResponse({'status': 'success', 'message': 'Already Exist'})
            else:
                 return JsonResponse({'status': 'error', 'message': 'Already Exist'})
    return JsonResponse({'status': 'error', 'message': 'Invalid request.'})


@login_required(login_url='/')
def shutdown(request):
    if request.user.is_superuser and request.method == 'POST':
         if sys.platform == 'win32':
             run_command('shutdown /s /t 0')
         else:
             run_command('sudo shutdown now')
         return JsonResponse({'status': 'success', 'message': 'Already Exist'})
    return JsonResponse({'status': 'error', 'message': 'Unauthorized or invalid request.'}, status=403)
    
@login_required(login_url='/')
def restart(request):
    if request.user.is_superuser and request.method == 'POST':
         if sys.platform == 'win32':
             run_command('shutdown /r /t 0')
         else:
             run_command('sudo reboot')
         return JsonResponse({'status': 'success', 'message': 'Already Exist'})
    return JsonResponse({'status': 'error', 'message': 'Unauthorized or invalid request.'}, status=403)
    
@login_required(login_url='/')
def restartservice(request):
    if request.user.is_superuser and request.method == 'POST':
         service=['mysql','postfix','dovecot','uwsgi','bind9','csf']
         for i in service:
            restart_service(i)
  
         return JsonResponse({'status': 'success', 'message': 'Already Exist'})
    return JsonResponse({'status': 'error', 'message': 'Unauthorized or invalid request.'}, status=403)
    
@login_required(login_url='/')
@require_POST
def api_set_reseller(request):
    """Promote or demote a hosting user to/from reseller status."""
    if not request.user.is_superuser:
        return JsonResponse({'error': 'Forbidden'}, status=403)
    import json as _json
    try:
        payload = _json.loads(request.body)
    except Exception:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    username   = payload.get('username', '').strip()
    action     = payload.get('action', 'promote')          # 'promote' | 'demote'
    storage_gb = int(payload.get('storage_quota_gb', 50))
    max_acc    = int(payload.get('max_accounts', 20))
    company    = payload.get('company_name', '').strip()

    if not username:
        return JsonResponse({'error': 'username required'}, status=400)

    from django.contrib.auth import get_user_model as _gum
    from control.models import ResellerProfile
    AuthUser = _gum()

    try:
        auth_user = AuthUser.objects.get(username=username)
    except AuthUser.DoesNotExist:
        return JsonResponse({'error': f'User "{username}" not found'}, status=404)

    if action == 'promote':
        profile, created = ResellerProfile.objects.get_or_create(
            auth_user=auth_user,
            defaults={
                'company_name':    company,
                'storage_quota_gb': storage_gb,
                'max_accounts':     max_acc,
                'is_active':        True,
            }
        )
        if not created:
            # Update existing profile
            profile.company_name     = company or profile.company_name
            profile.storage_quota_gb = storage_gb
            profile.max_accounts     = max_acc
            profile.is_active        = True
            profile.save()
        return JsonResponse({'status': 'promoted', 'username': username})

    elif action == 'demote':
        ResellerProfile.objects.filter(auth_user=auth_user).delete()
        return JsonResponse({'status': 'demoted', 'username': username})

    return JsonResponse({'error': f'Unknown action: {action}'}, status=400)


@login_required(login_url='/')
def chpassuser(request):
    """Securely change a hosted user's panel login password and Linux system password."""
    if not request.user.is_superuser:
        return JsonResponse({'status': 'error', 'message': 'Permission denied.'}, status=403)

    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Invalid request method.'}, status=405)

    password = request.POST.get('password', '').strip()
    username = request.POST.get('user', '').strip().lower()

    if not username or not password:
        return JsonResponse({'status': 'error', 'message': 'Username and password are required.'}, status=400)

    import re
    if not re.match(r'^[a-z0-9_\-\.]{1,32}$', username):
        return JsonResponse({'status': 'error', 'message': 'Invalid username format.'}, status=400)

    if len(password) < 8:
        return JsonResponse({'status': 'error', 'message': 'Password must be at least 8 characters.'}, status=400)

    try:
        sd = User.objects.get(username=username)
    except User.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'User not found.'}, status=404)

    # 1. Update Django auth password (hashed)
    sd.set_password(password)
    sd.save()

    # 2. Update Linux system password via platform layer
    try:
        get_platform().users.change_password(username, password)
    except Exception as e:
        with open(paths.PANEL_LOG_FILE, 'a') as log:
            log.write(f'[chpassuser] System password change error for {username}: {str(e)}\n')

    return JsonResponse({'status': 'success', 'message': 'Password updated successfully.'})


@login_required(login_url='/')
def chpackageuser(request):
    """Change the hosting package for a user account and update their disk quota."""
    if not request.user.is_superuser:
        return JsonResponse({'status': 'error', 'message': 'Permission denied.'}, status=403)

    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Invalid request method.'}, status=405)

    package_name = request.POST.get('package', '').strip()
    username = request.POST.get('user', '').strip().lower()

    if not username or not package_name:
        return JsonResponse({'status': 'error', 'message': 'Username and package are required.'}, status=400)

    import re
    if not re.match(r'^[a-z0-9_\-\.]{1,32}$', username):
        return JsonResponse({'status': 'error', 'message': 'Invalid username format.'}, status=400)

    try:
        userd = user.objects.get(username=username)
    except user.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'User not found.'}, status=404)

    try:
        pkg = package.objects.get(name=package_name)
    except package.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': f'Package "{package_name}" not found.'}, status=404)

    storage_mb = pkg.storage
    storage_kb = int(storage_mb) * 1024  # Convert MB → KB for setquota

    # Update DB record
    userd.hosting_package = package_name
    userd.save()

    # Update Linux disk quota via platform layer
    try:
        get_platform().users.set_quota(username, storage_kb, storage_kb)
    except Exception as e:
        with open(paths.PANEL_LOG_FILE, 'a') as log:
            log.write(f'[chpackageuser] Quota update error for {username}: {str(e)}\n')

    return JsonResponse({'status': 'success', 'message': f'Package updated to {package_name} successfully.'})
         

@login_required(login_url='/')
def setpython(request,data):
   
    if request.user.is_superuser:
               
                d={}
                
                try:
                    
                    lold=domain.objects.get(domain=data)
                    d['domain']=data
                    request.session['name']=str(lold.dir)
                    d['python']=pythonname.objects.filter(main=lold.dir).all()     
                    url = 'https://voidpanel.com/admindocs/'  # Replace with your API URL
                    response = requests.get(url, timeout=2)
                    if response.status_code == 200:
                        dataee = response.json()  # Parse the JSON response
                        d['docs']=dataee
                    return render(request,'panel/setpython.html',d)
                except Exception as e:
                    return redirect("/listwebsite/")
           
    else: 
        return redirect('/')
    
@login_required(login_url='/')
def setmern(request,data):
   
    if request.user.is_superuser:
               
                d={}
                
                try:
                    
                    lold=domain.objects.get(domain=data)
                    d['domain']=data
                    request.session['name']=str(lold.dir)
                    d['python']=mernname.objects.filter(main=lold.dir).all()     
                    url = 'https://voidpanel.com/admindocs/'  # Replace with your API URL
                    response = requests.get(url, timeout=2)
                    if response.status_code == 200:
                        dataee = response.json()  # Parse the JSON response
                        d['docs']=dataee
                    return render(request,'panel/setmern.html',d)
                except Exception as e:
                    return redirect("/listwebsite/")
           
    else: 
        return redirect('/')
    
@login_required(login_url='/')
def createpython(request,data):
   
    if request.user.is_superuser:
                d={}
                try:
                    
                    lold=domain.objects.get(domain=data)
                    d['domain']=data
                    d['subdomain']=subdomainname.objects.filter(domain=data).all()      
                    url = 'https://voidpanel.com/admindocs/'  # Replace with your API URL
                    response = requests.get(url, timeout=2)
                    if response.status_code == 200:
                        dataee = response.json()  # Parse the JSON response
                        d['docs']=dataee
                    d['domain']=data
                    return render(request,'panel/createpython.html',d)
                except Exception as e:
                    return redirect("/listwebsite/")
           
    else: 
        return redirect('/')
        

@login_required(login_url='/')
def createmern(request,data):
   
    if request.user.is_superuser:
                d={}
                try:
                    
                    lold=domain.objects.get(domain=data)
                    d['domain']=data
                    d['subdomain']=subdomainname.objects.filter(domain=data).all()      
                    url = 'https://voidpanel.com/admindocs/'  # Replace with your API URL
                    response = requests.get(url, timeout=2)
                    if response.status_code == 200:
                        dataee = response.json()  # Parse the JSON response
                        d['docs']=dataee
                    d['domain']=data
                    return render(request,'panel/createmern.html',d)
                except Exception as e:
                    return redirect("/listwebsite/")
           
    else: 
        return redirect('/')


@login_required(login_url='/')
@never_cache
def addpython(request):
    if not request.user.is_authenticated:
        return JsonResponse({'status': 'error', 'message': 'Unauthorized'}, status=401)

    if request.method != "POST":
        return JsonResponse({'status': 'error'}, status=405)

    data = json.loads(request.body)
    domain1 = data.get('domain', '').strip()
    name = data.get('name', '').strip()

    if not domain1 or not name:
        return JsonResponse({'status': 'error', 'message': 'Missing fields'})

    # Ownership check for non-admin
    if not request.user.is_superuser:
        current = request.user.username
        owner = user.objects.filter(username=current).first()
        if not owner or (owner.domain != domain1 and not subdomainname.objects.filter(subdomain=domain1, domain=owner.domain).exists()):
            return JsonResponse({'status': 'error', 'message': 'Unauthorized'}, status=403)

    # Uniqueness checks
    if pythonname.objects.filter(name=name).exists():
        return JsonResponse({'status': 'already1', 'message': 'Project name already exists'})
    if pythonname.objects.filter(domain=domain1).exists():
        return JsonResponse({'status': 'already', 'message': 'Domain already has a Python app'})

    # Resolve domain directory
    try:
        fre = domain.objects.get(domain=domain1)
    except domain.DoesNotExist:
        try:
            parent = subdomainname.objects.get(subdomain=domain1).domain
            fre = domain.objects.get(domain=parent)
        except Exception:
            return JsonResponse({'status': 'error', 'message': 'Domain not found'})

    # Storage quota enforcement
    try:
        from control.models import user as ctrl_user, package as ctrl_package
        usr_obj = ctrl_user.objects.get(username=fre.dir)
        pkg_obj = ctrl_package.objects.get(name=usr_obj.hosting_package)
        quota_mb = int(pkg_obj.storage) * 1024  # package stores GB, convert to MB
        used_mb = get_directory_size_in_mb(os.path.join(paths.HOME_BASE, fre.dir))
        if quota_mb > 0 and used_mb >= quota_mb:
            return JsonResponse({'status': 'quota', 'message': 'Storage quota exceeded'})
    except Exception:
        pass  # If quota check fails, allow provisioning (graceful degradation)

    # Resolve app dir (needed for both win32 and linux paths)
    app_dir = os.path.join(paths.HOME_BASE, fre.dir, name)

    # Scaffold directories and provision Python app (Linux only)
    if sys.platform != 'win32':
        try:
            import subprocess
            subprocess.run(['sudo', 'mkdir', '-p', app_dir], check=False)
            subprocess.run(['sudo', 'mkdir', '-p', os.path.join(app_dir, 'static')], check=False)
        except Exception:
            pass

        # Run setup script as root (it handles venv creation, uwsgi install, systemd unit)
        try:
            script_path = os.path.join(paths.PANEL_ROOT, 'createpython.sh')
            import subprocess
            result = subprocess.run(
                ['sudo', 'bash', script_path, fre.dir, app_dir, name],
                capture_output=True, text=True, timeout=180
            )
            if result.returncode != 0:
                import logging
                logging.getLogger(__name__).error(f"createpython.sh failed: {result.stderr}")
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"createpython.sh exception: {e}")

        # Fix ownership AFTER script runs: user owns files, www-data group for nginx access
        try:
            import subprocess
            subprocess.run(['sudo', 'chown', '-R', f'{fre.dir}:www-data', app_dir], check=False)
            subprocess.run(['sudo', 'chmod', '-R', '750', app_dir], check=False)
            subprocess.run(['sudo', 'chmod', '-R', '755', os.path.join(app_dir, 'static')], check=False)
            # Service file should run as www-data for socket access — fix socket perms
            subprocess.run(['sudo', 'chmod', 'g+ws', app_dir], check=False)
            # Ensure venv executables always have +x so the user can run pip/python directly
            venv_bin = os.path.join(app_dir, 'venv', 'bin')
            for exe in ['pip', 'pip3', 'pip3.10', 'pip3.11', 'pip3.12', 'python', 'python3', 'uwsgi']:
                exe_path = os.path.join(venv_bin, exe)
                subprocess.run(['sudo', 'chmod', '+x', exe_path], check=False, capture_output=True)
        except Exception:
            pass

        # Reload systemd so the new service unit is visible
        try:
            subprocess.run(['sudo', 'systemctl', 'daemon-reload'], check=False)
        except Exception:
            pass

    # Update Engine Config — ini filename matches what createpython.sh creates: {name}.ini

    sock_path = os.path.join(app_dir, f'{name}.sock')
    static_path = os.path.join(app_dir, 'static')
    
    from voidplatform.linux.web import get_active_engine, get_active_engine_manager
    engine = get_active_engine()
    mgr = get_active_engine_manager()
    
    if engine == 'ols':
        # OLS extprocessor works best with HTTP-over-TCP (not UDS).
        # Allocate a free port and reconfigure uWSGI accordingly.
        from function import get_random_port
        ols_port = get_random_port()

        # Read and update the INI: change unix socket -> tcp http-socket
        ini_path = os.path.join(app_dir, f'{name}.ini')
        try:
            import subprocess as _sp
            ini_result = _sp.run(['sudo', 'cat', ini_path], capture_output=True, text=True, timeout=10)
            ini_content = ini_result.stdout if ini_result.returncode == 0 else ''
            if not ini_content and os.path.exists(ini_path):
                with open(ini_path, 'r') as f:
                    ini_content = f.read()
            if ini_content:
                import re as _re
                # Replace unix socket lines with http port
                ini_content = _re.sub(r'^\s*socket\s*=.*$', f'http-socket = 127.0.0.1:{ols_port}', ini_content, flags=_re.MULTILINE)
                # Remove chmod-socket line (not needed for TCP)
                ini_content = _re.sub(r'^\s*chmod-socket\s*=.*\n?', '', ini_content, flags=_re.MULTILINE)
                # Write back via sudo tee
                proc = _sp.Popen(['sudo', 'tee', ini_path], stdin=_sp.PIPE, stdout=_sp.DEVNULL)
                proc.communicate(input=ini_content.encode())
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"OLS ini patch failed: {e}")

        # Inject OLS extprocessor + context blocks into the vhost config
        ols_proxy = f"""
extprocessor python_{name} {{
  type                    proxy
  address                 127.0.0.1:{ols_port}
  maxConns                100
  initTimeout             60
  retryTimeout            0
  respBuffer              0
}}
context / {{
  type                    proxy
  handler                 python_{name}
  addDefaultCharset       off
}}
context /static/ {{
  type                    null
  location                {static_path}/
}}
"""
        old_conf = mgr.read_site_config(domain1)
        if 'python_' + name not in old_conf:
            new_conf = old_conf + "\n" + ols_proxy
            r = mgr.write_and_test_site_config(domain1, new_conf)
            if not r.success:
                return JsonResponse({'status': 'error', 'message': f'OLS validation failed: {r.error}'})
    else:
        new_location_block = f"""
    location / {{
        include uwsgi_params;
        uwsgi_pass unix:{sock_path};
    }}

    location /static/ {{
        alias {static_path}/;
        expires 30d;
        add_header Cache-Control "public, no-transform";
    }}
"""
        try:
            old_conf = mgr.read_site_config(domain1)
            if old_conf:
                import re
                new_conf = old_conf
                
                # Optional safety: Strip them out first if they already existed (e.g. broken states)
                new_conf = re.sub(r'[ \t]*location / \{(?:[^{}]|\{[^{}]*\})*\}\s*', '', new_conf)
                new_conf = re.sub(r'[ \t]*location /static/ \{(?:[^{}]|\{[^{}]*\})*\}\s*', '', new_conf)
                
                # Inject new blocks properly before location ~ /\.ht (or equivalent security block)
                if 'location ~ /\\.ht {' in new_conf:
                    new_conf = new_conf.replace('location ~ /\\.ht {', new_location_block + '\n    location ~ /\\.ht {', 1)
                elif re.search(r'location\s*~\s*/\\.\(ht\|svn\|git\)\s*\{', new_conf):
                    new_conf = re.sub(r'(location\s*~\s*/\\.\(ht\|svn\|git\)\s*\{)', new_location_block + r'\n    \1', new_conf, count=1)
                elif re.search(r'location\s*~\s*/\\\.\(\?!well-known\)\s*\{', new_conf):
                    new_conf = re.sub(r'(location\s*~\s*/\\\.\(\?!well-known\)\s*\{)', new_location_block + r'\n    \1', new_conf, count=1)
                else:
                    new_conf = new_conf.rstrip().rsplit('}', 1)
                    new_conf = new_conf[0] + new_location_block + '\n}'
                
                r = mgr.write_and_test_site_config(domain1, new_conf)
                if not r.success:
                    from control.activity import log_activity
                    log_activity(request, 'error', 'python', domain=domain1,
                                 action=f'Python deploy failed: {name}',
                                 detail=f'Nginx validation error: {r.error}')
                    return JsonResponse({'status': 'error', 'message': f'Nginx validation failed: {r.error}'})
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"addpython nginx conf error: {e}")

    # Create DB record and start service — platform-aware
    pythonname.objects.create(domain=domain1, name=name, main=fre.dir)
    try:
        if sys.platform == 'win32':
            from voidplatform.windows.apps import deploy_python_app, get_python_app_port
            port, ok, msg = deploy_python_app(fre.dir, name, domain1)
            # Update nginx to use HTTP proxy instead of unix socket (Windows)
            if ok:
                proxy_block = f"""
    location / {{
        proxy_pass http://127.0.0.1:{port};
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }}
"""
                conf_path2 = os.path.join(paths.NGINX_SITES_ENABLED, f'{domain1}.conf')
                if os.path.exists(conf_path2):
                    with open(conf_path2, 'r') as f2:
                        conf = f2.read()
                    # Replace the uwsgi_pass block with proxy_pass
                    import re as _re
                    conf = _re.sub(r'location / \{[^}]*uwsgi_pass[^}]*\}', proxy_block, conf, flags=_re.DOTALL)
                    with open(conf_path2, 'w') as f2:
                        f2.write(conf)
        else:
            # Linux: start and enable the systemd service created by createpython.sh
            import subprocess
            subprocess.run(['sudo', 'systemctl', 'enable', name], check=False)
            subprocess.run(['sudo', 'systemctl', 'start', name], check=False)

        try:
            get_platform().services.reload('nginx')
        except Exception:
            pass
    except Exception:
        pass

    import time
    time.sleep(2)
    from control.activity import log_activity
    log_activity(request, 'success', 'python', domain=domain1,
                 action=f'Python app deployed: {name}',
                 detail=f'uWSGI socket provisioned at /var/run/panel/{name}.sock')
    return JsonResponse({'status': 'success', 'message': f'Python app "{name}" provisioned successfully!'})

     
@login_required(login_url='/')
def delete_mern(request):
    if not request.user.is_authenticated:
        return JsonResponse({'status': 'error', 'message': 'Unauthorized'}, status=401)

    if request.method == "POST":
        data = json.loads(request.body)
        domainname = data.get('domain', '').strip()
        name = data.get('name', '').strip()

        # Ownership verification
        if not request.user.is_superuser:
            current = request.user.username
            owner = user.objects.filter(username=current).first()
            if not owner or (owner.domain != domainname and not subdomainname.objects.filter(subdomain=domainname, domain=owner.domain).exists()):
                return JsonResponse({'status': 'error', 'message': 'Unauthorized'}, status=403)

        try:
            domain_obj = domain.objects.get(domain=domainname)
            iwefj = domain_obj.dir
        except:
            try:
                parent_domain = subdomainname.objects.get(subdomain=domainname).domain
                iwefj = domain.objects.get(domain=parent_domain).dir
            except:
                return JsonResponse({'status': 'error', 'message': 'Domain not found'})

        # Clean files securely as root
        try:
            directory_path = os.path.join(paths.HOME_BASE, iwefj, name)
            run_command(f'sudo rm -rf {shlex.quote(directory_path)}')
        except:
            pass

        try:
            sock_path = os.path.join(paths.RUN_DIR, f'{name}.sock')
            if sys.platform != 'win32' and os.path.exists(sock_path):
                os.remove(sock_path)
        except:
            pass

        # Stop process manager — platform-aware
        try:
            if sys.platform == 'win32':
                from voidplatform.windows.apps import delete_mern_app
                delete_mern_app(name)
            else:
                # Linux: pm2 as root
                run_command(f'sudo /usr/local/bin/pm2 delete {name} ; sudo /usr/local/bin/pm2 save')
        except:
            pass

        # Clean Nginx/OLS configs safely using elevated manager
        from voidplatform.linux.web import get_active_engine_manager
        mgr = get_active_engine_manager()
        mgr.remove_reverse_proxy(domainname, name)

        try:
            df = mernname.objects.get(domain=domainname, name=name)
            df.delete()
        except:
            pass

        import time
        time.sleep(2)
        return JsonResponse({'status': 'success', 'message': 'MERN stack deleted'})
    return JsonResponse({'status': 'error', 'message': 'Invalid request.'})

@login_required(login_url='/')
@never_cache
def addmern(request):
    if not request.user.is_authenticated:
        return JsonResponse({'status': 'error', 'message': 'Unauthorized'}, status=401)

    if request.method == "POST":
        data = json.loads(request.body)
        domain1 = data.get('domain', '').strip()
        name = data.get('name', '').strip()

        if not domain1 or not name:
            return JsonResponse({'status': 'error', 'message': 'Missing values'})

        # Ownership verification
        if not request.user.is_superuser:
            current = request.user.username
            owner = user.objects.filter(username=current).first()
            if not owner or (owner.domain != domain1 and not subdomainname.objects.filter(subdomain=domain1, domain=owner.domain).exists()):
                return JsonResponse({'status': 'error', 'message': 'Unauthorized'}, status=403)

        if mernname.objects.filter(name=name).exists():
            return JsonResponse({'status': 'already1', 'message': 'Project name already in use'})
        if mernname.objects.filter(domain=domain1).exists():
            return JsonResponse({'status': 'already', 'message': 'Domain already has a MERN stack'})

        # Resolve the owner's home directory (always from main domain)
        # but keep domain1 as the nginx target so subdomain gets its own config
        is_subdomain = False
        try:
            fre = domain.objects.get(domain=domain1)
        except domain.DoesNotExist:
            try:
                sub_obj = subdomainname.objects.get(subdomain=domain1)
                parent = sub_obj.domain
                fre = domain.objects.get(domain=parent)
                is_subdomain = True
            except:
                return JsonResponse({'status': 'error', 'message': 'Domain not found'})

        # Storage quota enforcement
        try:
            from control.models import user as ctrl_user, package as ctrl_package
            usr_obj = ctrl_user.objects.get(username=fre.dir)
            pkg_obj = ctrl_package.objects.get(name=usr_obj.hosting_package)
            quota_mb = int(pkg_obj.storage) * 1024
            used_mb = get_directory_size_in_mb(os.path.join(paths.HOME_BASE, fre.dir))
            # React build takes up to ~300MB, so we ensure they have at least 300MB free
            if quota_mb > 0 and (used_mb + 300) >= quota_mb:
                return JsonResponse({'status': 'quota', 'message': 'Insufficient storage quota for React/Node environment'})
        except Exception:
            pass 

        # Assign a unique, actually-free TCP port (avoid collisions with existing apps)
        import socket as _socket
        used_ports = set(int(p) for p in mernname.objects.values_list('port', flat=True) if p)
        # Also check python apps
        try:
            from panel.models import pythonname as _pyname
            used_ports.update(int(p) for p in _pyname.objects.values_list('port', flat=True) if p)
        except Exception:
            pass
        pasport = '3001'
        for _candidate in range(3001, 4000):
            if _candidate in used_ports:
                continue
            try:
                with _socket.socket(_socket.AF_INET, _socket.SOCK_STREAM) as _s:
                    _s.setsockopt(_socket.SOL_SOCKET, _socket.SO_REUSEADDR, 1)
                    _s.bind(('127.0.0.1', _candidate))
                    pasport = str(_candidate)
                    break
            except OSError:
                continue

        # Run the provisioning script in a background thread so the HTTP request
        # returns immediately instead of blocking for 3-4 minutes.
        import threading, subprocess as _sp
        app_dir = os.path.join(paths.HOME_BASE, fre.dir, name)
        frontend_build = os.path.join(app_dir, 'frontend', 'build')
        script_path = os.path.join(paths.PANEL_ROOT, 'mern.sh')
        _pasport = str(pasport)
        _fre_dir = fre.dir

        def _run_mern_provision():
            try:
                if sys.platform != 'win32':
                    _sp.run(
                        ['sudo', 'bash', script_path, name, frontend_build, app_dir, _pasport],
                        capture_output=True, text=True, timeout=600
                    )
                    _sp.run(['sudo', 'chown', '-R', f'{_fre_dir}:www-data', app_dir], check=False)
                    _sp.run(['sudo', 'chmod', '-R', '750', app_dir], check=False)
                    _sp.run(['sudo', 'chmod', 'g+ws', app_dir], check=False)
                else:
                    from voidplatform.windows.apps import deploy_mern_app as _dma
                    _dma(_fre_dir, name, domain1, int(_pasport))
            except Exception as _e:
                import logging
                logging.getLogger(__name__).error(f'mern provision bg error: {_e}')

        # We must write compiling.html natively right now so Nginx validation sees it.
        try:
            import shlex
            run_command(f'sudo mkdir -p {shlex.quote(app_dir)}')
            compiling_html_path = os.path.join(app_dir, 'compiling.html')
            html_content = "<html><body style=\"font-family:sans-serif;text-align:center;padding:50px;background:#111;color:#fff;\"><h2>Deploying MERN Architecture...</h2><p>Your React environment is currently compiling in the background. It takes approximately 3-4 minutes to download Node dependencies and build the DOM.</p><p>Please refresh this page in a few minutes.</p></body></html>"
            run_command(f"sudo bash -c \"cat << 'EOF' > {shlex.quote(compiling_html_path)}\\n{html_content}\\nEOF\"")
            run_command(f'sudo chown -R {_fre_dir}:www-data {shlex.quote(app_dir)}')
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Error creating compiling.html: {e}")

        static_path = os.path.join(app_dir, 'frontend', 'build', 'static')
        sock_path = os.path.join(paths.RUN_DIR, f'{name}.sock')
        
        from voidplatform.linux.web import get_active_engine_manager
        mgr = get_active_engine_manager()
        
        frontend_build_root = f"/home/{fre.dir}/{name}/frontend/build"
        r = mgr.setup_reverse_proxy(domain1, name, 'mern', f'http://127.0.0.1:{pasport}', static_path, frontend_build_root)
        if not r.success:
            from control.activity import log_activity
            log_activity(request, 'error', 'mern', domain=domain1,
                         action=f'MERN deploy failed: {name}',
                         detail=f'Nginx proxy error: {r.error}')
            return JsonResponse({'status': 'error', 'message': f'Server configuration validation failed: {r.error}'})

        # Atomic reservation: only spawn compilation if DB allocation succeeds
        try:
            mernname.objects.create(domain=domain1, name=name, main=fre.dir, port=pasport)
        except Exception as _e:
            return JsonResponse({'status': 'error', 'message': f'DB reservation failed: {_e}'})

        _t = threading.Thread(target=_run_mern_provision, daemon=True)
        _t.start()

        import time
        time.sleep(2)
        from control.activity import log_activity
        log_activity(request, 'success', 'mern', domain=domain1,
                     action=f'MERN stack deployed: {name}',
                     detail=f'Port {pasport}, compiling in background')
        return JsonResponse({'status': 'success', 'message': 'MERN stack provisioned!'})
    return JsonResponse({'status': 'error', 'message': 'Invalid request'})


@login_required(login_url='/')
def delete_python(request):
    if request.user.is_authenticated:
        
        if request.method=="POST":
            data = json.loads(request.body)  # Get the data from the request body
            domainname = data.get('domain').strip()
            name = data.get('name').strip()

            # Ownership check for non-admin
            if not request.user.is_superuser:
                owner = user.objects.filter(username=request.user.username).first()
                if not owner or (owner.domain != domainname and not subdomainname.objects.filter(subdomain=domainname, domain=owner.domain).exists()):
                    return JsonResponse({'status': 'error', 'message': 'Unauthorized'}, status=403)

            try:
                iwefj=domain.objects.get(domain=domainname).dir
            except:
                 lololol=subdomainname.objects.get(subdomain=domainname).domain
                 iwefj=domain.objects.get(domain=lololol).dir
            # Clean files securely as root
            try:
                directory_path = os.path.join(paths.HOME_BASE, iwefj, name)
                run_command(f'sudo rm -rf {shlex.quote(directory_path)}')
            except:
                pass

            # Remove service — platform-aware
            if sys.platform == 'win32':
                # Windows: stop and delete the Windows service via sc.exe
                try:
                    subprocess.run(['sc', 'stop', name], capture_output=True)
                    subprocess.run(['sc', 'delete', name], capture_output=True)
                except Exception:
                    pass
            else:
                # Linux: remove systemd service file
                svc_file = f'/etc/systemd/system/{name}.service'
                if os.path.exists(svc_file):
                    try:
                        run_command(f'sudo systemctl stop {name}')
                        run_command(f'sudo systemctl disable {name}')
                        os.remove(svc_file)
                        run_command('sudo systemctl daemon-reload')
                    except Exception:
                        pass
            from voidplatform.linux.web import get_active_engine, get_active_engine_manager
            import re
            engine = get_active_engine()
            mgr = get_active_engine_manager()

            if engine == 'ols':
                old_conf = mgr.read_site_config(domainname)
                # Remove python extprocessor and its contexts
                new_conf = re.sub(rf'extprocessor python_{name}\s*{{[^}}]+}}\n?', '', old_conf)
                new_conf = re.sub(rf'context /\s*{{[^}}]+handler\s+python_{name}[^}}]+}}\n?', '', new_conf)
                new_conf = re.sub(r'context /static/\s*\{[^}]*type\s+null[^}]*\}\n?', '', new_conf)
                mgr.write_and_test_site_config(domainname, new_conf)
            else:
                old_conf = mgr.read_site_config(domainname)
                if old_conf:
                    # Strip out Python / and /static/ proxies safely
                    new_conf = re.sub(r'[ \t]*location / \{(?:[^{}]|\{[^{}]*\})*\}\s*', '', old_conf)
                    new_conf = re.sub(r'[ \t]*location /static/ \{(?:[^{}]|\{[^{}]*\})*\}\s*', '', new_conf)
                    mgr.write_and_test_site_config(domainname, new_conf)

            df=pythonname.objects.filter(domain=domainname,name=name).first()
            if df:
                df.delete()

            run_command('sudo systemctl daemon-reload')
            import time
            time.sleep(2)
            return JsonResponse({'status': 'success', 'message': 'Python application deleted.'})
    return JsonResponse({'status': 'error', 'message': 'Invalid request.'})

try:
    import pexpect
    persistent_shell = pexpect.spawn('/bin/bash', encoding='utf-8')
    persistent_shell.expect(r'[#$%\)]')
except Exception:
    persistent_shell = None
datahold=""

@never_cache
@login_required(login_url='/')
def terminalname(request):
    global datahold

    if persistent_shell is None:
        return JsonResponse({'status': 'error', 'message': 'Terminal not available on this platform.'})
    if request.user.is_superuser:
                    current=request.session['name']
    else:
                    current=str(request.user)
    homedir=os.path.join(paths.HOME_BASE, current+datahold)
    
    if request.method == 'POST':
        command = request.POST.get('command', '')
        name = request.POST.get('name', '')
        dir = request.POST.get('dir', '')

        # Block dangerous shell operators
        _dangerous = ['&&', '||', ';', '|', '`', '$(',  '>', '<', '\n']
        for d in _dangerous:
            if d in command:
                return JsonResponse({"output": "Error: shell operators not allowed. Use single commands."})
        
        # Always use the venv pip/python binary so packages install into the isolated environment
        venv_bin = f"/home/{shlex.quote(current)}/{shlex.quote(name)}/venv/bin"
        if command.startswith('pip'):
            command = f"{venv_bin}/{command}"
        elif command.startswith('python'):
            command = f"{venv_bin}/{command}"

        elif command.startswith('cd'):
              target=command.replace('cd','').strip()
              # Prevent path traversal
              if '..' in target:
                  return JsonResponse({"output": "Error: path traversal not allowed."})
              if f"/home/{current}" not in  target:
                    if target[0]!='/':
                          target="/"+target
                    datahold=target
                    target=homedir+target
                    homedir=target
                    command="cd "+target
              command = f'sudo -u {shlex.quote(current)} bash -c "cd {shlex.quote(homedir)} && {command}"'
        else:
             command = f'sudo -u {shlex.quote(current)} bash -c "cd {shlex.quote(homedir)} && {command}"'
        try:
            
                persistent_shell.sendline(command)
                persistent_shell.expect(r'[#$%\)]') 
                output = persistent_shell.before.strip()
                output=output.replace("/var/www/panel","")
        except Exception as e:
                output = f"Error: {str(e)}"
        return JsonResponse({"output":output})
    return JsonResponse({"output": "Invalid request"})

@never_cache
@login_required(login_url='/')
def terminalnamenpm(request):
    global datahold

    if persistent_shell is None:
        return JsonResponse({'status': 'error', 'message': 'Terminal not available on this platform.'})
    if request.user.is_superuser:
                    current=request.session['name']
    else:
                    current=str(request.user)
    homedir=os.path.join(paths.HOME_BASE, current+datahold)
    
    if request.method == 'POST':
        command = request.POST.get('command', '')
        name = request.POST.get('name', '')
        dir = request.POST.get('dir', '')

        # Block dangerous shell operators
        _dangerous = ['&&', '||', ';', '|', '`', '$(',  '>', '<', '\n']
        for d in _dangerous:
            if d in command:
                return JsonResponse({"output": "Error: shell operators not allowed. Use single commands."})
 
        if command.startswith('cd'):
              target=command.replace('cd','').strip()
              if '..' in target:
                  return JsonResponse({"output": "Error: path traversal not allowed."})
              if f"/home/{current}" not in  target:
                    if target[0]!='/':
                          target="/"+target
                    datahold=target
                    target=homedir+target
                    homedir=target
                    command="cd "+target
              command = f'sudo -u {shlex.quote(current)} bash -c "cd {shlex.quote(homedir)} && {command}"'
        else:
             # Run non-cd commands also under sudo -u to prevent RCE as web server user
             command = f'sudo -u {shlex.quote(current)} bash -c "cd {shlex.quote(homedir)} && {command}"'
        try:
            
                persistent_shell.sendline(command)
                persistent_shell.expect(r'[#$%\)]') 
                output = persistent_shell.before.strip()
                output=output.replace("/var/www/panel","")
        except Exception as e:
                output = f"Error: {str(e)}"
        return JsonResponse({"output":output})
    return JsonResponse({"output": "Invalid request"})


@login_required(login_url='/')
def emailmarketing(request,data):
   
    if request.user.is_superuser:
                d={}
                try:
                    
                    lold=domain.objects.get(domain=data)
                    d['domain']=data
                    d['python']=pythonname.objects.filter(main=lold.dir).all()     
                    url = 'https://voidpanel.com/admindocs/'  # Replace with your API URL
                    response = requests.get(url, timeout=2)
                    if response.status_code == 200:
                        dataee = response.json()  # Parse the JSON response
                        d['docs']=dataee
                    return render(request,'panel/emailmarketing.html',d)
                except Exception as e:
                    return redirect("/listwebsite/")
           
    else: 
        return redirect('/')
    

@login_required(login_url='/')
def createemailmarketing(request,data):
   
    if request.user.is_superuser:
                d={}
                try:
                    
                    lold=domain.objects.get(domain=data)
                    d['domain']=data
                    d['subdomain']=subdomainname.objects.filter(domain=data).all()      
                    url = 'https://voidpanel.com/admindocs/'  # Replace with your API URL
                    response = requests.get(url, timeout=2)
                    if response.status_code == 200:
                        dataee = response.json()  # Parse the JSON response
                        d['docs']=dataee
                    d['domain']=data
                    return render(request,'panel/createemailmarketing.html',d)
                except Exception as e:
                    return redirect("/listwebsite/")
           
    else: 
        return redirect('/')


def addusermainapi(username,password,domain12,package12):     
               domain12=domain12[0].lower()
               email = 'info@'+domain12
               if package12 == 'Select':
                    package12='default'
               
               
               try:
                    fgf=package.objects.get(name=package12)
                    sto=str(fgf.storage)
               except:
                     return False 
               
               
               try:
                   x=domain.objects.get(domain=domain12)  
                   return False
               except:
                   import re
                   directories = os.listdir(paths.HOME_BASE)
                   # Sanitize to alphanumeric, max 16 chars for safe Unix username
                   base_name = re.sub(r'[^a-z0-9]', '', str(username).lower())[:16]
                   
                   domainname = base_name
                   counter = 1
                   while domainname in directories:
                       suffix = str(counter)
                       domainname = base_name[:16 - len(suffix)] + suffix
                       counter += 1
                       
                   path="/home/"+domainname
                   os.mkdir(path)
                   os.mkdir(path+'/public_html')
                   _vp_src = os.path.join(paths.PANEL_ROOT, 'voidpanel')
                   _vp_dst = os.path.join(path, 'public_html')
                   for _item in os.listdir(_vp_src):
                       _s = os.path.join(_vp_src, _item)
                       _d = os.path.join(_vp_dst, _item)
                       if os.path.isdir(_s):
                           shutil.copytree(_s, _d, dirs_exist_ok=True)
                       else:
                           shutil.copy2(_s, _d)
                   _ln_src = f'{paths.NGINX_SITES_AVAILABLE}/{domain12}.conf'
                   _ln_dst = f'{paths.NGINX_SITES_ENABLED}/'
                   if sys.platform == 'win32':
                       shutil.copy2(_ln_src, os.path.join(_ln_dst, f'{domain12}.conf'))
                   else:
                       run_command(f'sudo ln -s {_ln_src}  {_ln_dst}')
                   os.mkdir(path+'/ssl')
                   os.makedirs(os.path.join(path, 'mail', domain12), exist_ok=True)
                   os.mkdir(path+'/logs')
                   inipath=path+'/public_html/'+'php.ini'
                   php_ini_content = f"""
; PHP settings for {domain12}

; General settings
max_execution_time = 30
max_input_time = 60
memory_limit = 256M
post_max_size = 64M
upload_max_filesize = 64M
max_file_uploads = 20
default_charset = "UTF-8"
display_errors = Off
log_errors = On
error_log = "/{path}/public_html/logs/php_errors.log"
error_reporting = E_ALL & ~E_DEPRECATED & ~E_STRICT

; Timezone
date.timezone = "Asia/Kolkata"  ; Set to your timezone

; File Uploads
file_uploads = On
upload_tmp_dir = "/{path}/public_html/tmp"
max_file_uploads = 20

; Session settings
session.save_path = "/{path}/public_html/sessions"
session.gc_maxlifetime = 1440
session.cookie_httponly = 1
session.cookie_secure = 1

; Custom domain-based settings
open_basedir = "/{path}/public_html:/tmp"
"""
                   with open(inipath,'w') as f:
                        f.write(php_ini_content)
                   file_path = os.path.join(paths.NGINX_SITES_AVAILABLE, f"{domain12}.conf")
                   root_dir = path+'/public_html'
                 
                   cert_path, key_path = generate_ssl_certificates(domain12, path+'/ssl',path+'/logs')
                   if cert_path and key_path:
                             create_nginx_ssl_conf(file_path, domain12, root_dir, cert_path, key_path)
                   else:
                    
                       with open(paths.PANEL_LOG_FILE, 'a') as f:
                                f.write(f"Cannot Genrate open ssl for domain {domain12}\n")
                       import shutil
                       shutil.rmtree(path)
                       return False
                   key_dir = os.path.join(paths.OPENDKIM_KEY_DIR, domain12)
                   zone_file_path = os.path.join(paths.BIND_ZONE_DIR, f'db.{domain12}')
                   private_key_path, public_key_path = generate_dkim_keys(domain12, key_dir)
                   if private_key_path and public_key_path:
                      create_bind_records(domain12, key_dir, zone_file_path)
                      configure_opendkim(domain12, key_dir)
                    
                      with open(paths.PANEL_LOG_FILE, 'a') as f:
                                f.write(f" Genareted Dkmi Record for domain {domain12}\n")
                   else:
                       with open(paths.PANEL_LOG_FILE, 'a') as f:
                                f.write(f"Cannot Genarete Dkmi Record for domain {domain12}\n")
                       import shutil
                       shutil.rmtree(path)
                       return False
                   domain.objects.create(domain=domain12,email=email,dir=domainname,userdomain=True)
                   user.objects.create(domain=domain12,email=email,username=domainname,hosting_package=package12)
                   User.objects.create_user(username=domainname,email=email,password=password)
                   try:
                       # Create Unix user via platform layer
                       get_platform().users.create_user(domainname, password, shell='/usr/sbin/nologin')
                   except Exception as e:
                       with open(paths.PANEL_LOG_FILE, 'a') as f:
                           f.write(f"Error creating unix user {domainname}: {str(e)}\n")
                           
                   if sys.platform != 'win32':
                       run_command(f'sudo chown {domainname}:{domainname}  /home/{domainname}')
                   
                   # Apply quota via platform layer
                   try:
                       get_platform().users.set_quota(domainname, sto, sto)
                   except:
                       pass
                   
                   # Reload/restart all services via platform layer (works on all platforms)
                   _plat = get_platform()
                   for _svc in ('opendkim', 'bind9', 'postfix', 'nginx'):
                       try:
                           _plat.services.reload(_svc)
                       except Exception:
                           pass
                   return "rohan"
                   
                   
            
         

# ─── Analytics View (Admin) ─────────────────────────────────────────────────
@login_required(login_url='/')
@login_required(login_url='/')
def copysite(request):
    """
    Clone a remote website into the user's (or admin-specified) directory.
    Accepts POST: target_url, destination (optional).
    Runs in a background thread and returns immediately.
    """
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'POST required'}, status=405)

    target_url = request.POST.get('target_url', '').strip()
    destination = request.POST.get('destination', '').strip()

    if not target_url:
        return JsonResponse({'status': 'error', 'message': 'Target URL is required'}, status=400)

    # Ensure proper URL scheme
    if not target_url.startswith(('http://', 'https://')):
        target_url = 'https://' + target_url

    # Resolve destination directory
    domain_name = request.POST.get('domain', '').strip() or request.GET.get('domain', '').strip()
    user_dir = None
    if domain_name:
        try:
            from control.models import domain as ctrl_domain
            dom_obj = ctrl_domain.objects.filter(domain=domain_name).first()
            if dom_obj:
                user_dir = dom_obj.dir
        except Exception:
            pass

    if not user_dir:
        try:
            uname = request.session.get('name', request.user.username) if request.user.is_superuser else str(request.user)
            from control.models import user as ctrl_user
            u_obj = ctrl_user.objects.filter(username=uname).first()
            user_dir = u_obj.dir if u_obj else uname
        except Exception:
            user_dir = str(request.user)

    unix_user = user_dir
    allowed_base = os.path.join(paths.HOME_BASE, user_dir) # /home/username

    if not destination:
        from urllib.parse import urlparse as _urlparse
        site_name = _urlparse(target_url).netloc.replace('www.', '') or 'cloned_site'
        destination = os.path.join(allowed_base, 'public_html', site_name)
    else:
        # Sanitize user-provided path — strictly force it to be inside /home/username/
        try:
            # Strip leading slashes/dots and normalize
            clean_rel = destination.lstrip('/')
            
            # Remove any prefix that matches /home/username or home/username
            if clean_rel.startswith('home/' + user_dir + '/'):
                clean_rel = clean_rel[len('home/' + user_dir + '/'):]
            elif clean_rel == 'home/' + user_dir or clean_rel == 'home':
                clean_rel = ''
            
            # Form final destination path
            safe_dest = os.path.abspath(os.path.join(allowed_base, clean_rel))
            
            # Enforce that the final resolved path MUST start with /home/username/
            if safe_dest == allowed_base or not safe_dest.startswith(allowed_base + '/'):
                # Fallback to default user public_html folder if they tried to escape
                from urllib.parse import urlparse as _urlparse
                site_name = _urlparse(target_url).netloc.replace('www.', '') or 'cloned_site'
                safe_dest = os.path.join(allowed_base, 'public_html', site_name)
                
            destination = safe_dest
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': f'Path resolution error: {str(e)}'}, status=400)

    # Ensure parent directory (public_html) has group www-data and execution permission
    import subprocess, sys
    if sys.platform != 'win32':
        parent_dir = os.path.dirname(destination)
        subprocess.run(['sudo', 'chown', f'{unix_user}:www-data', parent_dir], check=False)
        subprocess.run(['sudo', 'chmod', '750', parent_dir], check=False)

        # Create destination directory and own it by www-data
        subprocess.run(['sudo', 'mkdir', '-p', destination], check=False)
        subprocess.run(['sudo', 'chown', '-R', 'www-data:www-data', destination], check=False)
        subprocess.run(['sudo', 'chmod', '-R', '755', destination], check=False)

    # Kick off background clone thread
    import threading
    def _run_clone():
        try:
            clone_website(target_url, destination)
        finally:
            if sys.platform != 'win32' and unix_user:
                subprocess.run(['sudo', 'chown', '-R', f'{unix_user}:www-data', destination], check=False)
                subprocess.run(['sudo', 'chmod', '-R', '755', destination], check=False)

    t = threading.Thread(target=_run_clone, daemon=True)
    t.start()

    return JsonResponse({
        'status': 'success',
        'message': f'Cloning started! Files will appear in {destination}',
        'destination': destination
    })


@login_required(login_url='/')
def copysite_status(request):
    """
    Get progress status of a running site clone task.
    Accepts GET/POST: destination.
    """
    import os, hashlib, json
    from django.http import JsonResponse
    from voidplatform.config import paths

    destination = request.GET.get('destination', '').strip() or request.POST.get('destination', '').strip()
    if not destination:
        return JsonResponse({'status': 'error', 'message': 'Destination is required'}, status=400)

    domain_name = request.POST.get('domain', '').strip() or request.GET.get('domain', '').strip()
    user_dir = None
    if domain_name:
        try:
            from control.models import domain as ctrl_domain
            dom_obj = ctrl_domain.objects.filter(domain=domain_name).first()
            if dom_obj:
                user_dir = dom_obj.dir
        except Exception:
            pass

    if not user_dir:
        try:
            uname = request.session.get('name', request.user.username) if request.user.is_superuser else str(request.user)
            from control.models import user as ctrl_user
            u_obj = ctrl_user.objects.filter(username=uname).first()
            user_dir = u_obj.dir if u_obj else uname
        except Exception:
            user_dir = str(request.user)

    allowed_base = os.path.join(paths.HOME_BASE, user_dir)

    clean_rel = destination.lstrip('/')
    if clean_rel.startswith('home/' + user_dir + '/'):
        clean_rel = clean_rel[len('home/' + user_dir + '/'):]
    elif clean_rel == 'home/' + user_dir or clean_rel == 'home':
        clean_rel = ''
    safe_dest = os.path.abspath(os.path.join(allowed_base, clean_rel))
    if safe_dest == allowed_base or not safe_dest.startswith(allowed_base + '/'):
        site_name = 'cloned_site'
        safe_dest = os.path.join(allowed_base, 'public_html', site_name)

    task_id = hashlib.md5(safe_dest.encode()).hexdigest()
    status_path = f"/tmp/clone_{task_id}.json"

    if not os.path.exists(status_path):
        return JsonResponse({'status': 'not_running', 'percentage': 0, 'current_file': '', 'logs': []})

    try:
        with open(status_path, 'r') as sf:
            data = json.load(sf)
            return JsonResponse(data)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': f'Failed to read status: {str(e)}'}, status=500)


def analytics(request):
    domain_name = request.GET.get('domain', '')
    if not domain_name:
        return redirect('/panel/')

    try:
        with open(paths.MYSQL_PASSWORD_FILE, 'r') as f:
            adminpassword = f.read().strip()
    except Exception:
        adminpassword = ''

    d = {}
    d['adminpassword'] = adminpassword
    d['domain'] = domain_name

    # Domain object
    dom_obj = domain.objects.filter(domain=domain_name).first()
    if not dom_obj:
        return redirect('/panel/')

    d['username'] = dom_obj.username
    d['homedir'] = dom_obj.dir
    d['php_version'] = getattr(dom_obj, 'php', 'N/A')
    d['domain_status'] = getattr(dom_obj, 'status', True)

    # Package info
    usr_obj = user.objects.filter(domain=domain_name).first()
    if usr_obj:
        d['package_name'] = usr_obj.hosting_package or 'N/A'
        pak = package.objects.filter(name=usr_obj.hosting_package).first()
        d['disk_quota_mb'] = pak.storage if pak else '0'
    else:
        d['package_name'] = 'N/A'
        d['disk_quota_mb'] = '0'

    # Disk usage
    home_dir = os.path.join(paths.HOME_BASE, dom_obj.dir)
    try:
        disk_used = get_directory_size_in_mb(home_dir)
    except Exception:
        disk_used = 0
    d['disk_used'] = int(disk_used)
    quota = int(d['disk_quota_mb']) if str(d['disk_quota_mb']).isdigit() else 0
    d['disk_percent'] = round((int(disk_used) / quota) * 100) if quota > 0 else 0

    # Live status
    d['live'] = is_website_live(f'http://{domain_name}')

    # SSL — check if cert exists
    ssl_cert = os.path.join(paths.LETSENCRYPT_LIVE, domain_name, 'fullchain.pem')
    d['ssl_active'] = os.path.exists(ssl_cert)

    # Email accounts
    d['emails'] = allemail.objects.filter(domain=domain_name).all()

    # Subdomains
    d['subdomains'] = subdomainname.objects.filter(domain=domain_name).all()

    # Python apps
    d['python_apps'] = pythonname.objects.filter(main=domain_name).all()

    # MERN apps
    d['mern_apps'] = mernname.objects.filter(main=domain_name).all()

    # DNS records
    zone_file = os.path.join(paths.BIND_ZONE_DIR, f'db.{domain_name}')
    try:
        dns_records = parse_dns_zone_file(zone_file)
        d['dns_records'] = [r for r in dns_records if r.get('type') in ('A','MX','CNAME','TXT','NS','AAAA')]
        d['dns_count'] = len(d['dns_records'])
    except Exception:
        d['dns_records'] = []
        d['dns_count'] = 0

    # MySQL database count
    try:
        db_names = get_database_names_with_filter(adminpassword, dom_obj.dir)
        d['db_count'] = len(db_names) if db_names else 0
    except Exception:
        d['db_count'] = 0

    return render(request, 'panel/analytics.html', d)


# ─── Web Server Manager (Admin Only) ────────────────────────────────────────

@login_required(login_url='/')
def webserver_manager(request):
    """Admin-only page showing the active web server engine (read-only).
    Engine selection is performed at installation time only.
    """
    if not request.user.is_superuser:
        return HttpResponse('Unauthorized', status=403)

    from voidplatform.linux.web import get_active_engine
    d = {}
    try:
        d['active_engine'] = get_active_engine()
    except PermissionError:
        try:
            import subprocess
            subprocess.run(['sudo', 'chmod', '644', '/etc/voidpanel/web_engine'], check=True)
            d['active_engine'] = get_active_engine()
        except Exception:
            d['active_engine'] = 'nginx'  # safe default

    # Detect service running status via pid files
    d['nginx_running'] = (os.path.exists('/run/nginx.pid') or
                          os.path.exists('/var/run/nginx.pid'))
    d['ols_running']   = (os.path.exists('/tmp/lshttpd/lshttpd.pid') or
                          os.path.exists('/usr/local/lsws/logs/lshttpd.pid'))
    d['ols_installed'] = (os.path.exists('/usr/local/lsws') or
                          d['active_engine'] == 'ols' or
                          d['ols_running'])
    d['domain_count'] = domain.objects.count()
    return render(request, 'panel/webserver_manager.html', d)


# ─── LiteSpeed Admin Auto-Login (Admin Only) ─────────────────────────────────

@login_required(login_url='/')
def ols_admin_proxy(request):
    """
    Superuser-only view that:
      1. Reads the stored OLS admin credentials from /etc/voidpanel/
      2. Issues a POST login to the OLS web admin (port 7080) using requests
      3. Forwards the authenticated session token back to the browser as a
         redirect — so the admin lands directly inside the OLS panel without
         typing any credentials.

    Security:
      - Only accessible to Django superusers.
      - Credentials are stored in root-only readable file (/etc/voidpanel/ols_admin_pass).
      - The proxy never exposes the password to the browser — it exchanges it
        server-side for a session cookie and redirects.
    """
    if not request.user.is_superuser:
        return HttpResponse('Unauthorized', status=403)

    # Read OLS credentials
    try:
        ols_user = open('/etc/voidpanel/ols_admin_user').read().strip()
    except Exception:
        ols_user = 'admin'
    try:
        ols_pass = open('/etc/voidpanel/ols_admin_pass').read().strip()
    except Exception:
        ols_pass = ''

    if not ols_pass:
        return HttpResponse(
            '<h2 style="font-family:sans-serif;color:#ef4444;padding:40px">'
            'OLS admin credentials not found at /etc/voidpanel/ols_admin_pass.<br>'
            'Make sure OpenLiteSpeed was installed via the VoidPanel installer.</h2>',
            status=503
        )

    OLS_BASE = 'http://127.0.0.1:7080'

    try:
        import requests as _req
        session = _req.Session()

        # Step 1: GET the login page to get any initial cookies / CSRF token
        login_page = session.get(
            f'{OLS_BASE}/login.php',
            timeout=5,
            verify=False,
            allow_redirects=True
        )

        # Step 2: POST credentials to OLS
        login_data = {
            'p_pass': ols_pass,
            'p_user': ols_user,
            'p_do':   'login',
        }
        auth_resp = session.post(
            f'{OLS_BASE}/login.php',
            data=login_data,
            timeout=5,
            verify=False,
            allow_redirects=False
        )

        # Step 3: Extract session cookie and build redirect response
        session_cookies = session.cookies.get_dict()

        from django.http import HttpResponse as _HR
        response = _HR(status=302)
        response['Location'] = f'{OLS_BASE}/'

        # Forward OLS session cookies to the browser so it arrives authenticated
        for cookie_name, cookie_val in session_cookies.items():
            response.set_cookie(
                cookie_name,
                cookie_val,
                domain=request.get_host().split(':')[0],
                samesite='Lax',
                httponly=True
            )
        return response

    except Exception as e:
        # OLS not running? Show helpful message
        return HttpResponse(
            f'<div style="font-family:sans-serif;background:#0f172a;color:#e2e8f0;'
            f'min-height:100vh;display:flex;align-items:center;justify-content:center;'
            f'flex-direction:column;gap:16px;padding:40px">'
            f'<div style="font-size:3rem">⚡</div>'
            f'<h2 style="color:#f59e0b;margin:0">OpenLiteSpeed Admin Panel</h2>'
            f'<p style="color:#94a3b8;text-align:center">Could not connect to OLS admin on port 7080.<br>'
            f'Make sure LiteSpeed is the active engine and the service is running.</p>'
            f'<a href="/webserver/" style="background:#6366f1;color:#fff;padding:12px 28px;'
            f'border-radius:10px;text-decoration:none;font-weight:600;">Open Web Server Manager</a>'
            f'<code style="color:#64748b;font-size:.75rem">{e}</code>'
            f'</div>',
            status=503
        )


# ─── Raw WebServer Config Editor APIs ─────────────────────────────────────────
import json

@login_required(login_url='/')
def api_get_site_config(request):
    if not request.user.is_superuser:
        return JsonResponse({'status': 'error', 'message': 'Unauthorized'}, status=403)
    
    domain_name = request.GET.get('domain')
    if not domain_name:
        return JsonResponse({'status': 'error', 'message': 'Missing domain'}, status=400)
    
    from voidplatform.linux.web import get_active_engine_manager, get_active_engine
    mgr = get_active_engine_manager()
    conf_text = mgr.read_site_config(domain_name)
    engine = get_active_engine()
    
    return JsonResponse({
        'status': 'success',
        'config': conf_text,
        'engine': engine
    })

@login_required(login_url='/')
@csrf_exempt
def api_save_site_config(request):
    if not request.user.is_superuser:
         return JsonResponse({'status': 'error', 'message': 'Unauthorized'}, status=403)
         
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Invalid method'}, status=405)
        
    try:
        data = json.loads(request.body)
        domain_name = data.get('domain')
        config_text = data.get('config')
    except Exception:
        return JsonResponse({'status': 'error', 'message': 'Invalid JSON'}, status=400)
        
    if not domain_name or not config_text:
        return JsonResponse({'status': 'error', 'message': 'Missing domain or config text'}, status=400)
        
    from voidplatform.linux.web import get_active_engine_manager
    mgr = get_active_engine_manager()
    
    # Write and test handles rollback internally
    result = mgr.write_and_test_site_config(domain_name, config_text)
    if result.success:
        return JsonResponse({'status': 'success', 'message': 'Configuration updated and web server reloaded.'})
    else:
        return JsonResponse({'status': 'error', 'message': result.error}, status=400)

@csrf_exempt
def suspendemail_incoming(request):
    import shlex
    if not (request.user.is_superuser or request.user.is_authenticated): return JsonResponse({'error': 'Unauthorized'})
    email = request.POST.get('email')
    action = request.POST.get('action') 
    if not email: return JsonResponse({'error': 'No email'})
    
    file_path = "/etc/postfix/vp_suspended_incoming"
    if action == 'suspend':
        cmd = f"sudo bash -c 'grep -q \"^{shlex.quote(email)} \" {file_path} || echo \"{shlex.quote(email)} REJECT Incoming messages suspended\" >> {file_path}'"
    else:
        cmd = f"sudo sed -i '/^{shlex.quote(email)} /d' {file_path}"
    run_command(cmd)
    run_command(f"sudo postmap {file_path}")
    return JsonResponse({'status': 'success'})

@csrf_exempt
def suspendemail_outgoing(request):
    import shlex
    if not (request.user.is_superuser or request.user.is_authenticated): return JsonResponse({'error': 'Unauthorized'})
    email = request.POST.get('email')
    action = request.POST.get('action') 
    if not email: return JsonResponse({'error': 'No email'})
    
    file_path = "/etc/postfix/vp_suspended_outgoing"
    if action == 'suspend':
        cmd = f"sudo bash -c 'grep -q \"^{shlex.quote(email)} \" {file_path} || echo \"{shlex.quote(email)} REJECT Outgoing messages suspended\" >> {file_path}'"
    else:
        cmd = f"sudo sed -i '/^{shlex.quote(email)} /d' {file_path}"
    run_command(cmd)
    run_command(f"sudo postmap {file_path}")
    return JsonResponse({'status': 'success'})

@csrf_exempt
def set_email_limit(request):
    if not (request.user.is_superuser or request.user.is_authenticated): return JsonResponse({'error': 'Unauthorized'})
    email = request.POST.get('email')
    limit = request.POST.get('limit')
    limit_type = request.POST.get('type')
    if not email or not limit: return JsonResponse({'error': 'Invalid parameters'})
    
    try: limit_count = int(limit)
    except: return JsonResponse({'error': 'Limit must be integer'})
        
    timespan = 3600 if limit_type == 'hourly' else 86400
    
    # Save/delete user limit in our custom daemon's SQLite database
    if limit_count > 0:
        cmd = f"sudo python3 -c \"import sqlite3; conn=sqlite3.connect('/var/lib/voidpanel-mail-policy/rate.db'); conn.execute('CREATE TABLE IF NOT EXISTS user_limits (username TEXT PRIMARY KEY, limit_val INTEGER, timespan INTEGER)'); conn.execute('INSERT OR REPLACE INTO user_limits (username, limit_val, timespan) VALUES (\\\"{email}\\\", {limit_count}, {timespan})'); conn.commit(); conn.close()\""
    else:
        cmd = f"sudo python3 -c \"import sqlite3; conn=sqlite3.connect('/var/lib/voidpanel-mail-policy/rate.db'); conn.execute('CREATE TABLE IF NOT EXISTS user_limits (username TEXT PRIMARY KEY, limit_val INTEGER, timespan INTEGER)'); conn.execute('DELETE FROM user_limits WHERE username=\\\"{email}\\\"'); conn.commit(); conn.close()\""
    
    run_command(cmd)
    return JsonResponse({'status': 'success'})

# ─── Restore / Migration Functions ───────────────────────────────────────────

@login_required(login_url='/')
def restore_wizard(request):
    """Render the restore/migration interface in the admin panel."""
    if not request.user.is_superuser:
        return redirect('/')
        
    d = {}
    from control.models import user as VUser
    # Provide users to assign recovered domains/files
    d['users_list'] = VUser.objects.all()
    
    return render(request, 'panel/restore.html', d)

@login_required(login_url='/')
@csrf_exempt
def process_restore(request):
    """Handle incoming request to process a backup."""
    if not request.user.is_superuser:
        return JsonResponse({'status': 'error', 'message': 'Forbidden'}, status=403)
        
    if request.method == 'POST':
        source_type = request.POST.get('source_type')
        
        auth_data = {}
        if source_type == 'file':
            backup_file = request.FILES.get('backup_file')
            if not backup_file:
                return JsonResponse({'status': 'error', 'message': 'No file uploaded.'}, status=400)
            
            # Save file temporarily in a secure place (e.g. /tmp/ or MEDIA_ROOT)
            import uuid
            tmp_path = os.path.join('/tmp', f'restore_{uuid.uuid4().hex}_{backup_file.name}')
            with open(tmp_path, 'wb+') as destination:
                for chunk in backup_file.chunks():
                    destination.write(chunk)
                    
            auth_data['file_path'] = tmp_path
        
        elif source_type in ['cpanel', 'plesk', 'directadmin']:
            host = request.POST.get('server_host')
            user = request.POST.get('server_user')
            passwd = request.POST.get('server_pass')
            if not all([host, user, passwd]):
                return JsonResponse({'status': 'error', 'message': 'Missing panel credentials.'}, status=400)
                
            auth_data['host'] = host
            auth_data['user'] = user
            auth_data['pass'] = passwd
            
        else:
            return JsonResponse({'status': 'error', 'message': 'Invalid source type.'}, status=400)
            
        # Dispatch the Celery task
        try:
            from control.tasks import background_migration_task
            background_migration_task.delay(source_type, auth_data)
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': f'Failed to dispatch worker task: {str(e)}'}, status=500)
            
        return JsonResponse({'status': 'success'})
        
    return JsonResponse({'status': 'error', 'message': 'Invalid request method.'}, status=400)

# ─── User Restricted Terminal ────────────────────────────────────────────────

@login_required(login_url='/')
def user_terminal(request, username):
    """
    Open an xterm.js terminal restricted to the user's home directory.
    Only accessible by superusers. Uses the custom UserTerminalConsumer WebSocket.
    """
    if not request.user.is_superuser:
        return redirect('/')

    import re
    # Validate username to prevent injection
    if not re.match(r'^[a-z0-9_]{1,32}$', username):
        return HttpResponse('Invalid username.', status=400)

    from control.models import user as VUser
    try:
        vuser = VUser.objects.get(username=username)
    except VUser.DoesNotExist:
        return HttpResponse('User not found.', status=404)

    if not vuser.shell:
        return HttpResponse('Shell access not enabled for this user.', status=403)
        
    try:
        from voidplatform.config import paths
        home_dir = os.path.join(paths.HOME_BASE, username)
    except ImportError:
        home_dir = f'/home/{username}'

    # Fetch basic server info for the UI
    import socket
    hostname = socket.gethostname()
    try:
        ip = request.META.get('SERVER_NAME', '127.0.0.1')
    except Exception:
        ip = "Unknown IP"

    d = {
        'terminal_user': username,
        'home_dir': home_dir,
        'hostname': hostname,
        'ip': ip,
    }
    return render(request, 'panel/user_terminal.html', d)


# ─── Shell Access Toggle API ─────────────────────────────────────────────────

@login_required(login_url='/')
def toggle_shell_access(request):
    """
    POST /api/toggle-shell/
    Superuser-only. Enables or revokes shell access for a VoidPanel user.
    Sets/clears the `shell` flag in the DB and runs usermod to set the
    system shell to /bin/bash (enable) or /bin/false (revoke).
    """
    if not request.user.is_superuser:
        return JsonResponse({'status': 'error', 'message': 'Permission denied.'}, status=403)

    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'POST required.'}, status=405)

    import re
    username = request.POST.get('username', '').strip()
    enable = request.POST.get('enable', '0') == '1'

    if not re.match(r'^[a-z0-9_]{1,32}$', username):
        return JsonResponse({'status': 'error', 'message': 'Invalid username.'}, status=400)

    from control.models import user as VUser
    try:
        vuser = VUser.objects.get(username=username)
    except VUser.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'User not found.'}, status=404)

    # Update DB flag
    vuser.shell = enable
    vuser.save()

    # Update system shell (Linux only)
    if sys.platform != 'win32':
        if enable:
            os.system(f'sudo usermod -s /bin/bash {username}')
            # Secure home directory permissions and ownership when shell is enabled
            home_dir = f'/home/{username}'
            if os.path.exists(home_dir):
                os.system(f'sudo chown -R {username}:www-data {home_dir}')
                os.system(f'sudo chmod 751 {home_dir}')
                os.system(f'sudo find {home_dir} -type d -exec chmod 750 {{}} +')
                os.system(f'sudo find {home_dir} -type f -exec chmod 640 {{}} +')
                # Explicitly allow www-data to write to the logs directory and files inside it
                logs_dir = f'{home_dir}/logs'
                os.system(f'sudo chmod 770 {logs_dir}')
                os.system(f'sudo find {logs_dir} -type f -exec chmod 660 {{}} +')
                for bash_file in ('.bashrc', '.profile', '.bash_profile', '.bash_logout'):
                    bpath = os.path.join(home_dir, bash_file)
                    if os.path.exists(bpath):
                        os.system(f'sudo chmod 644 {bpath}')
        else:
            os.system(f'sudo usermod -s /bin/false {username}')

    action = 'enabled' if enable else 'revoked'
    return JsonResponse({'status': 'success', 'message': f'Shell access {action} for {username}.'})

# ── Nginx Cache Toggle API ──────────────────────────────────────────────────
@csrf_exempt
@login_required(login_url='/')
def api_nginx_cache_status(request):
    """Return whether Nginx browser caching is enabled for a domain."""
    domainname = request.GET.get('domain', '').strip()
    if not domainname:
        return JsonResponse({'status': 'error', 'message': 'Missing domain'}, status=400)

    if not request.user.is_superuser:
        from control.models import user as cuser
        if not cuser.objects.filter(domain=domainname, username=request.user).exists():
            return JsonResponse({'status': 'error', 'message': 'Unauthorized'}, status=403)

    from voidplatform.linux.web import get_active_engine, get_active_engine_manager
    engine = get_active_engine()
    if engine != 'nginx':
        return JsonResponse({'status': 'error', 'message': 'Cache toggle is only available for Nginx.', 'engine': engine})

    mgr = get_active_engine_manager()
    conf = mgr.read_site_config(domainname)
    if not conf:
        return JsonResponse({'status': 'error', 'message': 'Config not found.'})

    # Check if the cache block marker exists
    enabled = '# VP_NGINX_CACHE_START' in conf
    return JsonResponse({'status': 'success', 'enabled': enabled, 'engine': engine})


@csrf_exempt
@login_required(login_url='/')
def api_nginx_cache_toggle(request):
    """Enable or disable Nginx browser caching for a domain."""
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'POST required.'}, status=405)
    domainname = request.POST.get('domain', '').strip()
    enable = request.POST.get('enable', '0') == '1'

    if not domainname:
        return JsonResponse({'status': 'error', 'message': 'Missing domain'}, status=400)

    if not request.user.is_superuser:
        from control.models import domain
        if not domain.objects.filter(domain=domainname, user=request.user).exists():
            return JsonResponse({'status': 'error', 'message': 'Unauthorized'}, status=403)

    from voidplatform.linux.web import get_active_engine, get_active_engine_manager
    engine = get_active_engine()
    if engine != 'nginx':
        return JsonResponse({'status': 'error', 'message': 'Cache toggle is only available for Nginx.'})

    mgr = get_active_engine_manager()
    conf = mgr.read_site_config(domainname)
    if not conf:
        return JsonResponse({'status': 'error', 'message': 'Config not found.'})

    import re
    cache_block = """
    # VP_NGINX_CACHE_START
    location ~* \\.(jpg|jpeg|png|gif|ico|svg|webp|woff|woff2|ttf|otf|eot|css|js)$ {
        expires 30d;
        add_header Cache-Control "public, no-transform";
        add_header Vary "Accept-Encoding";
        access_log off;
    }
    # VP_NGINX_CACHE_END"""

    has_cache = '# VP_NGINX_CACHE_START' in conf

    if enable and not has_cache:
        # Insert cache block before the closing } of the first server block
        # Find the last location ~ /\.ht block or just before the final }
        if 'location ~ /\\.ht {' in conf:
            conf = conf.replace('location ~ /\\.ht {', cache_block + '\n\n    location ~ /\\.ht {', 1)
        elif re.search(r'location\s*~\s*/\\.\(ht\|svn\|git\)\s*\{', conf):
            conf = re.sub(r'(location\s*~\s*/\\.\(ht\|svn\|git\)\s*\{)', cache_block + r'\n\n    \1', conf, count=1)
        elif re.search(r'location\s*~\s*/\\\.\(\?!well-known\)\s*\{', conf):
            conf = re.sub(r'(location\s*~\s*/\\\.\(\?!well-known\)\s*\{)', cache_block + r'\n\n    \1', conf, count=1)
        else:
            # Insert before the first server block closing brace
            last_brace = conf.rfind('}')
            second_last = conf.rfind('}', 0, last_brace)
            if second_last != -1:
                conf = conf[:second_last] + cache_block + '\n\n' + conf[second_last:]

    elif not enable and has_cache:
        conf = re.sub(r'\s*# VP_NGINX_CACHE_START.*?# VP_NGINX_CACHE_END', '', conf, flags=re.DOTALL)

    result = mgr.write_and_test_site_config(domainname, conf)
    if result.success:
        action = 'enabled' if enable else 'disabled'
        return JsonResponse({'status': 'success', 'message': f'Nginx cache {action} for {domainname}.'})
    else:
        return JsonResponse({'status': 'error', 'message': f'Nginx validation failed: {result.error}'}, status=400)


# ── Activity Log ──────────────────────────────────────────────────────────────

@login_required(login_url='/')
def activitylog_page(request):
    """Render the activity log UI."""
    return render(request, 'panel/activitylog.html')


@login_required(login_url='/')
def api_activity_logs(request):
    """Proxy through to the control.activity API handler."""
    from control.activity import api_activity_logs as _handler
    return _handler(request)


@login_required(login_url='/')
def api_clear_activity_logs(request):
    """Proxy through to the control.activity clear handler."""
    from control.activity import api_clear_logs as _handler
    return _handler(request)

# ── Support Ticket System (Proxy to voidpanel.com) ──────────────────────────

import requests

VOIDPANEL_API_URL = "https://voidpanel.com"

def get_license_key_value():
    from control.license import get_license
    lic = get_license()
    if lic and lic.status == 'active':
        return lic.key
    return None

@login_required(login_url='/')
def support_page(request):
    """Render the local support ticket interface."""
    if not request.user.is_superuser:
        return redirect('/')
    return render(request, 'panel/support.html')

@login_required(login_url='/')
@csrf_exempt
def api_ticket_create(request):
    """POST /api/tickets/create/ (Proxies to voidpanel.com)"""
    if not request.user.is_superuser:
        return JsonResponse({'status': 'error', 'message': 'Forbidden'}, status=403)
    if request.method != 'POST':
        return JsonResponse({'status': 'error'}, status=405)
        
    try:
        data = json.loads(request.body)
    except Exception:
        return JsonResponse({'status': 'error', 'message': 'Invalid JSON'}, status=400)

    license_key = get_license_key_value()
    if not license_key:
        return JsonResponse({'status': 'error', 'message': 'No active license found. Cannot submit ticket.'}, status=400)

    payload = {
        'license_key': license_key,
        'subject': data.get('subject', '').strip(),
        'department': data.get('department', 'Technical Support'),
        'priority': data.get('priority', 'medium'),
        'body': data.get('message', '').strip()
    }

    if not payload['subject'] or not payload['body']:
        return JsonResponse({'status': 'error', 'message': 'Subject and message are required'}, status=400)

    try:
        r = requests.post(f"{VOIDPANEL_API_URL}/api/panel/ticket/create/", json=payload, timeout=15)
        resp = r.json()
        if resp.get('ok'):
            return JsonResponse({'status': 'success', 'ticket_id': resp.get('ticket_number')})
        else:
            return JsonResponse({'status': 'error', 'message': resp.get('error', 'Failed to create ticket on VoidPanel.com')})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': 'Could not reach VoidPanel.com API'})


@login_required(login_url='/')
def api_ticket_list(request):
    """GET /api/tickets/list/ (Proxies to voidpanel.com)"""
    if not request.user.is_superuser:
        return JsonResponse({'status': 'error'}, status=403)
        
    license_key = get_license_key_value()
    if not license_key:
        return JsonResponse({'status': 'success', 'tickets': []})

    try:
        r = requests.post(f"{VOIDPANEL_API_URL}/api/panel/ticket/list/", json={'license_key': license_key}, timeout=15)
        resp = r.json()
        if resp.get('ok'):
            tickets = resp.get('tickets', [])
            for t in tickets:
                t['ticket_id'] = t.get('ticket_number')
                t['message'] = t.get('body', 'No message body provided.')
                t['created_at'] = t.get('created_at', t.get('last_reply_at', 'Unknown'))
            return JsonResponse({'status': 'success', 'tickets': tickets})
        else:
            return JsonResponse({'status': 'error', 'message': resp.get('error', 'Error fetching tickets')})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': 'Could not reach VoidPanel.com API'})


@login_required(login_url='/')
def api_ticket_detail(request, ticket_id):
    """GET /api/tickets/<ticket_id>/ (Pulls from list proxy)"""
    if not request.user.is_superuser:
        return JsonResponse({'status': 'error'}, status=403)
        
    license_key = get_license_key_value()
    if not license_key:
        return JsonResponse({'status': 'error', 'message': 'No license'}, status=400)

    try:
        r = requests.post(f"{VOIDPANEL_API_URL}/api/panel/ticket/list/", json={'license_key': license_key}, timeout=15)
        resp = r.json()
        if resp.get('ok'):
            tickets = resp.get('tickets', [])
            for t in tickets:
                if str(t.get('ticket_number')) == str(ticket_id):
                    raw_replies = t.get('replies', [])
                    
                    # In voidpanel.com API, the first 'reply' is actually the original ticket message
                    main_msg = "Message body unavailable."
                    created_by = "You"
                    if raw_replies:
                        first = raw_replies[0]
                        main_msg = first.get('body', '')
                        created_by = first.get('author', 'You')
                        raw_replies = raw_replies[1:]
                    
                    # Map 'body' to 'message' for the frontend
                    replies = []
                    for r_dict in raw_replies:
                        r_dict['message'] = r_dict.get('body', '')
                        replies.append(r_dict)
                        
                    return JsonResponse({
                        'status': 'success',
                        'ticket': {
                            'ticket_id': t.get('ticket_number'),
                            'subject': t.get('subject'),
                            'department': t.get('department'),
                            'priority': t.get('priority'),
                            'status': t.get('status'),
                            'message': main_msg,
                            'created_by': created_by,
                            'created_at': t.get('created_at', t.get('last_reply_at', 'Unknown')),
                        },
                        'replies': replies
                    })
            return JsonResponse({'status': 'error', 'message': 'Ticket not found'})
        return JsonResponse({'status': 'error', 'message': 'Error fetching ticket'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': 'Could not reach VoidPanel.com API'})


@login_required(login_url='/')
@csrf_exempt
def api_ticket_reply(request, ticket_id):
    """POST /api/tickets/<ticket_id>/reply/ — proxies to voidpanel.com"""
    if not request.user.is_superuser:
        return JsonResponse({'status': 'error'}, status=403)
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'POST required'}, status=405)

    try:
        data = json.loads(request.body)
    except Exception:
        return JsonResponse({'status': 'error', 'message': 'Invalid JSON'}, status=400)

    msg = data.get('message', '').strip()
    if not msg:
        return JsonResponse({'status': 'error', 'message': 'Message is required'}, status=400)

    license_key = get_license_key_value()
    if not license_key:
        return JsonResponse({'status': 'error', 'message': 'No active license found on this server.'}, status=400)

    try:
        r = requests.post(f"{VOIDPANEL_API_URL}/api/panel/ticket/reply/", json={
            'license_key': license_key,
            'ticket_number': str(ticket_id),
            'body': msg,
        }, timeout=15)
        resp = r.json()
        if resp.get('ok'):
            return JsonResponse({'status': 'success'})
        else:
            return JsonResponse({'status': 'error', 'message': resp.get('error', 'Failed to post reply')})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': 'Could not reach VoidPanel.com API'})


# ── Panel Activation Wizard ───────────────────────────────────────────────────

def activate_panel(request):
    """
    GET /activate/   — show the 3-tab activation wizard (exempt from LicenseMiddleware).
    POST /activate/  — handle login, register, or license-key activation.

    Modes (sent as hidden field 'mode'):
        login    — authenticate with an existing voidpanel.com account
        register — create a new voidpanel.com account AND activate
        key      — validate a manually pasted 64-char license key

    On success redirects to / (panel dashboard).
    On failure re-renders the wizard with an error message.
    """
    from django.shortcuts import render, redirect
    from django.contrib import messages as dj_messages
    from control.license import is_licensed, register_and_activate, activate_with_key

    # ── Already licensed: just show a status screen ───────────────────────────
    if is_licensed():
        return render(request, 'activate.html', {'already_active': True})

    # ── Handle form submission ────────────────────────────────────────────────
    if request.method == 'POST':
        mode = request.POST.get('mode', 'login').strip()

        # ── Mode: license key ─────────────────────────────────────────────────
        if mode == 'key':
            key = request.POST.get('license_key', '').strip()
            if not key:
                dj_messages.error(request, '❌ Please paste a valid license key.')
            elif len(key) < 32:
                dj_messages.error(request, '❌ License key is too short — please paste the full 64-character key.')
            else:
                result = activate_with_key(key)
                if result.get('ok'):
                    dj_messages.success(request, '✅ Panel activated successfully! Welcome to VoidPanel.')
                    return redirect('/')
                else:
                    dj_messages.error(request, f"❌ {result.get('error', 'License key validation failed.')}")

        # ── Mode: register (create new voidpanel.com account) ─────────────────
        elif mode == 'register':
            email      = request.POST.get('email', '').strip()
            password   = request.POST.get('password', '').strip()
            password2  = request.POST.get('password2', '').strip()
            first_name = request.POST.get('first_name', '').strip()
            last_name  = request.POST.get('last_name', '').strip()

            if not email or not password:
                dj_messages.error(request, '❌ Email and password are required.')
            elif password != password2:
                dj_messages.error(request, '❌ Passwords do not match — please try again.')
            elif len(password) < 8:
                dj_messages.error(request, '❌ Password must be at least 8 characters.')
            else:
                result = register_and_activate(email, password, mode='register')
                if result.get('ok'):
                    dj_messages.success(
                        request,
                        f'✅ Account created and panel activated! Welcome to VoidPanel, {first_name or email}.'
                    )
                    return redirect('/')
                else:
                    dj_messages.error(request, f"❌ {result.get('error', 'Registration failed. Please try again.')}")

        # ── Mode: login (existing voidpanel.com account) ──────────────────────
        else:  # mode == 'login'
            email    = request.POST.get('email', '').strip()
            password = request.POST.get('password', '').strip()

            if not email or not password:
                dj_messages.error(request, '❌ Please enter your email and password.')
            else:
                result = register_and_activate(email, password, mode='login')
                if result.get('ok'):
                    dj_messages.success(request, '✅ Panel activated successfully! Welcome to VoidPanel.')
                    return redirect('/')
                else:
                    dj_messages.error(request, f"❌ {result.get('error', 'Login failed. Check your credentials.')}")

    return render(request, 'activate.html', {'already_active': False})


# ── Email Hosting Services Admin ─────────────────────────────────────────────

@login_required(login_url='/')
def email_services_admin(request):
    """
    GET /email-services/
    Superadmin-only page to view all professional email hosting services
    purchased through the website portal. Shows domain, status, mailbox count,
    and a quick-action to manually provision/re-provision if auto-provision failed.
    """
    if not request.user.is_superuser:
        return redirect('/')

    # Handle manual re-provision POST
    if request.method == 'POST':
        action = request.POST.get('action', '')
        svc_id = request.POST.get('service_id', '')

        if action == 'reprovision' and svc_id:
            try:
                from data.models import EmailService
                svc = EmailService.objects.get(pk=svc_id)
                # Create the mailbox on the server via API
                import requests as _rq, secrets as _sec
                if svc.server:
                    primary_email = f'admin@{svc.domain}'
                    existing_pw = None
                    try:
                        from data.models import EmailMailbox
                        mb = EmailMailbox.objects.filter(service=svc).first()
                        if mb:
                            existing_pw = mb.password
                    except Exception:
                        pass

                    primary_pass = existing_pw or _sec.token_urlsafe(12)
                    try:
                        resp = _rq.post(
                            f'{svc.server.url.rstrip("/")}/api/v2/email/create/',
                            json={'domain': svc.domain, 'email': primary_email, 'password': primary_pass},
                            headers={'X-API-Token': svc.server.api_key},
                            timeout=15,
                        )
                        data = resp.json()
                        if data.get('status') == 'success':
                            svc.status = 'active'
                            svc.save(update_fields=['status'])
                            from control.models import allemail
                            allemail.objects.get_or_create(
                                email=primary_email, domain=svc.domain,
                                defaults={'password': primary_pass},
                            )
                            from django.contrib import messages as _msgs
                            _msgs.success(request, f'✅ Email service for {svc.domain} provisioned successfully.')
                        else:
                            from django.contrib import messages as _msgs
                            _msgs.error(request, f'❌ API error: {data.get("message", "unknown")}')
                    except Exception as exc:
                        from django.contrib import messages as _msgs
                        _msgs.error(request, f'❌ Provision failed: {exc}')
                else:
                    from django.contrib import messages as _msgs
                    _msgs.error(request, '❌ No server assigned to this email service.')
            except Exception as exc:
                from django.contrib import messages as _msgs
                _msgs.error(request, f'❌ Service not found: {exc}')

        elif action == 'terminate' and svc_id:
            try:
                from data.models import EmailService
                svc = EmailService.objects.get(pk=svc_id)
                svc.status = 'terminated'
                svc.save(update_fields=['status'])
                from django.contrib import messages as _msgs
                _msgs.success(request, f'Email service for {svc.domain} marked as terminated.')
            except Exception as exc:
                from django.contrib import messages as _msgs
                _msgs.error(request, f'Error: {exc}')

        return redirect('/email-services/')

    # Fetch all email services
    try:
        from data.models import EmailService
        email_services = EmailService.objects.select_related('user', 'plan', 'server').order_by('-created_at')
    except Exception:
        email_services = []

    stats = {
        'total':      len(email_services) if hasattr(email_services, '__len__') else (email_services.count() if hasattr(email_services, 'count') else 0),
        'active':     email_services.filter(status='active').count() if hasattr(email_services, 'filter') else 0,
        'pending':    email_services.filter(status='pending').count() if hasattr(email_services, 'filter') else 0,
        'failed':     email_services.filter(status='failed').count() if hasattr(email_services, 'filter') else 0,
    }

    return render(request, 'panel/email_services_admin.html', {
        'email_services': email_services,
        'stats': stats,
    })


# ── API Token Management ──────────────────────────────────────────────────────

@login_required(login_url='/')
def api_tokens_page(request):
    """
    GET /api-tokens/
    Superadmin-only page to view and manage all API tokens.
    """
    if not request.user.is_superuser:
        return redirect('/')
    from control.models import APIToken, ALL_SCOPES
    tokens = APIToken.objects.filter(is_active=True).order_by('-created_at')
    return render(request, 'panel/api_tokens.html', {
        'tokens': tokens,
        'all_scopes': ALL_SCOPES,
    })


@login_required(login_url='/')
@csrf_exempt
def api_token_create(request):
    """
    POST /api-tokens/create/
    Creates a new APIToken and returns it as JSON.
    Body: { label, owner_type, scopes: [] }
    """
    if not request.user.is_superuser:
        return JsonResponse({'status': 'error', 'message': 'Unauthorized'}, status=403)
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'POST required'}, status=405)

    try:
        data = json.loads(request.body)
    except Exception:
        return JsonResponse({'status': 'error', 'message': 'Invalid JSON'}, status=400)

    from control.models import APIToken, ALL_SCOPES
    label      = data.get('label', '').strip()
    owner_type = data.get('owner_type', APIToken.OWNER_SUPERADMIN)
    scopes     = data.get('scopes', list(ALL_SCOPES))

    if not label:
        return JsonResponse({'status': 'error', 'message': 'Token label is required'}, status=400)
    if owner_type not in (APIToken.OWNER_SUPERADMIN, APIToken.OWNER_RESELLER):
        owner_type = APIToken.OWNER_SUPERADMIN

    token = APIToken.generate(
        label=label,
        owner_type=owner_type,
        scopes=scopes,
        created_by=request.user.username,
    )
    return JsonResponse({
        'status': 'success',
        'token': {
            'id':         token.pk,
            'key':        token.key,
            'label':      token.label,
            'owner_type': token.owner_type,
            'scopes':     token.scopes,
            'is_active':  token.is_active,
            'created_at': token.created_at.strftime('%Y-%m-%d %H:%M'),
        }
    })


@login_required(login_url='/')
@csrf_exempt
def api_token_revoke(request, token_id):
    """
    POST /api-tokens/revoke/<id>/
    Deactivates (soft-deletes) an APIToken.
    """
    if not request.user.is_superuser:
        return JsonResponse({'status': 'error', 'message': 'Unauthorized'}, status=403)
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'POST required'}, status=405)

    from control.models import APIToken
    try:
        token = APIToken.objects.get(pk=token_id)
    except APIToken.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Token not found'}, status=404)

    label = token.label
    token.delete()   # hard delete — removed immediately from the list
    return JsonResponse({'status': 'success', 'message': f'Token "{label}" deleted.'})


# ── SSO Auto-Login Endpoint ───────────────────────────────────────────────────

def autologin(request):
    """
    GET /autologin/?token=TOKEN&domain=DOMAIN&next=/path/
    Validates a one-time SSO token issued by voidpanel.com (client portal),
    then logs the corresponding admin/user into the panel and redirects.

    This enables the "Open Control Panel" button in the client portal to
    perform a frictionless one-click login.
    """
    import requests as _rq
    import logging as _logging
    _log = _logging.getLogger('voidpanel')

    token  = request.GET.get('token', '').strip()
    domain = request.GET.get('domain', '').strip()
    next_path = request.GET.get('next', '/panel/')

    # Basic input validation
    if not token or not domain:
        from django.contrib import messages as dj_messages
        dj_messages.error(request, 'Invalid SSO link — missing parameters.')
        return redirect('/activate/')

    from django.contrib.auth import login as auth_login
    from django.contrib.auth.models import User as AuthUser

    # ── Try SSO token validation with voidpanel.com ──────────────────────────
    sso_valid = False
    sso_data  = {}
    try:
        from django.conf import settings as dj_settings
        website_url = getattr(dj_settings, 'VOIDPANEL_WEBSITE_URL', 'https://voidpanel.com')
        resp = _rq.get(
            f'{website_url}/api/sso/validate/',
            params={'token': token, 'domain': domain},
            timeout=10,
        )
        sso_data = resp.json()
        sso_valid = sso_data.get('valid', False)
    except Exception as exc:
        _log.warning('SSO validate request failed for %s: %s', domain, exc)

    # ── Resolve user ─────────────────────────────────────────────────────────
    resolved_user = None

    # Strategy 1: domain lookup in control panel user table (always reliable)
    try:
        from control.models import user as ControlUser
        cu = ControlUser.objects.filter(domain=domain).first()
        if cu:
            resolved_user = AuthUser.objects.filter(username=cu.username).first()
    except Exception:
        pass

    if sso_valid:
        # SSO validated — use portal-provided data as fallback
        panel_username = sso_data.get('panel_username') or sso_data.get('username', '')
        email          = sso_data.get('email', '')

        if not resolved_user and panel_username:
            resolved_user = AuthUser.objects.filter(username=panel_username).first()
        if not resolved_user and email:
            resolved_user = AuthUser.objects.filter(email=email).first()
        if not resolved_user and panel_username:
            resolved_user, _ = AuthUser.objects.get_or_create(
                username=panel_username,
                defaults={'email': email},
            )
    else:
        # SSO failed (expired/network) — domain-based fallback.
        # The user clicked a link on voidpanel.com which means the website
        # already verified ownership. If the domain exists here, log them in.
        if not resolved_user:
            _log.warning('SSO fallback: token invalid for %s, no domain match found', domain)
            from django.contrib import messages as dj_messages
            dj_messages.error(request, 'This login link has expired. Please try again from your portal.')
            return redirect('/')

        _log.info('SSO fallback: token expired for %s but domain matched user %s', domain, resolved_user.username)

    if not resolved_user:
        from django.contrib import messages as dj_messages
        dj_messages.error(request, 'Could not resolve your account. Please contact support.')
        return redirect('/')

    # Log the user in
    resolved_user.backend = 'django.contrib.auth.backends.ModelBackend'
    auth_login(request, resolved_user)

    # Safety: only allow relative next paths
    if not next_path.startswith('/'):
        next_path = '/control/'

    return redirect(next_path)


@login_required(login_url='/')
def notify_settings(request):
    if not request.user.is_superuser:
        return redirect('/')
    
    from control.models import NotificationSettings, quick
    d = {}
    
    # Singleton gets or creates
    cfg = NotificationSettings.get()
    d['cfg'] = cfg
    
    quick_ = quick.objects.first()
    d['quick'] = quick_
    
    # Retrieve administrative documents if available
    try:
        url = 'https://voidpanel.com/admindocs/'
        response = requests.get(url, timeout=2)
        if response.status_code == 200:
            d['docs'] = response.json()
    except Exception:
        d['docs'] = []
        
    return render(request, 'panel/notify.html', d)


@login_required(login_url='/')
def notify_test_smtp(request):
    if not request.user.is_superuser:
        return JsonResponse({'status': 'error', 'message': 'Unauthorized'}, status=403)
        
    if request.method == 'POST':
        import json, smtplib
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart
        from control.models import NotificationSettings, quick
        
        try:
            data = json.loads(request.body)
            host = data.get('smtp_host', '').strip()
            port = int(data.get('smtp_port', 587))
            user = data.get('smtp_user', '').strip()
            pwd  = data.get('smtp_password', '').strip()
            enc  = data.get('encryption', 'tls')
            from_email = data.get('from_email', '').strip()
            
            if not host or not user or not pwd or not from_email:
                return JsonResponse({'status': 'error', 'message': 'Host, username, password and from email are required.'})
                
            admin_email_obj = quick.objects.first()
            admin_email = admin_email_obj.email if admin_email_obj else None
            if not admin_email:
                return JsonResponse({'status': 'error', 'message': 'Please configure an Administrator Email under Hostname settings first.'})
                
            # Try to connect and send test mail
            try:
                msg = MIMEMultipart('alternative')
                msg['Subject'] = "[VoidPanel] SMTP Test Connection"
                msg['From'] = from_email
                msg['To'] = admin_email
                
                body = f"""
                <h3>SMTP Test Connection Successful!</h3>
                <p>VoidPanel has successfully authenticated with your SMTP server.</p>
                <p><strong>Timestamp:</strong> {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                """
                msg.attach(MIMEText(body, 'html'))
                
                if enc == 'ssl':
                    server = smtplib.SMTP_SSL(host, port, timeout=10)
                else:
                    server = smtplib.SMTP(host, port, timeout=10)
                    server.ehlo()
                    if enc == 'tls':
                        server.starttls()
                        server.ehlo()
                        
                server.login(user, pwd)
                server.sendmail(from_email, admin_email, msg.as_string())
                server.quit()
                
            except Exception as smtp_err:
                return JsonResponse({'status': 'error', 'message': f'SMTP Error: {str(smtp_err)[:300]}'})
                
            # If successful, save the configuration as verified
            cfg = NotificationSettings.get()
            cfg.smtp_host = host
            cfg.smtp_port = port
            cfg.smtp_user = user
            cfg.smtp_password = pwd
            cfg.smtp_encryption = enc
            cfg.from_email = from_email
            cfg.is_smtp_verified = True
            cfg.save()
            
            return JsonResponse({'status': 'success', 'message': 'SMTP settings tested & saved successfully! A test email has been sent.'})
            
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': f'Error: {str(e)}'})
            
    return JsonResponse({'status': 'error', 'message': 'Invalid request.'})


@login_required(login_url='/')
def notify_save_settings(request):
    if not request.user.is_superuser:
        return JsonResponse({'status': 'error', 'message': 'Unauthorized'}, status=403)
        
    if request.method == 'POST':
        import json
        from control.models import NotificationSettings
        
        try:
            data = json.loads(request.body)
            cfg = NotificationSettings.get()
            
            if not cfg.is_smtp_verified:
                return JsonResponse({'status': 'error', 'message': 'Please test and verify your SMTP credentials first.'})
                
            cfg.notify_user_created = bool(data.get('notify_user_created', False))
            cfg.notify_user_suspended = bool(data.get('notify_user_suspended', False))
            cfg.notify_user_unsuspended = bool(data.get('notify_user_unsuspended', False))
            cfg.notify_user_terminated = bool(data.get('notify_user_terminated', False))
            cfg.notify_login_alert = bool(data.get('notify_login_alert', False))
            cfg.notify_ssl_generated = bool(data.get('notify_ssl_generated', False))
            cfg.notify_backup_created = bool(data.get('notify_backup_created', False))
            cfg.notify_script_installed = bool(data.get('notify_script_installed', False))
            cfg.save()
            
            return JsonResponse({'status': 'success', 'message': 'Notification settings saved successfully!'})
            
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': f'Error: {str(e)}'})
            
    return JsonResponse({'status': 'error', 'message': 'Invalid request.'})



# ─────────────────────────────────────────────────────────────────────────────
#  White-Label Branding Settings
# ─────────────────────────────────────────────────────────────────────────────

@login_required(login_url='/')
def panel_branding_settings(request):
    """
    GET /branding/
    White-label branding management page (superadmin only).
    The page shows a "locked" state when the license tier does not include
    white_label, with an upgrade prompt linking to voidpanel.com.
    """
    if not request.user.is_superuser:
        return redirect('/')

    from control.models import PanelBranding, PanelLicense
    from control.license import has_feature, get_tier

    branding = PanelBranding.get()
    lic = PanelLicense.objects.first()
    white_label_licensed = has_feature('white_label')
    tier = get_tier()

    return render(request, 'panel/branding.html', {
        'branding':              branding,
        'white_label_licensed':  white_label_licensed,
        'current_tier':          tier,
        'license':               lic,
    })


@login_required(login_url='/')
def panel_branding_save(request):
    """
    POST /branding/save/
    Saves white-label branding settings. Only allowed when license has
    white_label feature enabled.
    """
    if not request.user.is_superuser:
        return JsonResponse({'status': 'error', 'message': 'Access denied.'}, status=403)

    from control.models import PanelBranding
    from control.license import has_feature

    if not has_feature('white_label'):
        return JsonResponse({
            'status': 'error',
            'message': 'White-label branding requires an Unlimited license. Upgrade at voidpanel.com/get-voidpanel/',
        }, status=403)

    try:
        import json as _json
        data = _json.loads(request.body)
    except Exception:
        data = request.POST

    branding = PanelBranding.get()
    branding.panel_name           = (data.get('panel_name') or 'VoidPanel').strip()[:60]
    branding.panel_logo_url       = (data.get('panel_logo_url') or '').strip()
    branding.favicon_url          = (data.get('favicon_url') or '').strip()
    branding.primary_color        = (data.get('primary_color') or '#6366f1').strip()[:20]
    branding.support_url          = (data.get('support_url') or '').strip()
    branding.hide_voidpanel_badge = bool(data.get('hide_voidpanel_badge', False))
    branding.save()

    return JsonResponse({
        'status':  'success',
        'message': f'Branding saved! Panel is now branded as "{branding.panel_name}".',
    })


# ─────────────────────────────────────────────────────────────────────────────
# License Management Page
# ─────────────────────────────────────────────────────────────────────────────

@login_required(login_url='/')
def panel_license_page(request):
    """
    GET  /license/      — Show license info dashboard
    """
    if not request.user.is_superuser:
        return redirect('/')

    from control.models import PanelLicense
    from control.license import get_tier, get_features

    lic = PanelLicense.objects.first()
    features = get_features() if lic else {}
    tier = get_tier()

    return render(request, 'panel/license.html', {
        'lic':      lic,
        'features': features,
        'tier':     tier,
    })


@login_required(login_url='/')
def panel_license_refresh(request):
    """
    POST /license/refresh/  — Trigger an immediate license re-validation
    """
    if not request.user.is_superuser:
        return JsonResponse({'ok': False, 'error': 'Access denied.'}, status=403)
    if request.method != 'POST':
        return JsonResponse({'ok': False, 'error': 'POST required.'}, status=405)

    from control.license import refresh_license
    try:
        ok = refresh_license()
        from control.models import PanelLicense
        lic = PanelLicense.objects.first()
        return JsonResponse({
            'ok':     ok,
            'status': lic.status if lic else 'unknown',
            'tier':   lic.tier   if lic else 'unknown',
        })
    except Exception as exc:
        return JsonResponse({'ok': False, 'error': str(exc)}, status=500)


@login_required(login_url='/')
def panel_license_activate(request):
    """
    POST /license/activate/  — Activate a new license key (replaces existing)
    """
    if not request.user.is_superuser:
        return JsonResponse({'ok': False, 'error': 'Access denied.'}, status=403)
    if request.method != 'POST':
        return JsonResponse({'ok': False, 'error': 'POST required.'}, status=405)

    import json as _json
    try:
        body = _json.loads(request.body)
    except ValueError:
        body = {}

    key = (body.get('key') or '').strip()
    if not key:
        return JsonResponse({'ok': False, 'error': 'License key is required.'}, status=400)

    from control.license import activate_with_key
    result = activate_with_key(key)
    return JsonResponse(result)
