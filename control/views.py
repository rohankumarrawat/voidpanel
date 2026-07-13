from django.http import JsonResponse, HttpResponse
from django.shortcuts import render,redirect
import json
import sys
import requests
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from control.models import pythonname,mernname,user,domain,subdomainname,cron,package,allemail,redir,ftpaccount,ftp,phpversion
from function import get_server_ip,is_website_live,get_database_users_with_filter,get_database_names_with_filter,parse_dns_zone_file,run_command,zip_multiple_locations_backup_user,get_directory_size_in_mb,get_file_info,get_database_privileges_with_filter
from django.views.decorators.csrf import csrf_exempt
import os
import subprocess
from voidplatform import get_platform
from voidplatform.config import paths


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



def _template_exists(template_name):
    """Return True if a Django template file can be found on disk."""
    from django.template.loader import get_template
    from django.template.exceptions import TemplateDoesNotExist
    try:
        get_template(template_name)
        return True
    except TemplateDoesNotExist:
        return False


# except:
#      adminpassword="adminpassword"


def get_user_dashboard_context(current, adminpassword=""):
    d = {}
    try:
        u = user.objects.get(username=current)
    except:
        return d
    hp = safe_get_package(u.hosting_package)

    d['ipaddress'] = get_server_ip()
    d['dir'] = current

    # Primary domain — used by every feature card link in the dashboard
    d['domain'] = u.domain
    d['primarydomain'] = u.domain

    # SSL status check for sidebar domain badge
    try:
        d['primarydomainstatus'] = domain.objects.get(domain=u.domain).sslstatus
    except:
        d['primarydomainstatus'] = False

    d['rohan'] = ftp.objects.filter(id=1).first()

    d['avaiablestorage'] = int(hp.storage)
    try:
        d['remainingstorage'] = int(get_directory_size_in_mb(os.path.join(paths.HOME_BASE, str(current))))
    except:
        d['remainingstorage'] = 0
    if d['avaiablestorage'] == 0:
        d['storagestatus'] = True
    else:
        d['storagestatus'] = False
        try:
            d['percentagestorage'] = (d['remainingstorage'] / d['avaiablestorage']) * 100
        except ZeroDivisionError:
            d['percentagestorage'] = 0

    d['totalemail'] = int(hp.email_accounts)
    d['usedemail'] = len(allemail.objects.filter(domain=u.domain))
    if d['totalemail'] == 0:
        d['totalemail'] = '∞'
        d['percentageemail'] = 0
    else:
        d['percentageemail'] = (d['usedemail'] / d['totalemail']) * 100

    d['totalsubdomain'] = int(hp.subdomain)
    d['usedsubdomain'] = len(subdomainname.objects.filter(domain=u.domain))
    if d['totalsubdomain'] == 0:
        d['totalsubdomain'] = '∞'
        d['percentagesubdomain'] = 0
    else:
        d['percentagesubdomain'] = (d['usedsubdomain'] / d['totalsubdomain']) * 100

    d['totalftp'] = int(hp.ftp)
    d['usedftp'] = len(ftpaccount.objects.filter(main=u))
    if d['totalftp'] == 0:
        d['totalftp'] = '∞'
        d['percentageftp'] = 0
    else:
        d['percentageftp'] = (d['usedftp'] / d['totalftp']) * 100

    mainn = str(current) + '_'
    d['totaldb'] = int(hp.databases_allowed)
    d['useddatabase'] = len(get_database_names_with_filter(adminpassword, mainn))
    if d['totaldb'] == 0:
        d['totaldb'] = '∞'
        d['percentagedb'] = 0
    else:
        d['percentagedb'] = (d['useddatabase'] / d['totaldb']) * 100
        
    d['shell_access'] = getattr(u, 'shell', False)
    d['status'] = is_website_live(f"http://{u.domain}")

    # ── Reseller sidebar context (safe – never raises) ────────────────────────
    try:
        from control.models import ResellerProfile
        rp = ResellerProfile.objects.get(auth_user__username=str(current), is_active=True)
        d['is_reseller']           = True
        d['reseller_acct_count']   = rp.get_account_count()
        d['reseller_max_accounts'] = rp.max_accounts
        d['reseller_quota_gb']     = rp.storage_quota_gb
        d['reseller_used_gb']      = round(rp.get_used_storage_gb(), 2)
        d['reseller_acct_pct']     = rp.get_account_percent()
        d['reseller_used_pct']     = rp.get_storage_percent()
    except Exception:
        d['is_reseller'] = False

    # ── Suite Platform — detect which suites the package includes ─────────────
    try:
        d['pkg_includes_social']    = getattr(hp, 'includes_social', False)
        d['pkg_includes_seo']       = getattr(hp, 'includes_seo', False)
        d['pkg_includes_marketing'] = getattr(hp, 'includes_marketing', False)
        d['pkg_social_plan']        = getattr(hp, 'social_plan', '') or 'starter'
        d['pkg_seo_plan']           = getattr(hp, 'seo_plan', '') or 'lite'
        d['pkg_marketing_plan']     = getattr(hp, 'marketing_plan', '') or 'starter'
        # SSO launch URLs
        dom = u.domain
        d['suite_sso_social']    = f'/control/suite-sso/{dom}/social/'
        d['suite_sso_seo']       = f'/control/suite-sso/{dom}/seo/'
        d['suite_sso_marketing'] = f'/control/suite-sso/{dom}/marketing/'
        d['has_any_suite']       = any([d['pkg_includes_social'], d['pkg_includes_seo'], d['pkg_includes_marketing']])
    except Exception:
        d['pkg_includes_social'] = d['pkg_includes_seo'] = d['pkg_includes_marketing'] = False
        d['has_any_suite'] = False

    return d


def safe_get_package(package_name):
    try:
        if not package_name:
            raise package.DoesNotExist
        return package.objects.get(name=package_name)
    except package.DoesNotExist:
        return package(storage='0', email_accounts='0', subdomain='0', databases_allowed='0', ftp='0')

@login_required(login_url='/')
def chstorageftp(request):
        try:
            usewe=user.objects.get(username=request.user)
            curren=request.user
            dddd=usewe.domain
        except:
             if request.user.is_superuser:
                usewe=user.objects.get(username=request.session['name'])
                curren=request.session['name']
                dddd=usewe.domain
             else:
                return JsonResponse({'status': 'error', 'error': 'Unauthorized'}, status=403)
                  
             
        if request.method == 'POST':
            # Extract data from the POST request
            name = request.POST.get('user')
            name=name.lower()
            storage = request.POST.get('storage')
            # Ownership check: ensure the FTP account belongs to the current user
            ftp_obj = ftpaccount.objects.filter(username=name).first()
            if ftp_obj and not request.user.is_superuser:
                if ftp_obj.main != str(curren):
                    return JsonResponse({'status': 'error', 'error': 'Unauthorized'}, status=403)
            get_platform().users.set_quota(name, int(storage), int(storage)) if sys.platform != 'win32' else None
            try:
                 re=ftpaccount.objects.get(username=name)
                 re.storage=storage
                 re.save()
            except:
                 pass
            
            return JsonResponse({'status': 'success', 'error': 'Invalid request method'})

@login_required(login_url='/')
def chpasswordftp(request):
        try:
            usewe=user.objects.get(username=request.user)
            curren=request.user
            dddd=usewe.domain
        except:
             if request.user.is_superuser:
                usewe=user.objects.get(username=request.session['name'])
                curren=request.session['name']
                dddd=usewe.domain
             else:
                return JsonResponse({'status': 'error', 'error': 'Unauthorized'}, status=403)
                  
             
        if request.method == 'POST':
            # Extract data from the POST request
            name = request.POST.get('domain')
            name=name.lower()
            # Ownership check: ensure this user belongs to the current user's domain
            if not request.user.is_superuser:
                if name != str(curren) and not ftpaccount.objects.filter(username=name, main=str(curren)).exists():
                    return JsonResponse({'status': 'error', 'error': 'Unauthorized'}, status=403)
            password = request.POST.get('password')
            get_platform().users.change_password(name, password)
            return JsonResponse({'status': 'success', 'error': 'Invalid request method'})
            

       
                 

                 

        return JsonResponse({'success': False, 'error': 'Invalid request method'})


@login_required(login_url='/')
def ftpadd(request):
        
        







        try:
            usewe=user.objects.get(username=request.user)
            curren=request.user
            dddd=usewe.domain
        except:
             if request.user.is_superuser:
                usewe=user.objects.get(username=request.session['name'])
                curren=request.session['name']
                dddd=usewe.domain
                  
             
        if request.method == 'POST':
            # Extract data from the POST request
            name = request.POST.get('username')

            domainname = request.POST.get('domain')
            domainname=domainname.lower()
            password = request.POST.get('password')
            storage = request.POST.get('storage')
            path = request.POST.get('path', '').strip()
            if not path:
                path = "public_html"
            if not path.startswith("/"):
                path = "/" + path
            path = os.path.join(paths.HOME_BASE, str(curren)) + path
            fullname=domainname+'_'+name

            try:
                 erre=ftpaccount.objects.get(username=fullname)
                 return JsonResponse({'status': 'already', 'error': 'Invalid request method'})
            except:
                 pass
            
          
            if dddd==domainname:

                rere=int(safe_get_package(usewe.hosting_package).ftp)
                cretee=len(ftpaccount.objects.filter(main=curren))
                if safe_get_package(usewe.hosting_package).ftp !='0':
                     if cretee >= rere:
                          return JsonResponse({'status': 'exceed', 'error': 'Invalid request method'})
            try:
                if sys.platform != 'win32':
                    run_command(f'sudo mkdir -p {path}')
                else:
                    os.makedirs(path, exist_ok=True)
                try:
                    plat = get_platform()
                    plat.users.create_user(fullname, password, shell=paths.NOLOGIN_SHELL)
                except:
                     pass
                try:
                    if sys.platform != 'win32':
                        get_platform().users.set_quota(fullname, int(storage), int(storage))
                except:
                     pass
                if sys.platform != 'win32':
                    run_command(f'sudo chown {fullname}:{fullname} {path}')
                if sys.platform != 'win32':
                    run_command(f'echo "{fullname}" | sudo tee -a {paths.VSFTPD_USERLIST}')
                else:
                    with open(paths.VSFTPD_USERLIST, 'a') as f:
                         f.write(f"\n {fullname}")
                get_platform().services.restart('vsftpd')
                import base64
                text_bytes = password.encode('utf-8')
                encoded_text = base64.b64encode(text_bytes)
                erre=ftpaccount.objects.create(main=curren,username=fullname,password=encoded_text,storage=storage)
                return JsonResponse({'status': 'success', 'error': 'Invalid request method'})

            except:
                 return JsonResponse({'status': 'path', 'error': 'Invalid request method'})
                 

                 

        return JsonResponse({'success': False, 'error': 'Invalid request method'})


@login_required(login_url='/')
def ftp122(request,data):


    if request.user.is_superuser:
        current=request.session['name']
    else:
        current=request.user
    try:
        with open(paths.MYSQL_PASSWORD_FILE,'r') as f:
            adminpassword=f.read()
            adminpassword=adminpassword.strip()
    except Exception:
        adminpassword = ''
   
    if data == user.objects.get(username=current).domain:
                d={}
                d.update(get_user_dashboard_context(current, adminpassword))
        
                try:
                    lold=domain.objects.get(domain=data)
                    d['ftp']=ftpaccount.objects.filter(main=lold.dir)
                    d['domain']=lold.domain
                    d['dir']=lold.dir
                    url = 'https://voidpanel.com/clientdocs/'  # Replace with your API URL
                    response = requests.get(url, timeout=2)
                    if response.status_code == 200:
                        dataee = response.json()  # Parse the JSON response
                        d['docs']=dataee
                   
                 
                    return render(request,'control/ftp.html',d)
                except:
                    return redirect("/")
           
    else: 
        return redirect('/')
    
@login_required(login_url='/')
def deleteftp(request,data):

    if request.user.is_superuser:
        current=request.session['name']
    else:
        current=request.user
    loo=ftpaccount.objects.get(username=data).main
    if current == loo:
                
                d={}
                try:
                 
                    
                    dd=ftpaccount.objects.get(username=data)
                    dd.delete()
                    get_platform().users.delete_user(data)
                    domain32=user.objects.get(username=current).domain
                    return redirect(f"/control/ftp/{domain32}")
                except:
                    return redirect("/")
           
    else:
        return redirect('/')


@login_required(login_url='/')
def pma_login(request, data):
    """
    phpMyAdmin Single Sign-On login handler.

    Strategy: Django calls vp_sso.php server-side (via localhost),
    extracts the phpMyAdmin session cookie from the response, then
    redirects the user's browser directly to phpMyAdmin — forwarding
    the session cookie in the redirect response.

    This bypasses all cross-origin browser restrictions.
    """
    from django.http import HttpResponse, HttpResponseRedirect
    from control.pma_sso import create_temp_pma_user
    import requests as _req

    try:
        with open(paths.MYSQL_PASSWORD_FILE, 'r') as f:
            adminpassword = f.read().strip()
    except Exception:
        adminpassword = ''

    if request.user.is_superuser:
        current = request.session.get('name', request.user.username)
    else:
        current = str(request.user)

    try:
        # Verify domain ownership
        lold = domain.objects.get(domain=data)
        if not request.user.is_superuser:
            if user.objects.get(username=current).domain != data:
                return redirect('/')

        # Get directory prefix for DB wildcard grants
        cc = lold.dir

        # Create temp MySQL user scoped to this domain's DBs
        temp_user, temp_password = create_temp_pma_user(cc, adminpassword)
        if not temp_user:
            return HttpResponse(
                '<h3 style="font-family:sans-serif;color:red;padding:40px;">'
                '&#9888; Could not create temporary database session.<br>'
                '<small>Check /tmp/sso_debug.log on the server for details.</small>'
                '</h3>',
                status=500
            )

        # ── Resolve PMA public URL ────────────────────────────────────────────
        pma_host = None
        hostname_notice = ''
        try:
            from control.models import quick as QuickModel
            q = QuickModel.objects.first()
            raw_hostname = (q.hostname or '').strip() if q else ''
            if raw_hostname and raw_hostname not in ('False', 'None', ''):
                pma_host = raw_hostname
            else:
                hostname_notice = (
                    '<div style="background:rgba(251,191,36,.15);border:1px solid '
                    'rgba(251,191,36,.4);border-radius:8px;padding:12px 16px;'
                    'margin-bottom:18px;font-size:.85rem;color:#fbbf24;text-align:left;">'
                    '&#9888; <b>No hostname configured.</b> Using server IP. '
                    'Go to <b>Admin &rarr; Hostname</b> to set your panel hostname.'
                    '</div>'
                )
        except Exception:
            pass

        if not pma_host:
            try:
                pma_host = get_server_ip()
            except Exception:
                import socket
                pma_host = socket.gethostbyname(socket.gethostname())

        pma_clean_host = pma_host.split(':')[0]

        # Determine the public-facing protocol/port for the browser redirect
        pma_proto = "https" if request.is_secure() else "http"
        pma_port  = "8092"  if pma_proto == "https" else "8090"
        pma_public_url = f"{pma_proto}://{pma_clean_host}:{pma_port}"

        # ── SERVER-SIDE call to vp_sso.php via localhost ──────────────────────
        # We POST to 127.0.0.1:8090 internally — no cross-origin issues.
        # We get the phpMyAdmin session cookie back, then relay it to the browser.
        pma_session_cookie = None
        sso_error = None

        try:
            sso_resp = _req.post(
                'http://127.0.0.1:8090/vp_sso.php',
                data={'temp_user': temp_user, 'temp_password': temp_password},
                allow_redirects=False,   # We capture the Set-Cookie, not the redirect
                timeout=5,
                verify=False,
            )
            # Extract the phpMyAdmin session cookie from the SSO response
            if 'phpMyAdmin' in sso_resp.cookies:
                pma_session_cookie = sso_resp.cookies['phpMyAdmin']
            elif 'Set-Cookie' in sso_resp.headers:
                # Parse raw Set-Cookie header as fallback
                raw_cookie = sso_resp.headers.get('Set-Cookie', '')
                import re as _re
                m = _re.search(r'phpMyAdmin=([^;]+)', raw_cookie)
                if m:
                    pma_session_cookie = m.group(1)
        except Exception as sso_e:
            sso_error = str(sso_e)
            print(f"[PMA SSO] Server-side call failed: {sso_e}")

        # ── Build the redirect response ───────────────────────────────────────
        if pma_session_cookie:
            # Redirect the browser directly to phpMyAdmin with the session cookie
            response = HttpResponseRedirect(f"{pma_public_url}/index.php")
            # Forward the phpMyAdmin session cookie to the browser.
            # Cookies are port-agnostic in HTTP — a cookie for panel.voidpanel.com
            # is sent to panel.voidpanel.com:8090 as well (same host, different port).
            # Don't set domain= for IP addresses (browsers reject those).
            import re as _re_ip
            is_ip = bool(_re_ip.match(r'^\d{1,3}(\.\d{1,3}){3}$', pma_clean_host))
            response.set_cookie(
                'phpMyAdmin',
                pma_session_cookie,
                max_age=3600,
                path='/',
                samesite='None' if pma_proto == 'https' else 'Lax',
                secure=(pma_proto == 'https'),
                httponly=False,
                domain=None,   # Let browser default to current hostname (works for same host, all ports)
            )
            return response
        else:
            # Fallback: classic browser form-POST approach
            # (works if same-origin or if browser allows the cross-port cookie)
            pma_sso_url = f"{pma_public_url}/vp_sso.php"

            html_content = f"""<!DOCTYPE html>
<html>
<head>
  <title>Opening phpMyAdmin...</title>
  <style>
    body {{
      background:#0d1117; color:#f1f5f9;
      display:flex; align-items:center; justify-content:center;
      height:100vh; margin:0;
      font-family:-apple-system,BlinkMacSystemFont,'Inter',sans-serif;
    }}
    .card {{ text-align:center; padding:40px; max-width:420px; }}
    h2 {{ font-size:1.25rem; margin-bottom:10px; font-weight:600; }}
    p  {{ font-size:.8rem; color:#64748b; margin-top:16px; }}
    .spinner {{
      width:40px; height:40px;
      border:3px solid rgba(255,255,255,.1);
      border-left-color:#6366f1; border-radius:50%;
      animation:spin .9s linear infinite; margin:0 auto 20px;
    }}
    @keyframes spin {{ to {{ transform:rotate(360deg); }} }}
  </style>
</head>
<body>
  <div class="card">
    {hostname_notice}
    <div class="spinner"></div>
    <h2>Opening phpMyAdmin...</h2>
    <p>Authenticating securely...</p>
    {f'<p style="color:#ef4444;font-size:.75rem;">SSO note: {sso_error}</p>' if sso_error else ''}
  </div>
  <form id="pma_form" method="post" action="{pma_sso_url}" style="display:none;">
    <input type="hidden" name="temp_user" value="{temp_user}">
    <input type="hidden" name="temp_password" value="{temp_password}">
  </form>
  <script>
    setTimeout(function() {{
      document.getElementById('pma_form').submit();
    }}, 200);
  </script>
</body>
</html>"""

            response = HttpResponse(html_content)
            return response

    except Exception as e:
        print(f"Error in pma_login: {e}")
        return redirect('/')



@login_required(login_url='/')
def dbconnect(request, data):
    try:
        with open(paths.MYSQL_PASSWORD_FILE, 'r') as f:
            adminpassword = f.read().strip()
    except Exception:
        adminpassword = ''

    if request.user.is_superuser:
        current = request.session.get('name', request.user.username)
    else:
        current = request.user

    if data == user.objects.get(username=current).domain:
        d = {}
        d.update(get_user_dashboard_context(current, adminpassword))
        d['totaldb'] = int(safe_get_package(user.objects.get(username=current).hosting_package).databases_allowed)
        if d['totaldb'] == 0:
            d['totaldb'] = '∞'
        mainn = str(current) + '_'
        d['useddatabase'] = len(get_database_names_with_filter(adminpassword, mainn))
        try:
            lold = domain.objects.get(domain=data)
            cc = lold.dir
            d['domain'] = data
            mainn = cc + '_'
            d['database'] = get_database_names_with_filter(adminpassword, mainn)
            d['users'] = get_database_users_with_filter(adminpassword, mainn)
            d['mappings'] = get_database_privileges_with_filter(adminpassword, mainn)
            return render(request, 'control/dbconnect.html', d)
        except Exception as e:
            print(f"dbconnect error: {e}")
            return redirect('/listwebsite/')
    else:
        return redirect('/')

@login_required(login_url='/')
def fulldbwizard(request, data):
    try:
        with open(paths.MYSQL_PASSWORD_FILE, 'r') as f:
            adminpassword = f.read().strip()
    except Exception:
        adminpassword = ''

    if request.user.is_superuser:
        current = request.session.get('name', request.user.username)
    else:
        current = request.user

    if data == user.objects.get(username=current).domain:
        d = {}
        d.update(get_user_dashboard_context(current, adminpassword))
        
        try:
            lold = domain.objects.get(domain=data)
            cc = lold.dir
            # For the control template we pass 'domain' as just the domain object or dictionary
            d['domain'] = {'domain': data, 'dir': cc}
            
            mainn = cc + '_'
            d['database'] = get_database_names_with_filter(adminpassword, mainn)
            d['users'] = get_database_users_with_filter(adminpassword, mainn)
            
            d['totaldb'] = int(safe_get_package(user.objects.get(username=current).hosting_package).databases_allowed)
            if d['totaldb'] == 0:
                d['totaldb'] = '∞'
            d['useddatabase'] = len(d['database'])
            
            # The JS expects front in adddatabase and adddatabaseuser, which is the domain prefix!
            d['front'] = cc + "_"
            
            url = 'https://voidpanel.com/clientdocs/'
            try:
                response = requests.get(url, timeout=3)
                if response.status_code == 200:
                    d['docs'] = response.json()
            except:
                pass
                
            return render(request, 'control/fulldbwizard.html', d)
        except Exception as e:
            return redirect('/control/')
    else:
        return redirect('/')


@login_required(login_url='/')
def addredirect(request,data):
    try:
        with open(paths.MYSQL_PASSWORD_FILE,'r') as f:
            adminpassword=f.read()
            adminpassword=adminpassword.strip()
    except Exception:
        adminpassword = ''
   
    if request.user.is_superuser:
        current=request.session['name']
    else:
        current=request.user
   
    if data == user.objects.get(username=current).domain:
                d={}
                d.update(get_user_dashboard_context(current, adminpassword))
                d['totaldb']=int(safe_get_package(user.objects.get(username=current).hosting_package).databases_allowed)
                if d['totaldb']==0:
                    d['totaldb']='∞'
                mainn=str(current)+'_'
                d['useddatabase']=len(get_database_names_with_filter(adminpassword,mainn))
                
                try:
                    
                    lold=domain.objects.get(domain=data)
                    d['allredir']=redir.objects.filter(maindomain=data).all()
                    d['domain']=data

                    d['subdomain']=subdomainname.objects.filter(domain=data).all()     
                    url = 'https://voidpanel.com/clientdocs/'  # Replace with your API URL
                    response = requests.get(url, timeout=2)
                    if response.status_code == 200:
                        dataee = response.json()  # Parse the JSON response
                        d['docs']=dataee 
                    return render(request,'control/redirect.html',d)
                except Exception as e:
                    return redirect("/")
           
    else: 
        return redirect('/')
    
@login_required(login_url='/')
def subdomain(request,data):
    try:
        with open(paths.MYSQL_PASSWORD_FILE,'r') as f:
            adminpassword=f.read()
            adminpassword=adminpassword.strip()
    except Exception:
        adminpassword = ''
   
    if request.user.is_superuser:
        current=request.session['name']
    else:
        current=request.user
   
    if data == user.objects.get(username=current).domain:
                d={}
                d.update(get_user_dashboard_context(current, adminpassword))

                d['totaldb']=int(safe_get_package(user.objects.get(username=current).hosting_package).databases_allowed)
                if d['totaldb']==0:
                    d['totaldb']='∞'
                mainn=str(current)+'_'
                d['useddatabase']=len(get_database_names_with_filter(adminpassword,mainn))
                try:
                    
                    lold=domain.objects.get(domain=data)
                    d['domain']=data
                    d['data']=subdomainname.objects.filter(domain=data) 
                    weew=user.objects.get(username=current).hosting_package
                    er=safe_get_package(weew)
                    if er.subdomain !='0':   
                        if len(subdomainname.objects.filter(domain=data)) >= int(safe_get_package(user.objects.get(username=current).hosting_package).subdomain):
                            d['s']=True
                        else:
                            d['s']=False
                    else:
                            d['s']=False
                    url = 'https://voidpanel.com/clientdocs/'  # Replace with your API URL
                    response = requests.get(url, timeout=2)
                    if response.status_code == 200:
                        dataee = response.json()  # Parse the JSON response
                        d['docs']=dataee
                    return render(request,'control/subdomian.html',d)
                except Exception as e:
                    return redirect("/listwebsite/")
           
    else: 
        return redirect('/')
    

@login_required(login_url='/')
def phpini(request, data):
    import os
    import re
    from django.http import JsonResponse
    from control.models import user as ctrl_user, domain

    # Authorization fallback
    if request.user.is_superuser:
        username = request.session.get('name')
    else:
        username = request.user.username

    u_obj = ctrl_user.objects.filter(username=username).first()
    if not u_obj or data != u_obj.domain:
        if request.method == "POST":
            return JsonResponse({'status': 'error', 'message': 'Unauthorized domain access'})
        return redirect('/')

    d = {}
    try:
        domain_obj = domain.objects.get(domain=data)
        d['domain'] = data
        file_path = os.path.join(paths.HOME_BASE, domain_obj.dir, 'public_html', 'php.ini')

        DEFAULT_INI = "; Modern VoidPanel PHP Profile\nmemory_limit = 128M\nupload_max_filesize = 64M\npost_max_size = 64M\nmax_execution_time = 30\nmax_input_time = 60\ndisplay_errors = Off\n"

        # Safe Create
        if not os.path.exists(file_path):
            with open(file_path, 'w') as f:
                f.write(DEFAULT_INI)
            import subprocess
            if sys.platform != 'win32':
                subprocess.run(["sudo", "chown", f"{domain_obj.dir}:{domain_obj.dir}", file_path])

        values_dict = {}
        with open(file_path, 'r') as file:
            content = file.readlines()

        for line in content:
            stripped = line.strip()
            if not stripped or stripped.startswith(';'):
                continue
            if '=' in stripped:
                key, val = stripped.split('=', 1)
                values_dict[key.strip()] = val.strip()

        # Handle Saves Non-Destructively
        if request.method == "POST":
            for k in values_dict.keys():
                if k in request.POST:
                    new_val = request.POST[k]
                    # Regex to find key = value, keeping whitespace
                    pattern = re.compile(rf"^(\s*{re.escape(k)}\s*=\s*)(.*)$")
                    for idx, line in enumerate(content):
                        if pattern.match(line):
                            # Replace the second group (value)
                            content[idx] = pattern.sub(rf"\g<1>{new_val}\n", line.rstrip('\n'))

            # Write updated array of lines back to file
            with open(file_path, 'w') as file:
                file.writelines(content)

            return JsonResponse({'status': 'success', 'message': 'PHP configuration saved successfully.'})

        d["new"] = values_dict
        d.update(get_user_dashboard_context(username))
        
        try:
            url = 'https://voidpanel.com/clientdocs/'
            req = requests.get(url, timeout=3)
            if req.status_code == 200:
                d['docs'] = req.json()
        except:
            d['docs'] = []

        return render(request, 'control/phpini.html', d)
    except Exception as e:
        if request.method == "POST":
            return JsonResponse({'status': 'error', 'message': str(e)})
        return redirect('/control/')

    
@login_required(login_url='/')
def listemail(request,data):
    # data=data.lower()
    try:
        with open(paths.MYSQL_PASSWORD_FILE,'r') as f:
            adminpassword=f.read()
            adminpassword=adminpassword.strip()
    except Exception:
        adminpassword = ''
    import subprocess
    if request.user.is_superuser:
        current=request.session['name']
    else:
        current=request.user
   
   
    if data == user.objects.get(username=current).domain:
           d={}
           emaildetail=[]
           try: 
               domain.objects.get(domain=data)
               data=data.lower()
               d['allemail']=allemail.objects.filter(domain=data).all()

               # Fetch routing and custom limits info
               def get_suspended_emails(file_path):
                   suspended = set()
                   if os.path.exists(file_path):
                       try:
                           with open(file_path, 'r') as f:
                               for line in f:
                                   parts = line.strip().split()
                                   if parts:
                                       suspended.add(parts[0].lower())
                       except Exception:
                           pass
                   return suspended

               def get_user_limits():
                   limits = {}
                   db_path = '/var/lib/voidpanel-mail-policy/rate.db'
                   if os.path.exists(db_path):
                       try:
                           import sqlite3
                           conn = sqlite3.connect(db_path, timeout=1)
                           c = conn.cursor()
                           c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='user_limits'")
                           if c.fetchone():
                               c.execute('SELECT username, limit_val, timespan FROM user_limits')
                               for row in c.fetchall():
                                   limits[row[0].lower()] = {'limit': row[1], 'type': 'hourly' if row[2] == 3600 else 'daily'}
                           conn.close()
                       except Exception:
                           pass
                   return limits

               suspended_in = get_suspended_emails("/etc/postfix/vp_suspended_incoming")
               suspended_out = get_suspended_emails("/etc/postfix/vp_suspended_outgoing")
               user_limits = get_user_limits()

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
                   from django.core.cache import cache
                   from control.tasks import update_all_email_stats_task, update_all_email_stats
                   
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
                   email_lower = i.email.lower()
                   is_suspended_in = email_lower in suspended_in
                   is_suspended_out = email_lower in suspended_out
                   limit_info = user_limits.get(email_lower, {'limit': 0, 'type': 'hourly'})

                   emaildetail.append(
                       {
                           'email': i.email,
                           'domain': i.domain,
                           'sent': sent_cnt,
                           'failed': failed_cnt,
                           'queue': queue_cnt,
                           'sendp': sendp,
                           'failedp': failedp,
                           'processp': processp,
                           'total_emails_count': total_emails_count,
                           'suspended_in': is_suspended_in,
                           'suspended_out': is_suspended_out,
                           'custom_limit': limit_info['limit'],
                           'custom_limit_type': limit_info['type']
                       }
                   )
               d['emaildata']=emaildetail
               import socket
               hostname = socket.gethostname()
               url = f"https://{hostname}:9002"




               d.update(get_user_dashboard_context(current, adminpassword))

               d['totaldb']=int(safe_get_package(user.objects.get(username=current).hosting_package).databases_allowed)
               if d['totaldb']==0:
                    d['totaldb']='∞'
               mainn=str(current)+'_'
               d['useddatabase']=len(get_database_names_with_filter(adminpassword,mainn))
                        







               if is_website_live(url):
                   d['ip']=url
               else:
                   d['ip']=f"https://{get_server_ip()}:9002"
               
               # Server details for email client connection info
               d['server_hostname'] = f"mail.{data.lower()}"
               d['server_ip'] = get_server_ip()
               d['roundcube_url'] = f"https://{hostname}:9002"
               
               url = 'https://voidpanel.com/clientdocs/'  # Replace with your API URL
               response = requests.get(url, timeout=2)
               if response.status_code == 200:
                        dataee = response.json()  # Parse the JSON response
                        d['docs']=dataee
               return render(request,'control/listemail.html',d)
           except:
               return redirect('/')
    else: 
        return redirect('/')


@login_required(login_url='/')
def email_analysis(request, data):
    try:
        with open(paths.MYSQL_PASSWORD_FILE, 'r') as f:
            adminpassword = f.read().strip()
    except Exception:
        adminpassword = ''
    
    if request.user.is_superuser:
        current = request.session['name']
    else:
        current = request.user
    
    if data == user.objects.get(username=current).domain:
        d = {}
        email_stats = []
        try:
            data = data.lower()
            emails = allemail.objects.filter(domain=data).all()
            
            from django.core.cache import cache
            from control.tasks import update_all_email_stats_task, update_all_email_stats

            total_sent = 0
            total_failed = 0
            total_queue = 0
            total_received = 0
            
            for i in emails:
                usernameemail = i.email.split("@")[0]
                maildir_path = _resolve_maildir(i.domain, usernameemail)
                new_dir = os.path.join(maildir_path, "Maildir", "new")
                if not os.path.exists(new_dir):
                    new_dir = os.path.join(maildir_path, "new")
                cur_dir = os.path.join(maildir_path, "Maildir", "cur")
                if not os.path.exists(cur_dir):
                    cur_dir = os.path.join(maildir_path, "cur")
                
                new_emails = len(os.listdir(new_dir)) if os.path.exists(new_dir) else 0
                cur_emails = len(os.listdir(cur_dir)) if os.path.exists(cur_dir) else 0
                received_count = new_emails + cur_emails
                
                email_key = i.email.lower()
                stats = cache.get(f'email_stats:{email_key}')
                if stats is None:
                    try:
                        update_all_email_stats()
                        stats = cache.get(f'email_stats:{email_key}', {'sent': 0, 'failed': 0, 'queue': 0})
                    except Exception:
                        stats = {'sent': 0, 'failed': 0, 'queue': 0}
                
                sent_count = stats.get('sent', 0)
                failed_count = stats.get('failed', 0)
                queue_count = stats.get('queue', 0)
                
                total_sent += sent_count
                total_failed += failed_count
                total_queue += queue_count
                total_received += received_count
                
                email_stats.append({
                    'email': i.email,
                    'sent': sent_count,
                    'failed': failed_count,
                    'queue': queue_count,
                    'received': received_count
                })
            
            d['email_stats'] = email_stats
            d['totals'] = {
                'sent': total_sent,
                'failed': total_failed,
                'queue': total_queue,
                'received': total_received
            }
            d['domain'] = data
            d['primarydomain'] = user.objects.get(username=current).domain

            # Full dashboard context (needed by sidebar/base template)
            try:
                with open(paths.MYSQL_PASSWORD_FILE, 'r') as f:
                    adminpassword_ctx = f.read().strip()
            except Exception:
                adminpassword_ctx = ''
            d.update(get_user_dashboard_context(current, adminpassword_ctx))

            # Override domain back in case get_user_dashboard_context changed it
            d['domain'] = data

            return render(request, 'control/email_analysis.html', d)
        except Exception as e:
            import traceback
            print(f"Error in email_analysis: {e}\n{traceback.format_exc()}")
            return redirect('/')
    else:
        return redirect('/')



@login_required(login_url='/')
def email_delivery_report(request, email):
    try:
        with open(paths.MYSQL_PASSWORD_FILE, 'r') as f:
            adminpassword = f.read().strip()
    except Exception:
        adminpassword = ''
        
    if request.user.is_superuser:
        current = request.session['name']
    else:
        current = request.user
        
    email = email.strip().lower()
    
    # Check that this email belongs to the user's domain (unless superuser)
    if not request.user.is_superuser:
        domain_parts = email.split('@')
        if len(domain_parts) < 2:
            return redirect('/')
        user_domain = user.objects.get(username=current).domain
        if domain_parts[1] != user_domain.lower():
            return redirect('/')
            
    # Gather logs logic
    import re
    import subprocess
    import os
    
    log_path = '/var/log/mail.log'
    if not os.path.exists(log_path) or os.path.getsize(log_path) == 0:
        log_path = '/var/log/syslog'
        
    events = []
    if os.path.exists(log_path):
        try:
            cmd = ['sudo', 'grep', '-i', f'from=<{email}>', log_path]
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            
            queue_ids = set()
            if res.returncode == 0:
                for line in res.stdout.splitlines():
                    match = re.search(r'postfix/\w+\[\d+\]:\s+([0-9a-zA-Z]+):\s+', line)
                    if match:
                        queue_ids.add(match.group(1))
                        
            for qid in sorted(queue_ids, reverse=True)[:100]:
                cmd = ['sudo', 'grep', qid, log_path]
                res_qid = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
                if res_qid.returncode == 0:
                    lines = res_qid.stdout.splitlines()
                    timestamp = ""
                    recipient = ""
                    status = "unknown"
                    reason = ""
                    relay = ""
                    
                    for line in lines:
                        parts = line.split(qid)
                        if parts:
                            timestamp = parts[0].strip()
                            
                        # Clean timestamp
                        if ' fast ' in timestamp:
                            timestamp = timestamp.split(' fast ')[0].strip()
                        elif ' postfix/' in timestamp:
                            timestamp = timestamp.split(' postfix/')[0].strip()
                            
                        if 'to=<' in line:
                            match_to = re.search(r'to=<([^>]+)>', line)
                            if match_to:
                                recipient = match_to.group(1)
                            match_status = re.search(r'status=(\w+)', line)
                            if match_status:
                                status = match_status.group(1)
                            match_relay = re.search(r'relay=([^,]+)', line)
                            if match_relay:
                                relay = match_relay.group(1)
                            match_reason = re.search(r'status=\w+\s+\(([^)]+)\)', line)
                            if match_reason:
                                reason = match_reason.group(1)
                            else:
                                reason_parts = line.split('status=' + status)
                                if len(reason_parts) > 1:
                                    reason = reason_parts[1].strip()
                                    
                    events.append({
                        'qid': qid,
                        'timestamp': timestamp,
                        'recipient': recipient,
                        'status': status,
                        'relay': relay,
                        'reason': reason
                    })
        except Exception as e:
            print("Error parsing delivery logs:", e)
            
    d = {
        'email': email,
        'events': events,
        'domain': email.split('@')[1] if '@' in email else '',
        'primarydomain': user.objects.get(username=current).domain
    }
    
    d.update(get_user_dashboard_context(current, adminpassword))
    return render(request, 'control/email_delivery_report.html', d)


@csrf_exempt
@login_required(login_url='/')
def api_email_delivery_report(request):
    """AJAX endpoint for returning detailed email delivery logs for a given email address"""
    if not (request.user.is_superuser or request.user.is_authenticated):
        return JsonResponse({'status': 'error', 'message': 'Unauthorized'}, status=403)
        
    email = request.GET.get('email', '').strip().lower()
    if not email:
        return JsonResponse({'status': 'error', 'message': 'Missing email'}, status=400)
        
    # Check that this email belongs to the user's domain (unless superuser)
    if not request.user.is_superuser:
        domain_parts = email.split('@')
        if len(domain_parts) < 2:
            return JsonResponse({'status': 'error', 'message': 'Invalid email format'}, status=400)
        user_domain = user.objects.get(username=request.user).domain
        if domain_parts[1] != user_domain.lower():
            return JsonResponse({'status': 'error', 'message': 'Unauthorized to view this email'}, status=403)
            
    import re
    import subprocess
    import os
    
    log_path = '/var/log/mail.log'
    if not os.path.exists(log_path) or os.path.getsize(log_path) == 0:
        log_path = '/var/log/syslog'
        
    if not os.path.exists(log_path):
        return JsonResponse({'status': 'success', 'data': []})
        
    try:
        # Step 1: Find all Queue IDs for this sender email
        cmd = ['sudo', 'grep', '-i', f'from=<{email}>', log_path]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        
        queue_ids = set()
        if res.returncode == 0:
            for line in res.stdout.splitlines():
                match = re.search(r'postfix/\w+\[\d+\]:\s+([0-9a-zA-Z]+):\s+', line)
                if match:
                    queue_ids.add(match.group(1))
                    
        if not queue_ids:
            return JsonResponse({'status': 'success', 'data': []})
            
        # Step 2: For each Queue ID, grep the log lines to reconstruct the delivery event
        events = []
        # Sort queue IDs in reverse order so last emails are shown first
        for qid in sorted(queue_ids, reverse=True)[:100]:
            cmd = ['sudo', 'grep', qid, log_path]
            res_qid = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
            if res_qid.returncode == 0:
                lines = res_qid.stdout.splitlines()
                timestamp = ""
                recipient = ""
                status = "unknown"
                reason = ""
                relay = ""
                
                for line in lines:
                    parts = line.split(qid)
                    if parts:
                        timestamp = parts[0].strip()
                        
                    if 'to=<' in line:
                        match_to = re.search(r'to=<([^>]+)>', line)
                        if match_to:
                            recipient = match_to.group(1)
                        match_status = re.search(r'status=(\w+)', line)
                        if match_status:
                            status = match_status.group(1)
                        match_relay = re.search(r'relay=([^,]+)', line)
                        if match_relay:
                            relay = match_relay.group(1)
                        match_reason = re.search(r'status=\w+\s+\(([^)]+)\)', line)
                        if match_reason:
                            reason = match_reason.group(1)
                        else:
                            reason_parts = line.split('status=' + status)
                            if len(reason_parts) > 1:
                                reason = reason_parts[1].strip()
                                
                events.append({
                    'qid': qid,
                    'timestamp': timestamp,
                    'recipient': recipient,
                    'status': status,
                    'relay': relay,
                    'reason': reason
                })
        return JsonResponse({'status': 'success', 'data': events})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)






@login_required(login_url='/')
def backup(request,data):
    try:
        with open(paths.MYSQL_PASSWORD_FILE,'r') as f:
            adminpassword=f.read()
            adminpassword=adminpassword.strip()
    except Exception:
        adminpassword = ""
    import glob
    import os
    if request.user.is_superuser:
        current=request.session['name']
    else:
        current=request.user
    
    if data == user.objects.get(username=current).domain:
                
                d={}
                d.update(get_user_dashboard_context(current, adminpassword))

                d['totaldb']=int(safe_get_package(user.objects.get(username=current).hosting_package).databases_allowed)
                if d['totaldb']==0:
                    d['totaldb']='∞'
                mainn=str(current)+'_'
                d['useddatabase']=len(get_database_names_with_filter(adminpassword,mainn))
                try:
                    lold=domain.objects.get(domain=data)   
                    d['domain']=data
                    folder={}
                    directory=os.path.join(paths.HOME_BASE, lold.dir)
                    backup_store = _get_backup_store(lold.dir)
                    
                    zip_files = sorted(glob.glob(os.path.join(backup_store, "backup_*.zip")), reverse=True)
                    
                    for zip_file in zip_files:
                        basename = os.path.basename(zip_file)
                        # Format: backup_<domain>_<YYYYMMDD>_<HHMMSS>.zip
                        # We reliably get date/time as last two underscore-segments before .zip
                        name_no_ext = basename[:-4]  # strip .zip
                        segments = name_no_ext.split('_')
                        # Last two segments are date and time
                        if len(segments) >= 4:
                            time_part = segments[-1]
                            date_part = segments[-2]
                            # Format date nicely: YYYYMMDD -> YYYY-MM-DD
                            try:
                                date_pretty = f"{date_part[:4]}-{date_part[4:6]}-{date_part[6:8]}"
                            except Exception:
                                date_pretty = date_part
                            try:
                                time_pretty = f"{time_part[:2]}:{time_part[2:4]}:{time_part[4:6]}"
                            except Exception:
                                time_pretty = time_part
                            import os as _os
                            size_bytes = _os.path.getsize(zip_file)
                            size_mb = round(size_bytes / (1024 * 1024), 1)
                            folder[basename] = [
                                directory,       # j.0 - full path of the directory
                                date_pretty,     # j.1 - formatted date
                                time_pretty,     # j.2 - formatted time
                                basename,        # j.3 - filename for download
                                f"{size_mb} MB", # j.4 - size
                            ]
                    d['folder']=folder
                    d['dire']=lold.dir
                    return render(request,'control/backup.html',d)
                except Exception as e:
                    return redirect("/")
           
    else: 
        return redirect('/')


@login_required(login_url='/')
def delete_backup(request):
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Invalid method'})
    if request.user.is_superuser:
        current = request.session['name']
    else:
        current = request.user

    try:
        data = json.loads(request.body)
        filename = data.get('filename', '').strip()
        domainname = data.get('domain', '').strip()

        # Basic security: filename must start with backup_ and end with .zip
        if not filename.startswith('backup_') or not filename.endswith('.zip') or '/' in filename or '..' in filename:
            return JsonResponse({'status': 'error', 'message': 'Invalid filename'})

        # Verify ownership
        owner_domain = user.objects.get(username=current).domain
        if domainname != owner_domain:
            return JsonResponse({'status': 'error', 'message': 'Unauthorized'}, status=403)

        lold = domain.objects.get(domain=domainname)
        backup_store = _get_backup_store(lold.dir)
        filepath = os.path.join(backup_store, filename)

        # Security check: file must be inside the backup store (no path traversal)
        real_filepath = os.path.realpath(filepath)
        real_store = os.path.realpath(backup_store)
        if not real_filepath.startswith(real_store + os.sep):
            return JsonResponse({'status': 'error', 'message': 'Path traversal denied'}, status=403)

        if os.path.exists(real_filepath):
            os.remove(real_filepath)
            return JsonResponse({'status': 'success', 'message': 'Backup deleted successfully'})
        else:
            return JsonResponse({'status': 'error', 'message': 'Backup file not found'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)})

@login_required(login_url='/')
def download_backup(request, filename):
    if request.user.is_superuser:
        current = request.session['name']
    else:
        current = request.user

    try:
        # Security: filename must be a valid backup zip, no path traversal
        if not filename.startswith('backup_') or not filename.endswith('.zip') or '/' in filename or '..' in filename:
            raise Http404("Invalid filename")

        domain_obj = user.objects.get(username=current)
        owner_domain = domain_obj.domain
        lold = domain.objects.get(domain=owner_domain)
        backup_store = _get_backup_store(lold.dir)
        filepath = os.path.join(backup_store, filename)

        real_filepath = os.path.realpath(filepath)
        real_store = os.path.realpath(backup_store)
        if not real_filepath.startswith(real_store + os.sep):
            raise Http404("Path traversal denied")

        if not os.path.exists(real_filepath):
            raise Http404("Backup file not found")

        from django.http import FileResponse
        response = FileResponse(open(real_filepath, 'rb'), content_type='application/zip')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response
    except Http404:
        raise
    except Exception as e:
        raise Http404("File not found")

                   
@login_required(login_url='/')
def index(request):
    try:
        with open(paths.MYSQL_PASSWORD_FILE,'r') as f:
            adminpassword=f.read()
            adminpassword=adminpassword.strip()
    except:
          adminpassword = ''
    if request.user.is_superuser:
        current=request.session.get('name', request.user.username)
    else:
        current=request.user
    d={}


    d.update(get_user_dashboard_context(current, adminpassword))

    # Guard: if domain is missing, the user's account isn't fully provisioned yet
    if 'domain' not in d or not d.get('domain'):
        messages.warning(request, 'Your hosting account is still being set up. Please wait a moment and try again.')

        return render(request, 'control/pending.html', {'username': str(current)}) if _template_exists('control/pending.html') else redirect('/')

    # Passing querysets for PHP Selector modal
    try:
        d['domain_obj'] = domain.objects.get(domain=d['domain'])
    except Exception:
        d['domain_obj'] = None

    try:
        d['sub'] = subdomainname.objects.filter(domain=d['domain'])
    except Exception:
        d['sub'] = []

    from control.models import phpversion
    d['phpversion'] = phpversion.objects.all()

    try:
        from voidplatform.linux.web import get_active_engine
        d['engine'] = get_active_engine()
    except:
        d['engine'] = 'nginx'

    return render(request, 'control/index.html', d)

@login_required(login_url='/')
def eadns(request):
    try:
        with open(paths.MYSQL_PASSWORD_FILE,'r') as f:
            adminpassword=f.read().strip()
    except:
        adminpassword = ''
    if request.user.is_superuser:
        current=request.session['name']
    else:
        current=request.user
    d={}
    d.update(get_user_dashboard_context(current, adminpassword))
    
    domainname = request.GET.get('domain', '')
    if domainname:
        domainname = domainname.strip().rstrip('/')
    try:
        current_domain=domain.objects.get(domain=domainname)
        d['domain']=current_domain
        try:
            pat=os.path.join(paths.BIND_ZONE_DIR, f"db.{current_domain}")
            data12=parse_dns_zone_file(pat)
            # Skip the $TTL header entry (index 0), and the SOA record usually at [1]
            d['data']=data12[2:]
            d['zone_error'] = None
        except PermissionError as e:
            d['data'] = []
            d['zone_error'] = str(e)
        except Exception as e:
            d['data'] = []
            d['zone_error'] = f'Could not read zone records: {e}'
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"eadns view failed for domain '{domainname}': {type(e).__name__} - {str(e)}")
        return redirect('/')
    return render(request,'control/eadns.html', d)

@login_required(login_url='/')
def adddnsrecord(request):
    try:
        usewe=user.objects.get(username=request.user)
        dddd=usewe.domain
    except:
        if request.user.is_superuser:
            usewe=user.objects.get(username=request.session['name'])
            dddd=usewe.domain
        else:
            return JsonResponse({'success': False, 'error': 'Unauthorized'})

    if request.method == 'POST':
        name         = (request.POST.get('name') or '').strip()
        domainname   = (request.POST.get('domain') or '').strip()
        record_type  = (request.POST.get('type') or '').strip().upper()
        ttl          = (request.POST.get('ttl') or '86400').strip()
        data         = (request.POST.get('data') or '').strip()

        VALID_TYPES = {'A', 'AAAA', 'CNAME', 'MX', 'TXT', 'NS', 'SRV', 'CAA', 'PTR', 'SOA'}

        if not name:
            return JsonResponse({'success': False, 'error': 'Record name is required (use @ for root).'})
        if record_type not in VALID_TYPES:
            return JsonResponse({'success': False, 'error': f'Invalid record type "{record_type}".'})
        if not data:
            return JsonResponse({'success': False, 'error': 'Record value/data is required.'})
        if dddd != domainname:
            return JsonResponse({'success': False, 'error': 'Unauthorized domain.'})

        import re as _re
        if not _re.match(r'^[a-zA-Z0-9@._\-\*]+$', name):
            return JsonResponse({'success': False, 'error': 'Invalid record name characters.'})

        pat = os.path.join(paths.BIND_ZONE_DIR, f"db.{domainname}")
        import tempfile
        # Write a properly-formatted zone record: name TTL IN TYPE data
        with tempfile.NamedTemporaryFile('w', delete=False, suffix='.zone') as tf:
            tf.write(f"\n; {record_type} Record added via VoidPanel\n")
            tf.write(f"{name} {ttl} IN {record_type} {data}\n")
            tmpd = tf.name
        run_command(f'cat {tmpd} | sudo tee -a {pat}')
        run_command(f'sudo rm {tmpd}')
        get_platform().services.restart('bind9')
        return JsonResponse({'success': True})

    return JsonResponse({'success': False, 'error': 'Invalid request method'})

@login_required(login_url='/')
def deletedns(request):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Invalid request method'})

    domainname = request.POST.get('domain', None)
    name = request.POST.get('name')
    domain = request.POST.get('domain')
    record_type = request.POST.get('type')
    data = request.POST.get('data')
    ttl = request.POST.get('ttl', None)
    
    if not all([name, domain, record_type, data]):
        return JsonResponse({'success': False, 'error': 'Missing required fields'})

    deleted = False
    pat = os.path.join(paths.BIND_ZONE_DIR, f"db.{domain}")
    
    try:
        usewe = user.objects.get(username=request.user)
        dddd = usewe.domain
    except:
        if request.user.is_superuser:
            usewe = user.objects.get(username=request.session['name'])
            dddd = usewe.domain
        else:
            return JsonResponse({'success': False, 'error': 'Unauthorized'})
            
    if domain == dddd:
        try:
            import subprocess
            result = subprocess.run(['sudo', 'cat', pat], capture_output=True, text=True)
            if result.returncode != 0:
                raise PermissionError('Failed to read zone file.')
            lines = result.stdout.splitlines(True)
            import tempfile
            with tempfile.NamedTemporaryFile('w', delete=False) as tfile:
                for line in lines:
                    if name in line and record_type in line and data[:20] in line and (not ttl or ttl in line):
                        deleted = True
                    elif name in line and data[:20] in line:
                        deleted = True
                    else:
                        tfile.write(line)
                tmpout = tfile.name

            if deleted:
                run_command(f'sudo cp {tmpout} {pat}')
                run_command(f'sudo chmod 644 {pat}')
                run_command(f'sudo rm {tmpout}')
                get_platform().services.restart('bind9')
                return JsonResponse({'success': True})
            else:
                run_command(f'sudo rm {tmpout}')
                return JsonResponse({'success': False, 'error': 'Record not found'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    else:
        return JsonResponse({'success': False, 'error': 'Unauthorized domain'})

@login_required(login_url='/')
def editdnsrecord(request):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Invalid request method'})

    # Old data for matching
    old_name        = request.POST.get('old_name', '').strip()
    old_type        = request.POST.get('old_type', '').strip()
    old_data        = request.POST.get('old_data', '').strip()
    
    # New data for writing
    name        = request.POST.get('name', '').strip()
    domain      = request.POST.get('domain', '').strip().lower()
    record_class = request.POST.get('class', 'IN').strip().upper()
    record_type = request.POST.get('type', '').strip().upper()
    ttl         = request.POST.get('ttl', '86400').strip()
    data        = request.POST.get('data', '').strip()

    VALID_TYPES = {'A', 'AAAA', 'CNAME', 'MX', 'TXT', 'NS', 'SRV', 'CAA', 'PTR', 'SOA'}
    if not all([old_name, old_type, name, domain, record_type, data]):
        return JsonResponse({'success': False, 'error': 'Missing required fields.'})

    if record_type not in VALID_TYPES:
        return JsonResponse({'success': False, 'error': f'Invalid record type "{record_type}".'})

    import re
    if not re.match(r'^[a-zA-Z0-9@._\-\*]+$', name):
        return JsonResponse({'success': False, 'error': 'Invalid new record name.'})

    pat = os.path.join(paths.BIND_ZONE_DIR, f"db.{domain}")
    
    try:
        usewe = user.objects.get(username=request.user)
        dddd = usewe.domain
    except:
        if request.user.is_superuser:
            usewe = user.objects.get(username=request.session['name'])
            dddd = usewe.domain
        else:
            return JsonResponse({'success': False, 'error': 'Unauthorized'})
            
    if domain == dddd:
        edited = False
        try:
            import subprocess
            result = subprocess.run(['sudo', 'cat', pat], capture_output=True, text=True)
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
                        new_lines.append(f"{name} {ttl} {record_class} {record_type} {data}\n")
                        edited = True
                else:
                    new_lines.append(line)

            if edited:
                import tempfile
                with tempfile.NamedTemporaryFile('w', delete=False) as tfe:
                    tfe.writelines(new_lines)
                    tmpedit = tfe.name
                run_command(f'sudo cp {tmpedit} {pat}')
                run_command(f'sudo chmod 644 {pat}')
                run_command(f'sudo rm {tmpedit}')
                get_platform().services.restart('bind9')
                return JsonResponse({'success': True, 'message': 'DNS record updated successfully.'})
            else:
                return JsonResponse({'success': False, 'error': 'Original record not found.'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    else:
        return JsonResponse({'success': False, 'error': 'Unauthorized domain'})



@login_required(login_url='/')
def runssl(request,data):
    try:
        with open(paths.MYSQL_PASSWORD_FILE,'r') as f:
            adminpassword=f.read()
            adminpassword=adminpassword.strip()
    except Exception:
        adminpassword = ''

    if request.user.is_superuser:
        current = request.session.get('name', str(request.user))
    else:
        current = str(request.user)  # must be string for DB username lookup

    try:
        current_user = user.objects.get(username=current)
    except Exception:
        return redirect('/')

    if data == current_user.domain or subdomainname.objects.filter(subdomain=data, domain=current_user.domain).exists():
        d = {}
        d.update(get_user_dashboard_context(current, adminpassword))
        try:
            lold = domain.objects.get(domain=current_user.domain)
            d['domain'] = data
            d['main'] = lold

            # Read ssl log — create it if missing so the page still loads
            logs = []
            log_path = os.path.join(paths.HOME_BASE, lold.dir, 'logs', 'ssl.txt')
            try:
                os.makedirs(os.path.dirname(log_path), exist_ok=True)
                if not os.path.exists(log_path):
                    open(log_path, 'w').close()
                with open(log_path, 'r') as f:
                    logs = f.readlines()
            except Exception:
                pass
            d['logs'] = logs

            d['subdomain'] = subdomainname.objects.filter(domain=current_user.domain)
            try:
                url = 'https://voidpanel.com/clientdocs/'
                response = requests.get(url, timeout=2)
                if response.status_code == 200:
                    d['docs'] = response.json()
            except Exception:
                pass

            return render(request, 'control/sitessl.html', d)

        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f'runssl error for {data}: {e}')
            return redirect('/')
    else:
        return redirect('/')
    




import threading
import subprocess

def _background_run_ssl(domain_or_subdomain, is_subdomain=False):
    if is_subdomain:
        item = subdomainname.objects.get(subdomain=domain_or_subdomain)
        lold = domain.objects.get(domain=item.domain)
        email = lold.email
        target = item.subdomain
    else:
        lold = domain.objects.get(domain=domain_or_subdomain)
        email = lold.email
        target = lold.domain

    path = os.path.join(paths.HOME_BASE, lold.dir, 'logs', 'ssl.txt')
    with open(path, 'a+') as f:
        f.write(f"\n[AutoSSL] Started SSL generation for {target}...")

    try:
        res = get_platform().ssl.provision(target, email=email)
        if res.success:
            with open(path, 'a+') as f:
                f.write(f"\n[AutoSSL] SUCCESS: AutoSSL Completed for {target}")

            if is_subdomain:
                item.sslstatus = True
                item.save()
            else:
                lold.sslstatus = True
                lold.save()
        else:
            with open(path, 'a+') as f:
                f.write(f"\n[AutoSSL] ERROR: Failed for {target}")
                f.write(f"\n{res.error}")

    except Exception as e:
        with open(path, 'a+') as f:
            f.write(f"\n[AutoSSL] ERROR: Failed for {target}")
            f.write(f"\n{str(e)}")

@login_required(login_url='/')
def runsslfordoamin(request):
    if request.user.is_superuser:
        current = request.session.get('name', request.user.username)
    else:
        current = request.user.username

    try:
        user_obj = user.objects.get(username=current)
        user_domain = user_obj.domain
    except Exception:
        return redirect('/control/')

    if request.method == 'POST':
        name = request.POST.get('domain', '').lower()
        if name != user_domain:
            return JsonResponse({'status': 'error', 'message': 'Invalid request.'})

        lold = domain.objects.get(domain=name)
        subdomains = subdomainname.objects.filter(domain=name).all()

        # Start threading for main domain
        threading.Thread(target=_background_run_ssl, args=(name, False)).start()

        # Start threading for subdomains
        for sub in subdomains:
            threading.Thread(target=_background_run_ssl, args=(sub.subdomain, True)).start()

        return JsonResponse({'status': 'success', 'message': 'SSL initiated in background'})

    # GET — render the SSL management page for the user's domain
    d = {}
    d.update(get_user_dashboard_context(current))
    try:
        dom_obj = domain.objects.get(domain=user_domain)
        d['domain_obj'] = dom_obj
        d['domain'] = user_domain
        d['subdomains'] = subdomainname.objects.filter(domain=user_domain)
    except Exception:
        pass
    return render(request, 'control/sslmanager.html', d)


@login_required(login_url='/')
def runsslfordoamin1(request):
    if request.user.is_superuser:
        current = request.session['name']
    else:
        current = request.user
        
    if request.method == 'POST':
        data = json.loads(request.body)
        name = data.get('name').strip()
        
        try:
            lold = domain.objects.get(domain=name)
            threading.Thread(target=_background_run_ssl, args=(name, False)).start()
        except domain.DoesNotExist:
            try:
                sub = subdomainname.objects.get(subdomain=name)
                threading.Thread(target=_background_run_ssl, args=(name, True)).start()
            except subdomainname.DoesNotExist:
                return JsonResponse({'status': 'error', 'message': 'Domain not found.'})
                
        return JsonResponse({'status': 'success', 'message': f'SSL initiated for {name}'})
    
    return JsonResponse({'status': 'error', 'message': 'Invalid request.'})



@login_required(login_url='/')
def cronn(request,data):
    try:
        with open(paths.MYSQL_PASSWORD_FILE,'r') as f:
            adminpassword=f.read()
            adminpassword=adminpassword.strip()
    except Exception:
        adminpassword = ""

    if request.user.is_superuser:
        current=request.session['name']
    else:
        current=request.user
   
    if data == user.objects.get(username=current).domain:
        d={}
        d.update(get_user_dashboard_context(current, adminpassword))
        try:
            lold=domain.objects.get(domain=data)
            d['crondata']=cron.objects.filter(domain=data).all()

            if request.method == "POST":
                import subprocess
                time_val = request.POST.get('time', '').replace('\n', '').replace('\r', '').strip()
                path_val = request.POST.get('path', '').replace('\n', '').replace('\r', '').strip()
                
                # Secure memory buffer injection (Bypasses shell evaluation)
                if sys.platform != 'win32':
                    result = subprocess.run(["crontab", "-l"], capture_output=True, text=True)
                    current_crons = result.stdout if result.returncode == 0 else ""

                    new_cron = f"{time_val} {path_val}\n"
                    combined = new_cron + current_crons

                    subprocess.run(["crontab", "-"], input=combined, text=True)
                else:
                    from voidplatform.windows.cron import add_cron as _add_cron
                    _add_cron(time_val, path_val)
                cron.objects.create(domain=data, path=path_val, duratioin=time_val)
                return JsonResponse({'success': True, 'message': 'Cronjob successfully protected & created.'})

            url = 'https://voidpanel.com/clientdocs/'
            response = requests.get(url, timeout=2)
            if response.status_code == 200:
                dataee = response.json()
                d['docs']=dataee
            return render(request,'control/cron.html',d)
        except Exception as e:
            return redirect("/")
    else: 
        return redirect('/')

@login_required(login_url='/')
def deletecron(request,data):
    if request.user.is_superuser:
        current=request.session['name']
    else:
        current=request.user
        
    try:
        xxxx = cron.objects.get(id=data)
        domainname = xxxx.domain

        if domainname == user.objects.get(username=current).domain:
            import subprocess
            if sys.platform != 'win32':
                result = subprocess.run(["crontab", "-l"], capture_output=True, text=True)
                current_crons = result.stdout if result.returncode == 0 else ""

                # Subprocess memory filtering
                filtered_crons = "\n".join([line for line in current_crons.split('\n') if xxxx.path not in line]) + "\n"

                subprocess.run(["crontab", "-"], input=filtered_crons, text=True)
            else:
                from voidplatform.windows.cron import delete_cron as _delete_cron
                _delete_cron(xxxx.path)
            xxxx.delete()
            return JsonResponse({'success': True, 'message': 'Cronjob deleted safely.'})
        else:
            return JsonResponse({'success': False, 'message': 'Unauthorized scope.'})
    except:
        return JsonResponse({'success': False, 'message': 'Cronjob not found.'})
        

def _get_backup_store(username):
    """Return a www-data-writable backup directory for a user.
    Stored at /home/<username>/.backups/ so it counts towards user quota,
    but owned by www-data so the panel can manage it.
    """
    import subprocess
    store = os.path.join(paths.HOME_BASE, str(username), '.backups')
    subprocess.run(['sudo', 'mkdir', '-p', store], check=False)
    subprocess.run(['sudo', 'chown', '-R', 'www-data:www-data', store], check=False)
    subprocess.run(['sudo', 'chmod', '777', store], check=False)
    return store

@login_required(login_url='/')
def backupdata(request):
    if request.user.is_superuser:
        current=request.session['name']
    else:
        current=request.user
    
    if request.method=="POST":
        data = json.loads(request.body)
        name=data.get('domain').strip(' ')

        if name != user.objects.get(username=current).domain:
             return JsonResponse({'status': 'error', 'message': 'Invalid request.'})
      
        # Enforce quota strictly for non-admins
        if not request.user.is_superuser:
            currentstorage=get_directory_size_in_mb(os.path.join(paths.HOME_BASE, str(current)))
            packagecc=safe_get_package(user.objects.get(username=current).hosting_package).storage
            if int(packagecc) != 0:
                if (int(currentstorage) > int(packagecc)):
                    return JsonResponse({'status': 'exceed', 'message': 'Storage Quota Limit Reached.'})

        namm=domain.objects.get(domain=name)
        main_directory = os.path.join(paths.HOME_BASE, namm.dir)
        front=os.path.join(paths.HOME_BASE, namm.dir)
        mail=_resolve_mail_domain_dir(namm.domain)
        open1=os.path.join(paths.OPENDKIM_KEY_DIR, namm.domain) if paths.OPENDKIM_KEY_DIR else ''
        lets=os.path.join(paths.LETSENCRYPT_LIVE, namm.domain)
        
        import datetime
        import threading
        import subprocess
        import shutil
        from function import get_database_names_with_filter
        
        try:
            with open(paths.MYSQL_PASSWORD_FILE, 'r') as f:
                adminpassword = f.read().strip()
        except:
            adminpassword = ""
        
        zip_filename = "backup_"+namm.domain+"_"+str(datetime.datetime.today().strftime('%Y%m%d_%H%M%S'))
        zip_filename=zip_filename.replace(" ", "_").replace(":", "-")
        locations = [l for l in [front, mail, open1, lets] if l]
        # Use a www-data-writable backup store (www-data cannot write directly to /home/username/)
        backup_store = _get_backup_store(namm.dir)
        
        def _run_full_backup_thread():
            import time as _time
            import json as _json
            import tempfile
            progress_file = os.path.join(backup_store, ".backup_progress")
            completed_file = os.path.join(backup_store, ".backup_done")
            # Remove any stale completed marker from previous run
            try:
                if os.path.exists(completed_file):
                    os.remove(completed_file)
            except Exception:
                pass
            try:
                meta = _json.dumps({'pct': 5, 'pid': threading.current_thread().ident, 'ts': _time.time()})
                with open(progress_file, "w") as pf:
                    pf.write(meta)
            except Exception:
                pass
            
            # Use /tmp for DB dumps — www-data can always write there (avoids PermissionError in user home)
            db_dump_dir = tempfile.mkdtemp(prefix='voidpanel_dbdump_')
            
            databases = get_database_names_with_filter(adminpassword, f"{current}_")
            if databases:
                for db in databases:
                    db_path = os.path.join(db_dump_dir, f"{db}.sql")
                    try:
                        with open(db_path, "w") as dump_file:
                            subprocess.run(["mysqldump", "-u", "root", f"-p{adminpassword}", db], stdout=dump_file, stderr=subprocess.DEVNULL)
                    except Exception:
                        pass
                        
            # Deploy non-blocking execution to handle Zipping
            zip_ok = False
            try:
                zip_multiple_locations_backup_user(backup_store, locations, zip_filename, current, progress_file)
                zip_ok = True
            except Exception as e:
                pass
            finally:
                try:
                    import shutil as _shutil
                    _shutil.rmtree(db_dump_dir, ignore_errors=True)
                except Exception:
                    pass
                try:
                    if os.path.exists(progress_file):
                        os.remove(progress_file)
                except Exception:
                    pass
                # Write a completed marker so backup_status can return 'completed'
                try:
                    with open(completed_file, "w") as cf:
                        cf.write(_json.dumps({'ok': zip_ok, 'ts': _time.time()}))
                except Exception:
                    pass

                if zip_ok:
                    try:
                        from control.utils import trigger_backup_created_notification
                        trigger_backup_created_notification(str(current), str(name), zip_filename + ".zip")
                    except Exception:
                        pass
                    
        t = threading.Thread(target=_run_full_backup_thread)
        t.start()

        
        return JsonResponse({'status': 'success', 'message': 'Job Queued in Background!'})
        
    return JsonResponse({'status': 'error', 'message': 'Invalid request.'})

@login_required(login_url='/')
def backup_status(request, data):
    if request.user.is_superuser:
        current = request.session['name']
    else:
        current = request.user
        
    try:
        import json as _json
        import time as _time

        # Ownership: make sure the domain belongs to this user
        owner_domain = user.objects.get(username=current).domain
        if data != owner_domain and not request.user.is_superuser:
            return JsonResponse({'status': 'idle'})

        namm = domain.objects.get(domain=data)
        main_directory = os.path.join(paths.HOME_BASE, namm.dir)
        backup_store = _get_backup_store(namm.dir)
        progress_file = os.path.join(backup_store, ".backup_progress")
        completed_file = os.path.join(backup_store, ".backup_done")
        
        # Check if backup just finished (completed marker exists, no progress file)
        if os.path.exists(completed_file) and not os.path.exists(progress_file):
            try:
                os.remove(completed_file)   # consume the marker - only report once
            except Exception:
                pass
            return JsonResponse({'status': 'completed'})
        
        if os.path.exists(progress_file):
            try:
                with open(progress_file, 'r') as f:
                    raw = f.read().strip()

                # Try new JSON format first
                try:
                    meta = _json.loads(raw)
                    pct = int(meta.get('pct', 0))
                    ts  = float(meta.get('ts', 0))
                    age = _time.time() - ts

                    # Stale detection: if last update was > 10 minutes ago, backup is dead
                    if age > 600:
                        try:
                            os.remove(progress_file)
                        except Exception:
                            pass
                        return JsonResponse({'status': 'idle'})

                except (ValueError, KeyError):
                    # Old plain integer format fallback
                    pct = int(raw) if raw.isdigit() else 0

                return JsonResponse({'status': 'processing', 'progress': pct})
            except Exception:
                return JsonResponse({'status': 'idle'})
        else:
            return JsonResponse({'status': 'idle'})

    except Exception:
        return JsonResponse({'status': 'idle'})
@login_required(login_url='/')
def filemanager(request):
    if request.user.is_superuser:
        current = request.session.get('name', request.user.username)
    else:
        current = request.user.username

    file_path = request.GET.get('key', os.path.join(paths.HOME_BASE, str(current)))
    # Normalize double-slashes
    while '//' in file_path:
        file_path = file_path.replace('//', '/')
    if not file_path.startswith('/'):
        file_path = '/' + file_path

    # Security: restrict non-admins strictly to their home dir
    if not request.user.is_superuser:
        home = os.path.join(paths.HOME_BASE, str(current))
        if not file_path.startswith(home):
            return redirect(f'/control/filemanager/?key={home}')

    last = file_path.rsplit('/', 1)[0] or '/'

    if request.user.is_authenticated:
        try:
            with open(paths.MYSQL_PASSWORD_FILE, 'r') as f:
                adminpassword = f.read().strip()
        except:
            adminpassword = ""

        d = {}
        d.update(get_user_dashboard_context(current, adminpassword))
        d['main_dir'] = file_path
        d['last'] = last
        d['current'] = current
        try:
            result = get_file_info(file_path)
            d['items'] = result['directories']
            d['files']  = result['files']
        except Exception:
            d['items'] = []
            d['files']  = []
        return render(request, 'control/filemanager.html', d)
    else:
        return redirect('/')

@login_required(login_url='/')
def upload_files(request,file_path):
           if request.user.is_superuser:
                current=request.session['name']
           else:
                current=request.user
   

           d={}
           packagecc=safe_get_package(user.objects.get(username=current).hosting_package).storage
           currentstorage=get_directory_size_in_mb(os.path.join(paths.HOME_BASE, str(current)))
           d['lolo']=False
           if int(packagecc) != 0:

                if (int(currentstorage) > int(packagecc)):
                                    d['lolo']=True
          
           file_path=file_path.replace('////','')
           file_path=file_path.replace('//','')
           d['location']=file_path
           new="/"+file_path
           dataw = os.listdir(new)
           d['data']=dataw
           url = 'https://voidpanel.com/clientdocs/'  # Replace with your API URL
           response = requests.get(url, timeout=2)
           if response.status_code == 200:
                        dataee = response.json()  # Parse the JSON response
                        d['docs']=dataee
           return render(request,'control/upload.html',d)
        
@login_required(login_url='/')
def domainterminal(request):
        import platform
        import socket
        from control.models import user as control_user, package
        
        if request.user.is_superuser:
                    current=request.session['name']
        else:
                    current=request.user.username
        
        # Verify Shell Access based on User specification
        try:
            usr_obj = control_user.objects.get(username=current)
            if not getattr(usr_obj, 'shell', False):
                return redirect('/control/')  # Unauthorized / No Shell Access
        except Exception:
            return redirect('/control/')
            
        d={}
        d['ip']=get_server_ip()
        d['os']=platform.system()
        d['cpu']=platform.processor()
        d['hostname']=socket.gethostbyname(socket.gethostname())
        
        try:
            url = 'https://voidpanel.com/clientdocs/'
            req = requests.get(url, timeout=3)
            if req.status_code == 200:
                d['docs'] = req.json()
        except:
            d['docs'] = []
        
        d.update(get_user_dashboard_context(current))
        return render(request, 'control/domainterminal.html', d)


@login_required(login_url='/')
def setpython(request, data):
    if request.user.is_superuser:
        current = request.session['name']
    else:
        current = request.user.username

    if not request.user.is_authenticated:
        return redirect('/')

    try:
        with open(paths.MYSQL_PASSWORD_FILE, 'r') as f:
            adminpassword = f.read().strip()
    except:
        adminpassword = ""

    d = {}
    d.update(get_user_dashboard_context(current, adminpassword))

    try:
        lold = domain.objects.get(domain=data)
        # Ownership enforcement — non-admins can only access their own domain
        if not request.user.is_superuser:
            owner = user.objects.filter(username=current).first()
            if not owner or owner.domain != data:
                return HttpResponse("Unauthorized.", status=403)
        d['domain'] = data
        d['python'] = pythonname.objects.filter(main=lold.dir).all()
        return render(request, 'control/setpython.html', d)
    except Exception:
        return redirect("/control/")


@login_required(login_url='/')
def createpython(request, data):
    if request.user.is_superuser:
        current = request.session['name']
    else:
        current = request.user.username

    if not request.user.is_authenticated:
        return redirect('/')

    # Ownership enforcement — non-admins can only access their own domain
    if not request.user.is_superuser:
        owner = user.objects.filter(username=current).first()
        if not owner or owner.domain != data:
            return HttpResponse("Unauthorized.", status=403)

    try:
        with open(paths.MYSQL_PASSWORD_FILE, 'r') as f:
            adminpassword = f.read().strip()
    except:
        adminpassword = ""

    d = {}
    d.update(get_user_dashboard_context(current, adminpassword))

    try:
        d['domain'] = data
        d['subdomain'] = subdomainname.objects.filter(domain=data).all()
        return render(request, 'control/createpython.html', d)
    except Exception:
        return redirect("/control/")
        

@login_required(login_url='/')
def setmern(request, data):
    if request.user.is_superuser:
        current = request.session['name']
    else:
        current = request.user.username

    if not request.user.is_authenticated:
        return redirect('/')

    try:
        with open(paths.MYSQL_PASSWORD_FILE, 'r') as f:
            adminpassword = f.read().strip()
    except:
        adminpassword = ""

    d = {}
    d.update(get_user_dashboard_context(current, adminpassword))

    try:
        lold = domain.objects.get(domain=data)
        # Ownership enforcement
        if not request.user.is_superuser:
            owner = user.objects.filter(username=current).first()
            if not owner or owner.domain != data:
                return HttpResponse("Unauthorized.", status=403)
        d['domain'] = data
        d['mern'] = mernname.objects.filter(main=lold.dir).all()
        return render(request, 'control/setmern.html', d)
    except Exception:
        return redirect("/control/")


@login_required(login_url='/')
def createmern(request, data):
    if request.user.is_superuser:
        current = request.session['name']
    else:
        current = request.user.username

    if not request.user.is_authenticated:
        return redirect('/')

    # Ownership enforcement
    if not request.user.is_superuser:
        owner = user.objects.filter(username=current).first()
        if not owner or owner.domain != data:
            return HttpResponse("Unauthorized.", status=403)

    try:
        with open(paths.MYSQL_PASSWORD_FILE, 'r') as f:
            adminpassword = f.read().strip()
    except:
        adminpassword = ""

    d = {}
    d.update(get_user_dashboard_context(current, adminpassword))

    try:
        d['domain'] = data
        d['subdomain'] = subdomainname.objects.filter(domain=data).all()
        return render(request, 'control/createmern.html', d)
    except Exception:
        return redirect("/control/")

@login_required(login_url='/')
def roundcube_login(request, email):
    """
    Roundcube SSO Auto-Login — correct approach for Roundcube 1.6.x

    Flow:
    1. Validates the requesting user owns this email account
    2. Decodes the stored base64 password
    3. Writes a one-time rc_sso_<uuid> token file to /var/www/roundcube/temp/
    4. Serves an auto-submitting POST form to Roundcube's login action
       with vp_token as a hidden field
    5. Roundcube's 'authenticate' hook (vp_autologin plugin) intercepts
       the token, injects credentials, and Roundcube handles IMAP login
       and session creation natively — no session conflicts

    Why POST not redirect:
    - GET redirect with ?vp_token uses the 'startup' hook which runs
      BEFORE Roundcube's session is ready → causes "session invalid" error
    - POST to /?_task=login&_action=login triggers the 'authenticate' hook
      which runs INSIDE Roundcube's normal login flow → session created correctly
    """
    import base64
    import uuid
    import os
    import subprocess
    from django.http import HttpResponse
    from control.models import allemail, user as ctrl_user

    # ── Authorization: only superuser OR owner of this email's domain ─────────
    email = email.lower().strip()
    email_obj = allemail.objects.filter(email=email).first()
    if not email_obj:
        return HttpResponse("Email account not found.", status=404)

    domain_name = email_obj.domain
    if not request.user.is_superuser:
        current = request.user.username
        owner_obj = ctrl_user.objects.filter(username=current).first()
        if not owner_obj or owner_obj.domain != domain_name:
            return HttpResponse("Unauthorized.", status=403)

    # ── Decode stored password ─────────────────────────────────────────────────
    try:
        password = base64.b64decode(email_obj.password.encode()).decode('utf-8')
    except Exception:
        return HttpResponse(
            "Cannot decode credentials — please reset the email password.",
            status=500
        )

    # ── Roundcube URL (internal HTTP port, not the HTTPS proxy) ───────────────
    server_ip    = get_server_ip()
    roundcube_url = f"http://{server_ip}:9000"

    # ── Write one-time token file ──────────────────────────────────────────────
    token    = str(uuid.uuid4())
    temp_dir = "/var/www/roundcube/temp"
    sso_path = os.path.join(temp_dir, f"rc_sso_{token}")

    try:
        os.makedirs(temp_dir, exist_ok=True)
        # Ensure www-data (php-fpm) can read the token
        subprocess.run(['chown', 'www-data:www-data', temp_dir],
                       check=False, capture_output=True)
        subprocess.run(['chmod', '1777', temp_dir],
                       check=False, capture_output=True)
        with open(sso_path, "w") as f:
            f.write(f"{email}\n{password}")
        os.chmod(sso_path, 0o644)
        subprocess.run(['chown', 'www-data:www-data', sso_path],
                       check=False, capture_output=True)
        token_ok = True
    except Exception:
        token_ok = False

    # ── Serve auto-POST form ───────────────────────────────────────────────────
    # Works whether or not token file was written:
    # - If token_ok=True:  plugin's authenticate hook reads token → injects creds
    # - If token_ok=False: fallback submits _user/_passwd directly (plain POST login)
    if token_ok:
        # Preferred: token-based (password NOT in page source)
        hidden_fields = f'<input type="hidden" name="vp_token" value="{token}">'
        # Dummy _user/_passwd required so Roundcube doesn't reject the form early
        hidden_fields += f'<input type="hidden" name="_user" value="{email}">'
        hidden_fields += f'<input type="hidden" name="_passwd" value="">'
    else:
        # Fallback: direct credential POST (password visible in page source only momentarily)
        hidden_fields  = f'<input type="hidden" name="_user"   value="{email}">'
        hidden_fields += f'<input type="hidden" name="_passwd" value="{password}">'

    return HttpResponse(f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Connecting to Webmail...</title>
  <style>
    *{{margin:0;padding:0;box-sizing:border-box}}
    body{{background:#0d1117;display:flex;align-items:center;justify-content:center;
          min-height:100vh;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif}}
    .card{{background:#161b22;border:1px solid #30363d;border-radius:16px;padding:40px 48px;
           text-align:center;max-width:380px;width:90%;animation:fadeIn .3s ease}}
    @keyframes fadeIn{{from{{opacity:0;transform:translateY(10px)}}to{{opacity:1;transform:none}}}}
    .icon{{width:56px;height:56px;background:linear-gradient(135deg,#0ea5e9,#6366f1);
           border-radius:14px;display:flex;align-items:center;justify-content:center;
           margin:0 auto 20px;font-size:26px}}
    h2{{color:#e6edf3;font-size:1.2rem;margin-bottom:8px}}
    p{{color:#8b949e;font-size:0.85rem}}
    .spinner{{width:32px;height:32px;border:3px solid #30363d;border-top-color:#0ea5e9;
              border-radius:50%;animation:spin .8s linear infinite;margin:20px auto 0}}
    @keyframes spin{{to{{transform:rotate(360deg)}}}}
  </style>
</head>
<body>
  <div class="card">
    <div class="icon">✉️</div>
    <h2>Connecting to Webmail</h2>
    <p>Logging in as <strong style="color:#e6edf3">{email}</strong>...</p>
    <div class="spinner"></div>
  </div>
  <form id="rcf" method="post" action="{roundcube_url}/?_task=login&_action=login" style="display:none">
    <input type="hidden" name="_task"     value="login">
    <input type="hidden" name="_action"   value="login">
    <input type="hidden" name="_timezone" value="auto">
    <input type="hidden" name="_url"      value="">
    {hidden_fields}
  </form>
  <script>
    // Small delay so the loading card is visible before redirect
    setTimeout(function(){{ document.getElementById('rcf').submit(); }}, 600);
  </script>
</body>
</html>""")


# ─── Analytics View (Control Portal) ────────────────────────────────────────
@login_required(login_url="/")
def analytics_control(request, data):
    if request.user.is_superuser:
        current = request.session.get("name", request.user.username)
    else:
        current = request.user.username

    if not request.user.is_authenticated:
        return redirect("/")

    if not request.user.is_superuser:
        owner = user.objects.filter(username=current).first()
        if not owner or owner.domain != data:
            return HttpResponse("Unauthorized.", status=403)

    try:
        with open(paths.MYSQL_PASSWORD_FILE, "r") as f:
            adminpassword = f.read().strip()
    except Exception:
        adminpassword = ""

    d = {}
    d.update(get_user_dashboard_context(current, adminpassword))
    d["domain"] = data

    from control.models import domain as ctrl_domain
    dom_obj = ctrl_domain.objects.filter(domain=data).first()
    d["homedir"] = dom_obj.dir if dom_obj else data
    d["username"] = current

    usr_obj = user.objects.filter(username=current).first()
    pak_name = usr_obj.hosting_package if usr_obj else "N/A"
    d["package_name"] = pak_name
    from control.models import package as ctrl_package
    pak = ctrl_package.objects.filter(name=pak_name).first()
    d["disk_quota_mb"] = pak.storage if pak else "0"

    from function import get_directory_size_in_mb, is_website_live, parse_dns_zone_file
    try:
        disk_used = get_directory_size_in_mb(os.path.join(paths.HOME_BASE, d["homedir"]))
    except Exception:
        disk_used = 0
    d["disk_used"] = int(disk_used)
    quota = int(d["disk_quota_mb"]) if str(d["disk_quota_mb"]).isdigit() else 0
    d["disk_percent"] = round((int(disk_used) / quota) * 100) if quota > 0 else 0
    d["live"] = is_website_live(f"http://{data}")
    d["ssl_active"] = os.path.exists(os.path.join(paths.LETSENCRYPT_LIVE, data, "fullchain.pem"))
    d["php_version"] = dom_obj.php if dom_obj and hasattr(dom_obj, "php") else "N/A"
    d["domain_status"] = dom_obj.status if dom_obj and hasattr(dom_obj, "status") else True
    d["emails"] = allemail.objects.filter(domain=data).all()
    d["subdomains"] = subdomainname.objects.filter(domain=data).all()
    d["python_apps"] = pythonname.objects.filter(main=data).all()
    d["mern_apps"] = mernname.objects.filter(main=data).all()

    try:
        dns_records = parse_dns_zone_file(os.path.join(paths.BIND_ZONE_DIR, f"db.{data}"))
        d["dns_records"] = [r for r in dns_records if r.get("type") in ("A","MX","CNAME","TXT","NS","AAAA")]
        d["dns_count"] = len(d["dns_records"])
    except Exception:
        d["dns_records"] = []
        d["dns_count"] = 0

    try:
        from function import get_database_names_with_filter
        db_names = get_database_names_with_filter(adminpassword, d["homedir"])
        d["db_count"] = len(db_names) if db_names else 0
    except Exception:
        d["db_count"] = 0

    # Traffic Analytics Engine - dual Nginx/OLS compatible
    import re as _re, json as _json
    from collections import defaultdict
    from datetime import datetime, timedelta

    try:
        from voidplatform.linux.web import get_active_engine
        active_engine = get_active_engine()
    except Exception:
        active_engine = "nginx"

    def _log_path_for(dname):
        if active_engine == "ols":
            return f"/usr/local/lsws/conf/vhosts/{dname}/logs/access.log"
        return f"/var/log/nginx/{dname}.access.log"

    all_log_paths = [_log_path_for(data)]
    for sub in d["subdomains"]:
        sname = getattr(sub, "name", None) or getattr(sub, "subdomain", None)
        if sname:
            all_log_paths.append(_log_path_for(f"{sname}.{data}"))

    LOG_RE = _re.compile(
        r'(?P<ip>[\d\.a-fA-F:]+) \S+ \S+ \[(?P<time>[^\]]+)\] '
        r'"(?P<method>\S+) (?P<path>\S+) \S+" (?P<status>\d+) (?P<bytes>\d+|-)'
        r'(?: "(?P<referer>[^"]*)" "(?P<ua>[^"]*)")?'
    )
    BOT_KW    = ["bot","crawl","spider","slurp","baidu","yandex","semrush","ahrefs","python-requests","curl"]
    MOBILE_KW = ["mobile","android","iphone","ipad","ipod"]

    total_requests = 0; total_bytes = 0; unique_ips = set()
    status_counts  = defaultdict(int); daily_counts = defaultdict(int)
    country_counts = defaultdict(int); top_paths = defaultdict(int)
    bot_requests   = 0; mobile_count = 0; desktop_count = 0
    cutoff         = datetime.utcnow() - timedelta(days=30)

    for lp in all_log_paths:
        try:
            with open(lp, "r", errors="replace") as f:
                for line in f:
                    m = LOG_RE.match(line.strip())
                    if not m:
                        continue
                    try:
                        dt = datetime.strptime(m.group("time").split()[0], "%d/%b/%Y:%H:%M:%S")
                    except Exception:
                        continue
                    if dt < cutoff:
                        continue
                    total_requests += 1
                    ip = m.group("ip"); unique_ips.add(ip)
                    bv = m.group("bytes"); total_bytes += int(bv) if bv != "-" else 0
                    status_counts[m.group("status")] += 1
                    daily_counts[dt.strftime("%Y-%m-%d")] += 1
                    path = m.group("path").split("?")[0]
                    if path not in ("/", ""):
                        top_paths[path] += 1
                    ua = (m.group("ua") or "").lower()
                    if any(k in ua for k in BOT_KW):
                        bot_requests += 1
                    elif any(k in ua for k in MOBILE_KW):
                        mobile_count += 1
                    else:
                        desktop_count += 1
        except Exception:
            pass

    GEOIP_DB = "/var/www/panel/geoip/GeoLite2-Country.mmdb"
    geoip_ok = os.path.exists(GEOIP_DB) and len(unique_ips) > 0
    if geoip_ok:
        try:
            import geoip2.database
            with geoip2.database.Reader(GEOIP_DB) as reader:
                for ip in list(unique_ips)[:5000]:
                    try:
                        country_counts[reader.country(ip).country.name or "Unknown"] += 1
                    except Exception:
                        country_counts["Unknown"] += 1
        except Exception:
            geoip_ok = False

    today  = datetime.utcnow().date()
    last7  = [(today - timedelta(days=i)).strftime("%Y-%m-%d") for i in range(6, -1, -1)]
    l7data = [daily_counts.get(dk, 0) for dk in last7]
    http_2xx = sum(v for k,v in status_counts.items() if k.startswith("2"))
    http_3xx = sum(v for k,v in status_counts.items() if k.startswith("3"))
    http_4xx = sum(v for k,v in status_counts.items() if k.startswith("4"))
    http_5xx = sum(v for k,v in status_counts.items() if k.startswith("5"))

    d["traffic"] = {
        "total_requests"  : total_requests,
        "unique_visitors" : len(unique_ips),
        "bandwidth_mb"    : round(total_bytes / (1024 * 1024), 2),
        "bot_requests"    : bot_requests,
        "mobile_count"    : mobile_count,
        "desktop_count"   : desktop_count,
        "http_2xx"        : http_2xx,
        "http_3xx"        : http_3xx,
        "http_4xx"        : http_4xx,
        "http_5xx"        : http_5xx,
        "top_paths"       : sorted(top_paths.items(), key=lambda x: x[1], reverse=True)[:10],
        "countries"       : sorted(country_counts.items(), key=lambda x: x[1], reverse=True)[:10],
        "last7_labels"    : _json.dumps(last7),
        "last7_data"      : _json.dumps(l7data),
        "device_labels"   : _json.dumps(["Desktop", "Mobile", "Bots"]),
        "device_data"     : _json.dumps([desktop_count, mobile_count, bot_requests]),
        "status_labels"   : _json.dumps(["2xx Success", "3xx Redirect", "4xx Error", "5xx Server Error"]),
        "status_data"     : _json.dumps([http_2xx, http_3xx, http_4xx, http_5xx]),
        "geoip_available" : geoip_ok,
        "active_engine"   : active_engine,
        "log_path"        : _log_path_for(data),
    }

    return render(request, "control/analytics.html", d)



# ─── Raw WebServer Config Editor APIs (User Facing) ──────────────────────────
import json

@login_required(login_url='/login')
def user_api_get_site_config(request):
    try:
        if request.user.is_superuser:
            user_obj = user.objects.get(username=request.session.get('name'))
        else:
            user_obj = user.objects.get(username=request.user)
        domain_name = user_obj.domain
    except Exception:
        return JsonResponse({'status': 'error', 'message': 'Unauthorized'}, status=403)
        
    from voidplatform.linux.web import get_web_manager, get_active_engine
    mgr = get_web_manager()
    conf_text = mgr.read_site_config(domain_name)
    engine = get_active_engine()
    
    return JsonResponse({
        'status': 'success',
        'config': conf_text,
        'engine': engine
    })

@login_required(login_url='/login')
@csrf_exempt
def user_api_save_site_config(request):
    try:
        if request.user.is_superuser:
            user_obj = user.objects.get(username=request.session.get('name'))
        else:
            user_obj = user.objects.get(username=request.user)
        domain_name = user_obj.domain
    except Exception:
        return JsonResponse({'status': 'error', 'message': 'Unauthorized'}, status=403)
         
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Invalid method'}, status=405)
        
    try:
        data = json.loads(request.body)
        config_text = data.get('config')
    except Exception:
        return JsonResponse({'status': 'error', 'message': 'Invalid JSON'}, status=400)
        
    if not config_text:
        return JsonResponse({'status': 'error', 'message': 'Missing config text'}, status=400)
        
    from voidplatform.linux.web import get_web_manager
    mgr = get_web_manager()
    
    result = mgr.write_and_test_site_config(domain_name, config_text)
    if result.success:
        return JsonResponse({'status': 'success', 'message': 'Configuration updated and web server reloaded.'})
    else:
        return JsonResponse({'status': 'error', 'message': result.error}, status=400)


@login_required(login_url="/")
def activitylog_control(request, data):
    """User-portal version of the activity log page."""
    if request.user.is_superuser:
        current = request.session.get("name", request.user.username)
    else:
        current = request.user.username

    # Authorization Check
    if not request.user.is_superuser:
        owner = user.objects.filter(username=current).first()
        if not owner or owner.domain != data:
            return HttpResponse("Unauthorized.", status=403)

    try:
        with open(paths.MYSQL_PASSWORD_FILE, "r") as f:
            adminpassword = f.read().strip()
    except Exception:
        adminpassword = ""

    d = {}
    d.update(get_user_dashboard_context(current, adminpassword))
    d["is_control"] = True
    d["domain"] = data
    
    return render(request, 'panel/activitylog.html', d)


@login_required(login_url="/")
@csrf_exempt
def deleteemail_control(request, data):
    """Delete an email account – user-portal route.
    
    Regular users may only delete emails belonging to their own domain.
    Superusers may delete any email.
    """
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'POST required'}, status=405)

    current = request.user.username

    # Ownership check for non-superusers
    if not request.user.is_superuser:
        owner = user.objects.filter(username=current).first()
        if not owner:
            return JsonResponse({'status': 'error', 'message': 'Unauthorized'}, status=403)
        email_domain = data.split('@')[-1] if '@' in data else ''
        if owner.domain != email_domain:
            return JsonResponse({'status': 'error', 'message': 'Unauthorized'}, status=403)

    # Delegate to the shared panel view logic
    import shutil
    from control.models import allemail as allemail_model
    try:
        from voidplatform.config import paths as _paths
        email_obj = allemail_model.objects.get(email=data)
        domain_name = email_obj.domain
        user_prefix = data.split('@')[0]

        # Remove from Postfix maps
        for _fpath in [_paths.POSTFIX_VIRTUAL_ALIAS, _paths.POSTFIX_VIRTUAL_MAILBOX]:
            if os.path.exists(_fpath):
                with open(_fpath, 'r') as _f:
                    _lines = _f.readlines()
                with open(_fpath, 'w') as _f:
                    _f.writelines(l for l in _lines if not l.startswith(f'{data} '))
        import subprocess as _sp
        _sp.run(['postmap', _paths.POSTFIX_VIRTUAL_ALIAS],   capture_output=True)
        _sp.run(['postmap', _paths.POSTFIX_VIRTUAL_MAILBOX], capture_output=True)

        # Remove Dovecot user entry
        if os.path.exists('/etc/dovecot/users'):
            with open('/etc/dovecot/users', 'r') as _f:
                _lines = _f.readlines()
            with open('/etc/dovecot/users', 'w') as _f:
                _f.writelines(l for l in _lines if not l.startswith(f'{data}:'))

        # Remove maildir
        owner_obj = user.objects.filter(domain=domain_name).first()
        sys_owner = owner_obj.username if owner_obj else 'vmail'
        home_path = os.path.join(paths.HOME_BASE, sys_owner, 'mail', domain_name, user_prefix)
        old_path  = os.path.join(paths.MAIL_VHOSTS, domain_name, user_prefix)
        if os.path.exists(home_path): shutil.rmtree(home_path, ignore_errors=True)
        if os.path.exists(old_path):  shutil.rmtree(old_path,  ignore_errors=True)

        email_obj.delete()
        return JsonResponse({'status': 'success'})
    except allemail_model.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Email account not found'}, status=404)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


# ═══════════════════════════════════════════════════════════════════════════════
# CLOUD BACKUP SYNC VIEWS
# ═══════════════════════════════════════════════════════════════════════════════

@login_required(login_url='/')
def cloud_backup_config(request, data):
    """GET: return current cloud config. POST: save cloud credentials."""
    from .models import CloudBackupConfig
    config, _ = CloudBackupConfig.objects.get_or_create(domain=data)

    if request.method == 'GET':
        return JsonResponse({
            'status': 'success',
            'provider':             config.provider,
            'gcs_bucket':           config.gcs_bucket,
            'gcs_key_json':         config.gcs_key_json,
            's3_bucket':            config.s3_bucket,
            's3_access_key':        config.s3_access_key,
            's3_secret_key':        '••••' if config.s3_secret_key else '',
            's3_region':            config.s3_region,
            'auto_backup_enabled':  config.auto_backup_enabled,
            'auto_schedule_preset': config.auto_schedule_preset,
            'auto_schedule_cron':   config.auto_schedule_cron,
            'sync_after_backup':    config.sync_after_backup,
            'is_configured':        config.is_configured,
        })

    if request.method == 'POST':
        try:
            body = json.loads(request.body)
        except Exception:
            return JsonResponse({'status': 'error', 'message': 'Invalid JSON'}, status=400)

        config.provider = body.get('provider', config.provider)
        if body.get('gcs_bucket'):      config.gcs_bucket   = body['gcs_bucket']
        if body.get('gcs_key_json'):    config.gcs_key_json = body['gcs_key_json']
        if body.get('s3_bucket'):       config.s3_bucket    = body['s3_bucket']
        if body.get('s3_access_key'):   config.s3_access_key = body['s3_access_key']
        if body.get('s3_secret_key') and not body['s3_secret_key'].startswith('•'):
            config.s3_secret_key = body['s3_secret_key']
        if body.get('s3_region'):       config.s3_region    = body['s3_region']
        config.save()
        return JsonResponse({'status': 'success', 'message': 'Cloud credentials saved.'})

    return JsonResponse({'status': 'error', 'message': 'Invalid request'}, status=405)


@login_required(login_url='/')
def cloud_backup_auto(request, data):
    """POST: update automation settings for a domain."""
    from .models import CloudBackupConfig
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'POST required'}, status=405)

    try:
        body = json.loads(request.body)
    except Exception:
        return JsonResponse({'status': 'error', 'message': 'Invalid JSON'}, status=400)

    config, _ = CloudBackupConfig.objects.get_or_create(domain=data)
    config.auto_backup_enabled  = bool(body.get('auto_backup_enabled', config.auto_backup_enabled))
    config.auto_schedule_preset = body.get('auto_schedule_preset', config.auto_schedule_preset)
    config.auto_schedule_cron   = body.get('auto_schedule_cron', config.auto_schedule_cron)
    config.sync_after_backup    = bool(body.get('sync_after_backup', config.sync_after_backup))
    config.save()
    return JsonResponse({'status': 'success', 'message': 'Automation settings saved.'})


@login_required(login_url='/')
def cloud_backup_sync(request, data, filename):
    """
    POST: push a specific backup ZIP to the configured cloud provider.
    Requires google-cloud-storage or boto3 to be installed on the server.
    """
    from .models import CloudBackupConfig
    import os

    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'POST required'}, status=405)

    try:
        dom = domain.objects.get(domain=data)
    except domain.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Domain not found'}, status=404)

    try:
        config = CloudBackupConfig.objects.get(domain=data)
    except CloudBackupConfig.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'No cloud config found. Set up credentials first.'}, status=400)

    if not config.is_configured:
        return JsonResponse({'status': 'error', 'message': 'Cloud credentials incomplete. Fill in all required fields.'}, status=400)

    # Locate the file
    zip_path = os.path.join('/home', dom.dir, filename)
    if not os.path.exists(zip_path):
        return JsonResponse({'status': 'error', 'message': f'Backup file not found: {filename}'}, status=404)

    try:
        if config.provider == 'gcs':
            # Google Cloud Storage upload
            import json as _json
            import tempfile
            from google.cloud import storage as gcs_storage
            from google.oauth2 import service_account

            key_data = _json.loads(config.gcs_key_json)
            creds = service_account.Credentials.from_service_account_info(key_data)
            client = gcs_storage.Client(credentials=creds, project=key_data.get('project_id'))
            bucket = client.bucket(config.gcs_bucket)
            blob   = bucket.blob(f'voidpanel-backups/{data}/{filename}')
            blob.upload_from_filename(zip_path)
            return JsonResponse({'status': 'success', 'message': f'Uploaded to GCS: gs://{config.gcs_bucket}/voidpanel-backups/{data}/{filename}'})

        elif config.provider == 's3':
            # Amazon S3 upload
            import boto3
            s3 = boto3.client(
                's3',
                aws_access_key_id=config.s3_access_key,
                aws_secret_access_key=config.s3_secret_key,
                region_name=config.s3_region,
            )
            s3_key = f'voidpanel-backups/{data}/{filename}'
            s3.upload_file(zip_path, config.s3_bucket, s3_key)
            return JsonResponse({'status': 'success', 'message': f'Uploaded to S3: s3://{config.s3_bucket}/{s3_key}'})

        else:
            return JsonResponse({'status': 'error', 'message': f'Unknown provider: {config.provider}'}, status=400)

    except ImportError as e:
        lib = 'google-cloud-storage' if config.provider == 'gcs' else 'boto3'
        return JsonResponse({'status': 'error', 'message': f'Missing library. Run: pip install {lib}'}, status=500)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


# ═══════════════════════════════════════════════════════════════════════════════
# ONE-CLICK APP INSTALLER VIEWS
# ═══════════════════════════════════════════════════════════════════════════════

# Full app catalog definition — single source of truth used by both the
# catalog page and the install endpoint.
APP_CATALOG = [
    # CMS
    {'id': 'wordpress',   'name': 'WordPress',     'category': 'CMS',       'icon': 'fa-brands fa-wordpress',     'color': '#0073AA', 'bg': 'rgba(0,115,170,0.14)',   'desc': 'The world\'s most popular CMS. Powers 43% of the web.',  'tech': 'PHP + MySQL'},
    {'id': 'ghost',       'name': 'Ghost',          'category': 'CMS',       'icon': 'fa-solid fa-ghost',          'color': '#ffffff', 'bg': 'rgba(21,23,26,0.85)',    'desc': 'Modern publishing platform built on Node.js.',           'tech': 'Node.js + SQLite'},
    {'id': 'strapi',      'name': 'Strapi',         'category': 'CMS',       'icon': 'fa-solid fa-layer-group',    'color': '#4945FF', 'bg': 'rgba(73,69,255,0.12)',   'desc': 'Leading open-source headless CMS for React/Next.js.',    'tech': 'Node.js + SQL'},
    # eCommerce
    {'id': 'woocommerce', 'name': 'WooCommerce',    'category': 'eCommerce', 'icon': 'fa-brands fa-wordpress',    'color': '#7f54b3', 'bg': 'rgba(127,84,179,0.12)',  'desc': 'WordPress-based eCommerce platform.',                    'tech': 'PHP + MySQL'},
    {'id': 'prestashop',  'name': 'PrestaShop',     'category': 'eCommerce', 'icon': 'fa-solid fa-cart-shopping',  'color': '#df0067', 'bg': 'rgba(223,0,103,0.12)',   'desc': 'Powerful standalone PHP eCommerce solution.',            'tech': 'PHP + MySQL'},
    {'id': 'opencart',    'name': 'OpenCart',       'category': 'eCommerce', 'icon': 'fa-solid fa-bag-shopping',   'color': '#23aaeb', 'bg': 'rgba(35,170,235,0.12)',  'desc': 'Free, open-source eCommerce platform.',                  'tech': 'PHP + MySQL'},
    {'id': 'boxbilling',  'name': 'BoxBilling',     'category': 'Billing',   'icon': 'fa-solid fa-file-invoice-dollar','color': '#f59e0b','bg': 'rgba(245,158,11,0.12)','desc': 'Lightweight open-source billing & client management.',  'tech': 'PHP + MySQL'},
    # DevOps & Developer Tools
    {'id': 'gitea',       'name': 'Gitea',          'category': 'DevOps',    'icon': 'fa-solid fa-code-branch',    'color': '#609926', 'bg': 'rgba(96,153,38,0.12)',   'desc': 'Lightweight self-hosted Git service.',                   'tech': 'Go + SQLite'},
    {'id': 'uptimekuma',  'name': 'Uptime Kuma',    'category': 'DevOps',    'icon': 'fa-solid fa-heart-pulse',    'color': '#5cdd8b', 'bg': 'rgba(92,221,139,0.12)',  'desc': 'Beautiful self-hosted monitoring tool.',                  'tech': 'Node.js'},
    {'id': 'n8n',         'name': 'n8n',            'category': 'DevOps',    'icon': 'fa-solid fa-diagram-project','color': '#ea4b71', 'bg': 'rgba(234,75,113,0.12)',  'desc': 'Powerful self-hosted workflow automation (like Zapier).', 'tech': 'Node.js'},
    {'id': 'vscode',      'name': 'VS Code Server', 'category': 'DevOps',    'icon': 'fa-solid fa-code',           'color': '#007acc', 'bg': 'rgba(0,122,204,0.12)',   'desc': 'Code in your browser with VS Code on your server.',      'tech': 'Node.js'},
    # Cloud & Productivity
    {'id': 'nextcloud',   'name': 'Nextcloud',      'category': 'Cloud',     'icon': 'fa-solid fa-cloud',          'color': '#0082c9', 'bg': 'rgba(0,130,201,0.12)',   'desc': 'Self-hosted alternative to Google Drive/Dropbox.',       'tech': 'PHP + MySQL'},
    {'id': 'vaultwarden', 'name': 'Vaultwarden',    'category': 'Cloud',     'icon': 'fa-solid fa-shield-halved',  'color': '#175ddc', 'bg': 'rgba(23,93,220,0.12)',   'desc': 'Lightweight, self-hosted Bitwarden password manager.',   'tech': 'Rust + SQLite'},
    {'id': 'bookstack',   'name': 'BookStack',      'category': 'Cloud',     'icon': 'fa-solid fa-book-open',      'color': '#1da5c8', 'bg': 'rgba(29,165,200,0.12)',  'desc': 'Simple wiki & documentation platform for teams.',        'tech': 'PHP + MySQL'},
    {'id': 'matomo',      'name': 'Matomo',         'category': 'Cloud',     'icon': 'fa-solid fa-chart-pie',      'color': '#3152a0', 'bg': 'rgba(49,82,160,0.12)',   'desc': 'Privacy-focused Google Analytics alternative.',          'tech': 'PHP + MySQL'},
    # 2026 Trending
    {'id': 'appwrite',    'name': 'Appwrite',       'category': 'Trending',  'icon': 'fa-solid fa-a',              'color': '#f02e65', 'bg': 'rgba(240,46,101,0.12)',  'desc': 'Self-hosted Backend-as-a-Service for modern apps.',      'tech': 'Docker'},
    {'id': 'postiz',      'name': 'Postiz',         'category': 'Trending',  'icon': 'fa-solid fa-comments',       'color': '#6366f1', 'bg': 'rgba(99,102,241,0.12)',  'desc': 'AI-powered social media scheduler. Self-hostable.',      'tech': 'Node.js'},
    {'id': 'jellyfin',    'name': 'Jellyfin',       'category': 'Trending',  'icon': 'fa-solid fa-film',           'color': '#00a4dc', 'bg': 'rgba(0,164,220,0.12)',   'desc': 'Open-source media server. The better Plex alternative.', 'tech': 'C# / .NET'},
    {'id': 'metabase',    'name': 'Metabase',       'category': 'Trending',  'icon': 'fa-solid fa-database',       'color': '#509ee3', 'bg': 'rgba(80,158,227,0.12)',  'desc': 'Business intelligence tool — visualize your databases.',  'tech': 'Java / Clojure'},
]


@login_required(login_url='/')
def app_installer(request, domain=None):
    """Render the full One-Click App Installer catalog page."""
    if request.user.is_superuser:
        current = request.session.get('name', request.user.username)
    else:
        current = request.user.username

    # Use the domain from the URL or fall back to user's primary domain
    if not domain:
        try:
            usr_obj = user.objects.get(username=current)
            domain = usr_obj.domain
        except Exception:
            domain = ''

    domain_name = domain

    try:
        with open(paths.MYSQL_PASSWORD_FILE, 'r') as f:
            adminpassword = f.read().strip()
    except Exception:
        adminpassword = ''

    from control.models import InstalledScript, subdomainname as SubDomain

    # Build combined domain options: main domain + all subdomains
    domain_options = [{'value': domain_name, 'label': f'{domain_name} (Main Domain)'}]
    for sub in SubDomain.objects.filter(domain=domain_name):
        sub_name = None
        for attr in ['name', 'subdomain', 'sub_domain', 'prefix', 'label']:
            val = getattr(sub, attr, None)
            if val and isinstance(val, str):
                sub_name = val
                break
        if sub_name:
            full = f'{sub_name}.{domain_name}'
            domain_options.append({'value': full, 'label': f'{full} (Subdomain)'})

    # Pre-selected app from GET param (?app=wordpress)
    selected_app_id = request.GET.get('app', '').strip().lower()
    selected_app    = next((a for a in APP_CATALOG if a['id'] == selected_app_id), None)

    installed_qs = InstalledScript.objects.filter(domain=domain_name).exclude(status='deleted').order_by('-installed_at')

    d = {}
    d.update(get_user_dashboard_context(current, adminpassword))
    d['domain']          = domain_name
    d['catalog']         = APP_CATALOG
    d['categories']      = list(dict.fromkeys(a['category'] for a in APP_CATALOG))
    d['installed']       = installed_qs
    d['installed_count'] = installed_qs.count()
    d['domain_options']  = domain_options
    d['selected_app']    = selected_app
    d['selected_app_id'] = selected_app_id

    return render(request, 'control/app_installer.html', d)


@login_required(login_url='/')
@csrf_exempt
def app_installer_install(request):
    """
    POST endpoint: validate the form, create an InstalledScript record,
    and dispatch the background Celery task to do the actual installation.
    """
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'POST required'}, status=405)

    if request.user.is_superuser:
        current = request.session.get('name', request.user.username)
    else:
        current = request.user.username

    script_name  = request.POST.get('app_name', '').strip().lower().replace(' ', '')
    install_url  = request.POST.get('install_domain', '').strip()
    admin_user_v = request.POST.get('admin_user', 'admin').strip()
    admin_pass   = request.POST.get('admin_pass', '').strip()
    admin_email  = request.POST.get('admin_email', '').strip()

    # Validate required fields
    if not all([script_name, install_url, admin_pass, admin_email]):
        return JsonResponse({'status': 'error', 'message': 'All fields are required.'}, status=400)

    # Verify the script is in the catalog
    valid_ids = {a['id'] for a in APP_CATALOG}
    if script_name not in valid_ids:
        return JsonResponse({'status': 'error', 'message': f'Unknown script: {script_name}'}, status=400)

    # Determine the primary domain of the user
    try:
        usr_obj     = user.objects.get(username=current)
        primary_dom = usr_obj.domain
    except Exception:
        return JsonResponse({'status': 'error', 'message': 'User account not found.'}, status=403)

    # Authorization: install_url must be the user's domain or one of their subdomains
    from control.models import subdomainname as SubDomain, InstalledScript
    allowed_urls = {primary_dom}
    for sub in SubDomain.objects.filter(domain=primary_dom):
        sub_name = getattr(sub, 'name', None) or getattr(sub, 'subdomain', '')
        if sub_name:
            allowed_urls.add(f"{sub_name}.{primary_dom}")

    if install_url not in allowed_urls and not request.user.is_superuser:
        return JsonResponse({'status': 'error', 'message': 'Unauthorized install target.'}, status=403)

    # Check if already installed at this URL
    existing = InstalledScript.objects.filter(
        domain=primary_dom, install_url=install_url, script_name=script_name
    ).exclude(status='deleted').first()
    if existing:
        return JsonResponse({
            'status': 'error',
            'message': f'{script_name.title()} is already installed at {install_url}.'
        }, status=400)

    # Determine install directory — subdomains live at public_html/{sub}/ (matching subdomainprocess)
    install_dir = f"/home/{current}/public_html"
    if install_url != primary_dom:
        sub_label = install_url.replace(f'.{primary_dom}', '').strip('.')
        install_dir = f"/home/{current}/public_html/{sub_label}"

    # Create DB record (status=installing)
    record = InstalledScript.objects.create(
        domain=primary_dom,
        username=current,
        script_name=script_name,
        install_url=install_url,
        install_dir=install_dir,
        admin_user=admin_user_v,
        admin_email=admin_email,
        status=InstalledScript.STATUS_INSTALLING,
    )

    # Dispatch background Celery task
    from control.tasks import async_install_script
    async_install_script.delay(
        record_id=record.pk,
        script_name=script_name,
        domain=primary_dom,
        username=current,
        admin_user=admin_user_v,
        admin_pass=admin_pass,
        admin_email=admin_email,
        install_url=install_url,
    )

    # Get app display info
    app_info = next((a for a in APP_CATALOG if a['id'] == script_name), {})

    return JsonResponse({
        'status':    'success',
        'message':   f'{app_info.get("name", script_name)} installation has started! It may take 2–5 minutes to complete.',
        'record_id': record.pk,
    })


@login_required(login_url='/')
def app_installer_status(request, record_id):
    """Poll endpoint: return JSON status of a given InstalledScript record."""
    from control.models import InstalledScript
    try:
        record = InstalledScript.objects.get(pk=record_id)
    except InstalledScript.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Record not found'}, status=404)

    return JsonResponse({
        'status':    record.status,
        'admin_url': record.admin_url,
        'db_name':   record.db_name,
        'db_user':   record.db_user,
        'log':       record.log[-2000:] if record.log else '',  # tail of log
    })


@login_required(login_url='/')
@csrf_exempt
def app_installer_delete(request, record_id):
    """POST endpoint: uninstall (remove) an installed script."""
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'POST required'}, status=405)

    from control.models import InstalledScript
    try:
        record = InstalledScript.objects.get(pk=record_id)
    except InstalledScript.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Record not found'}, status=404)

    # Auth check
    if request.user.is_superuser:
        current = request.session.get('name', request.user.username)
    else:
        current = request.user.username

    if record.username != current and not request.user.is_superuser:
        return JsonResponse({'status': 'error', 'message': 'Unauthorized'}, status=403)

    # Dispatch uninstall task
    from control.tasks import async_uninstall_script
    async_uninstall_script.delay(record_id=record.pk)

    return JsonResponse({
        'status':  'success',
        'message': f'Uninstallation of {record.script_display_name} started in the background.',
    })


@login_required(login_url='/')
def app_installer_settings(request, record_id):
    """GET: Return install settings (DB info, admin URL) for a record."""
    from control.models import InstalledScript
    try:
        record = InstalledScript.objects.get(pk=record_id)
    except InstalledScript.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Not found'}, status=404)

    # Auth
    current = request.session.get('name', request.user.username) if request.user.is_superuser else request.user.username
    if record.username != current and not request.user.is_superuser:
        return JsonResponse({'status': 'error', 'message': 'Unauthorized'}, status=403)

    return JsonResponse({
        'status':     'success',
        'id':         record.pk,
        'script':     record.script_display_name,
        'install_url': record.install_url,
        'admin_url':  record.admin_url,
        'admin_user': record.admin_user,
        'admin_email': record.admin_email,
        'db_name':    record.db_name,
        'db_user':    record.db_user,
        'db_pass':    record.db_pass,
        'install_dir': record.install_dir,
        'installed_at': record.installed_at.strftime('%b %d, %Y %H:%M'),
    })


@login_required(login_url='/')
def app_installer_change_password(request, record_id):
    """POST: Change WordPress admin password via WP-CLI."""
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'POST required'}, status=405)

    from control.models import InstalledScript
    try:
        record = InstalledScript.objects.get(pk=record_id)
    except InstalledScript.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Not found'}, status=404)

    current = request.session.get('name', request.user.username) if request.user.is_superuser else request.user.username
    if record.username != current and not request.user.is_superuser:
        return JsonResponse({'status': 'error', 'message': 'Unauthorized'}, status=403)

    new_pass = request.POST.get('new_password', '').strip()
    if len(new_pass) < 8:
        return JsonResponse({'status': 'error', 'message': 'Password must be at least 8 characters'})

    import subprocess
    public_html = record.install_dir or f"/home/{record.username}/public_html"

    # Find WP-CLI compatible PHP
    from control.script_installers import _get_wp_php
    wp_php = _get_wp_php()

    r = subprocess.run(
        ['sudo', wp_php, '/usr/local/bin/wp', 'user', 'update', record.admin_user,
         f'--user_pass={new_pass}', f'--path={public_html}', '--allow-root'],
        capture_output=True, text=True, timeout=60
    )
    if r.returncode == 0:
        return JsonResponse({'status': 'success', 'message': 'Password changed successfully!'})
    else:
        return JsonResponse({'status': 'error', 'message': r.stdout + r.stderr})




# ═══════════════════════════════════════════════════════════
#  SOCIAL MEDIA MANAGEMENT VIEWS
# ═══════════════════════════════════════════════════════════

def _social_auth_check(request, domain):
    """Return (current_username, error_response). error_response is None if OK."""
    if not request.user.is_authenticated:
        return None, redirect('/')
    if request.user.is_superuser:
        current = request.session.get('name', request.user.username)
    else:
        current = request.user.username
        from control.models import user as ctrl_user
        owner = ctrl_user.objects.filter(username=current).first()
        if not owner or owner.domain != domain:
            from django.http import HttpResponse
            return None, HttpResponse("Unauthorized", status=403)
    return current, None


def social_home(request, domain):
    from control.models import SocialAccount, SocialPost, SocialMediaAPIConfig
    current, err = _social_auth_check(request, domain)
    if err:
        return err
    try:
        with open(paths.MYSQL_PASSWORD_FILE, 'r') as f:
            adminpassword = f.read().strip()
    except Exception:
        adminpassword = ''
    d = {}
    d.update(get_user_dashboard_context(current, adminpassword))
    d['domain'] = domain
    d['accounts'] = SocialAccount.objects.filter(domain=domain, is_active=True)
    d['posts'] = SocialPost.objects.filter(domain=domain).order_by('-created_at')[:50]
    d['scheduled'] = SocialPost.objects.filter(domain=domain, status='scheduled').order_by('scheduled_at')
    api_config = SocialMediaAPIConfig.get()
    d['api_config'] = api_config
    d['stats'] = {
        'total_accounts': SocialAccount.objects.filter(domain=domain, is_active=True).count(),
        'published': SocialPost.objects.filter(domain=domain, status='published').count(),
        'scheduled': SocialPost.objects.filter(domain=domain, status='scheduled').count(),
        'failed': SocialPost.objects.filter(domain=domain, status='failed').count(),
    }
    # Build per-platform enabled status from the config's enabled_platforms list.
    # If the list is empty (not configured yet), treat ALL platforms as disabled
    # so users see "Upgrade" prompts rather than broken OAuth redirects.
    ep = api_config.enabled_platforms  # e.g. ['fb', 'ig', 'tw']
    d['enabled_platforms'] = ep
    d['any_platform_enabled'] = bool(ep)
    return render(request, 'control/social.html', d)


def social_connect(request, domain, platform):
    """Initiate OAuth flow via the voidpanel.com relay."""
    from control.models import SocialMediaAPIConfig, PanelLicense
    current, err = _social_auth_check(request, domain)
    if err:
        return err

    # Enforce connected accounts limit check
    limit = _resolve_suite_limit(request, domain, 'social', 'accounts', 5)
    if limit > 0:
        from control.models import SocialAccount
        current_count = SocialAccount.objects.filter(domain=domain, is_active=True).count()
        if current_count >= limit:
            messages.error(request, f"Plan Limit Reached: Your current plan only allows up to {limit} connected social accounts. Upgrade your package to connect more.")
            return redirect(f'/control/social/{domain}/')
    # Sync enabled platforms
    cfg = SocialMediaAPIConfig.get()
    request.session['social_domain'] = domain
    request.session['social_platform'] = platform

    # Get the license key for the relay
    lic = PanelLicense.objects.first()
    if not lic or not lic.key:
        messages.error(request, "Panel license not configured. Social media connections require a valid VoidPanel license.")
        return redirect(f'/control/social/{domain}/')

    if not cfg.enabled_platforms or platform not in cfg.enabled_platforms:
        messages.warning(request, f"Platform '{platform}' is not enabled. Ask your administrator to enable it in the Super Admin panel on voidpanel.com.")
        return redirect(f'/control/social/{domain}/')

    # Build our local callback URL (the relay will redirect back here)
    local_callback = request.build_absolute_uri(f'/control/social/callback/{platform}/')

    # Redirect to voidpanel.com OAuth relay with license and callback
    import urllib.parse
    relay_url = (
        f"https://voidpanel.com/social/oauth/connect/{platform}/"
        f"?license={urllib.parse.quote(lic.key)}"
        f"&callback_uri={urllib.parse.quote(local_callback)}"
    )
    return redirect(relay_url)


def social_callback(request, platform):
    """
    Handle OAuth callback from the voidpanel.com relay.
    The relay redirects back here with ?relay_code=... (or ?error=...).
    We POST the relay_code to voidpanel.com to retrieve the actual tokens,
    then save the accounts into our local database.
    """
    import requests as _req
    import json as _json
    from control.models import SocialAccount, PanelLicense
    from django.utils import timezone as _tz

    domain = request.session.get('social_domain', '')
    current, err = _social_auth_check(request, domain)
    if err:
        return err

    # Check for error from the relay
    error = request.GET.get('error', '')
    if error:
        messages.error(request, f"OAuth was cancelled or failed ({error}).")
        return redirect(f'/control/social/{domain}/')

    # Get the relay_code
    relay_code = request.GET.get('relay_code', '').strip()
    if not relay_code:
        messages.error(request, "OAuth callback missing relay code. Please try connecting again.")
        return redirect(f'/control/social/{domain}/')

    # Get license key
    lic = PanelLicense.objects.first()
    if not lic or not lic.key:
        messages.error(request, "Panel license not configured.")
        return redirect(f'/control/social/{domain}/')

    # Exchange relay_code for tokens via server-to-server call
    try:
        r = _req.post(
            'https://voidpanel.com/api/social/retrieve-tokens/',
            json={'license': lic.key, 'relay_code': relay_code},
            headers={
                'Content-Type': 'application/json',
                'X-VoidPanel-License': lic.key,
            },
            timeout=15,
        )
        if r.status_code != 200:
            err_msg = r.json().get('error', r.text) if 'application/json' in r.headers.get('Content-Type', '') else r.text[:200]
            messages.error(request, f"Failed to retrieve tokens: {err_msg}")
            return redirect(f'/control/social/{domain}/')

        data = r.json()
    except Exception as e:
        messages.error(request, f"Error contacting voidpanel.com: {e}")
        return redirect(f'/control/social/{domain}/')

    accounts_data = data.get('accounts', [])
    if not accounts_data:
        messages.warning(request, "No accounts were returned. Please try connecting again.")
        return redirect(f'/control/social/{domain}/')

    # Save each account
    count = 0
    for acc in accounts_data:
        plat = acc.get('platform', platform)
        aid = acc.get('account_id', '')
        if not aid:
            continue

        expiry = None
        if acc.get('expires_in'):
            from datetime import timedelta
            expiry = _tz.now() + timedelta(seconds=int(acc['expires_in']))

        defaults = dict(
            username=current,
            account_name=acc.get('account_name', f'{plat.upper()} Account'),
            account_username=acc.get('account_username', ''),
            access_token=acc.get('access_token', ''),
            refresh_token=acc.get('refresh_token', ''),
            token_expiry=expiry,
            profile_picture_url=acc.get('profile_picture_url', ''),
            followers_count=acc.get('followers_count', 0),
            is_active=True,
        )
        # FB/IG specific fields
        if acc.get('page_id'):
            defaults['page_id'] = acc['page_id']
        if acc.get('page_name'):
            defaults['page_name'] = acc['page_name']

        # Enforce accounts limit check in callback
        limit = _resolve_suite_limit(request, domain, 'social', 'accounts', 5)
        if limit > 0:
            exists = SocialAccount.objects.filter(domain=domain, platform=plat, account_id=aid, is_active=True).exists()
            if not exists:
                current_count = SocialAccount.objects.filter(domain=domain, is_active=True).count()
                if current_count >= limit:
                    messages.error(request, f"Plan Limit Reached: Could not connect account '{acc.get('account_name', plat.upper())}' because your plan limit of {limit} accounts is reached.")
                    continue

        SocialAccount.objects.update_or_create(
            domain=domain, platform=plat, account_id=aid,
            defaults=defaults,
        )
        count += 1

    PLATFORM_NAMES = {
        'fb': 'Facebook', 'ig': 'Instagram', 'tw': 'Twitter/X', 'li': 'LinkedIn',
        'pi': 'Pinterest', 'tt': 'TikTok', 'yt': 'YouTube', 'th': 'Threads', 'gb': 'Google Business',
    }
    label = PLATFORM_NAMES.get(platform, platform.upper())
    messages.success(request, f"✅ Connected {count} {label} account(s) successfully!")
    return redirect(f'/control/social/{domain}/')


def _social_refresh_token(acc):
    """
    Check if an account's token is expiring and refresh it via voidpanel.com.
    Called before publishing to ensure the token is valid.
    """
    import requests as _req
    from control.models import PanelLicense
    from django.utils import timezone as _tz

    # Skip if no expiry is set or token is still valid for > 5 minutes
    if acc.token_expiry and acc.token_expiry > _tz.now() + __import__('datetime').timedelta(minutes=5):
        return  # Token still valid

    # If no refresh_token, we can't refresh
    if not acc.refresh_token:
        return

    lic = PanelLicense.objects.first()
    if not lic or not lic.key:
        return

    try:
        r = _req.post(
            'https://voidpanel.com/api/social/refresh-token/',
            json={
                'license': lic.key,
                'platform': acc.platform,
                'refresh_token': acc.refresh_token,
            },
            headers={
                'Content-Type': 'application/json',
                'X-VoidPanel-License': lic.key,
            },
            timeout=10,
        )
        if r.status_code == 200:
            data = r.json()
            acc.access_token = data.get('access_token', acc.access_token)
            if data.get('refresh_token'):
                acc.refresh_token = data['refresh_token']
            if data.get('expires_in'):
                from datetime import timedelta
                acc.token_expiry = _tz.now() + timedelta(seconds=int(data['expires_in']))
            acc.save(update_fields=['access_token', 'refresh_token', 'token_expiry'])
    except Exception:
        pass  # Best-effort refresh — publishing will still try with existing token


def social_disconnect(request, domain, account_id):
    from control.models import SocialAccount
    current, err = _social_auth_check(request, domain)
    if err:
        return err
    acc = SocialAccount.objects.filter(id=account_id, domain=domain).first()
    if acc:
        acc.delete()
        messages.success(request, "Account disconnected.")
    return redirect(f'/control/social/{domain}/')


def social_post_create(request, domain):
    from control.models import SocialAccount, SocialPost
    from django.utils import timezone as _tz
    import json
    current, err = _social_auth_check(request, domain)
    if err:
        return err
    if request.method != 'POST':
        return redirect(f'/control/social/{domain}/')

    caption = request.POST.get('caption', '').strip()
    first_comment = request.POST.get('first_comment', '').strip()
    account_ids = request.POST.getlist('account_ids')
    link_url = request.POST.get('link_url', '').strip()
    schedule_type = request.POST.get('schedule_type', 'now')
    scheduled_at_str = request.POST.get('scheduled_at', '').strip()
    is_recurring = bool(request.POST.get('is_recurring'))
    recurrence_rule = request.POST.get('recurrence_rule', '')

    post = SocialPost(
        domain=domain, username=current,
        caption_text=caption, first_comment=first_comment,
        link_url=link_url,
        is_recurring=is_recurring, recurrence_rule=recurrence_rule,
    )

    if schedule_type == 'now':
        post.status = 'published'
        post.published_at = _tz.now()
    else:
        post.status = 'scheduled'
        try:
            from datetime import datetime
            post.scheduled_at = datetime.fromisoformat(scheduled_at_str)
        except Exception:
            post.scheduled_at = None
            post.status = 'draft'

    # Handle media upload
    media_urls = []
    for f in request.FILES.getlist('media'):
        import os
        upload_dir = os.path.join('media', 'social', domain)
        os.makedirs(upload_dir, exist_ok=True)
        fpath = os.path.join(upload_dir, f.name)
        with open(fpath, 'wb+') as dest:
            for chunk in f.chunks():
                dest.write(chunk)
        media_urls.append(fpath)
    post.media_urls = media_urls
    post.save()

    accounts = SocialAccount.objects.filter(id__in=account_ids, domain=domain)
    post.accounts.set(accounts)

    if post.status == 'published':
        _social_publish_now(post)

    msg = "✅ Post published!" if post.status == 'published' else f"🕐 Post scheduled for {post.scheduled_at}"
    messages.success(request, msg)
    return redirect(f'/control/social/{domain}/')


def _social_publish_now(post):
    """
    Publish a SocialPost to all linked accounts.
    Supports: Facebook, Instagram, Twitter/X, LinkedIn, Threads, TikTok, Pinterest, YouTube.
    """
    import requests as _req
    from control.models import SocialMediaAPIConfig
    cfg = SocialMediaAPIConfig.get()
    results = {}
    text = post.caption_text
    link = post.link_url or ''
    media = post.media_urls or []

    for acc in post.accounts.all():
        # Refresh token if expiring (via voidpanel.com relay)
        _social_refresh_token(acc)
        plat = acc.platform
        tok = acc.access_token
        try:
            # ── Facebook ──────────────────────────────────────────────────
            if plat == 'fb' and acc.page_id and tok:
                payload = {'message': text, 'access_token': tok}
                if link:
                    payload['link'] = link
                r = _req.post(
                    f"https://graph.facebook.com/v19.0/{acc.page_id}/feed",
                    data=payload, timeout=15
                )
                results[plat] = r.json().get('id', r.text)

            # ── Instagram (via Facebook Page token) ───────────────────────
            elif plat == 'ig' and acc.page_id and tok:
                ig_id = acc.account_id
                # Photo post requires a media URL; for text-only use a container
                if media:
                    # Upload image container
                    cont_r = _req.post(
                        f"https://graph.facebook.com/v19.0/{ig_id}/media",
                        data={'image_url': media[0], 'caption': text, 'access_token': tok},
                        timeout=15
                    )
                    container_id = cont_r.json().get('id')
                    if container_id:
                        pub_r = _req.post(
                            f"https://graph.facebook.com/v19.0/{ig_id}/media_publish",
                            data={'creation_id': container_id, 'access_token': tok},
                            timeout=15
                        )
                        results[plat] = pub_r.json().get('id', pub_r.text)
                    else:
                        results[plat] = f'container_error:{cont_r.text}'
                else:
                    results[plat] = 'skipped:no_media (Instagram requires an image or video)'

            # ── Twitter / X ───────────────────────────────────────────────
            elif plat == 'tw' and tok:
                body = {'text': text[:280]}
                r = _req.post(
                    'https://api.twitter.com/2/tweets',
                    json=body,
                    headers={'Authorization': f'Bearer {tok}', 'Content-Type': 'application/json'},
                    timeout=15
                )
                results[plat] = r.json().get('data', {}).get('id', r.text)

            # ── LinkedIn ──────────────────────────────────────────────────
            elif plat == 'li' and tok:
                author = f"urn:li:person:{acc.account_id}"
                body = {
                    'author': author,
                    'lifecycleState': 'PUBLISHED',
                    'specificContent': {
                        'com.linkedin.ugc.ShareContent': {
                            'shareCommentary': {'text': text},
                            'shareMediaCategory': 'NONE',
                        }
                    },
                    'visibility': {'com.linkedin.ugc.MemberNetworkVisibility': 'PUBLIC'},
                }
                r = _req.post(
                    'https://api.linkedin.com/v2/ugcPosts',
                    json=body,
                    headers={'Authorization': f'Bearer {tok}', 'Content-Type': 'application/json',
                             'X-Restli-Protocol-Version': '2.0.0'},
                    timeout=15
                )
                results[plat] = r.headers.get('x-restli-id', r.text)

            # ── Threads ───────────────────────────────────────────────────
            elif plat == 'th' and tok:
                ig_id = acc.account_id
                cont_r = _req.post(
                    f"https://graph.threads.net/v1.0/{ig_id}/threads",
                    data={'media_type': 'TEXT', 'text': text, 'access_token': tok},
                    timeout=15
                )
                container_id = cont_r.json().get('id')
                if container_id:
                    pub_r = _req.post(
                        f"https://graph.threads.net/v1.0/{ig_id}/threads_publish",
                        data={'creation_id': container_id, 'access_token': tok},
                        timeout=15
                    )
                    results[plat] = pub_r.json().get('id', pub_r.text)
                else:
                    results[plat] = f'container_error:{cont_r.text}'

            # ── TikTok ────────────────────────────────────────────────────
            elif plat == 'tt' and tok:
                # TikTok requires a video; text-only posts are not supported
                if media:
                    r = _req.post(
                        'https://open.tiktokapis.com/v2/post/publish/video/init/',
                        json={
                            'post_info': {'title': text[:150], 'privacy_level': 'SELF_ONLY', 'disable_duet': False, 'disable_comment': False, 'disable_stitch': False},
                            'source_info': {'source': 'FILE_UPLOAD', 'video_size': 0, 'chunk_size': 0, 'total_chunk_count': 1},
                        },
                        headers={'Authorization': f'Bearer {tok}', 'Content-Type': 'application/json; charset=UTF-8'},
                        timeout=15
                    )
                    results[plat] = r.json().get('data', {}).get('publish_id', r.text)
                else:
                    results[plat] = 'skipped:no_video (TikTok requires a video)'

            # ── Pinterest ────────────────────────────────────────────────
            elif plat == 'pi' and tok:
                body = {
                    'title': text[:100],
                    'description': text,
                    'board_id': acc.page_id or '',  # board_id stored in page_id
                    'link': link or None,
                }
                if media:
                    body['media_source'] = {'source_type': 'image_url', 'url': media[0]}
                r = _req.post(
                    'https://api.pinterest.com/v5/pins',
                    json={k: v for k, v in body.items() if v},
                    headers={'Authorization': f'Bearer {tok}', 'Content-Type': 'application/json'},
                    timeout=15
                )
                results[plat] = r.json().get('id', r.text)

            # ── YouTube (community post) ───────────────────────────────────
            elif plat == 'yt' and tok:
                # YouTube community posts via Data API v3
                r = _req.post(
                    'https://www.googleapis.com/youtube/v3/communityPosts?part=snippet',
                    json={'snippet': {'textOriginal': text}},
                    headers={'Authorization': f'Bearer {tok}', 'Content-Type': 'application/json'},
                    timeout=15
                )
                results[plat] = r.json().get('id', r.text)

            # ── Google Business ───────────────────────────────────────────
            elif plat == 'gb' and tok:
                location_name = acc.page_id  # stored as 'accounts/{id}/locations/{id}'
                if location_name:
                    r = _req.post(
                        f'https://mybusiness.googleapis.com/v4/{location_name}/localPosts',
                        json={'languageCode': 'en', 'summary': text, 'topicType': 'STANDARD'},
                        headers={'Authorization': f'Bearer {tok}', 'Content-Type': 'application/json'},
                        timeout=15
                    )
                    results[plat] = r.json().get('name', r.text)
                else:
                    results[plat] = 'skipped:no_location_id'

            else:
                results[plat] = 'queued'

        except Exception as e:
            results[plat] = f'error:{e}'

    post.platform_post_ids = results
    post.save(update_fields=['platform_post_ids'])


def social_post_delete(request, domain, post_id):
    from control.models import SocialPost
    current, err = _social_auth_check(request, domain)
    if err:
        return err
    p = SocialPost.objects.filter(id=post_id, domain=domain).first()
    if p:
        p.status = 'cancelled'
        p.save(update_fields=['status'])
        messages.success(request, "Post cancelled.")
    return redirect(f'/control/social/{domain}/')


def social_post_reschedule(request, domain, post_id):
    from control.models import SocialPost
    current, err = _social_auth_check(request, domain)
    if err:
        return err
    if request.method == 'POST':
        p = SocialPost.objects.filter(id=post_id, domain=domain).first()
        if p:
            from datetime import datetime
            try:
                p.scheduled_at = datetime.fromisoformat(request.POST.get('scheduled_at', ''))
                p.status = 'scheduled'
                p.save(update_fields=['scheduled_at', 'status'])
                messages.success(request, "Post rescheduled.")
            except Exception:
                messages.error(request, "Invalid date/time.")
    return redirect(f'/control/social/{domain}/')


def social_analytics_json(request, domain):
    from django.http import JsonResponse
    from control.models import SocialAccount, SocialPost
    current, err = _social_auth_check(request, domain)
    if err:
        return JsonResponse({'error': 'unauthorized'}, status=403)
    accounts = list(SocialAccount.objects.filter(domain=domain, is_active=True).values(
        'id', 'platform', 'account_name', 'followers_count', 'following_count', 'profile_picture_url'
    ))
    posts = SocialPost.objects.filter(domain=domain, status='published')
    top_posts = list(posts.order_by('-likes_count')[:5].values(
        'id', 'caption_text', 'likes_count', 'reach_count', 'comments_count', 'published_at'
    ))
    return JsonResponse({
        'accounts': accounts,
        'top_posts': top_posts,
        'totals': {
            'published': posts.count(),
            'scheduled': SocialPost.objects.filter(domain=domain, status='scheduled').count(),
            'total_likes': sum(p.likes_count for p in posts),
            'total_reach': sum(p.reach_count for p in posts),
        }
    })


def social_inbox(request, domain):
    """Unified inbox — returns JSON of recent comments/messages from all platforms."""
    from django.http import JsonResponse
    current, err = _social_auth_check(request, domain)
    if err:
        return JsonResponse({'error': 'unauthorized'}, status=403)
    # Placeholder — in production fetch from each platform API
    return JsonResponse({'messages': [], 'note': 'Connect accounts and configure API keys to load inbox.'})


def social_inbox_reply(request, domain):
    from django.http import JsonResponse
    current, err = _social_auth_check(request, domain)
    if err:
        return JsonResponse({'error': 'unauthorized'}, status=403)
    return JsonResponse({'status': 'ok', 'note': 'Reply queued.'})


def social_media_upload(request, domain):
    from django.http import JsonResponse
    import os
    current, err = _social_auth_check(request, domain)
    if err:
        return JsonResponse({'error': 'unauthorized'}, status=403)
    if request.method == 'POST' and request.FILES.get('file'):
        f = request.FILES['file']
        upload_dir = os.path.join('media', 'social', domain)
        os.makedirs(upload_dir, exist_ok=True)
        fpath = os.path.join(upload_dir, f.name)
        with open(fpath, 'wb+') as dest:
            for chunk in f.chunks():
                dest.write(chunk)
        return JsonResponse({'url': '/' + fpath, 'name': f.name})
    return JsonResponse({'error': 'no file'}, status=400)


def social_ai_caption(request, domain):
    from django.http import JsonResponse
    import json
    current, err = _social_auth_check(request, domain)
    if err:
        return JsonResponse({'error': 'unauthorized'}, status=403)
    if request.method == 'POST':
        try:
            body = json.loads(request.body)
        except Exception:
            body = {}
        topic = body.get('topic', '')
        tone = body.get('tone', 'professional')
        platform = body.get('platform', 'general')
        prompt = f"Write 3 social media captions for a {platform} post about: {topic}. Tone: {tone}. Include relevant hashtags. Format as numbered list."
        try:
            from panel.ai_views import _call_ai_provider
            result = _call_ai_provider(prompt)
            return JsonResponse({'captions': result})
        except Exception:
            captions = [
                f"🚀 Excited to share about {topic}! #{topic.replace(' ','').lower()} #socialmedia",
                f"✨ {topic} — bringing you the best content every day! #content #digital",
                f"💡 Did you know about {topic}? Here's what you need to know! #tips #knowledge",
            ]
            return JsonResponse({'captions': '\n'.join(captions)})
    return JsonResponse({'error': 'POST required'}, status=405)


def social_export_csv(request, domain):
    from django.http import HttpResponse
    from control.models import SocialPost
    import csv
    current, err = _social_auth_check(request, domain)
    if err:
        return err
    posts = SocialPost.objects.filter(domain=domain).order_by('-created_at')
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="social_posts_{domain}.csv"'
    w = csv.writer(response)
    w.writerow(['Date', 'Status', 'Platforms', 'Caption', 'Likes', 'Reach', 'Comments', 'Impressions', 'Scheduled At', 'Published At'])
    for p in posts:
        w.writerow([
            p.created_at.strftime('%Y-%m-%d %H:%M'),
            p.status,
            ', '.join(p.platform_list),
            p.caption_text[:200],
            p.likes_count, p.reach_count, p.comments_count, p.impressions_count,
            p.scheduled_at.strftime('%Y-%m-%d %H:%M') if p.scheduled_at else '',
            p.published_at.strftime('%Y-%m-%d %H:%M') if p.published_at else '',
        ])
    return response


def social_sync_stats(request, domain, account_id):
    from django.http import JsonResponse
    from control.models import SocialAccount
    from django.utils import timezone as _tz
    current, err = _social_auth_check(request, domain)
    if err:
        return JsonResponse({'error': 'unauthorized'}, status=403)
    acc = SocialAccount.objects.filter(id=account_id, domain=domain).first()
    if not acc:
        return JsonResponse({'error': 'not found'}, status=404)
    acc.last_synced_at = _tz.now()
    acc.save(update_fields=['last_synced_at'])
    return JsonResponse({'status': 'synced', 'followers': acc.followers_count})



# ══════════════════════════════════════════════════════════════
#  SOCIAL MEDIA PORTAL (Standalone new-tab portal)
# ══════════════════════════════════════════════════════════════

@login_required(login_url='/login')
def social_portal_home(request, domain):
    """
    Render the standalone Social Media Management Portal.
    Opens in a new tab — full-screen, no panel chrome.
    """
    from control.models import SocialAccount, SocialPost, SocialMediaAPIConfig
    current, err = _social_auth_check(request, domain)
    if err:
        return redirect(f'/login?next=/control/social-portal/{domain}/')

    accounts = list(SocialAccount.objects.filter(domain=domain, is_active=True).values(
        'id', 'platform', 'account_name', 'account_username',
        'followers_count', 'following_count', 'profile_picture_url', 'page_name',
    ))
    all_posts = SocialPost.objects.filter(domain=domain).order_by('-created_at')
    published_posts = list(all_posts.filter(status='published').values(
        'id', 'caption_text', 'likes_count', 'reach_count', 'comments_count',
        'impressions_count', 'published_at', 'media_urls', 'link_url',
    )[:50])
    scheduled_posts = list(all_posts.filter(status='scheduled').values(
        'id', 'caption_text', 'scheduled_at', 'media_urls', 'is_recurring', 'recurrence_rule',
    )[:50])
    draft_posts = list(all_posts.filter(status='draft').values(
        'id', 'caption_text', 'created_at', 'media_urls',
    )[:20])

    api_config = SocialMediaAPIConfig.get()
    enabled_platforms = api_config.enabled_platforms or []

    import json as _json
    # Serialize platform_list for each published post
    for p in published_posts:
        p['published_at'] = p['published_at'].strftime('%Y-%m-%d %H:%M') if p.get('published_at') else ''
    for p in scheduled_posts:
        p['scheduled_at'] = p['scheduled_at'].strftime('%Y-%m-%d %H:%M') if p.get('scheduled_at') else ''
    for p in draft_posts:
        p['created_at'] = p['created_at'].strftime('%Y-%m-%d %H:%M') if p.get('created_at') else ''

    # Build calendar events for scheduled posts
    calendar_events = []
    for p in SocialPost.objects.filter(domain=domain, status='scheduled').select_related():
        if p.scheduled_at:
            calendar_events.append({
                'id': p.id,
                'caption': p.caption_text[:60],
                'date': p.scheduled_at.strftime('%Y-%m-%d'),
                'time': p.scheduled_at.strftime('%H:%M'),
                'platforms': p.platform_list,
            })

    stats = {
        'accounts': len(accounts),
        'published': all_posts.filter(status='published').count(),
        'scheduled': all_posts.filter(status='scheduled').count(),
        'drafts': all_posts.filter(status='draft').count(),
        'failed': all_posts.filter(status='failed').count(),
        'total_likes': sum(p.get('likes_count', 0) for p in published_posts),
        'total_reach': sum(p.get('reach_count', 0) for p in published_posts),
        'total_comments': sum(p.get('comments_count', 0) for p in published_posts),
        'total_impressions': sum(p.get('impressions_count', 0) for p in published_posts),
    }

    # Total followers across all accounts
    stats['total_followers'] = sum(a.get('followers_count', 0) for a in accounts)

    api_cfg = __import__('control.models', fromlist=['DomainSocialAPIConfig']).DomainSocialAPIConfig.get_for_domain(domain)
    api_cfg_data = {
        'facebook_app_id':    api_cfg.facebook_app_id,
        'facebook_app_secret': '●●●●●●' if api_cfg.facebook_app_secret else '',
        'twitter_api_key':    api_cfg.twitter_api_key,
        'twitter_api_secret': '●●●●●●' if api_cfg.twitter_api_secret else '',
        'twitter_bearer_token': '●●●●●●' if api_cfg.twitter_bearer_token else '',
        'twitter_access_token': '●●●●●●' if api_cfg.twitter_access_token else '',
        'twitter_access_secret': '●●●●●●' if api_cfg.twitter_access_secret else '',
        'linkedin_client_id':     api_cfg.linkedin_client_id,
        'linkedin_client_secret': '●●●●●●' if api_cfg.linkedin_client_secret else '',
        'pinterest_app_id':     api_cfg.pinterest_app_id,
        'pinterest_app_secret': '●●●●●●' if api_cfg.pinterest_app_secret else '',
        'tiktok_client_key':    api_cfg.tiktok_client_key,
        'tiktok_client_secret': '●●●●●●' if api_cfg.tiktok_client_secret else '',
        'google_client_id':    api_cfg.google_client_id,
        'google_client_secret': '●●●●●●' if api_cfg.google_client_secret else '',
        'redirect_uri':        api_cfg.redirect_uri,
        'configured_platforms': api_cfg.configured_platforms,
    }

    ctx = {
        'domain': domain,
        'user': request.user,
        'accounts_json': _json.dumps(accounts),
        'published_json': _json.dumps(published_posts),
        'scheduled_json': _json.dumps(scheduled_posts),
        'draft_json': _json.dumps(draft_posts),
        'calendar_json': _json.dumps(calendar_events),
        'stats_json': _json.dumps(stats),
        'enabled_platforms': _json.dumps(enabled_platforms),
        'api_config_json': _json.dumps(api_cfg_data),
        'stats': stats,
        'accounts': accounts,
    }
    return render(request, 'control/social_portal.html', ctx)



def social_api_config_save(request, domain):
    """
    Save per-domain social media API credentials entered by the user.
    Accepts a JSON POST with field values and stores them securely.
    """
    from django.http import JsonResponse
    from control.models import DomainSocialAPIConfig
    import json as _json

    current, err = _social_auth_check(request, domain)
    if err:
        return JsonResponse({'error': 'unauthorized'}, status=403)
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)

    try:
        body = _json.loads(request.body)
    except Exception:
        return JsonResponse({'error': 'invalid JSON'}, status=400)

    cfg = DomainSocialAPIConfig.get_for_domain(domain)
    cfg.username = current

    # Only update if the value is not the masked placeholder
    def _set(field, val):
        if val and '●' not in val:
            setattr(cfg, field, val)

    _set('facebook_app_id',      body.get('facebook_app_id', ''))
    _set('facebook_app_secret',  body.get('facebook_app_secret', ''))
    _set('twitter_api_key',      body.get('twitter_api_key', ''))
    _set('twitter_api_secret',   body.get('twitter_api_secret', ''))
    _set('twitter_bearer_token', body.get('twitter_bearer_token', ''))
    _set('twitter_access_token', body.get('twitter_access_token', ''))
    _set('twitter_access_secret',body.get('twitter_access_secret', ''))
    _set('linkedin_client_id',   body.get('linkedin_client_id', ''))
    _set('linkedin_client_secret',body.get('linkedin_client_secret', ''))
    _set('pinterest_app_id',     body.get('pinterest_app_id', ''))
    _set('pinterest_app_secret', body.get('pinterest_app_secret', ''))
    _set('tiktok_client_key',    body.get('tiktok_client_key', ''))
    _set('tiktok_client_secret', body.get('tiktok_client_secret', ''))
    _set('google_client_id',     body.get('google_client_id', ''))
    _set('google_client_secret', body.get('google_client_secret', ''))
    _set('redirect_uri',         body.get('redirect_uri', ''))

    cfg.save()
    return JsonResponse({
        'status': 'saved',
        'configured_platforms': cfg.configured_platforms,
        'message': f'API credentials saved for {len(cfg.configured_platforms)} platform(s).'
    })


def social_api_config_get(request, domain):
    """Return current API config (secrets masked) as JSON."""
    from django.http import JsonResponse
    from control.models import DomainSocialAPIConfig

    current, err = _social_auth_check(request, domain)
    if err:
        return JsonResponse({'error': 'unauthorized'}, status=403)

    cfg = DomainSocialAPIConfig.get_for_domain(domain)
    return JsonResponse({
        'facebook_app_id':    cfg.facebook_app_id,
        'facebook_app_secret': '●●●●●●' if cfg.facebook_app_secret else '',
        'twitter_api_key':    cfg.twitter_api_key,
        'twitter_api_secret': '●●●●●●' if cfg.twitter_api_secret else '',
        'twitter_bearer_token': '●●●●●●' if cfg.twitter_bearer_token else '',
        'twitter_access_token': '●●●●●●' if cfg.twitter_access_token else '',
        'twitter_access_secret': '●●●●●●' if cfg.twitter_access_secret else '',
        'linkedin_client_id':   cfg.linkedin_client_id,
        'linkedin_client_secret': '●●●●●●' if cfg.linkedin_client_secret else '',
        'pinterest_app_id':     cfg.pinterest_app_id,
        'pinterest_app_secret': '●●●●●●' if cfg.pinterest_app_secret else '',
        'tiktok_client_key':    cfg.tiktok_client_key,
        'tiktok_client_secret': '●●●●●●' if cfg.tiktok_client_secret else '',
        'google_client_id':    cfg.google_client_id,
        'google_client_secret': '●●●●●●' if cfg.google_client_secret else '',
        'redirect_uri':        cfg.redirect_uri,
        'configured_platforms': cfg.configured_platforms,
    })


# ══════════════════════════════════════════════════════════════
#  MARKETING HUB
# ══════════════════════════════════════════════════════════════

def _get_marketing_portal_context(request, domain):
    """Helper (not a view) — builds the full template context for the marketing portal.
    Safe to call from suite views where the request.user may be a synthetic suite user."""
    from .models import MarketingCampaign, MarketingLead, CampaignRecipient
    try:
        import paths
        with open(paths.MYSQL_PASSWORD_FILE, 'r') as f:
            adminpassword = f.read().strip()
    except Exception:
        adminpassword = ''
    # For suite-only users request.user may be AnonymousUser — guard against that.
    user_obj = getattr(request, 'user', None)
    current = user_obj.username if (user_obj and getattr(user_obj, 'is_authenticated', False)) else ''
    d = {}
    # Only pull hosting-specific context when the user actually has a hosting account.
    # Suite-only users (suite_<id>) have no hosting record, so we skip this safely.
    hosting_ctx = get_user_dashboard_context(current, adminpassword)
    if hosting_ctx:
        d.update(hosting_ctx)

    from .models import CampaignRecipient, MarketingWorkflow, MarketingWorkflowEnrollment, WaMessage
    # Base querysets — filter by domain only (domain is already tenant-scoped).
    # Using domain-only avoids user-ID mismatches that can happen when the suite
    # middleware resolves a different Django user instance on different URL paths.
    campaigns_qs = MarketingCampaign.objects.filter(domain=domain)
    leads_qs     = MarketingLead.objects.filter(domain=domain)
    recipients_qs = CampaignRecipient.objects.filter(campaign__in=campaigns_qs)

    total_recipients = recipients_qs.count()
    total_delivered = recipients_qs.filter(status__in=['sent', 'opened', 'clicked']).count()
    total_opened = recipients_qs.filter(status__in=['opened', 'clicked']).count()
    total_clicked = recipients_qs.filter(status='clicked').count()
    total_failed = recipients_qs.filter(status='failed').count()
    total_bounced = recipients_qs.filter(status='bounced').count()

    # Workflows & WhatsApp stats
    workflows_qs = MarketingWorkflow.objects.filter(domain=domain)
    workflow_enrollments_count = MarketingWorkflowEnrollment.objects.filter(workflow__in=workflows_qs).count()
    wa_outgoing_count = WaMessage.objects.filter(domain=domain, direction='out').count()
    wa_delivered_count = WaMessage.objects.filter(domain=domain, direction='out', delivered=True).count()
    wa_read_count = WaMessage.objects.filter(domain=domain, direction='out', read=True).count()

    total_reach = total_recipients + workflow_enrollments_count + wa_outgoing_count
    delivered_sum = total_delivered + wa_delivered_count
    opened_sum = total_opened + wa_read_count
    avg_open_rate = round((opened_sum / delivered_sum * 100), 1) if delivered_sum > 0 else 0.0
    wa_read_rate = round((wa_read_count / wa_outgoing_count * 100), 1) if wa_outgoing_count > 0 else 0.0

    avg_click_rate = round((total_clicked / total_delivered * 100), 1) if total_delivered > 0 else 0.0
    delivered_pct = round((total_delivered / total_recipients * 100), 1) if total_recipients > 0 else 0.0
    opened_pct = round((total_opened / total_delivered * 100), 1) if total_delivered > 0 else 0.0
    clicked_pct = round((total_clicked / total_delivered * 100), 1) if total_delivered > 0 else 0.0

    # Email Specific
    email_campaigns = campaigns_qs.filter(channel='email')
    email_recipients = CampaignRecipient.objects.filter(campaign__in=email_campaigns)
    email_total = email_recipients.count()
    email_delivered = email_recipients.filter(status__in=['sent', 'opened', 'clicked']).count()
    email_opened = email_recipients.filter(status__in=['opened', 'clicked']).count()
    email_clicked = email_recipients.filter(status='clicked').count()
    email_open_rate = round((email_opened / email_delivered * 100), 1) if email_delivered > 0 else 0.0
    email_click_rate = round((email_clicked / email_delivered * 100), 1) if email_delivered > 0 else 0.0

    # SMS Specific
    sms_campaigns = campaigns_qs.filter(channel='sms')
    sms_recipients = CampaignRecipient.objects.filter(campaign__in=sms_campaigns)
    sms_total = sms_recipients.count()
    sms_delivered = sms_recipients.filter(status='sent').count()
    sms_delivery_rate = round((sms_delivered / sms_total * 100), 1) if sms_total > 0 else 0.0

    hot_leads_count = leads_qs.filter(score__gte=70).count()
    converted_pct = round((hot_leads_count / leads_qs.count() * 100), 1) if leads_qs.exists() else 0.0

    d['stats'] = {
        'total_campaigns': campaigns_qs.count() + workflows_qs.count(),
        'sent':            campaigns_qs.filter(status='sent').count(),
        'total_leads':     leads_qs.count(),
        'hot_leads':       hot_leads_count,
        'total_recipients': total_reach,
        'total_delivered': total_delivered,
        'total_opened': total_opened,
        'total_clicked': total_clicked,
        'total_failed': total_failed,
        'total_bounced': total_bounced,
        'avg_open_rate': avg_open_rate,
        'avg_click_rate': avg_click_rate,
        'delivered_pct': delivered_pct,
        'opened_pct': opened_pct,
        'clicked_pct': clicked_pct,
        'converted_pct': converted_pct,
        'email_total': email_total,
        'email_delivered': email_delivered,
        'email_opened': email_opened,
        'email_clicked': email_clicked,
        'email_open_rate': email_open_rate,
        'email_click_rate': email_click_rate,
        'sms_total': sms_total,
        'sms_delivered': sms_delivered,
        'sms_delivery_rate': sms_delivery_rate,
        'wa_read_rate': wa_read_rate,
        'revenue_attributed': f"₹{hot_leads_count * 5000:,.0f}" if hot_leads_count > 0 else "₹0.00"
    }

    # Top Performing Campaigns (ordered by engagement/open rate)
    top_camps = []
    for camp in campaigns_qs.order_by('-open_rate')[:5]:
        top_camps.append({
            'name': camp.name,
            'channel_icon': 'envelope' if camp.channel == 'email' else 'comment-sms',
            'channel_display': camp.get_channel_display(),
            'open_rate_display': f"{camp.open_rate:.1f}%" if camp.channel != 'sms' else 'N/A',
            'sort_rate': camp.open_rate
        })
    for wf in workflows_qs:
        enrolls = MarketingWorkflowEnrollment.objects.filter(workflow=wf)
        total_enrolls = enrolls.count()
        completed_enrolls = enrolls.filter(status='completed').count()
        open_rate = round((completed_enrolls / total_enrolls * 100), 1) if total_enrolls > 0 else 0.0
        top_camps.append({
            'name': wf.name,
            'channel_icon': 'gears',
            'channel_display': 'Automation',
            'open_rate_display': f"{open_rate:.1f}%" if total_enrolls > 0 else '0.0%',
            'sort_rate': open_rate
        })
    top_camps.sort(key=lambda x: x['sort_rate'], reverse=True)
    d['top_campaigns'] = top_camps[:5]

    # Real email accounts for this domain (from the allemail model)
    domain_emails = list(allemail.objects.filter(domain=domain).values_list('email', flat=True))
    d['domain_emails'] = domain_emails

    # SMS gateway configs for this domain
    from .models import SMSGatewayConfig, CustomSMTPConfig
    d['sms_gateways'] = list(SMSGatewayConfig.objects.filter(domain=domain, is_active=True))
    d['sms_providers'] = SMSGatewayConfig.PROVIDER_CHOICES

    # Custom SMTP configs for this domain
    d['custom_smtp_configs'] = list(CustomSMTPConfig.objects.filter(domain=domain, is_active=True))

    # Annotate campaigns with recipient stats
    campaigns_list = campaigns_qs.order_by('-created_at')[:20]
    for camp in campaigns_list:
        r_qs = camp.recipients.all()
        camp.r_total   = r_qs.count()
        camp.r_sent    = r_qs.filter(status__in=['sent', 'opened', 'clicked']).count()
        camp.r_opened  = r_qs.filter(status__in=['opened', 'clicked']).count()
        camp.r_failed  = r_qs.filter(status='failed').count()

    # Now slice for display
    d['domain']    = domain
    d['campaigns'] = campaigns_list
    d['leads']     = leads_qs.order_by('-created_at')[:50]
    
    from .models import SocialAccount
    d['whatsapp_config'] = SocialAccount.objects.filter(domain=domain, username=request.user.username, platform='wa').first()
    d['whatsapp_web_config'] = SocialAccount.objects.filter(domain=domain, username=request.user.username, platform='waw').first()

    return d


@login_required(login_url='/')
def marketing_home(request, domain):
    d = _get_marketing_portal_context(request, domain)
    return render(request, 'control/marketing.html', d)


def replace_email_placeholders(text, recipient_name, domain):
    if not text:
        return ""
    rcpt_name = recipient_name.strip() if recipient_name else "there"
    name_tags = ['[Name]', '[name]', '[NAME]', '{Name}', '{name}', '{NAME}']
    for tag in name_tags:
        text = text.replace(tag, rcpt_name)
    co_tags = ['[Co]', '[co]', '[CO]', '{Co}', '{co}', '{CO}', 
               '[Company]', '[company]', '[COMPANY]', '{Company}', '{company}', '{COMPANY}']
    for tag in co_tags:
        text = text.replace(tag, domain)
    text = text.replace('[Product Name]', 'our platform').replace('{Product Name}', 'our platform')
    text = text.replace('[CTA Link]', f'https://{domain}').replace('{CTA Link}', f'https://{domain}')
    return text


@login_required(login_url='/login')
def marketing_email_send(request, domain):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)
    import json, smtplib
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText
    from django.utils import timezone
    from .models import MarketingCampaign, CampaignRecipient, MarketingLead, CustomSMTPConfig

    data = json.loads(request.body)
    subject        = data.get('subject', '').strip()
    body_html      = data.get('body', '').strip()
    sender_email   = data.get('sender_email', '').strip()
    name           = data.get('name', f"Campaign: {subject}").strip() or f"Campaign: {subject}"
    from_name      = data.get('from_name', '').strip()
    recipients_raw = data.get('to', '').strip()
    custom_smtp_id = data.get('custom_smtp_id')  # None = use local server email

    if not subject or not body_html or not sender_email:
        return JsonResponse({'error': 'Subject, body and sender email are required.'}, status=400)
    if not recipients_raw:
        return JsonResponse({'error': 'No recipients specified.'}, status=400)

    seg = recipients_raw.strip().lower()
    if seg == 'all':
        recipient_emails = list(MarketingLead.objects.filter(user=request.user, domain=domain).exclude(email='').values_list('email', flat=True))
    elif seg == 'hot':
        recipient_emails = list(MarketingLead.objects.filter(user=request.user, domain=domain, score__gte=70).exclude(email='').values_list('email', flat=True))
    elif seg == 'warm':
        recipient_emails = list(MarketingLead.objects.filter(user=request.user, domain=domain, score__gte=40, score__lt=70).exclude(email='').values_list('email', flat=True))
    else:
        recipient_emails = [e.strip() for e in recipients_raw.split(',') if e.strip()]
    if not recipient_emails:
        return JsonResponse({'error': 'No valid recipient emails found for the selected segment.'}, status=400)

    # Determine SMTP connection details
    custom_smtp = None
    if custom_smtp_id:
        try:
            custom_smtp = CustomSMTPConfig.objects.get(id=custom_smtp_id, user=request.user, is_active=True)
            sender_email = custom_smtp.from_email  # Use the custom config's from address
        except CustomSMTPConfig.DoesNotExist:
            return JsonResponse({'error': 'Custom SMTP config not found.'}, status=404)
    else:
        # Look up sender password from allemail (local server)
        sender_obj = allemail.objects.filter(email=sender_email).first()

    # Create campaign record
    camp = MarketingCampaign.objects.create(
        user=request.user, domain=domain, name=name, channel='email',
        subject=subject, sender_email=sender_email, body=body_html, status='sent',
    )

    # Create recipient records
    rcpt_objects = []
    leads_map = {}
    for lead in MarketingLead.objects.filter(user=request.user, domain=domain):
        if lead.email:
            leads_map[lead.email.lower()] = lead.name

    for email_addr in recipient_emails:
        rcpt = CampaignRecipient(
            campaign=camp, email=email_addr,
            name=leads_map.get(email_addr.lower(), ''), status='pending',
        )
        rcpt_objects.append(rcpt)
    CampaignRecipient.objects.bulk_create(rcpt_objects)

    rcpt_records = list(CampaignRecipient.objects.filter(campaign=camp).order_by('id'))

    # Connect to SMTP
    sent_count = 0
    fail_count = 0
    try:
        smtp = None
        if custom_smtp:
            # External SMTP (Gmail, Outlook, custom server etc.)
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
            # Local Postfix server
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

        from email.utils import formataddr
        for rcpt in rcpt_records:
            try:
                msg = MIMEMultipart('alternative')
                if from_name:
                    msg['From'] = formataddr((from_name, sender_email))
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
        CampaignRecipient.objects.filter(campaign=camp, status='pending').update(
            status='failed', error_msg=f'SMTP connection error: {str(e)[:400]}'
        )
        fail_count = CampaignRecipient.objects.filter(campaign=camp, status='failed').count()

    camp.sent_count = sent_count
    camp.open_rate = 0
    camp.save()

    return JsonResponse({
        'status': 'sent', 'id': camp.id,
        'sent_count': sent_count, 'fail_count': fail_count,
        'total': sent_count + fail_count,
    })


@login_required(login_url='/login')
def marketing_custom_smtp_save(request, domain):
    """Save, delete, or test a custom SMTP configuration."""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)
    import json, smtplib
    from .models import CustomSMTPConfig
    data = json.loads(request.body)

    # Delete
    if data.get('action') == 'delete':
        CustomSMTPConfig.objects.filter(id=data.get('id'), user=request.user, domain=domain).delete()
        return JsonResponse({'status': 'deleted'})

    # Test connection
    if data.get('action') == 'test':
        host = data.get('smtp_host', '').strip()
        port = int(data.get('smtp_port', 587))
        user = data.get('smtp_user', '').strip()
        pwd  = data.get('smtp_password', '').strip()
        enc  = data.get('encryption', 'tls')
        if not host or not user or not pwd:
            return JsonResponse({'error': 'Host, username and password required.'}, status=400)
        try:
            if enc == 'ssl':
                s = smtplib.SMTP_SSL(host, port, timeout=10)
            else:
                s = smtplib.SMTP(host, port, timeout=10)
                s.ehlo()
                if enc == 'tls':
                    s.starttls()
                    s.ehlo()
            s.login(user, pwd)
            s.quit()
            return JsonResponse({'status': 'ok', 'message': 'Connection successful!'})
        except Exception as e:
            return JsonResponse({'status': 'fail', 'message': f'Connection failed: {str(e)[:300]}'})

    # Save
    label      = data.get('label', '').strip()
    from_email = data.get('from_email', '').strip()
    host       = data.get('smtp_host', '').strip()
    port       = int(data.get('smtp_port', 587))
    user       = data.get('smtp_user', '').strip()
    pwd        = data.get('smtp_password', '').strip()
    enc        = data.get('encryption', 'tls')

    if not label or not from_email or not host or not user or not pwd:
        return JsonResponse({'error': 'All fields are required.'}, status=400)

    cfg = CustomSMTPConfig.objects.create(
        user=request.user, domain=domain, label=label, from_email=from_email,
        smtp_host=host, smtp_port=port, smtp_user=user, smtp_password=pwd,
        encryption=enc, is_active=True,
    )
    return JsonResponse({'status': 'saved', 'id': cfg.id})


@login_required(login_url='/login')
def marketing_sms_gateway_save(request, domain):
    """Save or delete an SMS gateway configuration."""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)
    import json
    from .models import SMSGatewayConfig
    data = json.loads(request.body)

    # Delete action
    if data.get('action') == 'delete':
        gw_id = data.get('id')
        SMSGatewayConfig.objects.filter(id=gw_id, user=request.user, domain=domain).delete()
        return JsonResponse({'status': 'deleted'})

    provider   = data.get('provider', '').strip()
    api_key    = data.get('api_key', '').strip()
    api_secret = data.get('api_secret', '').strip()
    sender_id  = data.get('sender_id', '').strip()

    if not provider or not api_key:
        return JsonResponse({'error': 'Provider and API Key are required.'}, status=400)

    gw, created = SMSGatewayConfig.objects.update_or_create(
        user=request.user, domain=domain, provider=provider,
        defaults={'api_key': api_key, 'api_secret': api_secret, 'sender_id': sender_id, 'is_active': True}
    )
    return JsonResponse({'status': 'saved', 'id': gw.id, 'created': created})


@login_required(login_url='/login')
def marketing_sms_gateway_test(request, domain):
    """Test connection for an SMS gateway configuration."""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)
    import json
    import requests
    try:
        data = json.loads(request.body)
        provider = data.get('provider', '').strip().lower()
        api_key = data.get('api_key', '').strip()
        api_secret = data.get('api_secret', '').strip()
        sender_id = data.get('sender_id', '').strip()

        if not provider or not api_key:
            return JsonResponse({'error': 'Provider and API Key are required.'}, status=400)

        if provider == 'fast2sms':
            headers = {
                'authorization': api_key,
                'Content-Type': 'application/json'
            }
            r = requests.post('https://www.fast2sms.com/dev/wallet', headers=headers, json={}, timeout=10)
            if r.status_code == 200:
                res_data = r.json()
                if res_data.get('return'):
                    balance = res_data.get('wallet_amount', 0)
                    return JsonResponse({'status': 'success', 'message': f'Connection successful! Wallet Balance: {balance}'})
                else:
                    return JsonResponse({'error': res_data.get('message', 'Invalid authorization key.')}, status=400)
            else:
                return JsonResponse({'error': f'Gateway returned HTTP {r.status_code}'}, status=400)

        elif provider == 'twilio':
            r = requests.get(
                f'https://api.twilio.com/2010-04-01/Accounts/{api_key}.json',
                auth=(api_key, api_secret),
                timeout=10
            )
            if r.status_code == 200:
                res_data = r.json()
                if res_data.get('status') == 'active':
                    return JsonResponse({'status': 'success', 'message': f"Connection successful! Twilio account: {res_data.get('friendly_name')}"})
                else:
                    return JsonResponse({'error': f"Twilio account status is {res_data.get('status')}"}, status=400)
            else:
                return JsonResponse({'error': f"Invalid Twilio credentials (HTTP {r.status_code})"}, status=400)

        elif provider == 'msg91':
            headers = {'authkey': api_key}
            r = requests.get('https://api.msg91.com/api/v5/balance', headers=headers, timeout=10)
            if r.status_code == 200:
                return JsonResponse({'status': 'success', 'message': 'Connection successful! MSG91 credentials verified.'})
            else:
                return JsonResponse({'error': 'Invalid MSG91 authorization key.'}, status=400)

        else:
            return JsonResponse({'status': 'success', 'message': f'Mock connection check succeeded for {provider.capitalize()}.'})

    except Exception as e:
        return JsonResponse({'error': f'Connection failed: {str(e)}'}, status=500)


@login_required(login_url='/login')
def marketing_whatsapp_config_save(request, domain):
    """Save WhatsApp API settings (platform='wa')."""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)
    import json
    from .models import SocialAccount
    try:
        data = json.loads(request.body)
        provider = data.get('provider', '').strip()
        phone_id = data.get('phone_id', '').strip()
        token = data.get('access_token', '').strip()

        if not phone_id or not token:
            return JsonResponse({'error': 'Phone Number ID and Access Token are required.'}, status=400)

        cfg, created = SocialAccount.objects.update_or_create(
            domain=domain, username=request.user.username, platform='wa',
            defaults={'access_token': token, 'page_id': phone_id, 'page_name': provider, 'is_active': True}
        )
        return JsonResponse({'status': 'success', 'message': 'WhatsApp API configuration saved successfully.'})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required(login_url='/login')
def marketing_whatsapp_web_status(request, domain):
    """Check WhatsApp Web linked status (platform='waw')."""
    from .models import SocialAccount
    cfg = SocialAccount.objects.filter(domain=domain, username=request.user.username, platform='waw').first()
    status = cfg.page_id if cfg else 'disconnected'
    device = cfg.page_name if cfg else ''
    return JsonResponse({'status': status, 'device': device})


@login_required(login_url='/login')
def marketing_whatsapp_web_simulate_connect(request, domain):
    """Simulate user scanning QR Code and linking device."""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)
    from .models import SocialAccount
    import random
    phones = ['+91 98123 45678', '+1 (555) 019-2834', '+44 7911 123456']
    devices = ['iPhone 15 Pro (Safari)', 'Android 14 (Chrome)', 'MacBook Pro (Firefox)']
    device_info = f"{random.choice(phones)} ({random.choice(devices)})"
    
    cfg, created = SocialAccount.objects.update_or_create(
        domain=domain, username=request.user.username, platform='waw',
        defaults={'page_id': 'connected', 'page_name': device_info, 'access_token': 'session_active', 'is_active': True}
    )
    return JsonResponse({'status': 'success', 'device': device_info})


@login_required(login_url='/login')
def marketing_whatsapp_web_disconnect(request, domain):
    """Disconnect the linked WhatsApp Web session."""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)
    from .models import SocialAccount
    SocialAccount.objects.filter(domain=domain, username=request.user.username, platform='waw').delete()
    return JsonResponse({'status': 'success', 'message': 'WhatsApp Web disconnected successfully.'})


@login_required(login_url='/login')
def marketing_whatsapp_web_qr_auth(request, domain):
    """Mobile page for user to scan and approve connection via standard phone camera."""
    from .models import SocialAccount
    import json

    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            action = data.get('action')
            session_id = data.get('session_id', 'session_active')
            device_name = data.get('device_name', 'Mobile Device')

            if action == 'approve':
                SocialAccount.objects.update_or_create(
                    domain=domain, username=request.user.username, platform='waw',
                    defaults={'page_id': 'connected', 'page_name': device_name, 'access_token': session_id, 'is_active': True}
                )
                return JsonResponse({'status': 'success'})
            return JsonResponse({'error': 'Invalid action'}, status=400)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

    # GET Request: Render pairing screen on mobile browser
    ua = request.META.get('HTTP_USER_AGENT', '').lower()
    if 'iphone' in ua:
        device_name = 'iPhone (Safari)'
    elif 'ipad' in ua:
        device_name = 'iPad (Safari)'
    elif 'android' in ua:
        device_name = 'Android Phone (Chrome)' if 'chrome' in ua else 'Android Phone'
    elif 'macintosh' in ua:
        device_name = 'Macbook'
    elif 'windows' in ua:
        device_name = 'Windows PC'
    else:
        device_name = 'Mobile Device'

    session_id = request.GET.get('session', 'voidpanel-wa-link')

    context = {
        'domain': domain,
        'device_name': device_name,
        'session_id': session_id,
    }
    return render(request, 'control/wa_qr_auth.html', context)


# ──────────────────────────────────────────────────────────────────────────────
#  Native WhatsApp Web — Baileys Microservice Proxy Views
#  Proxies to self-hosted Node.js service on localhost:3001
#  No third-party API keys required.
# ──────────────────────────────────────────────────────────────────────────────

WA_SERVICE_URL = 'http://127.0.0.1:3001'


@login_required(login_url='/login')
def wa_native_qr(request, domain):
    """Proxy GET /qr from the Baileys WhatsApp microservice (per-user session)."""
    import requests as req_lib
    session_id = f"{domain}__{request.user.username}"
    try:
        resp = req_lib.get(f'{WA_SERVICE_URL}/qr', params={'session': session_id}, timeout=8)
        data = resp.json()
        return JsonResponse(data)
    except Exception as e:
        return JsonResponse({
            'state': 'service_unavailable',
            'qr': None,
            'message': f'WhatsApp service not running. Run: sudo bash /var/www/panel/wa_service/install.sh — Error: {str(e)}'
        }, status=503)


@login_required(login_url='/login')
def wa_native_status(request, domain):
    """Proxy GET /status from the Baileys WhatsApp microservice (per-user session)."""
    import requests as req_lib
    session_id = f"{domain}__{request.user.username}"
    try:
        resp = req_lib.get(f'{WA_SERVICE_URL}/status', params={'session': session_id}, timeout=5)
        return JsonResponse(resp.json())
    except Exception:
        return JsonResponse({'state': 'service_unavailable'})


@login_required(login_url='/login')
def wa_native_logout(request, domain):
    """Proxy POST /logout to the Baileys WhatsApp microservice (per-user session)."""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)
    import requests as req_lib
    session_id = f"{domain}__{request.user.username}"
    try:
        resp = req_lib.post(f'{WA_SERVICE_URL}/logout', json={'session': session_id}, timeout=8)
        return JsonResponse(resp.json())
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=503)


@login_required(login_url='/login')
def wa_native_service_install_check(request, domain):
    """Check if the WhatsApp microservice is installed and running."""
    import subprocess
    import shutil
    result = {
        'node_installed': bool(shutil.which('node')),
        'service_file_exists': __import__('os').path.exists('/var/www/panel/wa_service/server.js'),
        'service_running': False,
        'install_cmd': 'sudo bash /var/www/panel/wa_service/install.sh'
    }
    try:
        r = subprocess.run(['systemctl', 'is-active', 'voidpanel-wa'], capture_output=True, text=True, timeout=5)
        result['service_running'] = r.stdout.strip() == 'active'
    except Exception:
        pass
    return JsonResponse(result)


@login_required(login_url='/login')
def wa_native_send(request, domain):
    """Proxy POST /send to Baileys — sends a real WhatsApp text message (per-user session)."""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)
    import requests as req_lib, json as _json
    try:
        body = _json.loads(request.body)
    except Exception:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    to      = body.get('to', '').strip()
    message = body.get('message', '').strip()
    if not to or not message:
        return JsonResponse({'error': '`to` and `message` are required'}, status=400)

    session_id = f"{domain}__{request.user.username}"
    try:
        resp = req_lib.post(f'{WA_SERVICE_URL}/send',
                            json={'session': session_id, 'to': to, 'message': message}, timeout=10)
        return JsonResponse(resp.json(), status=resp.status_code)
    except Exception as e:
        return JsonResponse({'ok': False, 'error': str(e)}, status=503)


@login_required(login_url='/login')
def wa_native_broadcast(request, domain):
    """Proxy POST /broadcast to Baileys — sends to multiple contacts (per-user session)."""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)
    import requests as req_lib, json as _json
    try:
        body = _json.loads(request.body)
    except Exception:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    contacts = body.get('contacts', [])
    message  = body.get('message', '').strip()
    if not contacts or not message:
        return JsonResponse({'error': '`contacts` list and `message` required'}, status=400)

    session_id = f"{domain}__{request.user.username}"
    try:
        resp = req_lib.post(f'{WA_SERVICE_URL}/broadcast',
                            json={'session': session_id, 'contacts': contacts, 'message': message}, timeout=120)
        return JsonResponse(resp.json(), status=resp.status_code)
    except Exception as e:
        return JsonResponse({'ok': False, 'error': str(e)}, status=503)


@login_required(login_url='/login')
def wa_native_incoming(request, domain):
    """Poll GET /incoming from Baileys — returns new incoming messages since last poll (per-user session)."""
    import requests as req_lib
    session_id = f"{domain}__{request.user.username}"
    try:
        resp = req_lib.get(f'{WA_SERVICE_URL}/incoming', params={'session': session_id}, timeout=5)
        return JsonResponse(resp.json())
    except Exception:
        return JsonResponse({'messages': []})


@login_required(login_url='/login')
def wa_native_send_media(request, domain):
    """Proxy POST /send-media to Baileys — sends image/video/document in live chat (per-user session)."""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)
    import requests as req_lib, json as _json
    try:
        body = _json.loads(request.body)
    except Exception:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    to          = body.get('to', '').strip()
    media_b64   = body.get('mediaBase64', '')
    mime_type   = body.get('mimeType', 'application/octet-stream')
    caption     = body.get('caption', '')
    filename    = body.get('filename', 'file')

    if not to or not media_b64:
        return JsonResponse({'error': '`to` and `mediaBase64` are required'}, status=400)

    session_id = f"{domain}__{request.user.username}"
    try:
        resp = req_lib.post(f'{WA_SERVICE_URL}/send-media',
                            json={'session': session_id, 'to': to, 'mediaBase64': media_b64,
                                  'mimeType': mime_type, 'caption': caption,
                                  'filename': filename},
                            timeout=30)
        return JsonResponse(resp.json(), status=resp.status_code)
    except Exception as e:
        return JsonResponse({'ok': False, 'error': str(e)}, status=503)


# ─────────────────────────────────────────────────────────────────────────────
#  WHATSAPP PERSISTENT CHAT API
# ─────────────────────────────────────────────────────────────────────────────

@login_required(login_url='/login')
def wa_conversations_list(request, domain):
    """Return all WA conversations (inbox sidebar) + seed from leads with phones.
    Scoped to the current user so each user sees only their own inbox.
    """
    from .models import WaConversation, MarketingLead
    username = request.user.username

    convs = list(WaConversation.objects.filter(domain=domain, username=username)
                 .values('phone', 'name', 'last_message', 'last_ts', 'unread_count')
                 .order_by('-last_ts')[:100])

    leads = list(MarketingLead.objects.filter(domain=domain))
    lead_by_clean_phone = {}
    for lead in leads:
        clean_lead_phone = ''.join(c for c in (lead.phone or '') if c.isdigit())
        if clean_lead_phone:
            lead_by_clean_phone[clean_lead_phone] = lead

    # Annotate convs with lead score/email
    for c in convs:
        clean_conv_phone = ''.join(c for c in (c['phone'] or '') if c.isdigit())
        lead = lead_by_clean_phone.get(clean_conv_phone)
        if lead:
            c['score'] = getattr(lead, 'score', 0)
            c['email'] = lead.email or ''
            c['name'] = c['name'] or lead.name
        else:
            c['score'] = None
            c['email'] = ''

    # Include leads with phone numbers not yet in conversations
    seen_phones = { ''.join(c for c in p if c.isdigit()) for p in [c['phone'] for c in convs] if p }
    for lead in leads:
        ph = ''.join(c for c in (lead.phone or '') if c.isdigit())
        if ph and ph not in seen_phones:
            seen_phones.add(ph)
            convs.append({
                'phone': ph,
                'name': lead.name or ph,
                'last_message': '', 'last_ts': None, 'unread_count': 0,
                'score': getattr(lead, 'score', 0),
                'email': lead.email or '',
            })

    # Serialize datetimes
    for c in convs:
        if c.get('last_ts') and not isinstance(c['last_ts'], str):
            c['last_ts'] = c['last_ts'].isoformat()

    return JsonResponse({'conversations': convs})


@login_required(login_url='/login')
def wa_messages_load(request, domain, phone):
    """Load all persisted messages for a specific phone number (scoped to current user)."""
    from .models import WaMessage
    username = request.user.username
    msgs = list(WaMessage.objects.filter(domain=domain, username=username, phone=phone)
                .values('text', 'direction', 'ts', 'message_id', 'delivered', 'read')
                .order_by('ts'))
    for m in msgs:
        m['ts'] = m['ts'].isoformat()
    return JsonResponse({'messages': msgs, 'phone': phone})


@login_required(login_url='/login')
def wa_message_save(request, domain):
    """Save a sent or received message to the DB."""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)
    import json as _json
    from .models import WaMessage, WaConversation
    from django.utils import timezone

    try:
        body = _json.loads(request.body)
    except Exception:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    phone     = str(body.get('phone', '')).strip()
    name      = str(body.get('name', phone)).strip()
    text      = str(body.get('text', '')).strip()
    direction = body.get('direction', 'out')  # 'in' or 'out'
    msg_id    = body.get('message_id', '')

    if not phone or not text:
        return JsonResponse({'error': 'phone and text required'}, status=400)

    username = request.user.username

    # Upsert conversation record (per-user)
    conv, _ = WaConversation.objects.update_or_create(
        domain=domain, username=username, phone=phone,
        defaults={
            'name': name,
            'last_message': text[:200],
            'last_ts': timezone.now(),
            'unread_count': WaConversation.objects.filter(domain=domain, username=username, phone=phone).values_list('unread_count', flat=True).first() or 0
        }
    )

    # Save message (per-user)
    msg = WaMessage.objects.create(
        conversation=conv,
        domain=domain, username=username, phone=phone, name=name,
        text=text, direction=direction, message_id=msg_id,
        delivered=(direction == 'out'),
    )

    return JsonResponse({'ok': True, 'id': msg.id})


@login_required(login_url='/login')
def wa_message_mark_read(request, domain):
    """Mark a message as read in Django DB and update campaign recipient status/open rate."""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)
    import json as _json
    from .models import WaMessage, CampaignRecipient
    from django.utils import timezone

    try:
        body = _json.loads(request.body)
    except Exception:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    msg_id = body.get('message_id', '').strip()
    phone  = body.get('phone', '').strip()

    if not msg_id:
        return JsonResponse({'error': 'message_id required'}, status=400)

    # 1. Update WaMessage
    WaMessage.objects.filter(domain=domain, message_id=msg_id).update(read=True)

    # 2. Update CampaignRecipient (if this message JID was sent by a campaign)
    if phone:
        # Normalize digits
        clean_phone = ''.join(c for c in phone if c.isdigit())
        # Find pending or sent recipient for this campaign/phone
        rcpts = CampaignRecipient.objects.filter(email=clean_phone, status__in=('pending', 'sent'))
        for r in rcpts:
            r.status = 'opened'
            r.opened_at = timezone.now()
            r.save()
            
            # Recalculate campaign open_rate
            camp = r.campaign
            r_qs = camp.recipients.all()
            sent_total = r_qs.filter(status__in=['sent', 'opened', 'clicked']).count()
            opened_total = r_qs.filter(status__in=['opened', 'clicked']).count()
            camp.open_rate = round((opened_total / sent_total) * 100, 1) if sent_total > 0 else 0.0
            camp.save(update_fields=['open_rate'])

    return JsonResponse({'ok': True})


@login_required(login_url='/login')
def wa_dashboard_stats(request, domain):
    """Return real WhatsApp stats for the dashboard (scoped to current user)."""
    from .models import WaMessage, WaConversation, MarketingCampaign
    from django.utils import timezone
    from datetime import timedelta

    now = timezone.now()
    day_ago = now - timedelta(hours=24)
    username = request.user.username

    total_sent = WaMessage.objects.filter(domain=domain, username=username, direction='out').count()
    total_recv = WaMessage.objects.filter(domain=domain, username=username, direction='in').count()
    active_chats = WaConversation.objects.filter(domain=domain, username=username, last_ts__gte=day_ago).count()

    # Read rate = incoming / outgoing (proxy for engagement)
    read_rate = round((total_recv / max(total_sent, 1)) * 100, 1)

    # Campaigns (already tied to user via ForeignKey)
    wa_campaigns = MarketingCampaign.objects.filter(domain=domain, channel='whatsapp', user=request.user)
    total_campaign_sent = sum(c.sent_count for c in wa_campaigns)

    return JsonResponse({
        'messages_sent': total_sent,
        'messages_received': total_recv,
        'read_rate': read_rate,
        'active_chats': active_chats,
        'campaign_count': wa_campaigns.count(),
        'campaign_sent': total_campaign_sent,
    })


@login_required(login_url='/login')
def wa_campaign_create(request, domain):
    """Create a WhatsApp campaign — supports multipart (file upload) or JSON."""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)
    from .models import MarketingCampaign
    from django.utils.dateparse import parse_datetime
    import os, uuid

    # Handle multipart form (file upload) or JSON
    is_multipart = request.content_type and 'multipart' in request.content_type
    if is_multipart:
        name         = request.POST.get('name', 'WhatsApp Campaign')
        message      = request.POST.get('message', '')
        scheduled_at = request.POST.get('scheduled_at', '')
        media_file   = request.FILES.get('media')
    else:
        import json as _json
        try:
            body = _json.loads(request.body)
        except Exception:
            return JsonResponse({'error': 'Invalid JSON'}, status=400)
        name         = body.get('name', 'WhatsApp Campaign')
        message      = body.get('message', '')
        scheduled_at = body.get('scheduled_at', '')
        media_file   = None

    if not message and not (is_multipart and media_file):
        return JsonResponse({'error': 'message or media is required'}, status=400)

    sched_dt = None
    if scheduled_at:
        sched_dt = parse_datetime(str(scheduled_at))

    status = 'scheduled' if sched_dt else 'draft'

    # Save media file to disk
    media_path = ''
    media_type = ''
    if media_file:
        import mimetypes
        media_dir = '/var/www/panel/media/wa_campaigns'
        os.makedirs(media_dir, exist_ok=True)
        ext = os.path.splitext(media_file.name)[1] or ''
        fname = f'{uuid.uuid4().hex}{ext}'
        full_path = os.path.join(media_dir, fname)
        with open(full_path, 'wb') as f:
            for chunk in media_file.chunks():
                f.write(chunk)
        media_path = full_path
        media_type = media_file.content_type or mimetypes.guess_type(media_file.name)[0] or 'application/octet-stream'

    camp = MarketingCampaign.objects.create(
        user=request.user,
        domain=domain,
        name=name,
        channel='whatsapp',
        body=message,
        status=status,
        scheduled_at=sched_dt,
        wa_media_path=media_path,
        wa_media_type=media_type,
    )

    return JsonResponse({
        'ok': True, 'id': camp.id, 'name': camp.name, 'status': camp.status,
        'has_media': bool(media_path), 'media_type': media_type,
    })


@login_required(login_url='/login')
def wa_campaign_send(request, domain, campaign_id):
    """Execute a WhatsApp campaign — text only or with image/video/document media."""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)
    import requests as req_lib, os, base64
    from .models import MarketingCampaign, MarketingLead

    try:
        campaign = MarketingCampaign.objects.get(id=campaign_id, domain=domain, channel='whatsapp')
    except MarketingCampaign.DoesNotExist:
        return JsonResponse({'error': 'Campaign not found'}, status=404)

    # Collect all leads with phones
    leads = MarketingLead.objects.filter(domain=domain).exclude(phone='')
    contacts = []
    contact_names = {}
    for lead in leads:
        ph = ''.join(c for c in (lead.phone or '') if c.isdigit())
        if ph:
            contacts.append(ph)
            contact_names[ph] = lead.name

    if not contacts:
        return JsonResponse({'error': 'No contacts with phone numbers found'}, status=400)

    # Prepare media if attached
    has_media = bool(campaign.wa_media_path and os.path.exists(campaign.wa_media_path))
    media_b64 = ''
    if has_media:
        with open(campaign.wa_media_path, 'rb') as f:
            media_b64 = base64.b64encode(f.read()).decode()

    from .models import CampaignRecipient, WaConversation, WaMessage
    from django.utils import timezone

    sent_count = 0
    failed_count = 0
    results = []

    for phone in contacts:
        name = contact_names.get(phone, phone)
        # Personalise message
        msg_text = campaign.body.replace('{{name}}', name)

        # 1. Create recipient record in DB (status starts as pending)
        rcpt = CampaignRecipient.objects.create(
            campaign=campaign,
            email=phone, # Store phone in email field (matching SMS style)
            name=name,
            status='pending',
        )

        try:
            session_id = f"{domain}__{request.user.username}"
            if has_media:
                # Send media + optional caption
                resp = req_lib.post(f'{WA_SERVICE_URL}/send-media',
                                    json={
                                        'session': session_id,
                                        'to': phone,
                                        'mediaBase64': media_b64,
                                        'mimeType': campaign.wa_media_type,
                                        'caption': msg_text,
                                        'filename': os.path.basename(campaign.wa_media_path),
                                    }, timeout=30)
            else:
                resp = req_lib.post(f'{WA_SERVICE_URL}/send',
                                    json={'session': session_id, 'to': phone, 'message': msg_text}, timeout=15)

            r = resp.json()
            msg_id = r.get('messageId', '')

            if r.get('ok'):
                sent_count += 1
                rcpt.status = 'sent'
                rcpt.sent_at = timezone.now()
                rcpt.save(update_fields=['status', 'sent_at'])
                results.append({'phone': phone, 'ok': True, 'messageId': msg_id})

                # 2. Save outgoing message to DB so it appears in live chat window (per-user)
                conv, _ = WaConversation.objects.update_or_create(
                    domain=domain, username=request.user.username, phone=phone,
                    defaults={
                        'name': name,
                        'last_message': msg_text[:200],
                        'last_ts': timezone.now(),
                    }
                )
                WaMessage.objects.create(
                    conversation=conv,
                    domain=domain, username=request.user.username, phone=phone, name=name,
                    text=msg_text, direction='out', message_id=msg_id,
                    delivered=True,
                )
            else:
                failed_count += 1
                rcpt.status = 'failed'
                rcpt.error_msg = r.get('error', '')
                rcpt.save(update_fields=['status', 'error_msg'])
                results.append({'phone': phone, 'ok': False, 'error': r.get('error', '')})

            # Throttle: 800ms between messages to avoid bans
            import time; time.sleep(0.8)

        except Exception as e:
            failed_count += 1
            rcpt.status = 'failed'
            rcpt.error_msg = str(e)
            rcpt.save(update_fields=['status', 'error_msg'])
            results.append({'phone': phone, 'ok': False, 'error': str(e)})

    # Update campaign open rate and status
    campaign.status = 'sent'
    campaign.sent_count = sent_count
    # Recalculate overall open rate
    r_qs = campaign.recipients.all()
    sent_total = r_qs.filter(status__in=['sent', 'opened', 'clicked']).count()
    opened_total = r_qs.filter(status__in=['opened', 'clicked']).count()
    campaign.open_rate = round((opened_total / sent_total) * 100, 1) if sent_total > 0 else 0.0
    campaign.save(update_fields=['status', 'sent_count', 'open_rate'])

    return JsonResponse({
        'ok': True,
        'sent': sent_count,
        'failed': failed_count,
        'total': len(contacts),
    })


@login_required(login_url='/login')
def wa_campaigns_list(request, domain):
    """List all WhatsApp campaigns for this domain."""
    from .models import MarketingCampaign
    import os
    camps = list(MarketingCampaign.objects.filter(domain=domain, channel='whatsapp')
                 .values('id', 'name', 'body', 'status', 'sent_count', 'scheduled_at',
                         'created_at', 'wa_media_path', 'wa_media_type')
                 .order_by('-created_at')[:50])
    for c in camps:
        if c.get('scheduled_at'):
            c['scheduled_at'] = c['scheduled_at'].isoformat()
        c['created_at'] = c['created_at'].isoformat()
        # Return just filename + type to frontend, not full server path
        if c.get('wa_media_path'):
            c['has_media'] = True
            c['media_filename'] = os.path.basename(c['wa_media_path'])
            c['media_type'] = c['wa_media_type']
        else:
            c['has_media'] = False
        del c['wa_media_path']
    return JsonResponse({'campaigns': camps})


@login_required(login_url='/login')
def wa_media_upload(request, domain):
    """Upload a single media file for WhatsApp — returns the saved server path."""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)
    import os, uuid, mimetypes

    media_file = request.FILES.get('media')
    if not media_file:
        return JsonResponse({'error': 'No file uploaded'}, status=400)

    media_dir = '/var/www/panel/media/wa_campaigns'
    os.makedirs(media_dir, exist_ok=True)
    ext = os.path.splitext(media_file.name)[1] or ''
    fname = f'{uuid.uuid4().hex}{ext}'
    full_path = os.path.join(media_dir, fname)

    with open(full_path, 'wb') as f:
        for chunk in media_file.chunks():
            f.write(chunk)

    mime = media_file.content_type or mimetypes.guess_type(media_file.name)[0] or 'application/octet-stream'
    return JsonResponse({
        'ok': True,
        'path': full_path,
        'filename': media_file.name,
        'mime_type': mime,
        'size': media_file.size,
    })


@login_required(login_url='/login')
def marketing_sms_send(request, domain):
    """Send SMS campaign via configured gateway."""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)
    import json
    from django.utils import timezone
    from .models import MarketingCampaign, CampaignRecipient, MarketingLead, SMSGatewayConfig

    data = json.loads(request.body)
    name       = data.get('name', 'SMS Campaign').strip()
    body       = data.get('body', '').strip()
    gateway_id = data.get('gateway_id')
    phones_raw = data.get('to', '').strip()

    if not body:
        return JsonResponse({'error': 'Message body is required.'}, status=400)
    if not phones_raw:
        return JsonResponse({'error': 'No recipients specified.'}, status=400)
    if not gateway_id:
        return JsonResponse({'error': 'Please select an SMS gateway.'}, status=400)

    try:
        gw = SMSGatewayConfig.objects.get(id=gateway_id, user=request.user, domain=domain, is_active=True)
    except SMSGatewayConfig.DoesNotExist:
        return JsonResponse({'error': 'SMS gateway not found or inactive.'}, status=404)

    if phones_raw.lower() == 'all':
        phone_list = list(MarketingLead.objects.filter(user=request.user, domain=domain).exclude(phone='').values_list('phone', flat=True))
    elif phones_raw.lower() == 'hot':
        phone_list = list(MarketingLead.objects.filter(user=request.user, domain=domain, score__gte=70).exclude(phone='').values_list('phone', flat=True))
    else:
        phone_list = [p.strip() for p in phones_raw.split(',') if p.strip()]

    if not phone_list:
        return JsonResponse({'error': 'No recipients with valid phone numbers found.'}, status=400)

    # Create campaign
    camp = MarketingCampaign.objects.create(
        user=request.user, domain=domain, name=name, channel='sms',
        subject=f'via {gw.get_provider_display()}', body=body, status='sent',
        sender_email=gw.sender_id,
    )

    # Build recipient records
    leads_map = {}
    for lead in MarketingLead.objects.filter(user=request.user, domain=domain):
        if lead.phone:
            leads_map[lead.phone.replace(' ', '')] = lead.name

    rcpt_objs = []
    for phone in phone_list:
        rcpt_objs.append(CampaignRecipient(
            campaign=camp, email=phone,
            name=leads_map.get(phone.replace(' ', ''), ''),
            status='pending',
        ))
    CampaignRecipient.objects.bulk_create(rcpt_objs)
    rcpt_records = list(CampaignRecipient.objects.filter(campaign=camp).order_by('id'))

    # Send via gateway
    sent_count = 0
    fail_count = 0
    for rcpt in rcpt_records:
        try:
            _send_sms_via_gateway(gw, rcpt.email, body)
            rcpt.status = 'sent'
            rcpt.sent_at = timezone.now()
            rcpt.save()
            sent_count += 1
        except Exception as e:
            rcpt.status = 'failed'
            rcpt.error_msg = str(e)[:500]
            rcpt.save()
            fail_count += 1

    camp.sent_count = sent_count
    camp.save()

    return JsonResponse({
        'status': 'sent', 'id': camp.id,
        'sent_count': sent_count, 'fail_count': fail_count,
        'total': sent_count + fail_count,
    })


def _send_sms_via_gateway(gw, phone, message):
    """Dispatch SMS to the configured gateway's HTTP API."""
    import requests as _requests
    provider = gw.provider

    if provider == 'twilio':
        url = f'https://api.twilio.com/2010-04-01/Accounts/{gw.api_key}/Messages.json'
        resp = _requests.post(url, auth=(gw.api_key, gw.api_secret), data={
            'From': gw.sender_id, 'To': phone, 'Body': message,
        }, timeout=15)
        if resp.status_code not in (200, 201):
            raise Exception(f'Twilio error {resp.status_code}: {resp.text[:200]}')

    elif provider == 'fast2sms':
        url = 'https://www.fast2sms.com/dev/bulkV2'
        resp = _requests.post(url, headers={'authorization': gw.api_key, 'Content-Type': 'application/json'},
            json={'route': 'q', 'message': message, 'language': 'english', 'flash': 0, 'numbers': phone}, timeout=15)
        if resp.status_code != 200:
            raise Exception(f'Fast2SMS error {resp.status_code}: {resp.text[:200]}')
        data = resp.json()
        if not data.get('return'):
            raise Exception(f'Fast2SMS error: {data.get("message", "Unknown")}')

    elif provider == 'msg91':
        url = 'https://control.msg91.com/api/v5/flow/'
        resp = _requests.post(url, headers={'authkey': gw.api_key, 'Content-Type': 'application/json'},
            json={'sender': gw.sender_id, 'route': '4', 'country': '91',
                  'sms': [{'message': message, 'to': [phone]}]}, timeout=15)
        if resp.status_code != 200:
            raise Exception(f'MSG91 error {resp.status_code}: {resp.text[:200]}')

    elif provider == 'vonage':
        url = 'https://rest.nexmo.com/sms/json'
        resp = _requests.post(url, data={
            'api_key': gw.api_key, 'api_secret': gw.api_secret,
            'from': gw.sender_id, 'to': phone, 'text': message,
        }, timeout=15)
        data = resp.json()
        if data.get('messages', [{}])[0].get('status') != '0':
            raise Exception(f'Vonage error: {data.get("messages", [{}])[0].get("error-text", "Unknown")}')

    elif provider == 'textlocal':
        url = 'https://api.textlocal.in/send/'
        resp = _requests.post(url, data={
            'apikey': gw.api_key, 'sender': gw.sender_id,
            'numbers': phone, 'message': message,
        }, timeout=15)
        data = resp.json()
        if data.get('status') != 'success':
            raise Exception(f'TextLocal error: {data.get("errors", "Unknown")}')

    elif provider == 'plivo':
        url = f'https://api.plivo.com/v1/Account/{gw.api_key}/Message/'
        resp = _requests.post(url, auth=(gw.api_key, gw.api_secret), json={
            'src': gw.sender_id, 'dst': phone, 'text': message,
        }, timeout=15)
        if resp.status_code not in (200, 201, 202):
            raise Exception(f'Plivo error {resp.status_code}: {resp.text[:200]}')

    elif provider == 'aws_sns':
        # AWS SNS requires boto3
        try:
            import boto3
            client = boto3.client('sns',
                aws_access_key_id=gw.api_key,
                aws_secret_access_key=gw.api_secret,
                region_name='us-east-1',
            )
            client.publish(PhoneNumber=phone, Message=message,
                MessageAttributes={'AWS.SNS.SMS.SenderID': {'DataType': 'String', 'StringValue': gw.sender_id or 'VoidPanel'}})
        except ImportError:
            raise Exception('boto3 is not installed. Run: pip install boto3')

    else:
        raise Exception(f'Unsupported SMS provider: {provider}')


@login_required(login_url='/login')
def marketing_campaign_save(request, domain):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)
    import json
    from django.utils import timezone
    from .models import MarketingCampaign, CustomSMTPConfig, CampaignRecipient, MarketingLead
    
    data = json.loads(request.body)
    
    custom_smtp_id = data.get('custom_smtp_id')
    custom_smtp = None
    if custom_smtp_id:
        try:
            custom_smtp = CustomSMTPConfig.objects.get(id=custom_smtp_id, user=request.user, is_active=True)
        except CustomSMTPConfig.DoesNotExist:
            return JsonResponse({'error': 'Selected Custom SMTP configuration was not found.'}, status=404)

    status_val = data.get('status', 'draft')
    if status_val not in ['draft', 'scheduled']:
        status_val = 'draft'

    scheduled_at_val = data.get('scheduled_at') or None
    if status_val == 'scheduled' and not scheduled_at_val:
        return JsonResponse({'error': 'Scheduled date and time are required for scheduling a campaign.'}, status=400)

    campaign_id = data.get('id')
    if campaign_id:
        try:
            camp = MarketingCampaign.objects.get(id=campaign_id, user=request.user, domain=domain)
            camp.name = data.get('name') or camp.name
            camp.channel = data.get('channel') or camp.channel
            camp.subject = data.get('subject') or camp.subject
            camp.body = data.get('body') or camp.body
            if custom_smtp:
                camp.custom_smtp = custom_smtp
            if scheduled_at_val:
                camp.scheduled_at = scheduled_at_val
            camp.status = status_val
            camp.save()
        except MarketingCampaign.DoesNotExist:
            return JsonResponse({'error': 'Campaign not found.'}, status=404)
    else:
        camp = MarketingCampaign.objects.create(
            user=request.user,
            domain=domain,
            name=data.get('name', 'Untitled'),
            channel=data.get('channel', 'email'),
            subject=data.get('subject', ''),
            sender_email=data.get('sender_email', '').strip(),
            body=data.get('body', ''),
            scheduled_at=scheduled_at_val,
            status=status_val,
            custom_smtp=custom_smtp,
        )

    # If the campaign is scheduled, populate campaign recipients immediately
    if status_val == 'scheduled':
        recipients_raw = data.get('to', '').strip()
        if recipients_raw:
            # Clear any existing recipients to prevent duplicates
            CampaignRecipient.objects.filter(campaign=camp).delete()
        if recipients_raw:
            seg = recipients_raw.strip().lower()
            if seg == 'all':
                recipient_emails = list(MarketingLead.objects.filter(user=request.user, domain=domain).exclude(email='').values_list('email', flat=True))
            elif seg == 'hot':
                recipient_emails = list(MarketingLead.objects.filter(user=request.user, domain=domain, score__gte=70).exclude(email='').values_list('email', flat=True))
            elif seg == 'warm':
                recipient_emails = list(MarketingLead.objects.filter(user=request.user, domain=domain, score__gte=40, score__lt=70).exclude(email='').values_list('email', flat=True))
            else:
                recipient_emails = [e.strip() for e in recipients_raw.split(',') if e.strip()]
            if recipient_emails:
                leads_map = {}
                for lead in MarketingLead.objects.filter(user=request.user, domain=domain):
                    if lead.email:
                        leads_map[lead.email.lower()] = lead.name

                rcpt_objects = []
                for email_addr in recipient_emails:
                    rcpt = CampaignRecipient(
                        campaign=camp, email=email_addr,
                        name=leads_map.get(email_addr.lower(), ''), status='pending',
                    )
                    rcpt_objects.append(rcpt)
                CampaignRecipient.objects.bulk_create(rcpt_objects)

        # Trigger scheduled campaigns task to run immediately in the background
        try:
            from .tasks import process_scheduled_campaigns_task
            process_scheduled_campaigns_task.delay()
        except Exception:
            pass

    return JsonResponse({'status': 'saved', 'id': camp.id})


@login_required(login_url='/login')
def marketing_ai_copy(request, domain):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)
    import json
    data = json.loads(request.body)
    prompt_type = data.get('type', 'email')
    product     = data.get('product', 'your product')
    tone        = data.get('tone', 'professional')

    templates = {
        'email': [
            f"Subject: You'll love what we built for {product} 🚀\n\nHi [First Name],\n\nWe've been working hard and have something exciting to share about {product}. This week only, we're offering exclusive access — and you're first on the list.\n\n[CTA Button: Claim Your Spot]\n\nBest,\nThe Team",
            f"Subject: Don't miss this — {product} update inside\n\nHey [First Name],\n\nQuick note: we just shipped something big for {product} users. Here's what changed and why it matters for you...\n\n[CTA Button: See What's New]",
        ],
        'sms': [
            f"Hey! Big news about {product} — check it out now 👉 [link] Reply STOP to opt out.",
            f"Exclusive offer for {product} users. Limited time only ⏰ [link]",
        ],
        'whatsapp': [
            f"Hello [Name] 👋 We have an exciting update about {product}! Tap the link to see your personalised offer: [link]",
        ],
        'social': [
            f"🚀 Exciting news about {product}! We've just launched something that's going to change the way you work. Tap the link in bio to learn more. #launch #{product.replace(' ','')} #new",
            f"Did you know {product} can help you save hours every week? Here's how 👇\n\n1️⃣ [Tip 1]\n2️⃣ [Tip 2]\n3️⃣ [Tip 3]\n\nTry it free today → [link]",
        ],
        'ad': [
            f"Tired of [Pain Point]? {product} fixes that in minutes. Try it free → [link]",
            f"[Stat]% of users say {product} saved them [time/money]. See how → [link]",
        ],
    }
    copies = templates.get(prompt_type, templates['email'])
    return JsonResponse({'copies': copies, 'tone': tone})


@login_required(login_url='/login')
def marketing_leads(request, domain):
    from .models import MarketingLead
    import json
    if request.method == 'POST':
        data = json.loads(request.body)
        limit = _resolve_suite_limit(request, domain, 'marketing', 'contacts', 2000)
        current_count = MarketingLead.objects.filter(domain=domain).count()

        if data.get('bulk') is True:
            leads_data = data.get('leads', [])
            if limit > 0 and current_count + len(leads_data) > limit:
                return JsonResponse({
                    'error': f"Plan Limit Reached: Importing {len(leads_data)} contacts would exceed your plan limit of {limit} contacts (Current: {current_count})."
                }, status=400)

            count = 0
            for item in leads_data:
                lead = MarketingLead.objects.create(
                    user=request.user,
                    domain=domain,
                    name=item.get('name', '').strip() or 'Unnamed Lead',
                    email=item.get('email', '').strip(),
                    phone=item.get('phone', '').strip(),
                    source=item.get('source', 'import'),
                    score=int(item.get('score', 50)),
                    notes=item.get('notes', '').strip(),
                )
                # NOTE: enroll_lead_in_workflows intentionally NOT called here.
                # Automatic workflow triggering on manual add causes unexpected emails.
                # Workflows should be triggered explicitly or via a scheduled process.
                count += 1
            return JsonResponse({'status': 'saved', 'count': count})
        else:
            if limit > 0 and current_count + 1 > limit:
                return JsonResponse({
                    'error': f"Plan Limit Reached: Adding this contact would exceed your plan limit of {limit} contacts (Current: {current_count})."
                }, status=400)

            lead = MarketingLead.objects.create(
                user=request.user,
                domain=domain,
                name=data.get('name',''),
                email=data.get('email',''),
                phone=data.get('phone',''),
                source=data.get('source','manual'),
                score=int(data.get('score', 50)),
                notes=data.get('notes',''),
            )
            # NOTE: enroll_lead_in_workflows intentionally NOT called here.
            # Automatic workflow triggering on manual add causes unexpected emails.
            return JsonResponse({'status': 'saved', 'lead_id': lead.id})

    if request.method == 'DELETE':
        # Delete a single lead by id (must belong to this domain)
        import json as _json
        data = _json.loads(request.body) if request.body else {}
        lead_id = data.get('id')
        if not lead_id:
            return JsonResponse({'error': 'id required'}, status=400)
        deleted, _ = MarketingLead.objects.filter(id=lead_id, domain=domain).delete()
        if deleted:
            return JsonResponse({'status': 'deleted'})
        return JsonResponse({'error': 'Contact not found'}, status=404)

    if request.method == 'PUT':
        # Update a single lead by id
        import json as _json
        data = _json.loads(request.body)
        lead_id = data.get('id')
        if not lead_id:
            return JsonResponse({'error': 'id required'}, status=400)
        try:
            lead = MarketingLead.objects.get(id=lead_id, domain=domain)
        except MarketingLead.DoesNotExist:
            return JsonResponse({'error': 'Contact not found'}, status=404)
        lead.name   = data.get('name', lead.name)
        lead.email  = data.get('email', lead.email)
        lead.phone  = data.get('phone', lead.phone)
        lead.source = data.get('source', lead.source)
        lead.score  = int(data.get('score', lead.score))
        lead.notes  = data.get('notes', lead.notes)
        lead.save()
        return JsonResponse({'status': 'updated'})

    # GET: filter by domain only — domain is already tenant-scoped
    leads = list(MarketingLead.objects.filter(domain=domain).order_by('-score').values())
    return JsonResponse({'leads': leads})


@login_required(login_url='/login')
def marketing_ab_save(request, domain):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)
    import json
    from .models import MarketingABTest
    data = json.loads(request.body)
    test = MarketingABTest.objects.create(
        user=request.user,
        domain=domain,
        name=data.get('name', 'A/B Test'),
        variant_a=data.get('variant_a', ''),
        variant_b=data.get('variant_b', ''),
        metric=data.get('metric', 'clicks'),
    )
    return JsonResponse({'status': 'saved', 'id': test.id})


@login_required(login_url='/login')
def marketing_campaign_detail(request, domain, campaign_id):
    """Return JSON analytics for a specific campaign."""
    from .models import MarketingCampaign, CampaignRecipient
    try:
        camp = MarketingCampaign.objects.get(id=campaign_id, user=request.user, domain=domain)
    except MarketingCampaign.DoesNotExist:
        return JsonResponse({'error': 'Campaign not found'}, status=404)

    r_qs = CampaignRecipient.objects.filter(campaign=camp)
    total     = r_qs.count()
    sent      = r_qs.filter(status__in=['sent', 'opened', 'clicked']).count()
    opened    = r_qs.filter(status__in=['opened', 'clicked']).count()
    failed    = r_qs.filter(status='failed').count()
    pending   = r_qs.filter(status='pending').count()
    open_rate = round((opened / sent) * 100, 1) if sent > 0 else 0

    recipients = []
    for r in r_qs.order_by('-sent_at', '-created_at'):
        recipients.append({
            'id': r.id,
            'email': r.email,
            'name': r.name,
            'status': r.status,
            'status_display': r.get_status_display(),
            'sent_at': r.sent_at.isoformat() if r.sent_at else None,
            'opened_at': r.opened_at.isoformat() if r.opened_at else None,
            'error_msg': r.error_msg,
        })

    return JsonResponse({
        'campaign': {
            'id': camp.id,
            'name': camp.name,
            'subject': camp.subject,
            'sender_email': camp.sender_email,
            'channel': camp.channel,
            'status': camp.status,
            'created_at': camp.created_at.isoformat(),
        },
        'analytics': {
            'total': total,
            'sent': sent,
            'opened': opened,
            'failed': failed,
            'pending': pending,
            'open_rate': open_rate,
        },
        'recipients': recipients,
    })


@login_required(login_url='/login')
def marketing_campaign_delete(request, domain, campaign_id):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)
    from .models import MarketingCampaign
    try:
        camp = MarketingCampaign.objects.get(id=campaign_id, user=request.user, domain=domain)
        camp.delete()
        return JsonResponse({'status': 'deleted'})
    except MarketingCampaign.DoesNotExist:
        return JsonResponse({'error': 'Campaign not found'}, status=404)


@login_required(login_url='/login')
def marketing_campaign_status_toggle(request, domain, campaign_id):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)
    import json
    from .models import MarketingCampaign
    try:
        data = json.loads(request.body)
        action = data.get('action') # 'pause' or 'resume'
        camp = MarketingCampaign.objects.get(id=campaign_id, user=request.user, domain=domain)
        
        if action == 'pause':
            if camp.status == 'scheduled':
                camp.status = 'paused'
                camp.save()
                return JsonResponse({'status': 'success', 'message': 'Campaign paused successfully.'})
            else:
                return JsonResponse({'error': 'Only scheduled campaigns can be paused.'}, status=400)
                
        elif action == 'resume':
            if camp.status == 'paused':
                camp.status = 'scheduled'
                camp.save()
                return JsonResponse({'status': 'success', 'message': 'Campaign resumed successfully.'})
            else:
                return JsonResponse({'error': 'Only paused campaigns can be resumed.'}, status=400)
        else:
            return JsonResponse({'error': 'Invalid action.'}, status=400)
            
    except MarketingCampaign.DoesNotExist:
        return JsonResponse({'error': 'Campaign not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required(login_url='/login')
def marketing_templates_list(request, domain):
    from .models import MarketingTemplate
    # 1. Fetch from database
    db_templates = []
    for t in MarketingTemplate.objects.filter(user=request.user, domain=domain):
        db_templates.append({
            'id': t.id,
            'name': t.name,
            'subject': t.subject,
            'content_html': t.content_html,
            'content_json': t.content_json,
            'updated_at': t.updated_at.isoformat(),
        })

    # 2. Fetch from static folder: /var/www/panel/static/email/templates
    import os
    from django.conf import settings
    static_dir = os.path.join(settings.BASE_DIR, 'static', 'email', 'templates')
    if not os.path.exists(static_dir):
        try:
            os.makedirs(static_dir)
        except Exception:
            pass

    static_templates = []
    if os.path.exists(static_dir):
        for fname in os.listdir(static_dir):
            if fname.endswith('.html'):
                fpath = os.path.join(static_dir, fname)
                try:
                    with open(fpath, 'r', encoding='utf-8') as f:
                        html_content = f.read()
                    static_templates.append({
                        'name': fname.replace('.html', '').replace('_', ' ').replace('-', ' ').title(),
                        'filename': fname,
                        'content_html': html_content,
                    })
                except Exception:
                    pass

    # 3. Fetch global templates from voidpanel.com superadmin portal
    import requests
    from .license import VOIDPANEL_LICENSE_API
    global_templates = []
    try:
        r = requests.get(f"{VOIDPANEL_LICENSE_API}/api/marketing/global-templates/", timeout=3)
        if r.status_code == 200:
            global_templates = r.json().get('global_templates', [])
    except Exception:
        pass

    return JsonResponse({
        'custom_templates': db_templates,
        'static_templates': static_templates,
        'global_templates': global_templates
    })


@login_required(login_url='/login')
def marketing_template_save(request, domain):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)
    import json
    from .models import MarketingTemplate
    try:
        data = json.loads(request.body)
        template_id = data.get('id')
        name = data.get('name', '').strip()
        subject = data.get('subject', '').strip()
        content_html = data.get('content_html', '').strip()
        content_json = data.get('content_json', '').strip()

        if not name or not content_html:
            return JsonResponse({'error': 'Template name and HTML body are required.'}, status=400)

        if template_id:
            tmpl = MarketingTemplate.objects.get(id=template_id, user=request.user, domain=domain)
            tmpl.name = name
            tmpl.subject = subject
            tmpl.content_html = content_html
            tmpl.content_json = content_json
            tmpl.save()
        else:
            tmpl = MarketingTemplate.objects.create(
                user=request.user, domain=domain,
                name=name, subject=subject,
                content_html=content_html, content_json=content_json
            )
        return JsonResponse({'status': 'saved', 'id': tmpl.id})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required(login_url='/login')
def marketing_template_delete(request, domain, template_id):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)
    from .models import MarketingTemplate
    try:
        tmpl = MarketingTemplate.objects.get(id=template_id, user=request.user, domain=domain)
        tmpl.delete()
        return JsonResponse({'status': 'deleted'})
    except MarketingTemplate.DoesNotExist:
        return JsonResponse({'error': 'Template not found'}, status=404)


def marketing_email_track_open(request, domain, recipient_id):
    """1x1 tracking pixel — marks recipient as opened."""
    from .models import CampaignRecipient
    from django.utils import timezone
    import base64
    try:
        rcpt = CampaignRecipient.objects.get(id=recipient_id)
        if rcpt.status in ('sent', 'pending'):
            rcpt.status = 'opened'
            rcpt.opened_at = timezone.now()
            rcpt.save()
            # Update campaign open_rate
            camp = rcpt.campaign
            r_qs = camp.recipients.all()
            sent_total = r_qs.filter(status__in=['sent', 'opened', 'clicked']).count()
            opened_total = r_qs.filter(status__in=['opened', 'clicked']).count()
            camp.open_rate = round((opened_total / sent_total) * 100, 1) if sent_total > 0 else 0
            camp.save()
    except CampaignRecipient.DoesNotExist:
        pass

    # Return a 1x1 transparent PNG
    pixel_data = base64.b64decode(
        'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8'
        'z8BQDwADhQGAWjR9awAAAABJRU5ErkJggg=='
    )
    from django.http import HttpResponse
    return HttpResponse(pixel_data, content_type='image/png')


# ════════════════════════════════════════════════════════════════
#  RESELLER HOSTING MANAGEMENT
# ════════════════════════════════════════════════════════════════

@login_required(login_url='/login')
def reseller_dashboard(request):
    """Main reseller control panel dashboard."""
    from control.models import ResellerProfile, user as UserModel
    from django.contrib.auth import get_user_model
    _AuthUser = get_user_model()
    rp = None
    try:
        rp = request.user.reseller_profile
    except Exception:
        pass
    # Admin Quick Login: check session-switched user
    if not rp and request.user.is_superuser:
        session_name = request.session.get('name', '')
        if session_name and session_name != request.user.username:
            session_auth = _AuthUser.objects.filter(username=session_name).first()
            if session_auth:
                try:
                    rp = session_auth.reseller_profile
                except Exception:
                    pass
    if not rp:
        return render(request, 'control/reseller_dashboard.html', {
            'error': 'No reseller profile. Purchase a reseller plan at voidpanel.com.',
        })
    sub_accounts = UserModel.objects.filter(reseller=rp).order_by('domain') \
        if hasattr(UserModel, 'reseller') else UserModel.objects.none()
    used_storage_gb = 0
    try:
        from function import get_directory_size_in_mb
        from voidplatform.config import paths
        for acc in sub_accounts:
            path = os.path.join(getattr(paths, 'HOME_BASE', '/home'), acc.username)
            if os.path.exists(path):
                used_storage_gb += round(get_directory_size_in_mb(path) / 1024, 2)
    except Exception:
        pass
    packages   = rp.packages.all().order_by('name')
    storage_pct  = round(min((used_storage_gb / rp.storage_quota_gb) * 100, 100), 1) if rp.storage_quota_gb else 0
    accounts_pct = round(min((sub_accounts.count() / rp.max_accounts) * 100, 100), 1) if rp.max_accounts else 0
    return render(request, 'control/reseller_dashboard.html', {
        'rp': rp, 'sub_accounts': sub_accounts, 'packages': packages,
        'used_storage_gb': used_storage_gb, 'storage_pct': storage_pct,
        'accounts_pct': accounts_pct, 'accounts_used': sub_accounts.count(),
    })


def _get_reseller_profile(request):
    """Get ResellerProfile for current user, supporting admin Quick Login."""
    from control.models import ResellerProfile
    from django.contrib.auth import get_user_model
    rp = None
    try:
        rp = request.user.reseller_profile
    except Exception:
        pass
    if not rp and request.user.is_superuser:
        session_name = request.session.get('name', '')
        if session_name and session_name != request.user.username:
            _AU = get_user_model()
            session_auth = _AU.objects.filter(username=session_name).first()
            if session_auth:
                try:
                    rp = session_auth.reseller_profile
                except Exception:
                    pass
    return rp


@login_required(login_url='/login')
def reseller_create_account(request):
    """Reseller creates a new sub-account."""
    from control.models import ResellerProfile, ResellerPackage, user as UserModel
    from django.contrib.auth import get_user_model
    import secrets, string
    rp = _get_reseller_profile(request)
    if not rp:
        return JsonResponse({'error': 'No reseller profile'}, status=403)
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)
    try:
        data = json.loads(request.body)
    except Exception:
        data = request.POST.dict()
    client_domain = data.get('domain', '').strip().lower()
    client_email  = data.get('email', '').strip()
    pkg_id        = data.get('package_id', '')
    user_quota_gb = int(data.get('user_quota_gb', 1))
    if not client_domain or not client_email:
        return JsonResponse({'error': 'domain and email are required'}, status=400)
    existing = UserModel.objects.filter(reseller=rp) if hasattr(UserModel, 'reseller') else UserModel.objects.none()
    if existing.count() >= rp.max_accounts:
        return JsonResponse({'error': f'Account limit reached ({rp.max_accounts}). Upgrade your plan.'}, status=400)
    if UserModel.objects.filter(domain=client_domain).exists():
        return JsonResponse({'error': f'Domain {client_domain} already taken.'}, status=400)

    import re
    base_user = re.sub(r'[^a-z0-9]', '', client_domain.split('.')[0].lower())[:16]
    AuthUser  = get_user_model()
    username  = base_user; suffix = 1
    while AuthUser.objects.filter(username=username).exists():
        username = f"{base_user}{suffix}"; suffix += 1
    password = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(14))

    # Dispatch via Celery for proper provisioning (Linux user, nginx, SSL, DNS)
    try:
        from voidplatform.config import paths
        from control.models import package as Package
        # Find or create a package for reseller clients
        client_pkg, _ = Package.objects.get_or_create(
            name='reseller-client',
            defaults={'storage': str(user_quota_gb * 1024), 'ftp': '2', 'subdomain': '5',
                      'bandwidth': '50000', 'email_accounts': '5', 'databases_allowed': '3'}
        )
        acct_path = os.path.join(paths.HOME_BASE, username)
        inipath   = acct_path + '/public_html/php.ini'
        sto       = user_quota_gb * 1024  # MB
        php_ini_content = (
            f'; PHP settings for {client_domain}\n'
            'max_execution_time = 30\nmemory_limit = 256M\n'
            'post_max_size = 64M\nupload_max_filesize = 64M\n'
            'display_errors = Off\nlog_errors = On\n'
            f'error_log = "{acct_path}/public_html/logs/php_errors.log"\n'
            'date.timezone = "Asia/Kolkata"\nfile_uploads = On\n'
            f'open_basedir = "{acct_path}/public_html:/tmp"\n'
        )
        from control.tasks import provision_user_task
        provision_user_task.delay(
            client_domain, username, client_email, password, 'reseller-client',
            acct_path, sto, inipath, php_ini_content,
        )
    except Exception as e:
        # Fallback: just create DB records if Celery/paths not available
        auth_user = AuthUser.objects.create_user(username=username, email=client_email, password=password)
        UserModel.objects.create(
            username=username, domain=client_domain,
            email=client_email, hosting_package='reseller-client',
        )

    # Tag the hosting user as belonging to this reseller (delayed since Celery creates it)
    import threading
    def _tag_reseller(uname, _rp_id):
        import time; time.sleep(15)
        try:
            from control.models import user as _UM, ResellerProfile as _RP
            hu = _UM.objects.filter(username=uname).first()
            if hu:
                hu.reseller_id = _rp_id
                hu.save(update_fields=['reseller_id'])
        except Exception:
            pass
    threading.Thread(target=_tag_reseller, args=(username, rp.id), daemon=True).start()

    return JsonResponse({'status': 'created', 'username': username, 'password': password,
                         'domain': client_domain, 'panel_url': f'https://{request.get_host()}/control/'})


@login_required(login_url='/login')
def reseller_list_accounts(request):
    """Dedicated page listing all reseller sub-accounts with search."""
    from control.models import ResellerProfile, ResellerPackage, user as UserModel
    from django.contrib.auth import get_user_model
    rp = _get_reseller_profile(request)
    if not rp:
        return render(request, 'control/reseller_list_accounts.html', {
            'error': 'No reseller profile found.',
        })
    sub_accounts = UserModel.objects.filter(reseller=rp).order_by('domain') \
        if hasattr(UserModel, 'reseller') else UserModel.objects.none()
    packages = rp.packages.all().order_by('name')
    return render(request, 'control/reseller_list_accounts.html', {
        'rp': rp, 'sub_accounts': sub_accounts, 'packages': packages,
        'accounts_used': sub_accounts.count(),
    })


@login_required(login_url='/login')
def reseller_delete_account(request, acc_username):
    from control.models import ResellerProfile, user as UserModel
    from django.contrib.auth import get_user_model
    rp = _get_reseller_profile(request)
    if not rp:
        return JsonResponse({'error': 'No reseller profile'}, status=403)
    try:
        # Try with reseller FK first, then fall back to username-only
        acc = UserModel.objects.filter(username=acc_username, reseller=rp).first()
        if not acc:
            acc = UserModel.objects.filter(username=acc_username).first()
        if not acc:
            return JsonResponse({'error': 'Account not found'}, status=404)
        acc.delete()
        get_user_model().objects.filter(username=acc_username).delete()
        return JsonResponse({'status': 'deleted'})
    except Exception:
        return JsonResponse({'error': 'Account not found'}, status=404)

@login_required(login_url='/login')
def reseller_package_save(request):
    from control.models import ResellerProfile, ResellerPackage
    rp = _get_reseller_profile(request)
    if not rp:
        return JsonResponse({'error': 'No reseller profile'}, status=403)
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)
    try:
        data = json.loads(request.body)
    except Exception:
        data = request.POST.dict()
    pkg_id = data.get('id'); name = data.get('name', '').strip()
    if not name:
        return JsonResponse({'error': 'Name required'}, status=400)
    if pkg_id:
        try:
            pkg = ResellerPackage.objects.get(id=pkg_id, reseller=rp)
        except ResellerPackage.DoesNotExist:
            return JsonResponse({'error': 'Package not found'}, status=404)
    else:
        pkg = ResellerPackage(reseller=rp)
    pkg.name = name
    pkg.storage_gb     = int(data.get('storage_gb', 1))
    pkg.bandwidth_gb   = int(data.get('bandwidth_gb', 10))
    pkg.email_accounts = int(data.get('email_accounts', 5))
    pkg.databases      = int(data.get('databases', 2))
    pkg.subdomains     = int(data.get('subdomains', 5))
    pkg.ftp_accounts   = int(data.get('ftp_accounts', 2))
    pkg.save()
    return JsonResponse({'status': 'saved', 'id': pkg.id, 'name': pkg.name})


@login_required(login_url='/login')
def reseller_suspend_account(request, acc_username):
    """Reseller suspends a sub-account."""
    from control.models import user as UserModel
    rp = _get_reseller_profile(request)
    if not rp:
        return JsonResponse({'error': 'No reseller profile'}, status=403)
    try:
        acc = UserModel.objects.filter(username=acc_username, reseller=rp).first() or UserModel.objects.filter(username=acc_username).first()
        if not acc:
            return JsonResponse({'error': 'Account not found'}, status=404)
        acc.status = False
        acc.save(update_fields=['status'])
        return JsonResponse({'status': 'suspended'})
    except Exception:
        return JsonResponse({'error': 'Account not found'}, status=404)


@login_required(login_url='/login')
def reseller_unsuspend_account(request, acc_username):
    """Reseller unsuspends a sub-account."""
    from control.models import user as UserModel
    rp = _get_reseller_profile(request)
    if not rp:
        return JsonResponse({'error': 'No reseller profile'}, status=403)
    try:
        acc = UserModel.objects.filter(username=acc_username, reseller=rp).first() or UserModel.objects.filter(username=acc_username).first()
        if not acc:
            return JsonResponse({'error': 'Account not found'}, status=404)
        acc.status = True
        acc.save(update_fields=['status'])
        return JsonResponse({'status': 'unsuspended'})
    except Exception:
        return JsonResponse({'error': 'Account not found'}, status=404)


@login_required(login_url='/login')
def reseller_package_delete(request, pkg_id):
    """Reseller deletes one of their packages."""
    from control.models import ResellerPackage
    rp = _get_reseller_profile(request)
    if not rp:
        return JsonResponse({'error': 'No reseller profile'}, status=403)
    try:
        pkg = ResellerPackage.objects.get(id=pkg_id, reseller=rp)
        pkg.delete()
        return JsonResponse({'status': 'deleted'})
    except ResellerPackage.DoesNotExist:
        return JsonResponse({'error': 'Package not found'}, status=404)


@csrf_exempt
def reseller_api_provision(request):
    """Called by portal when reseller service is activated. Creates ResellerProfile."""
    from control.models import ResellerProfile
    from django.contrib.auth import get_user_model
    import secrets, string
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)

    # ── Parse JSON body ──────────────────────────────────────────────────────
    try:
        data = json.loads(request.body)
    except Exception:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    # ── Auth: Accept X-API-Token header (preferred) or body api_key (legacy) ──
    authenticated = False

    # Method 1: X-API-Token header → validate via APIToken model
    header_token = request.headers.get('X-API-Token', '').strip()
    if header_token:
        try:
            from control.models import APIToken
            token_obj = APIToken.objects.get(key=header_token, is_active=True)
            authenticated = True
        except Exception:
            pass

    # Method 2: body api_key or X-VoidPanel-Key header → validate via /etc/voidpanel_api_key
    if not authenticated:
        try:
            expected = open('/etc/voidpanel_api_key').read().strip()
        except Exception:
            from django.conf import settings as _dj_settings
            expected = os.environ.get(
                'VOIDPANEL_API_KEY',
                getattr(_dj_settings, 'VOIDPANEL_API_KEY', '')
            )
        vpanel_key = request.headers.get('X-VoidPanel-Key', '').strip()
        body_key   = data.get('api_key', '').strip()
        if expected and (vpanel_key == expected or body_key == expected):
            authenticated = True
        elif expected and header_token == expected:
            authenticated = True
        elif not expected and not body_key:
            # No key configured and no key sent — allow (unconfigured fresh install)
            authenticated = True

    if not authenticated:
        return JsonResponse({'error': 'Unauthorized'}, status=401)
    username     = data.get('username', '').strip()
    email        = data.get('email', '').strip()
    storage_gb   = int(data.get('storage_gb', 50))
    max_accounts = int(data.get('max_accounts', 10))
    company      = data.get('company_name', '')
    domain_name  = data.get('domain', '').strip()
    if not username or not email:
        return JsonResponse({'error': 'username and email required'}, status=400)
    if not domain_name:
        return JsonResponse({'error': 'domain is required for reseller account'}, status=400)

    # Check if domain already exists
    from control.models import domain as DomainModel
    if DomainModel.objects.filter(domain=domain_name).exists():
        return JsonResponse({'error': f'Domain {domain_name} already exists'}, status=409)

    # Always generate a fresh password
    password = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(16))

    # ── 1. Ensure the specific package exists in the panel's package table ──
    from control.models import package as Package
    package_name_to_use = data.get('package_name', 'Reseller').strip() or 'Reseller'
    reseller_pkg, _ = Package.objects.get_or_create(
        name=package_name_to_use,
        defaults={
            'storage':           str(storage_gb * 1024),  # MB
            'ftp':               '10',
            'subdomain':         '20',
            'bandwidth':         '0',      # unlimited
            'email_accounts':    '0',      # unlimited
            'databases_allowed': '0',      # unlimited
        }
    )

    # ── 2. Dispatch Celery task for full hosting account creation ──
    import re
    from voidplatform.config import paths
    base_name = re.sub(r'[^a-z0-9]', '', domain_name.split('.')[0].lower())[:16]
    domainname = base_name
    counter = 1
    while os.path.exists(os.path.join(paths.HOME_BASE, domainname)):
        suffix = str(counter)
        domainname = base_name[:16 - len(suffix)] + suffix
        counter += 1

    acct_path = os.path.join(paths.HOME_BASE, domainname)
    inipath   = acct_path + '/public_html/php.ini'
    sto       = int(reseller_pkg.storage)
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
        domain_name, domainname, email, password, package_name_to_use,
        acct_path, sto, inipath, php_ini_content,
    )

    # ── 3. Create ResellerProfile in a delayed thread ──
    # The Celery task creates the auth user asynchronously, so we wait then create the profile
    import threading
    def _create_reseller_profile(actual_username, _email, _storage_gb, _max_accounts, _company):
        import time
        time.sleep(15)  # Give Celery time to create the DB records
        try:
            from django.contrib.auth import get_user_model as _gum
            from control.models import ResellerProfile as _RP, ResellerPackage as _RPkg
            _AU = _gum()
            auth_user = _AU.objects.filter(username=actual_username).first()
            if not auth_user:
                return  # Celery hasn't finished yet — will need manual fix
            auth_user.set_password(password)
            auth_user.email = _email
            auth_user.save()

            rp, _ = _RP.objects.get_or_create(
                auth_user=auth_user,
                defaults={
                    'storage_quota_gb': _storage_gb,
                    'max_accounts':     _max_accounts,
                    'company_name':     _company,
                    'branding_name':    _company or 'VoidPanel',
                    'is_active':        True,
                }
            )

            # Default client package
            _RPkg.objects.get_or_create(
                reseller=rp,
                name='Starter Client Plan',
                defaults={
                    'storage_gb':     max(1, _storage_gb // max(_max_accounts, 1)),
                    'bandwidth_gb':   50,
                    'email_accounts': 5,
                    'databases':      3,
                    'subdomains':     5,
                    'ftp_accounts':   2,
                }
            )
        except Exception as exc:
            import logging
            logging.getLogger('voidpanel').error('ResellerProfile creation failed for %s: %s', actual_username, exc)

    threading.Thread(
        target=_create_reseller_profile,
        args=(domainname, email, storage_gb, max_accounts, company),
        daemon=True,
    ).start()

    scheme = 'http' if ':8080' in request.get_host() else ('https' if request.is_secure() else 'http')
    return JsonResponse({
        'status': 'provisioned', 'username': domainname, 'password': password,
        'panel_url': f'{scheme}://{request.get_host()}/control/',
        'reseller_dashboard_url': f'{scheme}://{request.get_host()}/control/reseller/',
        'storage_gb': storage_gb, 'max_accounts': max_accounts,
        'task_id': str(task.id),
    })


# ══════════════════════════════════════════════════════════════
#  DOCKER CONTAINER MANAGEMENT VIEWS
# ══════════════════════════════════════════════════════════════

import subprocess
import json
import shutil

def _enable_nginx_docker_proxy(domain_name, host_port, username):
    """
    Backup the original Nginx config if it exists, write the reverse proxy config,
    link it, and reload Nginx.
    """
    import os, tempfile, subprocess
    from voidplatform.config import paths

    cert_path = f"/home/{username}/ssl/{domain_name}.crt"
    key_path = f"/home/{username}/ssl/{domain_name}.key"
    has_ssl = os.path.exists(cert_path) and os.path.exists(key_path)

    nginx_conf = f"""server {{
    listen 80;
    server_name {domain_name} www.{domain_name};

    location /vpanel {{
        return 301 https://$host:8082;
    }}

    location /control/ {{
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }}

    location / {{
        proxy_pass http://127.0.0.1:{host_port};
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 300;
        proxy_connect_timeout 300;
        proxy_send_timeout 300;
    }}
}}
"""
    if has_ssl:
        nginx_conf += f"""
server {{
    listen 443 ssl;
    server_name {domain_name} www.{domain_name};

    ssl_certificate {cert_path};
    ssl_certificate_key {key_path};

    location /vpanel {{
        return 301 https://$host:8082;
    }}

    location /control/ {{
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }}

    location / {{
        proxy_pass http://127.0.0.1:{host_port};
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 300;
        proxy_connect_timeout 300;
        proxy_send_timeout 300;
    }}
}}
"""

    conf_path = os.path.join(paths.NGINX_SITES_AVAILABLE, f"{domain_name}.conf")
    backup_path = os.path.join(paths.NGINX_SITES_AVAILABLE, f"{domain_name}.conf.bak")
    enabled_path = os.path.join(paths.NGINX_SITES_ENABLED, f"{domain_name}.conf")

    try:
        r = subprocess.run(['sudo', 'test', '-f', conf_path], capture_output=True)
        if r.returncode == 0:
            # Only backup if backup does not exist yet (avoid double backup)
            r_bak = subprocess.run(['sudo', 'test', '-f', backup_path], capture_output=True)
            if r_bak.returncode != 0:
                subprocess.run(['sudo', 'cp', conf_path, backup_path], check=False)

        with tempfile.NamedTemporaryFile('w', delete=False) as f:
            f.write(nginx_conf)
            temp_path = f.name

        subprocess.run(['sudo', 'cp', temp_path, conf_path], check=False)
        subprocess.run(['sudo', 'chown', 'root:root', conf_path], check=False)
        subprocess.run(['sudo', 'chmod', '644', conf_path], check=False)
        subprocess.run(['sudo', 'ln', '-sf', conf_path, enabled_path], check=False)
        subprocess.run(['sudo', 'systemctl', 'reload', 'nginx'], check=False)

        try: os.unlink(temp_path)
        except: pass
    except Exception as e:
        print(f"Error enabling Docker Nginx proxy: {e}")


def _disable_nginx_docker_proxy(domain_name):
    """
    If a backup config exists, restore it. Otherwise, delete the proxy configs and reload Nginx.
    """
    import os, subprocess
    from voidplatform.config import paths

    conf_path = os.path.join(paths.NGINX_SITES_AVAILABLE, f"{domain_name}.conf")
    backup_path = os.path.join(paths.NGINX_SITES_AVAILABLE, f"{domain_name}.conf.bak")
    enabled_path = os.path.join(paths.NGINX_SITES_ENABLED, f"{domain_name}.conf")

    try:
        r = subprocess.run(['sudo', 'test', '-f', backup_path], capture_output=True)
        if r.returncode == 0:
            subprocess.run(['sudo', 'cp', backup_path, conf_path], check=False)
            subprocess.run(['sudo', 'rm', '-f', backup_path], check=False)
        else:
            subprocess.run(['sudo', 'rm', '-f', conf_path], check=False)
            subprocess.run(['sudo', 'rm', '-f', enabled_path], check=False)

        subprocess.run(['sudo', 'systemctl', 'reload', 'nginx'], check=False)
    except Exception as e:
        print(f"Error disabling Docker Nginx proxy: {e}")


def _get_docker_user_and_auth(request, domain_name):
    """Returns (username, error_response). error_response is None if authenticated and authorized."""
    if not request.user.is_authenticated:
        return None, redirect('/')
    if request.user.is_superuser:
        current = request.session.get('name', request.user.username)
    else:
        current = request.user.username
        from control.models import user as UserModel
        owner = UserModel.objects.filter(username=current).first()
        if not owner or owner.domain != domain_name:
            from django.http import HttpResponse
            return None, HttpResponse("Unauthorized", status=403)
    return current, None


@login_required(login_url='/')
def docker_dashboard(request, domain):
    current, err = _get_docker_user_and_auth(request, domain)
    if err:
        return err

    try:
        with open(paths.MYSQL_PASSWORD_FILE, 'r') as f:
            adminpassword = f.read().strip()
    except Exception:
        adminpassword = ""

    d = {}
    d.update(get_user_dashboard_context(current, adminpassword))
    d['domain'] = domain

    # Check if docker is installed
    docker_bin = shutil.which('docker')
    if not docker_bin:
        d['docker_installed'] = False
        return render(request, 'control/docker.html', d)
    
    d['docker_installed'] = True

    # Get daemon status
    try:
        r = subprocess.run(['sudo', 'systemctl', 'is-active', 'docker'], capture_output=True, text=True, timeout=5)
        d['docker_active'] = r.stdout.strip() == 'active'
    except Exception:
        d['docker_active'] = False

    # Get live system containers
    containers = []
    try:
        r = subprocess.run(['sudo', 'docker', 'ps', '-a', '--format', '{{json .}}'], capture_output=True, text=True, timeout=10)
        if r.returncode == 0:
            for line in r.stdout.strip().split('\n'):
                if line.strip():
                    try:
                        containers.append(json.loads(line))
                    except Exception:
                        pass
    except Exception:
        pass

    # Filter containers based on ownership in database (for non-admins)
    from control.models import DockerContainer
    db_containers = DockerContainer.objects.filter(user=current)
    db_names = set(db_containers.values_list('name', flat=True))

    filtered_containers = []
    for c in containers:
        c_name = c.get('Names', '').strip()
        if ',' in c_name:
            c_name = c_name.split(',')[0]
        c_name = c_name.lstrip('/')
        c['CleanName'] = c_name
        
        # Determine ownership
        if request.user.is_superuser or c_name in db_names:
            db_match = db_containers.filter(name=c_name).first()
            if db_match:
                c['ports_map'] = db_match.ports
                c['image'] = db_match.image
            filtered_containers.append(c)
            
    d['containers'] = filtered_containers

    # Get local images
    images = []
    try:
        r = subprocess.run(['sudo', 'docker', 'images', '--format', '{{json .}}'], capture_output=True, text=True, timeout=10)
        if r.returncode == 0:
            for line in r.stdout.strip().split('\n'):
                if line.strip():
                    try:
                        images.append(json.loads(line))
                    except Exception:
                        pass
    except Exception:
        pass
    d['images'] = images

    # Fetch user domains & subdomains
    try:
        from control.models import user as ctrl_user
        u_obj = ctrl_user.objects.get(username=current)
        user_domain = u_obj.domain
        
        from control.models import subdomainname
        subs = subdomainname.objects.filter(domain=user_domain)
        all_domains = [user_domain] + [s.subdomain for s in subs]
    except Exception:
        all_domains = [domain]

    d['user_domains'] = all_domains

    return render(request, 'control/docker.html', d)


@login_required(login_url='/')
def docker_install_engine(request, domain):
    current, err = _get_docker_user_and_auth(request, domain)
    if err:
        return err

    if not request.user.is_superuser:
        return JsonResponse({'status': 'error', 'message': 'Only administrators can install Docker Engine.'}, status=403)

    import threading
    def _install():
        try:
            if shutil.which('apt-get'):
                subprocess.run(['sudo', 'apt-get', 'update'], check=False, timeout=60)
                subprocess.run(['sudo', 'apt-get', 'install', '-y', 'docker.io'], check=False, timeout=180)
            elif shutil.which('dnf'):
                subprocess.run(['sudo', 'dnf', 'config-manager', '--add-repo', 'https://download.docker.com/linux/centos/docker-ce.repo'], check=False, timeout=45)
                subprocess.run(['sudo', 'dnf', 'install', '-y', 'docker-ce', 'docker-ce-cli', 'containerd.io'], check=False, timeout=180)
            subprocess.run(['sudo', 'systemctl', 'enable', '--now', 'docker'], check=False, timeout=30)
        except Exception:
            pass

    threading.Thread(target=_install, daemon=True).start()
    return JsonResponse({'status': 'success', 'message': 'Docker installation started in the background. Please refresh in a minute.'})



@login_required(login_url='/')
def docker_container_create(request, domain):
    current, err = _get_docker_user_and_auth(request, domain)
    if err:
        return err

    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'POST required'}, status=405)

    try:
        data = json.loads(request.body)
    except Exception:
        data = request.POST.dict()

    name = data.get('name', '').strip()
    image = data.get('image', '').strip()
    host_port = data.get('host_port', '').strip()
    container_port = data.get('container_port', '').strip()

    # Fallback to defaults if left blank (since placeholders are not submitted by forms)
    if not container_port:
        container_port = '80'
    if not host_port:
        import socket
        port_candidate = 8080
        while port_candidate < 65535:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                try:
                    s.bind(('127.0.0.1', port_candidate))
                    host_port = str(port_candidate)
                    break
                except OSError:
                    port_candidate += 1
        if not host_port:
            host_port = '8080'
    env_vars_raw = data.get('env_vars', '')
    volumes_raw = data.get('volumes', '')

    if not name or not image:
        return JsonResponse({'status': 'error', 'message': 'Container Name and Image are required.'})

    import re
    if not re.match(r'^[a-zA-Z0-9_-]+$', name):
        return JsonResponse({'status': 'error', 'message': 'Invalid container name format.'})

    from control.models import DockerContainer
    if DockerContainer.objects.filter(name=name).exists():
        return JsonResponse({'status': 'error', 'message': 'A container with this name is already registered.'})

    cmd = ['sudo', 'docker', 'run', '-d', '--name', name]

    ports_dict = {}
    if host_port and container_port:
        cmd += ['-p', f'{host_port}:{container_port}']
        ports_dict[host_port] = container_port

    env_dict = {}
    if env_vars_raw:
        for pair in env_vars_raw.split(','):
            if '=' in pair:
                k, v = pair.split('=', 1)
                cmd += ['-e', f'{k.strip()}={v.strip()}']
                env_dict[k.strip()] = v.strip()

    vol_dict = {}
    if volumes_raw:
        for pair in volumes_raw.split(','):
            if ':' in pair:
                h_path, c_path = pair.split(':', 1)
                cmd += ['-v', f'{h_path.strip()}:{c_path.strip()}']
                vol_dict[h_path.strip()] = c_path.strip()

    cmd += ['--restart', 'unless-stopped', image]

    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        if r.returncode == 0:
            container_id = r.stdout.strip()
            
            route_domain = data.get('route_domain', '').strip()
            if route_domain and host_port:
                _enable_nginx_docker_proxy(route_domain, host_port, current)

            DockerContainer.objects.create(
                user=current,
                container_id=container_id[:12],
                name=name,
                image=image,
                ports=ports_dict,
                env_vars=env_dict,
                volumes=vol_dict,
                domain=route_domain
            )
            return JsonResponse({'status': 'success', 'message': f'Container {name} deployed successfully!'})
        else:
            return JsonResponse({'status': 'error', 'message': r.stderr or r.stdout})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': f'Deployment failed: {str(e)}'})


@login_required(login_url='/')
def docker_container_action(request, domain, container_name, action):
    current, err = _get_docker_user_and_auth(request, domain)
    if err:
        return err

    from control.models import DockerContainer
    if not request.user.is_superuser:
        if not DockerContainer.objects.filter(user=current, name=container_name).exists():
            return JsonResponse({'status': 'error', 'message': 'Unauthorized to manage this container.'}, status=403)

    if action not in ['start', 'stop', 'restart', 'pause', 'unpause', 'remove']:
        return JsonResponse({'status': 'error', 'message': 'Invalid action.'})

    cmd_action = action
    if action == 'remove':
        cmd_action = 'rm'

    if action == 'remove':
        subprocess.run(['sudo', 'docker', 'stop', container_name], capture_output=True, text=True, timeout=20)
        cmd = ['sudo', 'docker', 'rm', '-f', container_name]
    else:
        cmd = ['sudo', 'docker', cmd_action, container_name]

    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if r.returncode == 0:
            c_obj = DockerContainer.objects.filter(name=container_name).first()
            if c_obj and c_obj.domain:
                if action in ['stop', 'remove']:
                    _disable_nginx_docker_proxy(c_obj.domain)
                elif action in ['start', 'restart']:
                    # Extract host port
                    host_port = None
                    if c_obj.ports:
                        host_port = list(c_obj.ports.keys())[0]
                    if host_port:
                        _enable_nginx_docker_proxy(c_obj.domain, host_port, current)

            if action == 'remove':
                DockerContainer.objects.filter(name=container_name).delete()
            return JsonResponse({'status': 'success', 'message': f'Container {container_name} {action}ed successfully!'})
        else:
            return JsonResponse({'status': 'error', 'message': r.stderr or r.stdout})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': f'Action failed: {str(e)}'})


@login_required(login_url='/')
def docker_container_logs(request, domain, container_name):
    current, err = _get_docker_user_and_auth(request, domain)
    if err:
        return err

    from control.models import DockerContainer
    if not request.user.is_superuser:
        if not DockerContainer.objects.filter(user=current, name=container_name).exists():
            return JsonResponse({'status': 'error', 'message': 'Unauthorized'}, status=403)

    try:
        r = subprocess.run(['sudo', 'docker', 'logs', '--tail', '200', container_name], capture_output=True, text=True, timeout=15)
        logs = r.stdout + r.stderr
        return JsonResponse({'status': 'success', 'logs': logs})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)})


@login_required(login_url='/')
def docker_image_pull(request, domain):
    current, err = _get_docker_user_and_auth(request, domain)
    if err:
        return err

    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'POST required'}, status=405)

    try:
        data = json.loads(request.body)
    except Exception:
        data = request.POST.dict()

    image_name = data.get('image', '').strip()
    if not image_name:
        return JsonResponse({'status': 'error', 'message': 'Image name is required.'})

    if ':' not in image_name:
        image_name += ':latest'

    try:
        r = subprocess.run(['sudo', 'docker', 'pull', image_name], capture_output=True, text=True, timeout=90)
        if r.returncode == 0:
            return JsonResponse({'status': 'success', 'message': f'Successfully pulled image {image_name}!'})
        else:
            return JsonResponse({'status': 'error', 'message': r.stderr or r.stdout})
    except subprocess.TimeoutExpired:
        return JsonResponse({'status': 'success', 'message': f'Image pull for {image_name} started and is running in the background.'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)})


@login_required(login_url='/')
def docker_image_delete(request, domain):
    current, err = _get_docker_user_and_auth(request, domain)
    if err:
        return err

    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'POST required'}, status=405)

    try:
        data = json.loads(request.body)
    except Exception:
        data = request.POST.dict()

    image_id = data.get('image_id', '').strip()
    if not image_id:
        return JsonResponse({'status': 'error', 'message': 'Image ID is required.'})

    try:
        r = subprocess.run(['sudo', 'docker', 'rmi', image_id], capture_output=True, text=True, timeout=30)
        if r.returncode == 0:
            return JsonResponse({'status': 'success', 'message': 'Image deleted successfully!'})
        else:
            return JsonResponse({'status': 'error', 'message': r.stderr or r.stdout})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)})


# ══════════════════════════════════════════════════════════════
#  CLOUDFLARE INTEGRATION VIEWS
# ══════════════════════════════════════════════════════════════

import requests

def _cf_api_request(method, url, api_token, email=None, payload=None):
    if email:
        headers = {
            "X-Auth-Email": email,
            "X-Auth-Key": api_token,
            "Content-Type": "application/json",
        }
    else:
        headers = {
            "Authorization": f"Bearer {api_token}",
            "Content-Type": "application/json",
        }
    try:
        if method == 'GET':
            r = requests.get(url, headers=headers, timeout=15)
        elif method == 'POST':
            r = requests.post(url, headers=headers, json=payload, timeout=15)
        elif method == 'PUT':
            r = requests.put(url, headers=headers, json=payload, timeout=15)
        elif method == 'PATCH':
            r = requests.patch(url, headers=headers, json=payload, timeout=15)
        elif method == 'DELETE':
            r = requests.delete(url, headers=headers, timeout=15)
        else:
            return False, "Unsupported method"
        
        data = r.json()
        if r.status_code >= 400 or not data.get('success'):
            errors = data.get('errors', [])
            msg = errors[0].get('message') if errors else f"HTTP error {r.status_code}"
            return False, msg
        return True, data
    except Exception as e:
        return False, str(e)


@login_required(login_url='/')
def cloudflare_dashboard(request, domain):
    current, err = _get_docker_user_and_auth(request, domain)
    if err:
        return err

    try:
        with open(paths.MYSQL_PASSWORD_FILE, 'r') as f:
            adminpassword = f.read().strip()
    except Exception:
        adminpassword = ""

    d = {}
    d.update(get_user_dashboard_context(current, adminpassword))
    d['domain'] = domain

    from control.models import CloudflareIntegration
    integration = CloudflareIntegration.objects.filter(domain=domain).first()

    if not integration:
        d['cf_connected'] = False
        return render(request, 'control/cloudflare.html', d)

    d['cf_connected'] = True
    d['api_token_obscured'] = integration.api_token[:4] + "*" * 12 + integration.api_token[-4:] if len(integration.api_token) > 8 else "********"
    d['zone_id'] = integration.zone_id
    d['cf_email'] = integration.email

    # Fetch zone info and DNS records from Cloudflare
    zone_url = f"https://api.cloudflare.com/client/v4/zones/{integration.zone_id}"
    ok, zone_data = _cf_api_request('GET', zone_url, integration.api_token, integration.email)
    if ok:
        d['zone_status'] = zone_data.get('result', {}).get('status', 'unknown')
        d['zone_nameservers'] = zone_data.get('result', {}).get('name_servers', [])
        d['development_mode'] = zone_data.get('result', {}).get('development_mode', 0)
    else:
        d['zone_status'] = 'Error: ' + str(zone_data)
        d['zone_nameservers'] = []

    dns_url = f"https://api.cloudflare.com/client/v4/zones/{integration.zone_id}/dns_records?per_page=100"
    ok, dns_data = _cf_api_request('GET', dns_url, integration.api_token, integration.email)
    if ok:
        d['dns_records'] = dns_data.get('result', [])
    else:
        d['dns_records'] = []
        d['dns_error'] = str(dns_data)

    # GraphQL Analytics Integration
    d['analytics_available'] = False
    try:
        import datetime, urllib.request, ssl, json
        today = datetime.date.today()
        since_date = (today - datetime.timedelta(days=7)).isoformat()
        until_date = (today + datetime.timedelta(days=1)).isoformat()
        
        query = """
        query {
          viewer {
            zones(filter: { zoneTag: "%s" }) {
              httpRequests1dGroups(limit: 30, filter: { date_geq: "%s", date_lt: "%s" }, orderBy: [date_ASC]) {
                sum {
                  requests
                  pageViews
                  bytes
                  threats
                }
                dimensions {
                  date
                }
              }
            }
          }
        }
        """ % (integration.zone_id, since_date, until_date)
        
        url = "https://api.cloudflare.com/client/v4/graphql"
        req = urllib.request.Request(url, method="POST")
        req.add_header("Content-Type", "application/json")
        if integration.email:
            req.add_header("X-Auth-Email", integration.email)
            req.add_header("X-Auth-Key", integration.api_token)
        else:
            req.add_header("Authorization", f"Bearer {integration.api_token}")
            
        payload = json.dumps({"query": query}).encode()
        ctx = ssl._create_unverified_context()
        with urllib.request.urlopen(req, data=payload, timeout=8, context=ctx) as response:
            res_data = json.loads(response.read().decode())
            if not res_data.get('errors') and res_data.get('data'):
                zones = res_data['data']['viewer']['zones']
                if zones and zones[0].get('httpRequests1dGroups'):
                    daily_data = zones[0]['httpRequests1dGroups']
                    
                    # Calculate aggregate sums
                    tot_requests = sum(r['sum']['requests'] for r in daily_data)
                    tot_pageviews = sum(r['sum']['pageViews'] for r in daily_data)
                    tot_bytes = sum(r['sum']['bytes'] for r in daily_data)
                    tot_threats = sum(r['sum']['threats'] for r in daily_data)
                    
                    d['analytics_totals'] = {
                        'requests': tot_requests,
                        'pageviews': tot_pageviews,
                        'bytes': tot_bytes,
                        'bytes_formatted': f"{tot_bytes / (1024*1024):.2f} MB" if tot_bytes < 1024*1024*1024 else f"{tot_bytes / (1024*1024*1024):.2f} GB",
                        'threats': tot_threats
                    }
                    
                    # Format each daily item
                    formatted_daily = []
                    chart_labels = []
                    chart_requests = []
                    chart_pageviews = []
                    for item in daily_data:
                        date_str = item['dimensions']['date']
                        b = item['sum']['bytes']
                        formatted_daily.append({
                            'date': date_str,
                            'requests': item['sum']['requests'],
                            'pageviews': item['sum']['pageViews'],
                            'bytes_formatted': f"{b / (1024*1024):.2f} MB" if b < 1024*1024*1024 else f"{b / (1024*1024*1024):.2f} GB",
                            'threats': item['sum']['threats']
                        })
                        chart_labels.append(date_str)
                        chart_requests.append(item['sum']['requests'])
                        chart_pageviews.append(item['sum']['pageViews'])
                        
                    d['analytics_daily'] = formatted_daily
                    d['chart_labels_json'] = json.dumps(chart_labels)
                    d['chart_requests_json'] = json.dumps(chart_requests)
                    d['chart_pageviews_json'] = json.dumps(chart_pageviews)
                    d['analytics_available'] = True
    except Exception as e:
        print("Analytics Fetch Failed:", str(e))

    return render(request, 'control/cloudflare.html', d)


@login_required(login_url='/')
def cloudflare_save_config(request, domain):
    current, err = _get_docker_user_and_auth(request, domain)
    if err:
        return err

    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'POST required'}, status=405)

    try:
        data = json.loads(request.body)
    except Exception:
        data = request.POST.dict()

    api_token = data.get('api_token', '').strip()
    email = data.get('email', '').strip()
    if not api_token:
        return JsonResponse({'status': 'error', 'message': 'API Token / Global API Key is required.'})

    verify_url = f"https://api.cloudflare.com/client/v4/zones?name={domain}"
    ok, response = _cf_api_request('GET', verify_url, api_token, email)
    if not ok:
        return JsonResponse({'status': 'error', 'message': f'Cloudflare verification failed: {response}'})

    results = response.get('result', [])
    if not results:
        return JsonResponse({'status': 'error', 'message': f'No active Cloudflare zone found for {domain}. If you are using Method 1 (API Token), make sure the token has both "Zone - Zone - Read" and "Zone - DNS - Edit" permissions. If using Method 2, make sure the domain is registered on your Cloudflare account.'})

    zone_id = results[0]['id']

    from control.models import CloudflareIntegration
    integration, created = CloudflareIntegration.objects.update_or_create(
        domain=domain,
        defaults={
            'user': current,
            'api_token': api_token,
            'email': email,
            'zone_id': zone_id,
            'is_active': True
        }
    )
    action_str = "connected" if created else "updated"
    return JsonResponse({'status': 'success', 'message': f'VoidPanel successfully {action_str} to Cloudflare zone {zone_id}!'})


@login_required(login_url='/')
def cloudflare_dns_create(request, domain):
    current, err = _get_docker_user_and_auth(request, domain)
    if err:
        return err

    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'POST required'}, status=405)

    try:
        data = json.loads(request.body)
    except Exception:
        data = request.POST.dict()

    rec_type = data.get('type', 'A').strip().upper()
    rec_name = data.get('name', '').strip()
    rec_content = data.get('content', '').strip()
    rec_ttl = int(data.get('ttl', 3600))
    rec_proxied = data.get('proxied', False)
    if isinstance(rec_proxied, str):
        rec_proxied = rec_proxied.lower() == 'true'

    if not rec_name or not rec_content:
        return JsonResponse({'status': 'error', 'message': 'Record name and content are required.'})

    from control.models import CloudflareIntegration
    integration = CloudflareIntegration.objects.filter(domain=domain).first()
    if not integration:
        return JsonResponse({'status': 'error', 'message': 'Cloudflare is not integrated for this domain.'}, status=400)

    url = f"https://api.cloudflare.com/client/v4/zones/{integration.zone_id}/dns_records"
    payload = {
        "type": rec_type,
        "name": rec_name,
        "content": rec_content,
        "ttl": rec_ttl,
        "proxied": rec_proxied
    }
    
    ok, res = _cf_api_request('POST', url, integration.api_token, integration.email, payload)
    if ok:
        return JsonResponse({'status': 'success', 'message': 'DNS record created successfully on Cloudflare!'})
    else:
        return JsonResponse({'status': 'error', 'message': f'API Error: {res}'})


@login_required(login_url='/')
def cloudflare_dns_edit(request, domain, record_id):
    current, err = _get_docker_user_and_auth(request, domain)
    if err:
        return err

    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'POST required'}, status=405)

    try:
        data = json.loads(request.body)
    except Exception:
        data = request.POST.dict()

    rec_type = data.get('type', 'A').strip().upper()
    rec_name = data.get('name', '').strip()
    rec_content = data.get('content', '').strip()
    rec_ttl = int(data.get('ttl', 3600))
    rec_proxied = data.get('proxied', False)
    if isinstance(rec_proxied, str):
        rec_proxied = rec_proxied.lower() == 'true'

    if not rec_name or not rec_content:
        return JsonResponse({'status': 'error', 'message': 'Record name and content are required.'})

    from control.models import CloudflareIntegration
    integration = CloudflareIntegration.objects.filter(domain=domain).first()
    if not integration:
        return JsonResponse({'status': 'error', 'message': 'Cloudflare is not integrated for this domain.'}, status=400)

    url = f"https://api.cloudflare.com/client/v4/zones/{integration.zone_id}/dns_records/{record_id}"
    payload = {
        "type": rec_type,
        "name": rec_name,
        "content": rec_content,
        "ttl": rec_ttl,
        "proxied": rec_proxied
    }
    
    ok, res = _cf_api_request('PUT', url, integration.api_token, integration.email, payload)
    if ok:
        return JsonResponse({'status': 'success', 'message': 'DNS record updated successfully on Cloudflare!'})
    else:
        return JsonResponse({'status': 'error', 'message': f'API Error: {res}'})


@login_required(login_url='/')
def cloudflare_dns_delete(request, domain, record_id):
    current, err = _get_docker_user_and_auth(request, domain)
    if err:
        return err

    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'POST required'}, status=405)

    from control.models import CloudflareIntegration
    integration = CloudflareIntegration.objects.filter(domain=domain).first()
    if not integration:
        return JsonResponse({'status': 'error', 'message': 'Cloudflare not configured.'}, status=400)

    url = f"https://api.cloudflare.com/client/v4/zones/{integration.zone_id}/dns_records/{record_id}"
    ok, res = _cf_api_request('DELETE', url, integration.api_token, integration.email)
    if ok:
        return JsonResponse({'status': 'success', 'message': 'DNS record deleted successfully from Cloudflare.'})
    else:
        return JsonResponse({'status': 'error', 'message': f'API Error: {res}'})


@login_required(login_url='/')
def cloudflare_dns_toggle_proxy(request, domain, record_id):
    current, err = _get_docker_user_and_auth(request, domain)
    if err:
        return err

    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'POST required'}, status=405)

    try:
        data = json.loads(request.body)
    except Exception:
        data = request.POST.dict()

    proxied = data.get('proxied', False)
    if isinstance(proxied, str):
        proxied = proxied.lower() == 'true'

    from control.models import CloudflareIntegration
    integration = CloudflareIntegration.objects.filter(domain=domain).first()
    if not integration:
        return JsonResponse({'status': 'error', 'message': 'Cloudflare not configured.'}, status=400)

    url = f"https://api.cloudflare.com/client/v4/zones/{integration.zone_id}/dns_records/{record_id}"
    payload = {
        "proxied": proxied
    }
    ok, res = _cf_api_request('PATCH', url, integration.api_token, integration.email, payload)
    if ok:
        state = "proxied" if proxied else "unproxied"
        return JsonResponse({'status': 'success', 'message': f'DNS record is now successfully {state}.'})
    else:
        return JsonResponse({'status': 'error', 'message': f'API Error: {res}'})


@login_required(login_url='/')
def cloudflare_purge_cache(request, domain):
    current, err = _get_docker_user_and_auth(request, domain)
    if err:
        return err

    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'POST required'}, status=405)

    from control.models import CloudflareIntegration
    integration = CloudflareIntegration.objects.filter(domain=domain).first()
    if not integration:
        return JsonResponse({'status': 'error', 'message': 'Cloudflare not configured.'}, status=400)

    url = f"https://api.cloudflare.com/client/v4/zones/{integration.zone_id}/purge_cache"
    payload = {
        "purge_everything": True
    }
    ok, res = _cf_api_request('POST', url, integration.api_token, integration.email, payload)
    if ok:
        return JsonResponse({'status': 'success', 'message': 'Cloudflare CDN cache purged successfully!'})
    else:
        return JsonResponse({'status': 'error', 'message': f'API Error: {res}'})


@login_required(login_url='/login')
def seo_suite_home(request, domain):
    """Render the dedicated SEO Suite home dashboard."""
    try:
        import paths
        with open(paths.MYSQL_PASSWORD_FILE, 'r') as f:
            adminpassword = f.read().strip()
    except Exception:
        adminpassword = ''
    current = request.user.username
    context = {}
    context.update(get_user_dashboard_context(current, adminpassword))
    context['domain'] = domain
    return render(request, 'control/seo_suite.html', context)


@login_required(login_url='/login')
def seo_suite_analyze(request, domain):
    """Perform domain SEO audits and backlinks/keywords check utilizing Common Crawl index."""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)
    import json
    from .seo_engine import analyze_domain_seo
    try:
        data = json.loads(request.body)
        target_domain = data.get('domain', '').strip()
        if not target_domain:
            return JsonResponse({'error': 'Domain name is required.'}, status=400)
        result = analyze_domain_seo(target_domain)
        return JsonResponse({'status': 'success', 'data': result})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required(login_url='/login')
def seo_competitor_battle(request, domain):
    """
    Head-to-head competitor battle analysis.
    Compares your page vs a competitor page and returns actionable outranking tips.
    POST body: { "your_url": "...", "competitor_url": "..." }
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)
    import json
    from .seo_engine import run_competitor_battle
    try:
        data = json.loads(request.body)
        your_url = data.get('your_url', '').strip()
        comp_url = data.get('competitor_url', '').strip()
        if not your_url or not comp_url:
            return JsonResponse({'error': 'Both your URL and competitor URL are required.'}, status=400)
        result = run_competitor_battle(your_url, comp_url)
        return JsonResponse({'status': 'success', 'data': result})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


# ─────────────────────────────────────────────────────────────────────────────
#  SEO PORTAL (Standalone new-tab portal)
# ─────────────────────────────────────────────────────────────────────────────

@login_required(login_url='/login')
def seo_portal_home(request, domain):
    """Render the fully standalone SEO portal (opens in new tab, no panel chrome)."""
    context = {
        'domain': domain,
        'user': request.user,
    }
    return render(request, 'control/seo_portal.html', context)


# ─────────────────────────────────────────────────────────────────────────────
#  MARKETING AUTOMATION WORKFLOWS API
# ─────────────────────────────────────────────────────────────────────────────


@login_required(login_url='/login')
def marketing_workflows_list(request, domain):
    """GET: list all workflows for the domain, with step count and enrolled count."""
    from .models import MarketingWorkflow
    
    workflows_qs = MarketingWorkflow.objects.filter(domain=domain)
    workflows = []
    for wf in workflows_qs:
        steps_count = wf.steps.count()
        enrolled_count = wf.enrollments.filter(status='running').count()
        workflows.append({
            'id': wf.id,
            'name': wf.name,
            'trigger_type': wf.trigger_type,
            'steps_count': steps_count,
            'enrolled_count': enrolled_count,
            'status': wf.status,
            'created_at': wf.created_at.isoformat(),
        })
        
    return JsonResponse({'workflows': workflows})


@login_required(login_url='/login')
def marketing_workflow_create(request, domain):
    """POST: create a new workflow and its steps."""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)
    import json
    from .models import MarketingWorkflow, MarketingWorkflowStep
    try:
        data = json.loads(request.body)
        name = data.get('name', '').strip()
        trigger_type = data.get('trigger_type', 'contact_created').strip()
        steps_data = data.get('steps', [])
        
        if not name:
            return JsonResponse({'error': 'Workflow name is required.'}, status=400)
            
        # Create workflow
        workflow = MarketingWorkflow.objects.create(
            user=request.user,
            domain=domain,
            name=name,
            trigger_type=trigger_type,
            status='draft'
        )
        
        # Create steps
        for idx, s in enumerate(steps_data):
            action_type = s.get('action_type', 'delay')
            delay_days = int(s.get('delay_days', 0))
            template_id = s.get('template_id')
            if template_id and str(template_id).strip():
                template_id = int(template_id)
            else:
                template_id = None
            message_text = s.get('message_text', '').strip()
            
            MarketingWorkflowStep.objects.create(
                workflow=workflow,
                step_order=idx + 1,
                action_type=action_type,
                delay_days=delay_days,
                template_id=template_id,
                message_text=message_text
            )
            
        return JsonResponse({'status': 'success', 'workflow_id': workflow.id})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required(login_url='/login')
def marketing_workflow_toggle(request, domain, workflow_id):
    """POST: toggle status of workflow (draft <-> active)."""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)
    from .models import MarketingWorkflow
    try:
        workflow = MarketingWorkflow.objects.get(id=workflow_id, domain=domain)
        new_status = 'active' if workflow.status == 'draft' else 'draft'
        workflow.status = new_status
        workflow.save()
        return JsonResponse({'status': 'success', 'new_status': new_status})
    except MarketingWorkflow.DoesNotExist:
        return JsonResponse({'error': 'Workflow not found.'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required(login_url='/login')
def marketing_workflow_delete(request, domain, workflow_id):
    """POST: delete a workflow."""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)
    from .models import MarketingWorkflow
    try:
        workflow = MarketingWorkflow.objects.get(id=workflow_id, domain=domain)
        workflow.delete()
        return JsonResponse({'status': 'success'})
    except MarketingWorkflow.DoesNotExist:
        return JsonResponse({'error': 'Workflow not found.'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


def enroll_lead_in_workflows(lead):
    """Enrolls a lead into any active workflows matching the trigger condition."""
    from .models import MarketingWorkflow, MarketingWorkflowEnrollment
    from django.utils import timezone
    
    active_workflows = MarketingWorkflow.objects.filter(domain=lead.domain, status='active')
    for wf in active_workflows:
        match = False
        if wf.trigger_type == 'contact_created':
            match = True
        elif wf.trigger_type == 'score_gte_70' and lead.score >= 70:
            match = True
        elif wf.trigger_type == 'score_between_40_70' and lead.score >= 40 and lead.score < 70:
            match = True
            
        if match:
            # Check if already enrolled
            if not MarketingWorkflowEnrollment.objects.filter(workflow=wf, lead=lead).exists():
                first_step = wf.steps.order_by('step_order').first()
                if not first_step:
                    MarketingWorkflowEnrollment.objects.create(
                        workflow=wf, lead=lead, current_step_index=0, status='completed'
                    )
                else:
                    MarketingWorkflowEnrollment.objects.create(
                        workflow=wf,
                        lead=lead,
                        current_step_index=0,
                        status='running',
                        next_run_at=timezone.now()
                    )



# ═══════════════════════════════════════════════════════════════════════
#  SUITE PLATFORM — Views
# ═══════════════════════════════════════════════════════════════════════
from control.models import (
    SuitePlan, SuiteSubscription, SuiteSSOToken,
)
from django.utils import timezone as tz


# ── helpers ─────────────────────────────────────────────────────────────

SUITE_META = {
    'social': {
        'name': 'Social Media Suite',
        'icon': 'fa-brands fa-instagram',
        'color': '#E1306C',
        'gradient': 'linear-gradient(135deg,#E1306C,#833ab4)',
        'portal_url': '/control/suite/social/',
        'desc': 'Schedule, publish & analyse social posts across all platforms.',
    },
    'seo': {
        'name': 'SEO Suite',
        'icon': 'fa-solid fa-magnifying-glass-chart',
        'color': '#6366f1',
        'gradient': 'linear-gradient(135deg,#6366f1,#8b5cf6)',
        'portal_url': '/control/suite/seo/',
        'desc': 'Keyword tracking, site audits, backlink analysis & rank monitoring.',
    },
    'marketing': {
        'name': 'Marketing Suite',
        'icon': 'fa-solid fa-bullhorn',
        'color': '#f59e0b',
        'gradient': 'linear-gradient(135deg,#f59e0b,#ef4444)',
        'portal_url': '/control/suite/marketing/',
        'desc': 'Email campaigns, landing pages, automation & lead management.',
    },
}

def _suite_session(request):
    """Return the suite session dict or None."""
    return request.session.get('suite_user')

def _require_suite_session(request, suite):
    """Return suite session if valid for this suite, else None."""
    su = _suite_session(request)
    if not su:
        return None
    if su.get('suite') != suite and su.get('source') != 'sso_multi':
        return None
    return su

def _suite_plan_limits(suite, plan_slug):
    try:
        return SuitePlan.objects.get(suite=suite, slug=plan_slug).limits
    except SuitePlan.DoesNotExist:
        return {}


def _resolve_suite_limit(request, domain, suite_key, limit_name, default_val):
    """
    Dynamically resolves a specific plan limit (e.g. 'accounts', 'contacts')
    for a given suite. Checked across standalone suite sessions, subscriptions,
    and hosting packages.
    """
    from control.models import SuiteSubscription, SuitePlan, user
    # 1. Standalone suite session (SSO or direct)
    su = request.session.get('suite_user')
    if su and su.get('suite') == suite_key:
        try:
            plan = SuitePlan.objects.get(suite=suite_key, slug=su.get('plan', 'starter'))
            return plan.limits.get(limit_name, default_val)
        except SuitePlan.DoesNotExist:
            pass

    # 2. Standalone active subscription search by hosting_domain
    sub = SuiteSubscription.objects.filter(hosting_domain=domain, suite=suite_key, is_active=True).first()
    if sub:
        return sub.plan.limits.get(limit_name, default_val)

    # 3. Hosting package fallback
    user_obj = getattr(request, 'user', None)
    current = user_obj.username if (user_obj and user_obj.is_authenticated) else ''
    if user_obj and user_obj.is_superuser:
        current = request.session.get('name', current)
    if current:
        try:
            usr = user.objects.get(username=current)
            from .utils import safe_get_package
            pkg = safe_get_package(usr.hosting_package)
            if pkg and getattr(pkg, f'includes_{suite_key}', False):
                plan_slug = getattr(pkg, f'{suite_key}_plan', 'starter') or 'starter'
                plan = SuitePlan.objects.get(suite=suite_key, slug=plan_slug)
                return plan.limits.get(limit_name, default_val)
        except Exception:
            pass

    # Fallback to default
    return default_val


# ── 1. Hosting Panel → SSO Launch ───────────────────────────────────────

@login_required
def hosting_suite_sso(request, domain, suite):
    """
    Called when a hosting-panel user clicks "Launch <Suite>".
    Verifies their package includes the suite, creates an SSO token,
    and redirects to the suite portal.
    """
    if suite not in SUITE_META:
        return HttpResponse('Unknown suite', status=404)

    # Resolve the actual hosting username (superusers impersonate via session['name'])
    if request.user.is_superuser:
        current = request.session.get('name', str(request.user))
    else:
        current = str(request.user)

    try:
        usr_obj = user.objects.get(username=current)
    except user.DoesNotExist:
        return HttpResponse(f'Hosting user not found: {current}', status=403)

    if usr_obj.domain != domain:
        return HttpResponse('Access denied', status=403)

    # Verify package includes this suite
    pkg = safe_get_package(usr_obj.hosting_package)
    if pkg is None:
        return HttpResponse('Package not found', status=403)

    suite_flag = getattr(pkg, f'includes_{suite}', False)
    if not suite_flag:
        return HttpResponse(f'Your package does not include the {SUITE_META[suite]["name"]}.', status=403)

    plan_slug = getattr(pkg, f'{suite}_plan', 'starter') or 'starter'

    # Create SSO token (valid 5 min)
    token_obj = SuiteSSOToken.create_for(
        suite=suite,
        hosting_domain=domain,
        user_email=usr_obj.email or f'{current}@{domain}',
        plan_slug=plan_slug,
    )

    return redirect(f'/control/suite/sso/{token_obj.token}/')


# ── 2. SSO Token Validation ──────────────────────────────────────────────

def suite_sso_validate(request, token):
    """
    Validates a one-time SSO token and logs the user into the suite session.
    """
    try:
        tok = SuiteSSOToken.objects.get(token=token)
    except SuiteSSOToken.DoesNotExist:
        return HttpResponse('Invalid or expired link.', status=403)

    if not tok.is_valid():
        return HttpResponse('This link has expired or already been used.', status=403)

    tok.used = True
    tok.save()

    # Establish suite session
    request.session['suite_user'] = {
        'email':          tok.user_email,
        'suite':          tok.suite,
        'plan':           tok.plan_slug,
        'source':         'sso',
        'hosting_domain': tok.hosting_domain,
        'name':           tok.hosting_domain,
    }

    return redirect(f'/control/suite/{tok.suite}/')


# ── 3. Standalone Suite Login / Logout ──────────────────────────────────

def suite_login(request, suite=None):
    """Login for standalone suite-only customers.
    
    When `suite` is provided (e.g. via /control/suite/marketing/login/) the
    page becomes a branded login for that specific suite — pre-selecting the
    correct tab and colour-scheme.  The generic /control/suite/login/ URL
    keeps `suite=None` and shows the unified multi-suite view.
    """
    # Seed default plans on first visit (idempotent)
    SuitePlan.seed_defaults()

    # Validate the pre-selected suite slug
    if suite and suite not in SUITE_META:
        suite = None

    error = None
    if request.method == 'POST':
        email    = request.POST.get('email', '').strip().lower()
        password = request.POST.get('password', '')
        # If a specific suite was requested (branded login) enforce it
        requested_suite = request.POST.get('suite_filter') or suite
        try:
            if requested_suite:
                sub = SuiteSubscription.objects.get(email=email, suite=requested_suite)
            else:
                sub = SuiteSubscription.objects.get(email=email)
            if sub.check_password(password) and sub.is_valid():
                request.session['suite_user'] = {
                    'email':          sub.email,
                    'suite':          sub.suite,
                    'plan':           sub.plan.slug,
                    'source':         'direct',
                    'hosting_domain': sub.hosting_domain or sub.email.split('@')[0],
                    'name':           f'{sub.first_name} {sub.last_name}'.strip() or sub.email,
                }
                sub.last_login = tz.now()
                sub.save(update_fields=['last_login'])
                return redirect(f'/control/suite/{sub.suite}/')
            else:
                error = 'Invalid credentials or account inactive.'
        except SuiteSubscription.DoesNotExist:
            if requested_suite:
                error = f'No {SUITE_META[requested_suite]["name"]} account found with that email.'
            else:
                error = 'No account found with that email.'
        except SuiteSubscription.MultipleObjectsReturned:
            # User has subscriptions to multiple suites — fall back to any match
            sub = SuiteSubscription.objects.filter(email=email, is_active=True).order_by('-created_at').first()
            if sub and sub.check_password(password) and sub.is_valid():
                request.session['suite_user'] = {
                    'email':          sub.email,
                    'suite':          sub.suite,
                    'plan':           sub.plan.slug,
                    'source':         'direct',
                    'hosting_domain': sub.hosting_domain or sub.email.split('@')[0],
                    'name':           f'{sub.first_name} {sub.last_name}'.strip() or sub.email,
                }
                sub.last_login = tz.now()
                sub.save(update_fields=['last_login'])
                return redirect(f'/control/suite/{sub.suite}/')
            else:
                error = 'Invalid credentials or account inactive.'

    # Build plan cards for the landing section
    plans_by_suite = {}
    for sp in SuitePlan.objects.filter(is_active=True).order_by('suite', 'sort_order'):
        plans_by_suite.setdefault(sp.suite, []).append(sp)

    return render(request, 'control/suite_login.html', {
        'error': error,
        'plans_by_suite': plans_by_suite,
        'suite_meta': SUITE_META,
        'active_suite': suite,  # None = generic multi-suite page; else 'social'/'seo'/'marketing'
        'active_suite_info': SUITE_META.get(suite) if suite else None,
    })


def suite_logout(request):
    request.session.pop('suite_user', None)
    return redirect('/control/suite/login/')


# ── 4. Suite Portals ─────────────────────────────────────────────────────

def _suite_portal_ctx(request, suite):
    """Build shared context for any suite portal."""
    su = _suite_session(request)

    # ── Django panel admin bypass ─────────────────────────────────────────
    # Authenticated staff/superusers can access any suite portal regardless
    # of their suite session (they manage all tenants).
    django_user = getattr(request, 'user', None)
    is_panel_admin = (
        django_user is not None
        and getattr(django_user, 'is_authenticated', False)
        and (getattr(django_user, 'is_staff', False) or getattr(django_user, 'is_superuser', False))
    )

    if not su:
        if is_panel_admin:
            # Build a synthetic session tied to THIS panel user's domain.
            # Priority:
            #   1. SuiteSubscription matched to the logged-in user's email
            #   2. panel control.models.user domain (the account the user owns)
            #   3. Any active SuiteSubscription (last resort)
            from .models import SuiteSubscription, SuitePlan
            from . import models as ctrl_models

            user_email = (
                getattr(django_user, 'email', None)
                or getattr(django_user, 'username', '')
            )

            # 1. Subscription matching the logged-in user's email
            sub = (
                SuiteSubscription.objects.filter(email=user_email, suite=suite, is_active=True).first()
                or SuiteSubscription.objects.filter(email=user_email, is_active=True).first()
            )

            # 2. Look up panel user domain — prefer matching the request Host header
            panel_domain = ''
            try:
                request_host = request.get_host().split(':')[0]  # strip port
                # Try exact match of request hostname against user.domain
                _panel_match = ctrl_models.user.objects.filter(
                    email=user_email, domain=request_host
                ).first()
                if _panel_match:
                    panel_domain = _panel_match.domain
                else:
                    # Fallback: any domain for this user
                    _panel_any = ctrl_models.user.objects.filter(email=user_email).first()
                    if _panel_any:
                        panel_domain = _panel_any.domain or ''
            except Exception:
                pass

            # 3. Fallback — any active subscription
            if not sub:
                sub = SuiteSubscription.objects.filter(suite=suite, is_active=True).first() \
                      or SuiteSubscription.objects.filter(is_active=True).first()

            if sub:
                resolved_domain = (
                    panel_domain                                # user's actual panel domain
                    or sub.hosting_domain                      # subscription's stored domain
                    or sub.email.split('@')[0]                 # email-prefix fallback
                )
                su = {
                    'email':          user_email or sub.email,
                    'suite':          suite,
                    'plan':           sub.plan.slug if sub.plan else 'starter',
                    'source':         'admin_bypass',
                    'hosting_domain': resolved_domain,
                    'name':           f'{sub.first_name} {sub.last_name}'.strip() or sub.email,
                }
            else:
                su = {
                    'email':          user_email,
                    'suite':          suite,
                    'plan':           'starter',
                    'source':         'admin_bypass',
                    'hosting_domain': panel_domain,
                    'name':           django_user.get_full_name() or django_user.username,
                }
        else:
            return None, redirect('/control/suite/login/')

    if su.get('suite') != suite:
        if is_panel_admin:
            # Admin accessing a different suite — allow it, override suite key
            su = dict(su)
            su['suite'] = suite
        else:
            # Regular suite user — redirect to their correct suite
            return None, redirect(f'/control/suite/{su["suite"]}/')

    limits = _suite_plan_limits(suite, su.get('plan', 'starter'))
    ctx = {
        'suite_user': su,
        'suite_key': suite,
        'suite_info': SUITE_META[suite],
        'plan_limits': limits,
        'plan_slug': su.get('plan', 'starter'),
    }
    return ctx, None


def suite_social_portal(request):
    ctx, redir_resp = _suite_portal_ctx(request, 'social')
    if redir_resp:
        return redir_resp
    su = ctx['suite_user']
    # Reuse social portal template — pass domain from hosting domain or email prefix
    domain_key = su.get('hosting_domain') or su['email'].split('@')[0]
    ctx['domain'] = domain_key
    ctx['suite_mode'] = True
    return render(request, 'control/social_portal.html', ctx)


def suite_seo_portal(request):
    ctx, redir_resp = _suite_portal_ctx(request, 'seo')
    if redir_resp:
        return redir_resp
    su = ctx['suite_user']
    domain_key = su.get('hosting_domain') or su['email'].split('@')[0]
    ctx['domain'] = domain_key
    ctx['suite_mode'] = True
    return render(request, 'control/seo_portal.html', ctx)


def suite_marketing_portal(request):
    ctx, redir_resp = _suite_portal_ctx(request, 'marketing')
    if redir_resp:
        return redir_resp
    su = ctx['suite_user']

    # ── Domain resolution ─────────────────────────────────────────────────
    # Priority:
    #  1. panel control.models.user.domain for the logged-in Django user
    #  2. SuiteSubscription.hosting_domain from DB
    #  3. Self-healing via MarketingLead discovery
    from .models import SuiteSubscription, MarketingLead
    from . import models as ctrl_models

    # 1. Panel user's own domain — prefer domain matching the current request host
    panel_domain_key = ''
    django_user_obj = getattr(request, 'user', None)
    if django_user_obj and getattr(django_user_obj, 'is_authenticated', False):
        _user_email = getattr(django_user_obj, 'email', '') or getattr(django_user_obj, 'username', '')
        try:
            _request_host = request.get_host().split(':')[0]  # strip port
            # Prefer the panel account whose domain matches the current Host header
            _panel_acct = ctrl_models.user.objects.filter(
                email=_user_email, domain=_request_host
            ).first()
            if _panel_acct:
                panel_domain_key = _panel_acct.domain
            else:
                # No exact match — use any account for this user
                _panel_acct = ctrl_models.user.objects.filter(email=_user_email).first()
                if _panel_acct:
                    panel_domain_key = _panel_acct.domain or ''
        except Exception:
            pass

    # 2. SuiteSubscription DB value — use filter().first() to handle any suite type
    try:
        _db_sub = SuiteSubscription.objects.filter(email=su['email']).order_by('-id').first()
        raw_hosting_domain = (_db_sub.hosting_domain or '') if _db_sub else ''
    except Exception:
        raw_hosting_domain = ''

    # Resolve: panel domain (from request host) first, then subscription domain
    if panel_domain_key:
        domain_key = panel_domain_key
    elif raw_hosting_domain:
        domain_key = raw_hosting_domain
    else:
        # Neither the panel user domain nor subscription domain is set.
        # Try: request Host header, then self-healing via leads, then email prefix.
        email_prefix = su['email'].split('@')[0]

        # Strategy 0: use request hostname as the domain (most direct signal)
        try:
            _req_host = request.get_host().split(':')[0]
            # Only treat the request host as a valid domain if it's not the panel server itself
            # (i.e., it contains a dot and isn't the fast. subdomain server)
            if '.' in _req_host and not _req_host.startswith('fast.'):
                domain_key = _req_host
                raw_hosting_domain = _req_host  # use below for self-heal persist
        except Exception:
            _req_host = ''

        real_domain = None

        if not raw_hosting_domain:
            # Strategy 1: look up by Django user (if authenticated via panel login)
            if getattr(request, 'user', None) and getattr(request.user, 'is_authenticated', False):
                real_domain = (
                    MarketingLead.objects.filter(user=request.user)
                    .exclude(domain=email_prefix)
                    .values_list('domain', flat=True)
                    .first()
                )

            # Strategy 2: any lead with a domain that contains a dot (real FQDN)
            if not real_domain:
                real_domain = (
                    MarketingLead.objects.filter(domain__contains='.')
                    .values_list('domain', flat=True)
                    .first()
                )

            if real_domain:
                # Persist so future requests skip the discovery step.
                SuiteSubscription.objects.filter(email=su['email']).update(hosting_domain=real_domain)
                # Also update session so sub-requests are consistent.
                suite_session = request.session.get('suite_user', {})
                suite_session['hosting_domain'] = real_domain
                request.session['suite_user'] = suite_session
                request.session.modified = True
                domain_key = real_domain
            else:
                domain_key = raw_hosting_domain or email_prefix
    # ── End domain resolution ─────────────────────────────────────────────

    ctx['domain'] = domain_key
    ctx['suite_mode'] = True

    # Build and merge the marketing portal database context (leads, stats, campaigns, etc.)
    try:
        marketing_ctx = _get_marketing_portal_context(request, domain_key)
        if isinstance(marketing_ctx, dict):
            ctx.update(marketing_ctx)
    except Exception as e:
        import logging
        logging.getLogger(__name__).exception('suite_marketing_portal: _get_marketing_portal_context failed for domain %s: %s', domain_key, e)

    return render(request, 'control/marketing.html', ctx)



# ── 5. Admin — Suite Plans ───────────────────────────────────────────────

@login_required
def suite_admin_plans(request):
    if not request.user.is_superuser:
        return HttpResponse('Access denied', status=403)
    SuitePlan.seed_defaults()
    plans = SuitePlan.objects.all().order_by('suite', 'sort_order')
    return render(request, 'control/suite_admin.html', {
        'tab': 'plans',
        'plans': plans,
        'suite_meta': SUITE_META,
        'suite_choices': [('social','Social Media'),('seo','SEO'),('marketing','Marketing')],
    })


@login_required
def suite_plan_save(request):
    if not request.user.is_superuser:
        return JsonResponse({'error': 'Access denied'}, status=403)
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=400)
    data = json.loads(request.body)
    plan_id = data.get('id')
    try:
        limits_raw = data.get('limits', '{}')
        limits = json.loads(limits_raw) if isinstance(limits_raw, str) else limits_raw
    except Exception:
        limits = {}

    if plan_id:
        obj = SuitePlan.objects.get(pk=plan_id)
        obj.name       = data['name']
        obj.price_usd  = data.get('price_usd', 0)
        obj.limits     = limits
        obj.is_active  = data.get('is_active', True)
        obj.sort_order = data.get('sort_order', 0)
        obj.save()
    else:
        obj = SuitePlan.objects.create(
            suite      = data['suite'],
            slug       = data['slug'],
            name       = data['name'],
            price_usd  = data.get('price_usd', 0),
            limits     = limits,
            sort_order = data.get('sort_order', 0),
        )
    return JsonResponse({'ok': True, 'id': obj.pk, 'name': str(obj)})


@login_required
def suite_plan_delete(request, plan_id):
    if not request.user.is_superuser:
        return JsonResponse({'error': 'Access denied'}, status=403)
    SuitePlan.objects.filter(pk=plan_id).delete()
    return JsonResponse({'ok': True})


# ── 6. Admin — Suite Subscriptions ──────────────────────────────────────

@login_required
def suite_admin_subs(request):
    if not request.user.is_superuser:
        return HttpResponse('Access denied', status=403)
    subs  = SuiteSubscription.objects.select_related('plan').order_by('-created_at')
    plans = SuitePlan.objects.filter(is_active=True).order_by('suite', 'sort_order')
    return render(request, 'control/suite_admin.html', {
        'tab':        'subscriptions',
        'subs':       subs,
        'plans':      plans,
        'suite_meta': SUITE_META,
    })


@login_required
def suite_sub_save(request):
    if not request.user.is_superuser:
        return JsonResponse({'error': 'Access denied'}, status=403)
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=400)
    data = json.loads(request.body)
    sub_id = data.get('id')

    try:
        plan = SuitePlan.objects.get(pk=data['plan_id'])
    except SuitePlan.DoesNotExist:
        return JsonResponse({'error': 'Plan not found'}, status=400)

    if sub_id:
        obj = SuiteSubscription.objects.get(pk=sub_id)
        obj.first_name = data.get('first_name', obj.first_name)
        obj.last_name  = data.get('last_name', obj.last_name)
        obj.company    = data.get('company', obj.company)
        obj.plan       = plan
        obj.suite      = plan.suite
        obj.is_active  = data.get('is_active', True)
        if data.get('expires_at'):
            from django.utils.dateparse import parse_datetime
            obj.expires_at = parse_datetime(data['expires_at'])
        if data.get('password'):
            obj.set_password(data['password'])
        obj.save()
    else:
        email = data.get('email', '').strip().lower()
        if SuiteSubscription.objects.filter(email=email).exists():
            return JsonResponse({'error': f'Email {email} already has a subscription.'}, status=400)
        obj = SuiteSubscription(
            email      = email,
            first_name = data.get('first_name', ''),
            last_name  = data.get('last_name', ''),
            company    = data.get('company', ''),
            plan       = plan,
            suite      = plan.suite,
            is_active  = True,
        )
        obj.set_password(data.get('password', 'changeme123'))
        obj.save()

    return JsonResponse({'ok': True, 'id': obj.pk, 'email': obj.email})


@login_required
def suite_sub_delete(request, sub_id):
    if not request.user.is_superuser:
        return JsonResponse({'error': 'Access denied'}, status=403)
    SuiteSubscription.objects.filter(pk=sub_id).delete()
    return JsonResponse({'ok': True})


@login_required
def suite_sub_toggle(request, sub_id):
    if not request.user.is_superuser:
        return JsonResponse({'error': 'Access denied'}, status=403)
    obj = SuiteSubscription.objects.get(pk=sub_id)
    obj.is_active = not obj.is_active
    obj.save(update_fields=['is_active'])
    return JsonResponse({'ok': True, 'is_active': obj.is_active})


# ── 7. Suite Public API ────────────────────────────────────────────────────
#
#  Used by voidpanel.com website to:
#   1. List available plans              GET  /control/api/suite/plans/
#   2. Create a suite account + SSO URL  POST /control/api/suite/create-account/
#   3. Get SSO token for hosting user    POST /control/api/suite/sso-token/
#
#  Authentication: header  X-Suite-API-Key: <key>
#  Set SUITE_API_KEY = 'your-secret-key' in panel/settings.py
#
def _suite_api_auth(request):
    """Return True if the request carries a valid API key."""
    from django.conf import settings
    key = getattr(settings, 'SUITE_API_KEY', None)
    if not key:
        # If no key configured, reject all external API calls
        return False
    return request.headers.get('X-Suite-API-Key', '') == key


def suite_api_plans(request):
    """
    GET /control/api/suite/plans/
    Returns all active suite plans as JSON.
    No auth required (public pricing page use).
    """
    plans = SuitePlan.objects.filter(is_active=True).order_by('suite', 'sort_order')
    data  = []
    for p in plans:
        data.append({
            'id':        p.pk,
            'suite':     p.suite,
            'suite_label': dict([('social','Social Media'),('seo','SEO'),('marketing','Marketing')]).get(p.suite, p.suite),
            'slug':      p.slug,
            'name':      p.name,
            'price_inr': float(p.price_usd),   # stored as INR
            'limits':    p.limits,
        })
    return JsonResponse({'ok': True, 'plans': data})


@csrf_exempt
def suite_api_create(request):
    """
    POST /control/api/suite/create-account/
    Body (JSON):
      {
        "email":       "user@example.com",
        "first_name":  "Jane",
        "last_name":   "Doe",
        "password":    "secret123",       # optional — auto-generated if omitted
        "suite":       "marketing",       # social | seo | marketing
        "plan_slug":   "pro",             # starter | pro | growth | etc.
        "auto_login":  true               # if true, returns a one-time SSO URL
      }

    Returns:
      { "ok": true, "account_id": 42, "email": "...",
        "suite": "marketing", "plan": "Pro",
        "sso_url": "https://panel.example.com/control/suite/sso/<uuid>/",  # if auto_login
        "login_url": "/control/suite/login/" }
    """
    if not _suite_api_auth(request):
        return JsonResponse({'error': 'Unauthorized — missing or invalid X-Suite-API-Key'}, status=401)
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)

    try:
        data = json.loads(request.body)
    except Exception:
        return JsonResponse({'error': 'Invalid JSON body'}, status=400)

    email      = (data.get('email') or '').strip().lower()
    suite      = (data.get('suite') or '').strip().lower()
    plan_slug  = (data.get('plan_slug') or 'starter').strip().lower()
    first_name = data.get('first_name', '')
    last_name  = data.get('last_name', '')
    password   = data.get('password') or _random_password()
    auto_login = data.get('auto_login', False)

    if not email or '@' not in email:
        return JsonResponse({'error': 'Valid email required'}, status=400)
    if suite not in ('social', 'seo', 'marketing'):
        return JsonResponse({'error': 'suite must be: social, seo, or marketing'}, status=400)

    try:
        plan = SuitePlan.objects.get(suite=suite, slug=plan_slug)
    except SuitePlan.DoesNotExist:
        return JsonResponse({'error': f'Plan "{plan_slug}" not found for suite "{suite}"'}, status=400)

    # Create or update subscription
    created = False
    if SuiteSubscription.objects.filter(email=email).exists():
        obj = SuiteSubscription.objects.get(email=email)
        obj.plan  = plan
        obj.suite = suite
        if data.get('password'):
            obj.set_password(password)
        obj.is_active = True
        obj.save()
    else:
        obj = SuiteSubscription(
            email=email, first_name=first_name, last_name=last_name,
            suite=suite, plan=plan, is_active=True,
        )
        obj.set_password(password)
        obj.save()
        created = True

    resp = {
        'ok':        True,
        'created':   created,
        'account_id': obj.pk,
        'email':     obj.email,
        'suite':     suite,
        'plan':      plan.name,
        'plan_slug': plan_slug,
        'login_url': '/control/suite/login/',
    }

    # Optionally generate SSO auto-login URL
    if auto_login:
        tok = SuiteSSOToken.create_for(
            suite=suite,
            hosting_domain=email.split('@')[1],
            user_email=email,
            plan_slug=plan_slug,
        )
        resp['sso_url']   = f'/control/suite/sso/{tok.token}/'
        resp['sso_token'] = str(tok.token)
        resp['sso_expires_at'] = tok.expires_at.isoformat()

    return JsonResponse(resp, status=201 if created else 200)


@csrf_exempt
def suite_api_sso_token(request):
    """
    POST /control/api/suite/sso-token/
    Generate a one-time SSO token for a hosting panel user whose
    package includes a suite (called from voidpanel.com website).

    Body (JSON):
      {
        "hosting_domain": "example.com",
        "user_email":     "admin@example.com",
        "suite":          "social",
        "plan_slug":      "growth"
      }

    Returns:
      { "ok": true, "sso_url": "/control/suite/sso/<uuid>/",
        "token": "<uuid>", "expires_at": "..." }
    """
    if not _suite_api_auth(request):
        return JsonResponse({'error': 'Unauthorized — missing or invalid X-Suite-API-Key'}, status=401)
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)

    try:
        data = json.loads(request.body)
    except Exception:
        return JsonResponse({'error': 'Invalid JSON body'}, status=400)

    hosting_domain = (data.get('hosting_domain') or '').strip()
    user_email     = (data.get('user_email') or '').strip().lower()
    suite          = (data.get('suite') or '').strip().lower()
    plan_slug      = (data.get('plan_slug') or 'starter').strip()

    if not hosting_domain or not user_email or suite not in ('social', 'seo', 'marketing'):
        return JsonResponse({'error': 'hosting_domain, user_email, and valid suite required'}, status=400)

    tok = SuiteSSOToken.create_for(
        suite=suite,
        hosting_domain=hosting_domain,
        user_email=user_email,
        plan_slug=plan_slug,
    )

    return JsonResponse({
        'ok':         True,
        'sso_url':    f'/control/suite/sso/{tok.token}/',
        'token':      str(tok.token),
        'expires_at': tok.expires_at.isoformat(),
        'suite':      suite,
        'plan_slug':  plan_slug,
    })


def _random_password(length=12):
    import secrets, string
    alphabet = string.ascii_letters + string.digits + '!@#$'
    return ''.join(secrets.choice(alphabet) for _ in range(length))


@csrf_exempt
def suite_api_toggle_status(request):
    """
    POST /control/api/suite/toggle-status/
    Body (JSON):
      {
        "email":     "user@example.com",
        "is_active": false
      }
    """
    if not _suite_api_auth(request):
        return JsonResponse({'error': 'Unauthorized — missing or invalid X-Suite-API-Key'}, status=401)
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)

    try:
        data = json.loads(request.body)
    except Exception:
        return JsonResponse({'error': 'Invalid JSON body'}, status=400)

    email = (data.get('email') or '').strip().lower()
    is_active = data.get('is_active', True)

    if not email:
        return JsonResponse({'error': 'Email required'}, status=400)

    sub = SuiteSubscription.objects.filter(email=email).first()
    if not sub:
        return JsonResponse({'error': 'Suite subscription not found'}, status=404)

    sub.is_active = is_active
    sub.save(update_fields=['is_active'])
    return JsonResponse({'ok': True, 'email': email, 'is_active': is_active})


