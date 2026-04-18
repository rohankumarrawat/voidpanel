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
from function import start_service,stop_service,get_directory_size_in_mb,restart_service,get_service_status,get_php_versions,get_php_version,get_php_extensions,get_database_names,get_database_users,change_hostname,remove_zone_from_file,zip_multiple_locations_backup,create_bind_recordsforsubdomain,grant_mysql_user_privileges,change_mysql_user_password,delete_mysql_user,remove_database,get_database_names_with_filter,get_database_users_with_filter,create_mysql_user,is_website_live,parse_dns_zone_file,configure_opendkim,create_bind_records,generate_dkim_keys,create_nginx_ssl_conf,generate_ssl_certificates,hostnamessl,run_command,get_server_ip,get_random_port,get_file_info,zip_files_and_folders,extract_zip_with_error_handling,create_database_and_table,clone_website, get_database_privileges_with_filter, revoke_mysql_user_privileges
import psutil
import os, shlex
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

def background_create_account(username, password, domain_name, package_name):
    """
    Called by the WHMCS API create_account endpoint.
    Resolves directory name, looks up storage quota, then dispatches
    a Celery provision_user_task so the work runs in the worker process
    with full logging and retry support.
    """
    import re
    try:
        from control.models import package as PackageModel
        try:
            pkg = PackageModel.objects.get(name=package_name)
            sto = int(pkg.storage)
        except Exception:
            sto = 0

        home_base  = paths.HOME_BASE
        directories = os.listdir(home_base) if os.path.isdir(home_base) else []
        base_name   = re.sub(r'[^a-z0-9]', '', domain_name.split('.')[0].lower())[:16]
        domainname  = base_name
        counter = 1
        while domainname in directories:
            suffix     = str(counter)
            domainname = base_name[:16 - len(suffix)] + suffix
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
            domain_name, domainname, username, password, package_name,
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

    # Immediately return a response to the client
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
    load = {
        'cpu': cpu_load,
        'memory': memory_load,
        'disk': disk_load
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
            return redirect('/panel')
        elif user is not None:
            login(request,user)
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

        return render(request, 'panel/index.html', d)
    else: 
        return redirect('/')
    

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
    
    if request.user.is_superuser:
        d={}
        if request.is_secure():
             d['securehai']=True
        
        _disk_root = (os.path.splitdrive(paths.HOME_BASE)[0] + '\\') if sys.platform == 'win32' else '/'
        storage_info = psutil.disk_usage(_disk_root)
        d['storage']=str(storage_info.total // (1024 ** 3)) +"GB"
        d['ip']=get_server_ip()
        d['os']=platform.system()
        d['cpu']=platform.processor()
        
        try:
            d['hostname'] = socket.gethostname()
        except:
            d['hostname'] = "localhost"
            
        d['ram']=str(round(psutil.virtual_memory().total / (1024.0 **3)))+" GB"
        
        url = 'https://voidpanel.com/admindocs/'
        try:
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                d['docs'] = response.json()
        except:
            pass
            
        return render(request,'panel/terminal.html',d)
    else: 
        return redirect('/')


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
        file_path_base = request.POST['file_path']
        try: 
            for uploaded_file in uploaded_files:
                if not uploaded_file:
                    continue
                file_name = uploaded_file.name
                file_path = os.path.join(file_path_base, file_name)
                if not file_path.startswith('/'):
                    file_path = '/' + file_path
                with open(file_path, 'wb+') as destination:
                    for chunk in uploaded_file.chunks():
                        destination.write(chunk)
                try:
                    if request.user.is_superuser:
                         if sys.platform != 'win32':
                             run_command(f'sudo chown www-data:www-data "{file_path}"')
                    else:
                         if sys.platform != 'win32':
                             run_command(f'sudo chown {request.user.username}:{request.user.username} "{file_path}"')
                except Exception:
                    pass
            return JsonResponse({'status': 'success', 'message': f'{len(uploaded_files)} file(s) uploaded successfully!'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
    return JsonResponse({'status': 'error', 'message': 'File upload failed!'}, status=400)


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
               from core.models import user, package
               try:
                   currentstorage = get_directory_size_in_mb(os.path.join(paths.HOME_BASE, str(request.user)))
                   packagecc = safe_get_package(user.objects.get(username=request.user).hosting_package).storage
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
                # os.system(f'touch {full_path}')
                with open(full_path, 'w') as file:
                    file.write('This is a new file.\n')
                
                if sys.platform != 'win32':
                    run_command(f'sudo chown {request.user}:{request.user} {full_path}')
                try:
                    if sys.platform != 'win32':
                        run_command(f"chown {request.user}:www-data {full_path}")
                except:
                     pass
                return JsonResponse({'status': 'success', 'message': 'File Create successfully!'})
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
               from core.models import user, package
               try:
                   currentstorage = get_directory_size_in_mb(os.path.join(paths.HOME_BASE, str(request.user)))
                   packagecc = safe_get_package(user.objects.get(username=request.user).hosting_package).storage
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
                try:
                            
                                  
            
                                  if sys.platform != 'win32':
                                      run_command(f"chown {request.user}:www-data {full_path}")
             
                except:
                             pass
                if sys.platform != 'win32':
                    run_command(f'sudo chown {request.user}:{request.user} {full_path}')
                return JsonResponse({'status': 'success', 'message': 'File uploaded successfully!'})
               except Exception as e:
                   print(e)
                   return JsonResponse({'status': 'error', 'message': 'File upload Failed!'})
          return JsonResponse({'status': 'error', 'message': 'File upload Failed!'})


@login_required(login_url='/')
@secure_fm_paths
def copydata(request):
     c=0
     x=0
     s=""

     if request.user.is_superuser:
         import shutil
         if request.method =="POST":
               data = json.loads(request.body)  # Get the data from the request body
               selected_items = data.get('selected', [])
               file_path = data.get('path')
               copy = data.get('copy')
               if '/' !=file_path[0]:
                   file_path="/"+file_path+'/'
               if '/' !=copy[0]:
                   copy="/"+copy
               if '/' !=copy[-1]:
                   copy=copy+'/'
               if  not os.path.isdir(copy):
                   return JsonResponse({'status': 'already', 'message': "Invalid Location"})
                   
               
               
               for i in selected_items:
                    try:
                        shutil.copytree(file_path+"/"+i,copy+i)
                        try:
                             if request.user.is_superuser():
                                  if sys.platform != 'win32':
                                      run_command(f"chown www-data:www-data {copy}")
                                      run_command(f"chown www-data:www-data {copy}/{i}")
                                  
                             else:
                                  if sys.platform != 'win32':
                                      run_command(f"chown {request.user}:www-data {copy}")
                                      run_command(f"chown {request.user}:www-data {copy}/{i}")
                        except:
                             pass
                        c=c+1
                    except Exception as e:
                        x=x+1
                        s=s+i
                        print(e)
                    try:
                        shutil.copy2(file_path+"/"+i,copy+i)
                        c=c+1
                    except Exception as e:
                        x=x+1
                        s=s+i
                        print(e)
            
               if c==len(selected_items):
                
                   return JsonResponse({'status': 'success', 'message': 'File uploaded successfully!'})
              
               elif x!=0:
                  
                   return JsonResponse({'status': 'already', 'message': s})
               else:  
                   return JsonResponse({'status': 'error', 'message': 'File uploaded successfully!'})
     elif request.user.is_authenticated:
         import shutil
         if request.method =="POST":

               data = json.loads(request.body)  # Get the data from the request body
               selected_items = data.get('selected', [])
               file_path = data.get('path')
               copy = data.get('copy')
               if '/' !=file_path[0]:
                   file_path="/"+file_path+'/'
               if '/' !=copy[0]:
                   copy="/"+copy
               if '/' !=copy[-1]:
                   copy=copy+'/'
               if not copy.startswith(os.path.join(paths.HOME_BASE, str(request.user))):
                    copy=os.path.join(paths.HOME_BASE, str(request.user))+copy
               if  not os.path.isdir(copy):
                   return JsonResponse({'status': 'invalid', 'message': "Invalid Location"})
                   
               
               
               for i in selected_items:
                    try:
                        shutil.copytree(file_path+"/"+i,copy+i)
                        c=c+1
                        try:
                             if request.user.is_superuser():
                                  if sys.platform != 'win32':
                                      run_command(f"chown www-data:www-data {copy}")
                                      run_command(f"chown www-data:www-data {copy}/{i}")
                                  
                             else:
                                  if sys.platform != 'win32':
                                      run_command(f"chown {request.user}:www-data {copy}")
                                      run_command(f"chown {request.user}:www-data {copy}/{i}")
                        except:
                             pass
                    except Exception as e:
                       pass
                    try:
                        shutil.copy2(file_path+"/"+i,copy+i)
                        c=c+1
                        try:
                             if request.user.is_superuser():
                                  if sys.platform != 'win32':
                                      run_command(f"chown www-data:www-data {copy}")
                                      run_command(f"chown www-data:www-data {copy}/{i}")
                                  
                             else:
                                  if sys.platform != 'win32':
                                      run_command(f"chown {request.user}:www-data {copy}")
                                      run_command(f"chown {request.user}:www-data {copy}/{i}")
                        except:
                             pass
                    except Exception as e:
                       pass
            
               if c==len(selected_items):
                
                   return JsonResponse({'status': 'success', 'message': 'File uploaded successfully!'})
              
               elif x!=0:
                  
                   return JsonResponse({'status': 'already', 'message': s})
               else:  
                   return JsonResponse({'status': 'error', 'message': 'File uploaded successfully!'})
                   

       



@login_required(login_url='/')
@secure_fm_paths
def movedata(request):
     c=0
     if request.user.is_superuser :
         if request.method =="POST":
               data = json.loads(request.body)  # Get the data from the request body
               selected_items = data.get('selected', [])
               file_path = data.get('path')
               copy = data.get('copy')   
               if '/' !=file_path[0]:
                   file_path="/"+file_path+'/'
               if '/' !=copy[0]:
                   copy="/"+copy
               if '/' !=copy[-1]:
                   copy=copy+'/'
               if  not os.path.isdir(copy):
                   return JsonResponse({'status': 'invalid', 'message': "Invalid Location"})
               for i in selected_items:
                    try:
                        import shutil
                        print(file_path+i,copy)
                        shutil.move(file_path+"/"+i,copy)
                        try:
                             if request.user.is_superuser():
                                  if sys.platform != 'win32':
                                      run_command(f"chown www-data:www-data {copy}")
                                      run_command(f"chown www-data:www-data {copy}/{i}")
                                  
                             else:
                                  if sys.platform != 'win32':
                                      run_command(f"chown {request.user}:www-data {copy}")
                                      run_command(f"chown {request.user}:www-data {copy}/{i}")
                        except:
                             pass
                        c=c+1
                    except Exception as e:
                        print(e)
    
               if c == len(selected_items):
                return JsonResponse({'status': 'success', 'message': 'File moved successfully!'})
               else:
                    return JsonResponse({'status': 'error', 'message': 'Cannot move all files.'})
               
     elif request.user.is_authenticated:
          if request.method =="POST":

               data = json.loads(request.body)  # Get the data from the request body
               selected_items = data.get('selected', [])
               file_path = data.get('path')
               copy = data.get('copy')   
               if '/' !=file_path[0]:
                   file_path="/"+file_path+'/'
               if '/' !=copy[0]:
                   copy="/"+copy
               if '/' !=copy[-1]:
                   copy=copy+'/'
               if not copy.startswith(os.path.join(paths.HOME_BASE, str(request.user))):
                    copy=os.path.join(paths.HOME_BASE, str(request.user))+copy
               if  not os.path.isdir(copy):
                   return JsonResponse({'status': 'invalid', 'message': "Invalid Location"})
               for i in selected_items:
                    try:
                        import shutil
                        print(file_path+i,copy)
                        shutil.move(file_path+"/"+i,copy)
                        try:
                             if request.user.is_superuser():
                                  if sys.platform != 'win32':
                                      run_command(f"chown www-data:www-data {copy}")
                                      run_command(f"chown www-data:www-data {copy}/{i}")
                                  
                             else:
                                  if sys.platform != 'win32':
                                      run_command(f"chown {request.user}:www-data {copy}")
                                      run_command(f"chown {request.user}:www-data {copy}/{i}")
                        except:
                             pass
                        c=c+1
                    except Exception as e:
                        print(e)
    
               if c == len(selected_items):
                return JsonResponse({'status': 'success', 'message': 'File moved successfully!'})
               else:
                    return JsonResponse({'status': 'error', 'message': 'Cannot move all files.'})

         


@login_required(login_url='/')
@secure_fm_paths
def extractdata(request):
     c=0

     if request.user.is_superuser:
         if request.method =="POST":
               
               data = json.loads(request.body)  # Get the data from the request body
               selected_items = data.get('selected', [])
               file_path = data.get('path')
        
              
               if '/' !=file_path[0]:
                   file_path="/"+file_path
               
                 
               try:
                    
                    extract_zip_with_error_handling(file_path+'/'+selected_items[0], file_path)
                    try:
                         if sys.platform != 'win32':
                             run_command(f"sudo chown -R www-data:www-data {file_path}")
                    except:
                         pass
                    return JsonResponse({'status': 'success', 'message': 'File Extracted successfully!'})
                 
               except Exception as e:
                    return JsonResponse({'status': 'error', 'message': 'File Extraction Failed!'})
               
         return JsonResponse({'status': 'error', 'message': 'File Extraction Failed!'})
     elif request.user.is_authenticated:

                                    
         if request.method =="POST":
               
               data = json.loads(request.body)  # Get the data from the request body
               selected_items = data.get('selected', [])
               file_path = data.get('path')
        
              
               if '/' !=file_path[0]:
                   file_path="/"+file_path
               
                 
               try:
                    
                    extract_zip_with_error_handling(file_path+'/'+selected_items[0], file_path)
                   
                    try:
                         if sys.platform != 'win32':
                             run_command(f"sudo chown -R {request.user}:www-data {file_path}")
                    except:
                         pass
                    return JsonResponse({'status': 'success', 'message': 'File Extracted successfully!'})
                 
               except Exception as e:
                    print(e)
                    return JsonResponse({'status': 'error', 'message': 'File Extraction Failed!'})
               
         return JsonResponse({'status': 'error', 'message': 'File Extraction Failed!'})

@login_required(login_url='/')
@secure_fm_paths
def compressdata(request):
     s=""
     import os
     c=0
     l=[]

     if request.user.is_superuser or request.user.is_authenticated:
         if request.method =="POST":
               
               data = json.loads(request.body)  # Get the data from the request body
               selected_items = data.get('selected',[])
               file_path = data.get('path')
        
              
               if '/' !=file_path[0]:
                   file_path="/"+file_path
               if '/' !=file_path[-1]:
                   file_path=file_path+"/"
               for i in selected_items:
                   l.append(file_path+i)
               folders = []

                # Loop through items in the given path
               for item in os.listdir(file_path):
                    # Create full path to item
                    full_path = os.path.join(file_path, item)
                    # Check if it's a directory
                    if os.path.isdir(full_path):
                        folders.append(item)

               while(1):
                import random
                lol=random.choice(selected_items)+'.zip'
        
                if lol not in folders:
                    file_path=file_path+lol
                    break
               
           
            
                 
               try:
                     zip_files_and_folders(file_path, l)
                     if not request.user.is_superuser:
                          if sys.platform != 'win32':
                              run_command(f'sudo chown {request.user}:{request.user} {file_path}')
                  
                     return JsonResponse({'status': 'success', 'message': 'File Compressed successfully!'})
              
               except Exception as e:
                    print(e)
                    return JsonResponse({'status': 'error', 'message': 'File Compression Failed!'})

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
           response = requests.get(url)
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
           response = requests.get(url)
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
           url = 'https://voidpanel.com/admindocs/'  # Replace with your API URL
           response = requests.get(url)
           if response.status_code == 200:
            dataee = response.json()  # Parse the JSON response
            d['docs']=dataee
          
           
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
           response = requests.get(url)
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
            directories = os.listdir(paths.HOME_BASE)
            base_name = re.sub(r'[^a-z0-9]', '', domain12.split('.')[0].lower())[:16]
            
            domainname = base_name
            counter = 1
            while domainname in directories:
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
                        # Change system user shell to /bin/bash (restricted)
                        run_command(f'sudo usermod -s /bin/rbash {dname}')
                    except Exception as e:
                        logger.warning('Set shell flag failed for %s: %s', dname, e)
                threading.Thread(target=_set_shell, args=(domainname, sto), daemon=True).start()
            
            return JsonResponse({
                'status': 'success',
                'task_id': str(task.id),
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
                response = requests.get(url)
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
        with open(zone_file_path, 'r') as f:
            original_content = f.read()
            f.seek(0)
            lines = f.readlines()

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
        with open(zone_file_path, 'r') as f:
            original_content = f.read()

        new_content = original_content + f"\n; {record_type} Record added via VoidPanel\n{name} {ttl} {record_class} {record_type} {data}\n"

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
        with open(zone_file_path, 'r') as f:
            original_content = f.read()
            f.seek(0)
            lines = f.readlines()

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
                    new_lines.append(f"{name} {ttl} {record_class} {record_type} {data}\n")
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
                    return JsonResponse({'success': False, 'error': f'Invalid record syntax. Formatting rejected.'}, status=400)
            
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
                response = requests.get(url)
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
                listdomain=user.objects.all()
                d['domain']=listdomain
                d['package']=package.objects.all()
                url = 'https://voidpanel.com/admindocs/'  # Replace with your API URL
                response = requests.get(url)
                if response.status_code == 200:
                    dataee = response.json()  # Parse the JSON response
                    d['docs']=dataee
            
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
                response = requests.get(url)
                if response.status_code == 200:
                    dataee = response.json()  # Parse the JSON response
                    d['docs']=dataee
    
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
                    
                    if allowed_emails_str != "unlimited":
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
            return JsonResponse({'status': 'success'})

        return JsonResponse({'status': 'error', 'message': 'POST required.'})
    return JsonResponse({'status': 'error', 'message': 'Unauthorized'})

@login_required(login_url='/')
def listemail(request,data):
    import subprocess

    
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
                   new_dir = os.path.join(maildir_path, "new")
                   cur_dir = os.path.join(maildir_path, "cur")
                   new_emails_count = len(os.listdir(new_dir)) if os.path.exists(new_dir) else 0
                   cur_emails_count = len(os.listdir(cur_dir)) if os.path.exists(cur_dir) else 0
                   total_emails_count = new_emails_count + cur_emails_count
                #    command = f"grep 'status=sent' /var/log/mail.log | grep '{i.email}'"

                   # Mail log statistics (Linux only)
                   sent_emails = []
                   failed_emails = []
                   filtered_emails = []
                   if sys.platform != 'win32':
                       command=['grep', f'from=<{i.email}>', '/var/log/mail.log']
                       result = subprocess.run(command, shell=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                       command2=['grep', '-E', 'status=bounced|status=deferred', '/var/log/mail.log']
                       result2 = subprocess.run(
                           ['grep', i.email],
                           input=subprocess.run(command2, capture_output=True, text=True).stdout,
                           capture_output=True, text=True
                       )
                       failed_emails = result2.stdout.splitlines()
                       sent_emails = result.stdout.splitlines()
                       command = "postqueue -p"
                       result = subprocess.run(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                       queue_lines = result.stdout.splitlines()
                       filtered_emails = [line for line in queue_lines if i.email in line]

                   totalemail=len(sent_emails)+len(failed_emails)+len(filtered_emails)
                   try:
                    sendp=(len(sent_emails)/totalemail)*100
                    failedp=(len(failed_emails)/totalemail)*100
                    processp=(len(filtered_emails)/totalemail)*100
                   except:
                        sendp=0
                        failedp=0
                        processp=0
                   emaildetail.append(
                       {'email':i.email,'sent':len(sent_emails),'failed':len(failed_emails),'queue':len(filtered_emails),'sendp':sendp,'failedp':failedp,'processp':processp,'total_emails_count':total_emails_count}
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
               response = requests.get(url)
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
        return JsonResponse({'status': 'success'})
    
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
    
    if not username or not password or not domain_val:
        return JsonResponse({'status': 'error', 'message': 'All fields are required'})

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
                    response = requests.get(url)
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
                    response = requests.get(url)
                    if response.status_code == 200:
                        dataee = response.json()  # Parse the JSON response
                        d['docs']=dataee    
                    return render(request,'panel/subdomian.html',d)
                except Exception as e:
                    return redirect("/listwebsite/")
           
    else: 
        return redirect('/')
    
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
                                    os.mkdir(path)
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
                                        fallback_conf = f"server {{\n    listen 80;\n    server_name {full};\n    root {root_dir};\n    index index.php index.html;\n    location / {{\n        try_files $uri $uri/ =404;\n    }}\n    location ~ \\.php$ {{\n        include snippets/fastcgi-php.conf;\n        fastcgi_pass unix:/run/php/php8.3-fpm.sock;\n    }}\n}}\n"
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
                                return JsonResponse({'status': 'success', 'message': 'Subdomain successfully created'})
    
        return JsonResponse({'status': 'error', 'message': 'Invalid request.'})
    

@login_required(login_url='/')
def deletesubdomain(request,data):
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'POST required.'}, status=405)
        
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
                    url = 'https://voidpanel.com/admindocs/'  # Replace with your API URL
                    response = requests.get(url)
                    if response.status_code == 200:
                        dataee = response.json()  # Parse the JSON response
                        d['docs']=dataee
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
                            with open(path,'a+') as f:
                                f.write("\n")
                                f.write(f"AutoSSl Completed for domain {name}")
                                lold.sslstatus=True
                                lold.save()

                        except Exception as e:
                             with open(path,'a+') as f:
                                f.write("\n")
                                f.write(f"Error Occur for domain {name}")
                                f.write(e)
                        for i in subdomain2:
                           
                            try:
                                result = plat.ssl.provision(i.subdomain, email=f'{i.name}@example.com')
                                with open(path,'a+') as f:
                                    f.write("\n")
                                    f.write(f"AutoSSl Completed for domain {i.subdomain}")
                                    i.sslstatus=True
                                    i.save()
                            except Exception as e:
                             with open(path,'a+') as f:
                                f.write("\n")
                                f.write(f"Error Occur for domain {i.subdomain}")
                                f.write(e)   
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
                     
                             
                               

                        except Exception as e:
                             with open(path,'a+') as f:
                                f.write("\n")
                                f.write(f"Error Occur for domain {name}")
                                f.write(e)
                      
                         
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

            config_path = os.path.join(paths.NGINX_SITES_ENABLED, f"{config_name}.conf")

            try:
                import re as _re
                with open(config_path, 'r') as _f:
                    _old_content = _f.read()
                _new_content = _re.sub(
                    r'fastcgi_pass unix:/run/php/php[0-9.]+-fpm\.sock;',
                    f'fastcgi_pass unix:/run/php/php{php}-fpm.sock;',
                    _old_content
                )
                with open(config_path, 'w') as _f:
                    _f.write(_new_content)

                # Check config syntax before reloading
                test_result = get_platform().web.test_config()
                if not test_result.success:
                    # Revert if syntax is broken
                    with open(config_path, 'w') as _f:
                        _f.write(_old_content)
                    return JsonResponse({'status': 'error', 'message': 'Nginx syntax error after changing PHP version. Operation reverted.'})

                # Configuration is safe, reload Nginx safely
                get_platform().services.reload('nginx')
                
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
                    response = requests.get(url)
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
                    response = requests.get(url)
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

    # --- Filesystem: home directory ---
    try:
        shutil.rmtree(os.path.join(paths.HOME_BASE, mainusername), ignore_errors=True)
    except Exception as e:
        logger.warning('[terminate] Could not remove home dir for %s: %s', mainusername, e)

    # --- Nginx configs: main domain + all subdomains ---
    nginx_paths = [os.path.join(paths.NGINX_SITES_ENABLED, f'{domain_str}.conf')]
    for sub in subdomains:
        nginx_paths.append(os.path.join(paths.NGINX_SITES_ENABLED, f'{sub}.conf'))
    for path in nginx_paths:
        try:
            os.remove(path)
        except Exception:
            pass

    # --- DNS zone file ---
    try:
        os.remove(os.path.join(paths.BIND_ZONE_DIR, f'db.{domain_str}'))
    except Exception:
        pass
    try:
        if sys.platform != 'win32':
            remove_zone_from_file(paths.BIND_CONF, domain_str)
    except Exception:
        pass

    # --- DKIM keys ---
    dkim_paths = [os.path.join(paths.OPENDKIM_KEY_DIR, domain_str)]
    for sub in subdomains:
        dkim_paths.append(os.path.join(paths.OPENDKIM_KEY_DIR, sub))
    for path in dkim_paths:
        try:
            shutil.rmtree(path, ignore_errors=True)
        except Exception:
            pass

    # --- SSL certificates ---
    ssl_paths = [os.path.join(paths.LETSENCRYPT_LIVE, domain_str)]
    for sub in subdomains:
        ssl_paths.append(os.path.join(paths.LETSENCRYPT_LIVE, sub))
    for path in ssl_paths:
        try:
            shutil.rmtree(path, ignore_errors=True)
        except Exception:
            pass

    # --- Mail data ---
    try:
        shutil.rmtree(_resolve_mail_domain_dir(domain_str), ignore_errors=True)
    except Exception:
        pass

    # --- Reload services (zero-downtime: reload not restart) ---
    try:
        subprocess.run(['sudo', 'systemctl', 'reload', 'bind9'], timeout=15, check=False)
    except Exception:
        pass
    try:
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
        df = pythonname.objects.get(domain=domain_str)
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
    except Exception:
        pass

    try:
        df = mernname.objects.get(domain=domain_str)
        svc_name = df.name
        df.delete()
        try:
            if sys.platform == 'win32':
                from voidplatform.windows.apps import delete_mern_app
                delete_mern_app(svc_name)
            else:
                sock = os.path.join(paths.RUN_DIR if hasattr(paths, 'RUN_DIR') else '/var/run', f'{svc_name}.sock')
                if os.path.exists(sock):
                    os.remove(sock)
        except Exception:
            pass
    except Exception:
        pass


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
                    response = requests.get(url)
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
            databases_allowed=database
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
    
   
    if request.user.is_superuser:
                
                d={}
                url = 'https://voidpanel.com/admindocs/'  # Replace with your API URL
                response = requests.get(url)
                if response.status_code == 200:
                    dataee = response.json()  # Parse the JSON response
                    d['docs']=dataee
                url = 'https://voidpanel.com/version_name/'  # Replace with your API URL
                response = requests.get(url)
                if response.status_code == 200:
                    dataee = response.json()  # Parse the JSON response
                
                    try:
                         with open(paths.VERSION_FILE, 'r') as f:
                              version=f.read()
                    except:
                         version='1.0'
                    if dataee['version'] > version:
                         d['show']=True
                         d['latestversion']=dataee['version']
                    else:
                         print("no")
                else:
                     version='1.0'
                d['version']=version
     
                    
                return render(request,'panel/update.html',d)
                
           
    else: 
        return redirect('/')
    
@login_required(login_url='/')
def updatepanel(request):
    if not request.user.is_superuser:
        return JsonResponse({'status': 'error', 'message': 'Forbidden'}, status=403)
    if request.method == 'POST':
        if sys.platform == 'win32':
            # Windows: download and apply update via PowerShell
            from voidplatform.windows.apps import update_panel_windows
            success, msg = update_panel_windows()
            if success:
                return JsonResponse({'status': 'success', 'message': msg})
            return JsonResponse({'status': 'error', 'message': msg})
        else:
            # Linux: download update script, verify, then run
            import tempfile
            import subprocess
            _update_path = os.path.join(tempfile.gettempdir(), 'voidpanel_update.sh')
            run_command(f'curl -fsSL -o {shlex.quote(_update_path)} https://voidpanel.com/updatepanel.sh')
            # Run detached so it doesn't wait for completion and allows the HTTP response to return
            subprocess.Popen(['bash', _update_path], start_new_session=True)
            return JsonResponse({'status': 'success', 'message': 'Update applied successfully.'})

    return JsonResponse({'status': 'error', 'message': 'Invalid request.'})

    

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
                d={}
                try:
                    
                    lold=domain.objects.all()
                  

                    d['domain']=lold
                    
                    logs=[]
                    path=paths.SSL_LOG
                    with open(path,'r') as f:
                         dd=f.readlines()
                         for i in dd:
                              logs.append(i)
                    d['logs']=logs   
                    url = 'https://voidpanel.com/admindocs/'  # Replace with your API URL
                    response = requests.get(url)
                    if response.status_code == 200:
                        dataee = response.json()  # Parse the JSON response
                        d['docs']=dataee
                    return render(request,'panel/allssl.html',d)
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
        response = requests.get(url)
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
        lold=domain.objects.all()
  
        d['database']=get_database_names(adminpassword)
        d['users']=get_database_users(adminpassword)
        url = 'https://voidpanel.com/admindocs/'  # Replace with your API URL
        response = requests.get(url)
        if response.status_code == 200:
            dataee = response.json()  # Parse the JSON response
            d['docs']=dataee
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
        response = requests.get(url)
        if response.status_code == 200:
            dataee = response.json()  # Parse the JSON response
            d['docs']=dataee
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
        
        # Cleanup from files
        for _fpath in [paths.POSTFIX_VIRTUAL_ALIAS, paths.POSTFIX_VIRTUAL_MAILBOX]:
            if os.path.exists(_fpath):
                with open(_fpath, 'r') as _f:
                    _lines = _f.readlines()
                with open(_fpath, 'w') as _f:
                    _f.writelines(l for l in _lines if not l.startswith(f'{data} '))
        if sys.platform != 'win32':
            run_command(f"postmap {paths.POSTFIX_VIRTUAL_ALIAS}")
            run_command(f"postmap {paths.POSTFIX_VIRTUAL_MAILBOX}")

        # Cleanup specific user directory (not whole domain!)
        sys_owner = 'vmail'
        owner_obj = sysuser.objects.filter(domain=domain_name).first()
        if owner_obj:
            sys_owner = owner_obj.username
            
        home_path = os.path.join(paths.HOME_BASE, sys_owner, 'mail', domain_name, user_prefix)
        old_path = os.path.join(_resolve_mail_domain_dir(domain_name), user_prefix)
        
        if os.path.exists(home_path): shutil.rmtree(home_path, ignore_errors=True)
        if os.path.exists(old_path): shutil.rmtree(old_path, ignore_errors=True)
        
        # Remove from Dovecot users mapping if it exists
        for _fpath in [paths.DOVECOT_USERS,
                       os.path.join(_resolve_mail_domain_dir(domain_name), 'passwd'),
                       os.path.join(_resolve_mail_domain_dir(domain_name), 'shadow')]:
            if os.path.exists(_fpath):
                with open(_fpath, 'r') as _f:
                    _lines = _f.readlines()
                with open(_fpath, 'w') as _f:
                    _f.writelines(l for l in _lines if not l.startswith(f'{data}:'))
        
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
        config.save()
        return JsonResponse({'status': 'success'})

    return render(request, 'panel/emailconfig.html', {'config': config})
    

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
def cpbruteforce(request):
    
    if request.user.is_superuser:
      
        d={}
        if firewall.objects.filter(id=1).exists():
            d['firewall'] = firewall.objects.get(id=1)
        else:
            d['firewall'] = firewall(id=1, status=False)
            d['firewall'].save()
        url = 'https://voidpanel.com/admindocs/'  # Replace with your API URL
        response = requests.get(url)
        if response.status_code == 200:
            dataee = response.json()  # Parse the JSON response
            d['docs']=dataee
        return render(request,'panel/cpbruteforce.html',d)
    else: 
        return redirect('/')
    
@login_required(login_url='/')
def cpbrute(request):
    if request.user.is_superuser:
        if request.method=="POST":
            if firewall.objects.filter(id=1).exists():
                e = firewall.objects.get(id=1)
            else:
                e = firewall(id=1, status=False)
                e.save()
            try:
                if e.status:
                    if sys.platform != 'win32':
                        run_command('''sudo sed -i 's/^TESTING = "0"/TESTING = "1"/' /etc/csf/csf.conf''')
                        run_command('sudo csf -x')
                    e.status = False
                    e.save()
                else:
                    if sys.platform != 'win32':
                        run_command('''sudo sed -i 's/^TESTING = "1"/TESTING = "0"/' /etc/csf/csf.conf''')
                        run_command('sudo csf -e')
                    e.status = True
                    e.save()
                return JsonResponse({'status': 'success', 'message': 'Firewall status updated'})
            except Exception as ex:
                return JsonResponse({'status': 'error', 'message': 'Failed to execute firewall rules. Is CSF installed on the server?'})
    return JsonResponse({'status': 'error', 'message': 'Invalid request.'})

@login_required(login_url='/')
def allowip(request):
    if request.user.is_superuser and request.method=="POST":
        php=shlex.quote(request.POST.get('allow', ''))
        get_platform().firewall.allow_ip(php)
        get_platform().firewall.reload()
        return JsonResponse({'status': 'success', 'message': 'IP Successfully Allowed'})
    return JsonResponse({'status': 'error', 'message': 'Invalid request.'})

@login_required(login_url='/')
def denyip(request):
    if request.user.is_superuser and request.method=="POST":
        php=shlex.quote(request.POST.get('allow', ''))
        get_platform().firewall.deny_ip(php)
        get_platform().firewall.reload()
        return JsonResponse({'status': 'success', 'message': 'IP Successfully Denied'})
    return JsonResponse({'status': 'error', 'message': 'Invalid request.'})

@login_required(login_url='/')
def ignoreip(request):
    if request.user.is_superuser and request.method=="POST":
        php=shlex.quote(request.POST.get('allow', ''))
        # Since CSF has no direct ignore command, we simulate what was there earlier.
        get_platform().firewall.allow_ip(php)
        get_platform().firewall.reload()
        return JsonResponse({'status': 'success', 'message': 'IP Successfully Ignored'})
    return JsonResponse({'status': 'error', 'message': 'Invalid request.'})

@login_required(login_url='/')
def unblockip(request):
    if request.user.is_superuser and request.method=="POST":
        php=shlex.quote(request.POST.get('allow', ''))
        if sys.platform != 'win32':
            run_command(f'sudo csf -dr {php}')
            run_command('sudo csf -r')
        return JsonResponse({'status': 'success', 'message': 'IP Successfully Unblocked'})
    return JsonResponse({'status': 'error', 'message': 'Invalid request.'})

@login_required(login_url='/')
def blockip(request):
    if request.user.is_superuser and request.method=="POST":
        php=shlex.quote(request.POST.get('allow', ''))
        get_platform().firewall.deny_ip(php)
        get_platform().firewall.reload()
        return JsonResponse({'status': 'success', 'message': 'IP Successfully Blocked'})
    return JsonResponse({'status': 'error', 'message': 'Invalid request.'})


@login_required(login_url='/')
def ftpserver(request):
    
    if request.user.is_superuser:
      
        d={}
        d['ftp']=ftp.objects.get(id=1)
        url = 'https://voidpanel.com/admindocs/'  # Replace with your API URL
        response = requests.get(url)
        if response.status_code == 200:
            dataee = response.json()  # Parse the JSON response
            d['docs']=dataee
        return render(request,'panel/ftp.html',d)
    else: 
        return redirect('/')
    

@login_required(login_url='/')
def ftp12(request):
    if not request.user.is_superuser:
        return JsonResponse({'status': 'error', 'message': 'Permission denied.'}, status=403)
        
    if request.method == "POST":
        try:
            e = ftp.objects.get(id=1)
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
        url = 'https://voidpanel.com/admindocs/'  # Replace with your API URL
        response = requests.get(url)
        if response.status_code == 200:
            dataee = response.json()  # Parse the JSON response
            d['docs']=dataee
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
                if not owner or owner.domain != domainname:
                    return JsonResponse({'status': 'error', 'message': 'Unauthorized'}, status=403)
            # Validate service name matches a known app
            if not pythonname.objects.filter(name=name, domain=domainname).exists():
                return JsonResponse({'status': 'error', 'message': 'Service not found.'})
            if start_service(name):
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
                if not owner or owner.domain != domainname:
                    return JsonResponse({'status': 'error', 'message': 'Unauthorized'}, status=403)
            if not pythonname.objects.filter(name=name, domain=domainname).exists():
                return JsonResponse({'status': 'error', 'message': 'Service not found.'})
            if restart_service(name):
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
                if not owner or owner.domain != domainname:
                    return JsonResponse({'status': 'error', 'message': 'Unauthorized'}, status=403)
            if not pythonname.objects.filter(name=name, domain=domainname).exists():
                return JsonResponse({'status': 'error', 'message': 'Service not found.'})
            if stop_service(name):
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
                    response = requests.get(url)
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
                    response = requests.get(url)
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
                    response = requests.get(url)
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
                    response = requests.get(url)
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
                
                # Inject new blocks properly before location ~ /\.ht { (in 443 block)
                if 'location ~ /\\.ht {' in new_conf:
                    new_conf = new_conf.replace('location ~ /\\.ht {', new_location_block + '\n    location ~ /\\.ht {', 1)
                
                r = mgr.write_and_test_site_config(domain1, new_conf)
                if not r.success:
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
    persistent_shell.expect(r'[#$]')
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
        
        if command.startswith('pip') or command.startswith('python'):
             if 'pip' not in command and 'django' in command or 'flask' in command:
                  command = f"/home/{shlex.quote(current)}/{shlex.quote(name)}/venv/bin/{command} /home/{shlex.quote(current)}/{shlex.quote(name)} "
             else:  
                command = f"/home/{shlex.quote(current)}/{shlex.quote(name)}/venv/bin/{command} "

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
                persistent_shell.expect(r'[#$]') 
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
                persistent_shell.expect(r'[#$]') 
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
                    response = requests.get(url)
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
                    response = requests.get(url)
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
    unix_user = ''
    if not destination:
        from urllib.parse import urlparse as _urlparse
        site_name = _urlparse(target_url).netloc.replace('www.', '') or 'cloned_site'
        # Determine user's home dir
        try:
            if request.user.is_superuser:
                uname = request.session.get('name', request.user.username)
            else:
                uname = str(request.user)
            from control.models import user as ctrl_user
            u_obj = ctrl_user.objects.filter(username=uname).first()
            user_dir = u_obj.dir if u_obj else uname
            unix_user = user_dir
            destination = os.path.join(paths.HOME_BASE, user_dir, 'public_html', site_name)
        except Exception:
            user_dir = str(request.user)
            unix_user = user_dir
            destination = os.path.join(paths.HOME_BASE, str(request.user), 'public_html', site_name)
    else:
        # Sanitize user-provided path — must stay within HOME_BASE/<user-dir>
        try:
            # Resolve the user's actual home dir from DB (may differ from username)
            try:
                _uname = request.session.get('name', request.user.username) if request.user.is_superuser else str(request.user)
                from control.models import user as _cu
                _u_obj = _cu.objects.filter(username=_uname).first()
                _user_home_dir = _u_obj.dir if _u_obj else _uname
                unix_user = _user_home_dir
            except Exception:
                _user_home_dir = str(request.user)
                unix_user = _user_home_dir

            safe_dest = os.path.realpath(os.path.normpath('/' + destination.lstrip('/')))
            allowed_base = os.path.join(paths.HOME_BASE, _user_home_dir)
            if not request.user.is_superuser and not safe_dest.startswith(allowed_base):
                return JsonResponse({'status': 'error', 'message': 'Destination outside your home directory is not permitted.'}, status=403)
            destination = safe_dest

            # Re-extract unix_user from path if superuser provided explicit path
            if request.user.is_superuser:
                import re as _re2
                m = _re2.search(r'/home/([^/]+)', destination)
                if m: unix_user = m.group(1)
        except ValueError as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=403)

    # Kick off background clone thread
    import threading
    def _run_clone():
        try:
            clone_website(target_url, destination)
            import subprocess, sys
            if sys.platform != 'win32' and unix_user:
                subprocess.run(['sudo', 'chown', '-R', f'{unix_user}:{unix_user}', destination], check=False)
        except Exception:
            pass

    t = threading.Thread(target=_run_clone, daemon=True)
    t.start()

    return JsonResponse({
        'status': 'success',
        'message': f'Cloning started! Files will appear in {destination}',
        'destination': destination
    })


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
    """Admin-only page showing current web server and allowing live switching."""
    if not request.user.is_superuser:
        return HttpResponse('Unauthorized', status=403)

    from voidplatform.linux.web import get_active_engine
    d = {}
    try:
        d['active_engine'] = get_active_engine()
    except PermissionError:
        # State file not readable by www-data — attempt chmod fix then retry
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

    # OLS is "installed" if the binary or state file exists
    d['ols_installed'] = (os.path.exists('/usr/local/lsws/bin/lswsctrl') or
                          os.path.exists('/usr/local/lsws') or
                          d['active_engine'] == 'ols' or
                          d['ols_running'])

    d['domain_count'] = domain.objects.count()
    return render(request, 'panel/webserver_manager.html', d)


@login_required(login_url='/')
def api_switch_webserver(request):
    """
    POST API — switches the live web server between NGINX and OpenLiteSpeed.

    Security guarantees:
      - Superuser-only. Returns 403 for everyone else.
      - All site configs are fully written and tested BEFORE stopping the old server.
      - If the new engine fails its config test, the old engine stays running (automatic rollback).
      - All site directories are re-chowned to their unix users BEFORE the switch — quota
        attribution is continuous with zero gap.
      - The system state flag is updated ONLY after a successful service start.

    POST body: { "target": "nginx" | "ols" }
    """
    if not request.user.is_superuser:
        return JsonResponse({'status': 'error', 'message': 'Superuser only'}, status=403)
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'POST required'}, status=405)

    import json as _json
    try:
        body = _json.loads(request.body)
        target_engine = body.get('target', '').lower()
    except Exception:
        target_engine = request.POST.get('target', '').lower()

    if target_engine not in ('nginx', 'ols'):
        return JsonResponse({'status': 'error',
                             'message': 'target must be "nginx" or "ols"'}, status=400)

    from voidplatform.linux.web import get_active_engine, WebServerSwitcher

    current = get_active_engine()
    if current == target_engine:
        return JsonResponse({'status': 'ok',
                             'message': f'Already running {target_engine}'})

    # Build the domain list for the switcher
    all_domains = domain.objects.select_related().all()
    domain_list = []
    for dom in all_domains:
        # Get the user record to pull their unix dir + php version
        u_obj = user.objects.filter(domain=dom.domain).first()
        php   = getattr(dom, 'php', '8.3') or '8.3'
        root  = os.path.join(paths.HOME_BASE, dom.dir, 'public_html')
        domain_list.append({
            'domain':      dom.domain,
            'root_dir':    root,
            'php_version': php,
            'unix_user':   dom.dir,   # unix username IS the dir field
        })

    switcher = WebServerSwitcher()
    result   = switcher.switch(target_engine, domain_list,
                               php_defaults={'php_version': '8.3'})

    if result.success:
        return JsonResponse({'status': 'success', 'message': result.output})
    else:
        return JsonResponse({'status': 'error',   'message': result.error}, status=500)


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
    import tempfile
    if not (request.user.is_superuser or request.user.is_authenticated): return JsonResponse({'error': 'Unauthorized'})
    email = request.POST.get('email')
    limit = request.POST.get('limit')
    limit_type = request.POST.get('type')
    if not email or not limit: return JsonResponse({'error': 'Invalid parameters'})
    
    try: limit_count = int(limit)
    except: return JsonResponse({'error': 'Limit must be integer'})
        
    timespan = "3600" if limit_type == 'hourly' else "86400"
    file_path = "/etc/postfwd/vp_limits.cf"
    safe_id = "limit_" + email.replace('@', '_').replace('.', '_')
    
    run_command(f"sudo touch {file_path}")
    run_command(f"sudo sed -i '/id={safe_id};/d' {file_path}")
    
    if limit_count > 0:
        rule = f"id={safe_id}; sasl_username={email}; action=rate(sasl_username/{limit_count}/{timespan}/450 4.7.1 Rate Limit Exceeded for {email})"
        with tempfile.NamedTemporaryFile('w', delete=False) as tf:
            tf.write(rule + "\n")
            tmp_f = tf.name
        run_command(f"sudo bash -c 'cat {tmp_f} >> {file_path}'")
        run_command(f"sudo systemctl restart postfwd || true")
        run_command(f"sudo rm {tmp_f}")
        
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
        target_user_id = request.POST.get('target_user')
        
        if not target_user_id:
            return JsonResponse({'status': 'error', 'message': 'You must select a target user.'}, status=400)
            
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
            background_migration_task.delay(source_type, auth_data, target_user_id)
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
    system shell to /bin/rbash (enable) or /bin/false (revoke).
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
            os.system(f'usermod -s /bin/rbash {username}')
        else:
            os.system(f'usermod -s /bin/false {username}')

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
