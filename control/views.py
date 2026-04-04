from django.http import JsonResponse, HttpResponse
from django.shortcuts import render,redirect
import json
import requests
from django.contrib.auth.decorators import login_required
from control.models import pythonname,mernname,user,domain,subdomainname,cron,package,allemail,redir,ftpaccount,ftp,phpversion
from function import get_server_ip,is_website_live,get_database_users_with_filter,get_database_names_with_filter,parse_dns_zone_file,run_command,zip_multiple_locations_backup_user,get_directory_size_in_mb,get_file_info
from django.views.decorators.csrf import csrf_exempt
import os
import subprocess


# except:
#      adminpassword="adminpassword"


def get_user_dashboard_context(current, adminpassword="adminpassword"):
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
        import os
        cert_path = f'/etc/letsencrypt/live/{u.domain}/fullchain.pem'
        d['primarydomainstatus'] = os.path.exists(cert_path)
    except:
        d['primarydomainstatus'] = False

    d['rohan'] = ftp.objects.filter(id=1).first()

    d['avaiablestorage'] = int(hp.storage)
    try:
        d['remainingstorage'] = int(get_directory_size_in_mb(f'/home/{current}'))
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
    if d['totalemail'] == 0:
        d['totalemail'] = '∞'
    d['usedemail'] = len(allemail.objects.filter(domain=u.domain))

    d['totalsubdomain'] = int(hp.subdomain)
    if d['totalsubdomain'] == 0:
        d['totalsubdomain'] = '∞'
    d['usedsubdomain'] = len(subdomainname.objects.filter(domain=u.domain))

    d['totalftp'] = int(hp.ftp)
    if d['totalftp'] == 0:
        d['totalftp'] = '∞'
    d['usedftp'] = len(ftpaccount.objects.filter(main=u))

    d['totaldb'] = int(hp.databases_allowed)
    if d['totaldb'] == 0:
        d['totaldb'] = '∞'
    d['shell_access'] = getattr(u, 'shell', False)
    mainn = str(current) + '_'
    d['useddatabase'] = len(get_database_names_with_filter(adminpassword, mainn))
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
                  
             
        if request.method == 'POST':
            # Extract data from the POST request
            name = request.POST.get('user')
            name=name.lower()
            storage = request.POST.get('storage')
            print(name,storage)
            run_command(f'sudo setquota -u {name} {storage} {storage} 0 0 /')
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
                  
             
        if request.method == 'POST':
            # Extract data from the POST request
            name = request.POST.get('domain')
            name=name.lower()
            password = request.POST.get('password')
            run_command(f"echo '{name}:{password}' | sudo chpasswd")
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
            path = request.POST.get('path')
           
            if path[0]!="/":
                 path="/"+path
            path="/home/"+curren+path
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
                run_command(f'mkdir -p {path}')
                try:
                    run_command(f'sudo useradd -m -s /usr/sbin/nologin {fullname} && sudo passwd -u {fullname} && echo "{fullname}:{password}" | sudo chpasswd')
                except:
                     pass
                try:
                    run_command(f'sudo setquota -u {fullname} {storage} {storage} 0 0 /')
                except:
                     pass
                run_command(f'sudo chown {fullname}:{fullname} {path}')
                with open('/etc/vsftpd.userlist','a') as f:
                     f.write(f"\n {fullname}")
                run_command("sudo systemctl restart vsftpd")
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
        with open('/etc/dontdelete.txt','r') as f:
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
                    response = requests.get(url)
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
                    run_command(f'sudo deluser {data}')
                    domain32=user.objects.get(username=current).domain
                    return redirect(f"/control/ftp/{domain32}")
                except:
                    return redirect("/")
           
    else: 
        return redirect('/')


@login_required(login_url='/')
def pma_login(request, data):
    from django.http import HttpResponse, JsonResponse
    from control.pma_sso import create_temp_pma_user
    try:
        with open('/etc/dontdelete.txt', 'r') as f:
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
        
        # Get directory prefix for wildcards
        cc = lold.dir
        
        # Create temp user
        temp_user, temp_password = create_temp_pma_user(cc, adminpassword)
        if not temp_user:
            return JsonResponse({'status': 'error', 'message': 'Failed to generate secure SSO session.'}, status=500)

        # Inject robust auto-submitting HTML form
        html_content = f"""
        <html>
        <head><title>Loading phpMyAdmin...</title></head>
        <body style="background-color: #0d1117; color: #fff; display: flex; justify-content: center; align-items: center; height: 100vh; font-family: sans-serif;">
            <div style="text-align: center;">
                <h2>Authenticating securely...</h2>
                <div style="width: 40px; height: 40px; border: 4px solid rgba(255,255,255,0.1); border-left-color: #fff; border-radius: 50%; animation: spin 1s linear infinite; margin: 0 auto; margin-top: 15px;"></div>
                <style>@keyframes spin {{ 0% {{ transform: rotate(0deg); }} 100% {{ transform: rotate(360deg); }} }}</style>
            </div>
            <form id="pma_login_form" method="post" action="http://{data}/phpmyadmin/index.php" style="display: none;">
                <input type="hidden" name="pma_username" value="{temp_user}">
                <input type="hidden" name="pma_password" value="{temp_password}">
            </form>
            <script>
                // Automatically submit the form to phpMyAdmin
                setTimeout(function() {{
                    document.getElementById('pma_login_form').submit();
                }}, 500);
            </script>
        </body>
        </html>
        """
        return HttpResponse(html_content)

    except Exception as e:
        print(f"Error in pma_login: {e}")
        return redirect('/')


@login_required(login_url='/')
def dbconnect(request, data):
    try:
        with open('/etc/dontdelete.txt', 'r') as f:
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
            return render(request, 'control/dbconnect.html', d)
        except Exception:
            return redirect('/listwebsite/')
    else:
        return redirect('/')


@login_required(login_url='/')
def addredirect(request,data):
    try:
        with open('/etc/dontdelete.txt','r') as f:
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
                    response = requests.get(url)
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
        with open('/etc/dontdelete.txt','r') as f:
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
                    response = requests.get(url)
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
        file_path = f'/home/{domain_obj.dir}/public_html/php.ini'

        DEFAULT_INI = "; Modern VoidPanel PHP Profile\nmemory_limit = 128M\nupload_max_filesize = 64M\npost_max_size = 64M\nmax_execution_time = 30\nmax_input_time = 60\ndisplay_errors = Off\n"

        # Safe Create
        if not os.path.exists(file_path):
            with open(file_path, 'w') as f:
                f.write(DEFAULT_INI)
            import subprocess
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
        with open('/etc/dontdelete.txt','r') as f:
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
               for i in allemail.objects.filter(domain=data).all():
                   usernameemail=i.email.split("@")[0]
                   maildir_path = f"/var/mail/vhosts/{i.domain}/{usernameemail}" 
                   new_dir = os.path.join(maildir_path, "new")
                   cur_dir = os.path.join(maildir_path, "cur")
                   new_emails_count = len(os.listdir(new_dir)) if os.path.exists(new_dir) else 0
                   cur_emails_count = len(os.listdir(cur_dir)) if os.path.exists(cur_dir) else 0
                   total_emails_count = new_emails_count + cur_emails_count
                   command=f'grep "from=<{i.email}>" /var/log/mail.log'
                   result = subprocess.run(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                   command = f"grep -E 'status=bounced|status=deferred' /var/log/mail.log | grep '{i.email}'"
                   result2 = subprocess.run(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
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
               d['server_hostname'] = hostname
               d['server_ip'] = get_server_ip()
               d['roundcube_url'] = f"https://{hostname}:9003"
               
               url = 'https://voidpanel.com/clientdocs/'  # Replace with your API URL
               response = requests.get(url)
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
        with open('/etc/dontdelete.txt', 'r') as f:
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
            
            total_sent = 0
            total_failed = 0
            total_queue = 0
            total_received = 0
            
            for i in emails:
                usernameemail = i.email.split("@")[0]
                maildir_path = f"/var/mail/vhosts/{i.domain}/{usernameemail}" 
                new_dir = os.path.join(maildir_path, "new")
                cur_dir = os.path.join(maildir_path, "cur")
                
                new_emails = len(os.listdir(new_dir)) if os.path.exists(new_dir) else 0
                cur_emails = len(os.listdir(cur_dir)) if os.path.exists(cur_dir) else 0
                received_count = new_emails + cur_emails
                
                # Sent stats
                cmd_sent = f'grep "from=<{i.email}>" /var/log/mail.log | wc -l'
                sent_count = int(subprocess.check_output(cmd_sent, shell=True).decode().strip())
                
                # Failed stats
                cmd_failed = f"grep -E 'status=bounced|status=deferred' /var/log/mail.log | grep '{i.email}' | wc -l"
                failed_count = int(subprocess.check_output(cmd_failed, shell=True).decode().strip())
                
                # Queue stats
                cmd_queue = f"postqueue -p | grep '{i.email}' | wc -l"
                queue_count = int(subprocess.check_output(cmd_queue, shell=True).decode().strip())
                
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
            # Basic context for sidebar/navbar
            d['ipaddress'] = get_server_ip()
            d['avaiablestorage'] = int(safe_get_package(user.objects.get(username=current).hosting_package).storage)
            d['remainingstorage'] = int(get_directory_size_in_mb(f'/home/{current}'))
            d['usedemail'] = len(emails)
            d['totalemail'] = safe_get_package(user.objects.get(username=current).hosting_package).email_accounts
            
            return render(request, 'control/email_analysis.html', d)
        except Exception as e:
            print(f"Error in email_analysis: {e}")
            return redirect('/')
    else:
        return redirect('/')






@login_required(login_url='/')
def backup(request,data):
    try:
        with open('/etc/dontdelete.txt','r') as f:
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
                    url = 'https://voidpanel.com/clientdocs/'  # Replace with your API URL
                    response = requests.get(url)
                    if response.status_code == 200:
                        dataee = response.json()  # Parse the JSON response
                        d['docs']=dataee
                    return render(request,'control/backup.html',d)
                except Exception as e:
                    return redirect("/")
           
    else: 
        return redirect('/')

                   
@login_required(login_url='/')
def index(request):
    try:
        with open('/etc/dontdelete.txt','r') as f:
            adminpassword=f.read()
            adminpassword=adminpassword.strip()
    except:
          adminpassword="adminpassword"
    if request.user.is_superuser:
        current=request.session['name']
    else:
        current=request.user
    d={}
    

    d.update(get_user_dashboard_context(current, adminpassword))
    return render(request, 'control/index.html', d)

@login_required(login_url='/')
def eadns(request):
    try:
        with open('/etc/dontdelete.txt','r') as f:
            adminpassword=f.read().strip()
    except:
        adminpassword="adminpassword"
    if request.user.is_superuser:
        current=request.session['name']
    else:
        current=request.user
    d={}
    d.update(get_user_dashboard_context(current, adminpassword))
    
    domainname = request.GET.get('domain')
    try:
        current_domain=domain.objects.get(domain=domainname)
        d['domain']=current_domain
        pat=f"/etc/bind/db.{current_domain}"
        data12=parse_dns_zone_file(pat)
        d['data']=data12[2:]
    except:
        return redirect('/')
        
    url = 'https://voidpanel.com/clientdocs/'
    response = requests.get(url)
    if response.status_code == 200:
        d['docs'] = response.json()
        
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
                  
             
        if request.method == 'POST':
            # Extract data from the POST request
            name = request.POST.get('name')

            domainname = request.POST.get('domain')
            record_class = request.POST.get('class')
            record_type = request.POST.get('type',None)
            ttl = request.POST.get('ttl')
            data = request.POST.get('data')
            if dddd==domainname:
                if name and record_class and record_type and data and domainname:
                    pat=f"/etc/bind/db.{domainname}"
                    with open(pat, 'a') as zone_file:
                        zone_file.write(f"\n; {record_type} Record for {domainname}\n")
                        zone_file.write(f"{name} {ttl} {record_class} {record_type} {data}\n")
                    run_command("sudo systemctl restart bind9")
                        
                    return JsonResponse({'success': True})
                else:
                    return JsonResponse({'success': False, 'error': 'Missing required fields'})
            else:
                 return JsonResponse({'success': False, 'error': 'Invalid request method'})
                 

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
    pat = f"/etc/bind/db.{domain}"
    
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
            with open(pat, 'r') as file:
                lines = file.readlines()
            with open(pat, 'w') as file:
                for line in lines:
                    if name in line and record_type in line and data[:20] in line and (not ttl or ttl in line):
                        deleted = True
                    elif name in line and data[:20] in line:
                        deleted = True
                    else:
                        file.write(line)

            if deleted:
                run_command("sudo systemctl restart bind9")
                return JsonResponse({'success': True})
            else:
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

    pat = f"/etc/bind/db.{domain}"
    
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
            with open(pat, 'r') as file:
                lines = file.readlines()
            
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
                with open(pat, 'w') as file:
                    file.writelines(new_lines)
                run_command("sudo systemctl restart bind9")
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
        with open('/etc/dontdelete.txt','r') as f:
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
                try:
                    
                    lold=domain.objects.get(domain=data)
                 
                    d['domain']=data
               
                    d['main']=lold
                    logs=[]
                    path='/home/'+lold.dir+"/logs/ssl.txt"
                    with open(path,'r') as f:
                         dd=f.readlines()
                         for i in dd:
                              logs.append(i)
                    d['logs']=logs
                
                    d['subdomain']=subdomainname.objects.filter(domain=data) 
                    url = 'https://voidpanel.com/clientdocs/'  # Replace with your API URL
                    response = requests.get(url)
                    if response.status_code == 200:
                        dataee = response.json()  # Parse the JSON response
                        d['docs']=dataee

                    return render(request,'control/sitessl.html',d)
                    
                except Exception as e:
                    return redirect("/")
           
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
        command = [
            "sudo", "certbot", "--nginx",
            "-d", target,
            "--non-interactive", "--agree-tos",
            "--email", f'{email}',
            "--redirect", "--no-eff-email"
        ]
    else:
        lold = domain.objects.get(domain=domain_or_subdomain)
        email = lold.email
        target = lold.domain
        command = [
            "sudo", "certbot", "--nginx",
            "-d", target, "-d", f'www.{target}',
            "--non-interactive", "--agree-tos",
            "--email", f'{email}',
            "--redirect", "--no-eff-email"
        ]

    path = f'/home/{lold.dir}/logs/ssl.txt'
    with open(path, 'a+') as f:
        f.write(f"\n[AutoSSL] Started SSL generation for {target}...")

    try:
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        with open(path, 'a+') as f:
            f.write(f"\n[AutoSSL] SUCCESS: AutoSSL Completed for {target}")
            
        if is_subdomain:
            item.sslstatus = True
            item.save()
        else:
            lold.sslstatus = True
            lold.save()
            
    except Exception as e:
        with open(path, 'a+') as f:
            f.write(f"\n[AutoSSL] ERROR: Failed for {target}")
            f.write(f"\n{str(e)}")

@csrf_exempt
@login_required(login_url='/')
def runsslfordoamin(request):
    if request.user.is_superuser:
        current = request.session['name']
    else:
        current = request.user
        
    if request.method == 'POST':
        name = request.POST.get('domain', '').lower()
        if name != user.objects.get(username=current).domain:
            return JsonResponse({'status': 'error', 'message': 'Invalid request.'})
            
        lold = domain.objects.get(domain=name)
        subdomains = subdomainname.objects.filter(domain=name).all()
        
        # Start threading for main domain
        threading.Thread(target=_background_run_ssl, args=(name, False)).start()
        
        # Start threading for subdomains
        for sub in subdomains:
            threading.Thread(target=_background_run_ssl, args=(sub.subdomain, True)).start()
            
        return JsonResponse({'status': 'success', 'message': 'SSL initiated in background'})
        
    return JsonResponse({'status': 'error', 'message': 'Invalid request.'})

@csrf_exempt
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
        with open('/etc/dontdelete.txt','r') as f:
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
                result = subprocess.run(["crontab", "-l"], capture_output=True, text=True)
                current_crons = result.stdout if result.returncode == 0 else ""
                
                new_cron = f"{time_val} {path_val}\n"
                combined = new_cron + current_crons
                
                subprocess.run(["crontab", "-"], input=combined, text=True)
                cron.objects.create(domain=data, path=path_val, duratioin=time_val)
                return JsonResponse({'success': True, 'message': 'Cronjob successfully protected & created.'})

            url = 'https://voidpanel.com/clientdocs/'
            response = requests.get(url)
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
            result = subprocess.run(["crontab", "-l"], capture_output=True, text=True)
            current_crons = result.stdout if result.returncode == 0 else ""
            
            # Subprocess memory filtering
            filtered_crons = "\n".join([line for line in current_crons.split('\n') if xxxx.path not in line]) + "\n"
            
            subprocess.run(["crontab", "-"], input=filtered_crons, text=True)
            xxxx.delete()
            return JsonResponse({'success': True, 'message': 'Cronjob deleted safely.'})
        else:
            return JsonResponse({'success': False, 'message': 'Unauthorized scope.'})
    except:
        return JsonResponse({'success': False, 'message': 'Cronjob not found.'})
        
@csrf_exempt
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
            currentstorage=get_directory_size_in_mb(f'/home/{current}')
            packagecc=safe_get_package(user.objects.get(username=current).hosting_package).storage
            if int(packagecc) != 0:
                if (int(currentstorage) > int(packagecc)):
                    return JsonResponse({'status': 'exceed', 'message': 'Storage Quota Limit Reached.'})

        namm=domain.objects.get(domain=name)
        main_directory = '/home/'+namm.dir
        front='/home/'+namm.dir
        mail="/var/mail/vhosts/"+namm.domain
        open1='/etc/opendkim/keys/'+namm.domain
        lets='/etc/letsencrypt/live/'+namm.domain
        
        import datetime
        import threading
        
        zip_filename = "backup_"+namm.domain+"_"+str(datetime.datetime.today().strftime('%Y%m%d_%H%M%S'))
        zip_filename=zip_filename.replace(" ", "_").replace(":", "-")
        locations = [front,mail,open1,lets]
        
        # Deploy non-blocking thread to handle Zipping
        t = threading.Thread(target=zip_multiple_locations_backup_user, args=(main_directory, locations, zip_filename, current))
        t.start()
        
        return JsonResponse({'status': 'success', 'message': 'Job Queued in Background!'})
        
    return JsonResponse({'status': 'error', 'message': 'Invalid request.'})


@login_required(login_url='/')
def filemanager(request):
    if request.user.is_superuser:
        current = request.session.get('name', request.user.username)
    else:
        current = request.user

    file_path = request.GET.get('key', f'/home/{current}')
    # Normalize double-slashes
    while '//' in file_path:
        file_path = file_path.replace('//', '/')
    if not file_path.startswith('/'):
        file_path = '/' + file_path

    # Security: restrict non-admins strictly to their home dir
    if not request.user.is_superuser:
        home = f'/home/{current}'
        if not file_path.startswith(home):
            return redirect(f'/control/filemanager/?key={home}')

    last = file_path.rsplit('/', 1)[0] or '/'

    if request.user.is_authenticated:
        d = {}
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
           currentstorage=get_directory_size_in_mb(f'/home/{current}')
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
           response = requests.get(url)
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
        with open('/etc/dontdelete.txt', 'r') as f:
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
        with open('/etc/dontdelete.txt', 'r') as f:
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
        with open('/etc/dontdelete.txt', 'r') as f:
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
        with open('/etc/dontdelete.txt', 'r') as f:
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
    Roundcube SSO Auto-Login.
    Decodes the stored base64 password for the given email account and
    renders an auto-submitting HTML form that logs the user directly into
    Roundcube webmail — no manual password entry required.
    """
    import base64
    import socket
    from control.models import allemail, user as ctrl_user

    # Authorization: only superuser or owner of this email's domain
    email = email.lower()
    email_obj = allemail.objects.filter(email=email).first()
    if not email_obj:
        return HttpResponse("Email account not found.", status=404)

    domain_name = email_obj.domain
    if not request.user.is_superuser:
        current = request.user.username
        owner_obj = ctrl_user.objects.filter(username=current).first()
        if not owner_obj or owner_obj.domain != domain_name:
            return HttpResponse("Unauthorized.", status=403)

    # Decode stored password
    try:
        password = base64.b64decode(email_obj.password.encode()).decode('utf-8')
    except Exception:
        return HttpResponse("Cannot decode credentials — please reset the email password first.", status=500)

    # Determine Roundcube URL (standard port 9003 or fall back to server IP)
    try:
        hostname = socket.gethostname()
        roundcube_url = f"https://{hostname}:9003"
    except Exception:
        roundcube_url = f"https://{get_server_ip()}:9003"

    # Build auto-submitting POST form (same pattern as phpMyAdmin SSO)
    html = f"""<!DOCTYPE html>
<html>
<head>
    <title>Logging in to Webmail...</title>
    <style>
        body {{ background: #0a0e1a; color: #e2e8f0; font-family: 'Inter', sans-serif;
               display: flex; align-items: center; justify-content: center; min-height: 100vh; margin: 0; }}
        .msg {{ text-align: center; }}
        .spinner {{ width: 40px; height: 40px; border: 3px solid rgba(99,102,241,0.2);
                   border-top-color: #6366f1; border-radius: 50%; animation: spin 0.8s linear infinite;
                   margin: 0 auto 20px; }}
        @keyframes spin {{ to {{ transform: rotate(360deg); }} }}
    </style>
</head>
<body>
<div class="msg">
    <div class="spinner"></div>
    <p>Redirecting to Roundcube Webmail...</p>
</div>
<form id="rclogin" action="{roundcube_url}/?_task=login" method="POST" target="_blank">
    <input type="hidden" name="_task" value="login">
    <input type="hidden" name="_action" value="login">
    <input type="hidden" name="_timezone" value="auto">
    <input type="hidden" name="_url" value="">
    <input type="hidden" name="_user" value="{email}">
    <input type="hidden" name="_pass" value="{password}">
</form>
<script>
    document.getElementById('rclogin').submit();
    // Redirect back to email list after short delay
    setTimeout(function() {{ window.location.href = '/control/listemail/{domain_name}/'; }}, 1500);
</script>
</body>
</html>"""
    return HttpResponse(html)


# ─── Analytics View (Control Portal) ────────────────────────────────────────
@login_required(login_url='/')
def analytics_control(request, data):
    if request.user.is_superuser:
        current = request.session.get('name', request.user.username)
    else:
        current = request.user.username

    if not request.user.is_authenticated:
        return redirect('/')

    # Ownership check
    if not request.user.is_superuser:
        owner = user.objects.filter(username=current).first()
        if not owner or owner.domain != data:
            return HttpResponse("Unauthorized.", status=403)

    try:
        with open('/etc/dontdelete.txt', 'r') as f:
            adminpassword = f.read().strip()
    except Exception:
        adminpassword = ''

    d = {}
    d.update(get_user_dashboard_context(current, adminpassword))
    d['domain'] = data

    # Domain object
    from control.models import domain as ctrl_domain
    dom_obj = ctrl_domain.objects.filter(domain=data).first()
    d['homedir'] = dom_obj.dir if dom_obj else data
    d['username'] = current

    # Package info
    usr_obj = user.objects.filter(username=current).first()
    pak_name = usr_obj.hosting_package if usr_obj else 'N/A'
    d['package_name'] = pak_name
    from control.models import package as ctrl_package
    pak = ctrl_package.objects.filter(name=pak_name).first()
    d['disk_quota_mb'] = pak.storage if pak else '0'

    # Disk usage
    import os
    from function import get_directory_size_in_mb, is_website_live, parse_dns_zone_file
    try:
        disk_used = get_directory_size_in_mb(f'/home/{d["homedir"]}')
    except Exception:
        disk_used = 0
    d['disk_used'] = int(disk_used)
    quota = int(d['disk_quota_mb']) if str(d['disk_quota_mb']).isdigit() else 0
    d['disk_percent'] = round((int(disk_used) / quota) * 100) if quota > 0 else 0

    # Live status
    d['live'] = is_website_live(f'http://{data}')

    # SSL
    d['ssl_active'] = os.path.exists(f'/etc/letsencrypt/live/{data}/fullchain.pem')

    # PHP
    d['php_version'] = dom_obj.php if dom_obj and hasattr(dom_obj, 'php') else 'N/A'
    d['domain_status'] = dom_obj.status if dom_obj and hasattr(dom_obj, 'status') else True

    # Email accounts
    d['emails'] = allemail.objects.filter(domain=data).all()

    # Subdomains
    d['subdomains'] = subdomainname.objects.filter(domain=data).all()

    # Python + MERN apps
    d['python_apps'] = pythonname.objects.filter(main=data).all()
    d['mern_apps'] = mernname.objects.filter(main=data).all()

    # DNS
    try:
        dns_records = parse_dns_zone_file(f'/etc/bind/db.{data}')
        d['dns_records'] = [r for r in dns_records if r.get('type') in ('A','MX','CNAME','TXT','NS','AAAA')]
        d['dns_count'] = len(d['dns_records'])
    except Exception:
        d['dns_records'] = []
        d['dns_count'] = 0

    # MySQL
    try:
        from function import get_database_names_with_filter
        db_names = get_database_names_with_filter(adminpassword, d['homedir'])
        d['db_count'] = len(db_names) if db_names else 0
    except Exception:
        d['db_count'] = 0

    return render(request, 'control/analytics.html', d)

