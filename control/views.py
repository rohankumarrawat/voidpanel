from django.http import JsonResponse
from django.shortcuts import render,redirect
import json
import requests
from django.contrib.auth.decorators import login_required
from control.models import pythonname,user,domain,subdomainname,cron,package,allemail,redir,ftpaccount,ftp,phpversion
from function import get_server_ip,is_website_live,get_database_users_with_filter,get_database_names_with_filter,parse_dns_zone_file,run_command,zip_multiple_locations_backup_user,get_directory_size_in_mb,get_file_info
from django.views.decorators.csrf import csrf_exempt
import os


# except:
#      adminpassword="adminpassword"

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

                rere=int(package.objects.get(name=usewe.hosting_package).ftp)
                cretee=len(ftpaccount.objects.filter(main=curren))
                if package.objects.get(name=usewe.hosting_package).ftp !='0':
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
    with open('/etc/dontdelete.txt','r') as f:
                                            adminpassword=f.read()
                                            adminpassword=adminpassword.strip()
   
    if data == user.objects.get(username=current).domain:
                d={}
                d['primarydomain']=user.objects.get(username=current).domain
                d['primarydomainstatus']=domain.objects.get(domain=d['primarydomain']).sslstatus
                d['ipaddress']=get_server_ip()
                d['dir']=current
                d['rohan']=ftp.objects.get(id=1)
                d['avaiablestorage']=int(package.objects.get(name=user.objects.get(username=current).hosting_package).storage)
                d['remainingstorage']=int(get_directory_size_in_mb(f'/home/{current}'))
                if d['avaiablestorage'] == 0:
                    d['storagestatus']=True
                else:
                    d['storagestatus']=False
                    
                    d['percentagestorage']=(d['remainingstorage']/d['avaiablestorage'])*100
                d['totalemail']=int(package.objects.get(name=user.objects.get(username=current).hosting_package).email_accounts)
                if d['totalemail']==0:
                    d['totalemail']='∞'
                d['usedemail']=len(allemail.objects.filter(domain=user.objects.get(username=current).domain))

                d['totalsubdomain']=int(package.objects.get(name=user.objects.get(username=current).hosting_package).subdomain)
                if d['totalsubdomain']==0:
                    d['totalsubdomain']='∞'
                d['usedsubdomain']=len(subdomainname.objects.filter(domain=user.objects.get(username=current).domain))

                d['totaldb']=int(package.objects.get(name=user.objects.get(username=current).hosting_package).databases_allowed)
                if d['totaldb']==0:
                    d['totaldb']='∞'
                mainn=str(current)+'_'
                d['useddatabase']=len(get_database_names_with_filter(adminpassword,mainn))

                d['totalftp']=int(package.objects.get(name=user.objects.get(username=current).hosting_package).ftp)
                if d['totalftp']==0:
                    d['totalftp']='∞'
                d['usedftp']=len(ftpaccount.objects.filter(main=user.objects.get(username=current)))
        
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
def dbconnect(request,data):
    with open('/etc/dontdelete.txt','r') as f:
                                            adminpassword=f.read()
                                            adminpassword=adminpassword.strip()

    if request.user.is_superuser:
        current=request.session['name']
    else:
        current=request.user
   
    if data == user.objects.get(username=current).domain:
                d={}
                d['primarydomain']=user.objects.get(username=current).domain
                d['phpversion']=phpversion.objects.all()
                d['ipaddress']=get_server_ip()
                d['dir']=current
                d['rohan']=ftp.objects.get(id=1)
                d['avaiablestorage']=int(package.objects.get(name=user.objects.get(username=current).hosting_package).storage)
                d['remainingstorage']=int(get_directory_size_in_mb(f'/home/{current}'))
                if d['avaiablestorage'] == 0:
                    d['storagestatus']=True
                else:
                    d['storagestatus']=False
                    
                    d['percentagestorage']=(d['remainingstorage']/d['avaiablestorage'])*100
                d['totalemail']=int(package.objects.get(name=user.objects.get(username=current).hosting_package).email_accounts)
                if d['totalemail']==0:
                    d['totalemail']='∞'
                d['usedemail']=len(allemail.objects.filter(domain=user.objects.get(username=current).domain))

                d['totalsubdomain']=int(package.objects.get(name=user.objects.get(username=current).hosting_package).subdomain)
                if d['totalsubdomain']==0:
                    d['totalsubdomain']='∞'
                d['usedsubdomain']=len(subdomainname.objects.filter(domain=user.objects.get(username=current).domain))

                d['totalftp']=int(package.objects.get(name=user.objects.get(username=current).hosting_package).ftp)
                if d['totalftp']==0:
                    d['totalftp']='∞'
                d['usedftp']=len(ftpaccount.objects.filter(main=user.objects.get(username=current)))

                d['totaldb']=int(package.objects.get(name=user.objects.get(username=current).hosting_package).databases_allowed)
                if d['totaldb']==0:
                    d['totaldb']='∞'
                mainn=str(current)+'_'
                d['useddatabase']=len(get_database_names_with_filter(adminpassword,mainn))
                try:
                    lold=domain.objects.get(domain=data)
                    cc=lold.dir
                    d['domain']=data
                    mainn=cc+"_"
                    d['database']=get_database_names_with_filter(adminpassword,mainn)
                    d['users']=get_database_users_with_filter(adminpassword,mainn)
                    url = 'https://voidpanel.com/clientdocs/'  # Replace with your API URL
                    response = requests.get(url)
                    if response.status_code == 200:
                        dataee = response.json()  # Parse the JSON response
                        d['docs']=dataee
                 
                    return render(request,'control/dbconnect.html',d)
                except:
                    return redirect("/listwebsite/")
           
    else: 
        return redirect('/')
    
@login_required(login_url='/')
def addredirect(request,data):
    with open('/etc/dontdelete.txt','r') as f:
                                            adminpassword=f.read()
                                            adminpassword=adminpassword.strip()
   
    if request.user.is_superuser:
        current=request.session['name']
    else:
        current=request.user
   
    if data == user.objects.get(username=current).domain:
                d={}
                d['primarydomain']=user.objects.get(username=current).domain
                d['phpversion']=phpversion.objects.all()
                d['ipaddress']=get_server_ip()
                d['dir']=current
                d['rohan']=ftp.objects.get(id=1)
                d['avaiablestorage']=int(package.objects.get(name=user.objects.get(username=current).hosting_package).storage)
                d['remainingstorage']=int(get_directory_size_in_mb(f'/home/{current}'))
                if d['avaiablestorage'] == 0:
                    d['storagestatus']=True
                else:
                    d['storagestatus']=False
                    
                    d['percentagestorage']=(d['remainingstorage']/d['avaiablestorage'])*100
                d['totalemail']=int(package.objects.get(name=user.objects.get(username=current).hosting_package).email_accounts)
                if d['totalemail']==0:
                    d['totalemail']='∞'
                d['usedemail']=len(allemail.objects.filter(domain=user.objects.get(username=current).domain))

                d['totalsubdomain']=int(package.objects.get(name=user.objects.get(username=current).hosting_package).subdomain)
                if d['totalsubdomain']==0:
                    d['totalsubdomain']='∞'
                d['usedsubdomain']=len(subdomainname.objects.filter(domain=user.objects.get(username=current).domain))

                d['totalftp']=int(package.objects.get(name=user.objects.get(username=current).hosting_package).ftp)
                if d['totalftp']==0:
                    d['totalftp']='∞'
                d['usedftp']=len(ftpaccount.objects.filter(main=user.objects.get(username=current)))
                d['totaldb']=int(package.objects.get(name=user.objects.get(username=current).hosting_package).databases_allowed)
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
    with open('/etc/dontdelete.txt','r') as f:
                                            adminpassword=f.read()
                                            adminpassword=adminpassword.strip()
   
    if request.user.is_superuser:
        current=request.session['name']
    else:
        current=request.user
   
    if data == user.objects.get(username=current).domain:
                d={}
                d['primarydomain']=user.objects.get(username=current).domain
                d['phpversion']=phpversion.objects.all()
                d['ipaddress']=get_server_ip()
                d['dir']=current
                d['rohan']=ftp.objects.get(id=1)
                d['avaiablestorage']=int(package.objects.get(name=user.objects.get(username=current).hosting_package).storage)
                d['remainingstorage']=int(get_directory_size_in_mb(f'/home/{current}'))
                if d['avaiablestorage'] == 0:
                    d['storagestatus']=True
                else:
                    d['storagestatus']=False
                    
                    d['percentagestorage']=(d['remainingstorage']/d['avaiablestorage'])*100
                d['totalemail']=int(package.objects.get(name=user.objects.get(username=current).hosting_package).email_accounts)
                if d['totalemail']==0:
                    d['totalemail']='∞'
                d['usedemail']=len(allemail.objects.filter(domain=user.objects.get(username=current).domain))

                d['totalsubdomain']=int(package.objects.get(name=user.objects.get(username=current).hosting_package).subdomain)
                if d['totalsubdomain']==0:
                    d['totalsubdomain']='∞'
                d['usedsubdomain']=len(subdomainname.objects.filter(domain=user.objects.get(username=current).domain))

                d['totalftp']=int(package.objects.get(name=user.objects.get(username=current).hosting_package).ftp)
                if d['totalftp']==0:
                    d['totalftp']='∞'
                d['usedftp']=len(ftpaccount.objects.filter(main=user.objects.get(username=current)))

                d['totaldb']=int(package.objects.get(name=user.objects.get(username=current).hosting_package).databases_allowed)
                if d['totaldb']==0:
                    d['totaldb']='∞'
                mainn=str(current)+'_'
                d['useddatabase']=len(get_database_names_with_filter(adminpassword,mainn))
                try:
                    
                    lold=domain.objects.get(domain=data)
                    d['domain']=data
                    d['data']=subdomainname.objects.filter(domain=data) 
                    weew=user.objects.get(username=current).hosting_package
                    er=package.objects.get(name=weew)
                    if er.subdomain !='0':   
                        if len(subdomainname.objects.filter(domain=data)) >= int(package.objects.get(name=user.objects.get(username=current).hosting_package).subdomain):
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
def phpini(request,data):
   
    if request.user.is_superuser:
        current=request.session['name']
    else:
        current=request.user
   
    if data == user.objects.get(username=current).domain:
                d={}
                try:
                    
                    lold=domain.objects.get(domain=data)

                    d['domain']=data
                    file_path = f'/home/{lold.dir}/public_html/php.ini'

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
                    url = 'https://voidpanel.com/clientdocs/'  # Replace with your API URL
                    response = requests.get(url)
                    if response.status_code == 200:
                        dataee = response.json()  # Parse the JSON response
                        d['docs']=dataee
                    return render(request,'control/phpini.html',d)
                except Exception as e:
                    return redirect("/listwebsite/")
           
    else: 
        return redirect('/')

    
@login_required(login_url='/')
def listemail(request,data):
    # data=data.lower()
    with open('/etc/dontdelete.txt','r') as f:
                                            adminpassword=f.read()
                                            adminpassword=adminpassword.strip()
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




               d['primarydomain']=user.objects.get(username=current).domain
               d['phpversion']=phpversion.objects.all()
               d['ipaddress']=get_server_ip()
               d['dir']=current
               d['rohan']=ftp.objects.get(id=1)
               d['avaiablestorage']=int(package.objects.get(name=user.objects.get(username=current).hosting_package).storage)
               d['remainingstorage']=int(get_directory_size_in_mb(f'/home/{current}'))
               if d['avaiablestorage'] == 0:
                    d['storagestatus']=True
               else:
                    d['storagestatus']=False
                    
                    d['percentagestorage']=(d['remainingstorage']/d['avaiablestorage'])*100
               d['totalemail']=int(package.objects.get(name=user.objects.get(username=current).hosting_package).email_accounts)
               if d['totalemail']==0:
                    d['totalemail']='∞'
               d['usedemail']=len(allemail.objects.filter(domain=user.objects.get(username=current).domain))

               d['totalsubdomain']=int(package.objects.get(name=user.objects.get(username=current).hosting_package).subdomain)
               if d['totalsubdomain']==0:
                    d['totalsubdomain']='∞'
               d['usedsubdomain']=len(subdomainname.objects.filter(domain=user.objects.get(username=current).domain))

               d['totalftp']=int(package.objects.get(name=user.objects.get(username=current).hosting_package).ftp)
               if d['totalftp']==0:
                    d['totalftp']='∞'
               d['usedftp']=len(ftpaccount.objects.filter(main=user.objects.get(username=current)))

               d['totaldb']=int(package.objects.get(name=user.objects.get(username=current).hosting_package).databases_allowed)
               if d['totaldb']==0:
                    d['totaldb']='∞'
               mainn=str(current)+'_'
               d['useddatabase']=len(get_database_names_with_filter(adminpassword,mainn))
                        







               if is_website_live(url):
                   d['ip']=url
               else:
                   d['ip']=f"https://{get_server_ip()}:9002"
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
def backup(request,data):
    with open('/etc/dontdelete.txt','r') as f:
                                            adminpassword=f.read()
                                            adminpassword=adminpassword.strip()
    import glob
    import os
    if request.user.is_superuser:
        current=request.session['name']
    else:
        current=request.user
    
    if data == user.objects.get(username=current).domain:
                
                d={}
                d['primarydomain']=user.objects.get(username=current).domain
                d['phpversion']=phpversion.objects.all()
                d['ipaddress']=get_server_ip()
                d['dir']=current
                d['rohan']=ftp.objects.get(id=1)
                d['avaiablestorage']=int(package.objects.get(name=user.objects.get(username=current).hosting_package).storage)
                d['remainingstorage']=int(get_directory_size_in_mb(f'/home/{current}'))
                if d['avaiablestorage'] == 0:
                    d['storagestatus']=True
                else:
                    d['storagestatus']=False
                    
                    d['percentagestorage']=(d['remainingstorage']/d['avaiablestorage'])*100
                d['totalemail']=int(package.objects.get(name=user.objects.get(username=current).hosting_package).email_accounts)
                if d['totalemail']==0:
                    d['totalemail']='∞'
                d['usedemail']=len(allemail.objects.filter(domain=user.objects.get(username=current).domain))
                d['totalsubdomain']=int(package.objects.get(name=user.objects.get(username=current).hosting_package).subdomain)
                if d['totalsubdomain']==0:
                    d['totalsubdomain']='∞'
                d['usedsubdomain']=len(subdomainname.objects.filter(domain=user.objects.get(username=current).domain))
                d['totalftp']=int(package.objects.get(name=user.objects.get(username=current).hosting_package).ftp)
                if d['totalftp']==0:
                    d['totalftp']='∞'
                d['usedftp']=len(ftpaccount.objects.filter(main=user.objects.get(username=current)))

                d['totaldb']=int(package.objects.get(name=user.objects.get(username=current).hosting_package).databases_allowed)
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
    

    d['primarydomain']=user.objects.get(username=current).domain
    d['domain']=d['primarydomain']
    
    try:
                        response = requests.get("http://"+d['primarydomain'], timeout=10)
                        
                        if response.status_code >= 200 and response.status_code < 400:
                            d['status']=True
    except:
                        d['status']=False
    d['sub']=subdomainname.objects.filter(domain=d['primarydomain']).all()
                
    

    
    d['primarydomainstatus']=domain.objects.get(domain=d['primarydomain']).sslstatus
    d['phpversion']=phpversion.objects.all()
    d['ipaddress']=get_server_ip()
    d['dir']=current
    d['rohan']=ftp.objects.get(id=1)
    d['avaiablestorage']=int(package.objects.get(name=user.objects.get(username=current).hosting_package).storage)
    d['remainingstorage']=int(get_directory_size_in_mb(f'/home/{current}'))
    if d['avaiablestorage'] == 0:
         d['storagestatus']=True
    else:
        d['storagestatus']=False
        
        d['percentagestorage']=(d['remainingstorage']/d['avaiablestorage'])*100
    d['totalemail']=int(package.objects.get(name=user.objects.get(username=current).hosting_package).email_accounts)
    if d['totalemail']==0:
         d['totalemail']='∞'
    d['usedemail']=len(allemail.objects.filter(domain=user.objects.get(username=current).domain))

    d['totalsubdomain']=int(package.objects.get(name=user.objects.get(username=current).hosting_package).subdomain)
    if d['totalsubdomain']==0:
         d['totalsubdomain']='∞'
    d['usedsubdomain']=len(subdomainname.objects.filter(domain=user.objects.get(username=current).domain))

    d['totalftp']=int(package.objects.get(name=user.objects.get(username=current).hosting_package).ftp)
    if d['totalftp']==0:
         d['totalftp']='∞'
    d['usedftp']=len(ftpaccount.objects.filter(main=user.objects.get(username=current)))

    d['totaldb']=int(package.objects.get(name=user.objects.get(username=current).hosting_package).databases_allowed)
    if d['totaldb']==0:
         d['totaldb']='∞'
    mainn=str(current)+'_'
    d['useddatabase']=len(get_database_names_with_filter(adminpassword,mainn))
   
    
        

         
    

    
   
    d['domain']=user.objects.get(username=current).domain
    d['mymy']=domain.objects.get(domain=user.objects.get(username=current).domain)
    url = 'https://voidpanel.com/clientdocs/'  # Replace with your API URL
    response = requests.get(url)
    if response.status_code == 200:
                        dataee = response.json()  # Parse the JSON response
                        d['docs']=dataee
    return render (request,'control/index.html',d)

@login_required(login_url='/')
def eadns(request):
           with open('/etc/dontdelete.txt','r') as f:
                                            adminpassword=f.read()
                                            adminpassword=adminpassword.strip()
           if request.user.is_superuser:
                    current=request.session['name']
           else:
                current=request.user
    
           domainname=request.GET.get('domain',None)
           if domainname:

                d={}
                d['primarydomain']=user.objects.get(username=current).domain
                d['primarydomainstatus']=domain.objects.get(domain=d['primarydomain']).sslstatus
                d['ipaddress']=get_server_ip()
                d['dir']=current
                d['rohan']=ftp.objects.get(id=1)
                d['avaiablestorage']=int(package.objects.get(name=user.objects.get(username=current).hosting_package).storage)
                d['remainingstorage']=int(get_directory_size_in_mb(f'/home/{current}'))
                if d['avaiablestorage'] == 0:
                    d['storagestatus']=True
                else:
                    d['storagestatus']=False
                    
                    d['percentagestorage']=(d['remainingstorage']/d['avaiablestorage'])*100
                d['totalemail']=int(package.objects.get(name=user.objects.get(username=current).hosting_package).email_accounts)
                if d['totalemail']==0:
                    d['totalemail']='∞'
                d['usedemail']=len(allemail.objects.filter(domain=user.objects.get(username=current).domain))

                d['totalsubdomain']=int(package.objects.get(name=user.objects.get(username=current).hosting_package).subdomain)
                if d['totalsubdomain']==0:
                    d['totalsubdomain']='∞'
                d['usedsubdomain']=len(subdomainname.objects.filter(domain=user.objects.get(username=current).domain))


                d['totaldb']=int(package.objects.get(name=user.objects.get(username=current).hosting_package).databases_allowed)
                if d['totaldb']==0:
                    d['totaldb']='∞'
                mainn=str(current)+'_'
                d['useddatabase']=len(get_database_names_with_filter(adminpassword,mainn))

                d['totalftp']=int(package.objects.get(name=user.objects.get(username=current).hosting_package).ftp)
                if d['totalftp']==0:
                    d['totalftp']='∞'
                d['usedftp']=len(ftpaccount.objects.filter(main=user.objects.get(username=current)))
                
                try:

                    current_domain=domain.objects.get(domain=domainname)
                    d['domain']=current_domain
                    pat=f"/etc/bind/db.{current_domain}"
                    data12=parse_dns_zone_file(pat)
                    d['data']=data12[2:]
                except:
                    return redirect('/')
                url = 'https://voidpanel.com/clientdocs/'  # Replace with your API URL
                response = requests.get(url)
                if response.status_code == 200:
                        dataee = response.json()  # Parse the JSON response
                        d['docs']=dataee
                return render(request,'control/eadns.html',d)
           else:
               return redirect('/')
   
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
           

           domainname=request.GET.get('domain',None)
           name = request.GET.get('name')
           domain = request.GET.get('domain')
           record_type = request.GET.get('type')
           data = request.GET.get('data')
           ttl = request.GET.get('ttl',None)
           records = []
           deleted = False
           pat=f"/etc/bind/db.{domain}"
           try:
            usewe=user.objects.get(username=request.user)
            dddd=usewe.domain
           except:
             if request.user.is_superuser:
                usewe=user.objects.get(username=request.session['name'])
                dddd=usewe.domain
           if domain ==dddd:

                with open(pat, 'r') as file:
                        lines = file.readlines()
                with open(pat, 'w') as file:
                            for line in lines:
                                print(line)
                                if name  in line and record_type  in line and data[:20]  in line and ttl in line:
                                    deleted = True
                                elif name  in line  and data[:20]  in line:
                                    deleted = True
                                else:
                                    file.write(line)

                if deleted:
                    run_command("sudo systemctl restart bind9")
                    return redirect(f"/eadns/?domain={domainname}")
                else:
                    
                            return redirect("/")
           else:
                 return redirect("/")



@login_required(login_url='/')
def runssl(request,data):
    with open('/etc/dontdelete.txt','r') as f:
                                            adminpassword=f.read()
                                            adminpassword=adminpassword.strip()

    if request.user.is_superuser:
        current=request.session['name']
    else:
        current=request.user

   
    if data == user.objects.get(username=current).domain:
           
                d={}
                d['primarydomain']=user.objects.get(username=current).domain
                d['primarydomainstatus']=domain.objects.get(domain=d['primarydomain']).sslstatus
                d['ipaddress']=get_server_ip()
                d['dir']=current
                d['rohan']=ftp.objects.get(id=1)
                d['avaiablestorage']=int(package.objects.get(name=user.objects.get(username=current).hosting_package).storage)
                d['remainingstorage']=int(get_directory_size_in_mb(f'/home/{current}'))
                if d['avaiablestorage'] == 0:
                    d['storagestatus']=True
                else:
                    d['storagestatus']=False
                    
                    d['percentagestorage']=(d['remainingstorage']/d['avaiablestorage'])*100
                d['totalemail']=int(package.objects.get(name=user.objects.get(username=current).hosting_package).email_accounts)
                if d['totalemail']==0:
                    d['totalemail']='∞'
                d['usedemail']=len(allemail.objects.filter(domain=user.objects.get(username=current).domain))

                d['totalsubdomain']=int(package.objects.get(name=user.objects.get(username=current).hosting_package).subdomain)
                if d['totalsubdomain']==0:
                    d['totalsubdomain']='∞'
                d['usedsubdomain']=len(subdomainname.objects.filter(domain=user.objects.get(username=current).domain))

                d['totaldb']=int(package.objects.get(name=user.objects.get(username=current).hosting_package).databases_allowed)
                if d['totaldb']==0:
                    d['totaldb']='∞'
                mainn=str(current)+'_'
                d['useddatabase']=len(get_database_names_with_filter(adminpassword,mainn))

                d['totalftp']=int(package.objects.get(name=user.objects.get(username=current).hosting_package).ftp)
                if d['totalftp']==0:
                    d['totalftp']='∞'
                d['usedftp']=len(ftpaccount.objects.filter(main=user.objects.get(username=current)))
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
    




@csrf_exempt
@login_required(login_url='/')
def runsslfordoamin(request):
    
    import subprocess
    if request.user.is_superuser:
        current=request.session['name']
    else:
        current=request.user
    if request.method == 'POST':
                        name=request.POST['domain']
                        print("test")
                        name=name.lower()
                        if name != user.objects.get(username=current).domain:
                             return JsonResponse({'status': 'error', 'message': 'Invalid request.'})
                             
                        
                        lold=domain.objects.get(domain=name)
                        
                        command = [
    "sudo", "certbot", "--nginx",
    "-d", name, "-d", f'www.{name}',    # Domains
    "--non-interactive",                    # No interaction
    "--agree-tos",                          # Automatically agree to terms of service
    "--email", f'{lold.email}',    # Provide email for notifications
    "--redirect",                           # Automatically redirect HTTP to HTTPS
    "--no-eff-email"                        # Disable the EFF email subscription prompt
]
                        
                        subdomain2=subdomainname.objects.filter(domain=name).all()
                  
                        path='/home/'+lold.dir+"/logs/ssl.txt"
                        try:
                            result = subprocess.run(command, capture_output=True, text=True, check=True)
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
                           
                            command = [
    "sudo", "certbot", "--nginx",
    "-d",  i.subdomain,   # Domains
    "--non-interactive",                    # No interaction
    "--agree-tos",                          # Automatically agree to terms of service
    "--email", f'{i.name}@example.com',    # Provide email for notifications
    "--redirect",                           # Automatically redirect HTTP to HTTPS
    "--no-eff-email"                        # Disable the EFF email subscription prompt
]
                            print(command)
                            try:
                                result = subprocess.run(command, capture_output=True, text=True, check=True)
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

@csrf_exempt
@login_required(login_url='/')
def runsslfordoamin1(request):
    import subprocess
    lol=None
    if request.user.is_superuser:
        current=request.session['name']
    else:
        current=request.user
 
    
    if request.method == 'POST':
                        data = json.loads(request.body)
                        name=data.get('name').strip(' ')
                 
                        try:
                            lold=domain.objects.get(domain=name)
                        
                            

                            command = [
    "sudo", "certbot", "--nginx",
    "-d",  lold.domain, "-d", f'www.{lold.domain}',    # Domains
    "--non-interactive",                    # No interaction
    "--agree-tos",                          # Automatically agree to terms of service
    "--email", f'{lold.email}',    # Provide email for notifications
    "--redirect",                           # Automatically redirect HTTP to HTTPS
    "--no-eff-email"                        # Disable the EFF email subscription prompt
]
                           
                        except:
                             lold1=subdomainname.objects.get(subdomain=name)
                             lold=domain.objects.get(domain=lold1.domain)
                

                             path='/home/'+lold.dir+"/logs/ssl.txt"
                             with open(path,'a+') as f:
                                f.write(f"\nfetched Subdomain {name}")
                             
                             with open(path,'a+') as f:
                                f.write(f"\nPerforming SSl for {name}")
                             command = [
    "sudo", "certbot", "--nginx",
    "-d", lold1.subdomain,
    "--non-interactive",  # No interaction
    "--agree-tos",  # Automatically agree to terms of service
    "--email", f'{lold.email}',  # Provide email for notifications
    "--redirect",  # Automatically redirect HTTP to HTTPS
    "--no-eff-email"  # Disable the EFF email subscription prompt
]

                            
                    
                        path='/home/'+lold.dir+"/logs/ssl.txt"
                      
                        try:
                            result = subprocess.run(command, capture_output=True, text=True, check=True)
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
def cronn(request,data):
    with open('/etc/dontdelete.txt','r') as f:
                                            adminpassword=f.read()
                                            adminpassword=adminpassword.strip()
    if request.user.is_superuser:
        current=request.session['name']
    else:
        current=request.user
   
    if data == user.objects.get(username=current).domain:
                d={}
                d['primarydomain']=user.objects.get(username=current).domain
                d['primarydomainstatus']=domain.objects.get(domain=d['primarydomain']).sslstatus
                d['ipaddress']=get_server_ip()
                d['dir']=current
                d['rohan']=ftp.objects.get(id=1)
                d['avaiablestorage']=int(package.objects.get(name=user.objects.get(username=current).hosting_package).storage)
                d['remainingstorage']=int(get_directory_size_in_mb(f'/home/{current}'))
                if d['avaiablestorage'] == 0:
                    d['storagestatus']=True
                else:
                    d['storagestatus']=False
                    
                    d['percentagestorage']=(d['remainingstorage']/d['avaiablestorage'])*100
                d['totalemail']=int(package.objects.get(name=user.objects.get(username=current).hosting_package).email_accounts)
                if d['totalemail']==0:
                    d['totalemail']='∞'
                d['usedemail']=len(allemail.objects.filter(domain=user.objects.get(username=current).domain))

                d['totalsubdomain']=int(package.objects.get(name=user.objects.get(username=current).hosting_package).subdomain)
                if d['totalsubdomain']==0:
                    d['totalsubdomain']='∞'
                d['usedsubdomain']=len(subdomainname.objects.filter(domain=user.objects.get(username=current).domain))

                d['totaldb']=int(package.objects.get(name=user.objects.get(username=current).hosting_package).databases_allowed)
                if d['totaldb']==0:
                    d['totaldb']='∞'
                mainn=str(current)+'_'
                d['useddatabase']=len(get_database_names_with_filter(adminpassword,mainn))

                d['totalftp']=int(package.objects.get(name=user.objects.get(username=current).hosting_package).ftp)
                if d['totalftp']==0:
                    d['totalftp']='∞'
                d['usedftp']=len(ftpaccount.objects.filter(main=user.objects.get(username=current)))
                try:
                    lold=domain.objects.get(domain=data)
                    d['crondata']=cron.objects.filter(domain=data).all()
                    if request.method =="POST":
                        time=request.POST['time']
                        path=request.POST['path']
          
                        run_command(f'(echo "{time} {path}" ; crontab -l) | crontab -')
                        ccc=cron.objects.create(domain=data,path=path,duratioin=time)
                    url = 'https://voidpanel.com/clientdocs/'  # Replace with your API URL
                    response = requests.get(url)
                    if response.status_code == 200:
                        dataee = response.json()  # Parse the JSON response
                        d['docs']=dataee
                    return render(request,'control/cron.html',d)
                except:
                    return redirect("/")
           
    else: 
        return redirect('/')
    

@login_required(login_url='/')
def deletecron(request,data):
        xxxx=cron.objects.get(id=data)
        domainname=xxxx.domain
        if request.user.is_superuser:
         current=request.session['name']
        else:
         current=request.user
        if domainname == user.objects.get(username=current).domain:
            run_command(f"crontab -l | grep -v '{xxxx.path}' | crontab -")
            xxxx.delete()
            return redirect(f'control/cron/{domainname}')
        else:
             return redirect(f'control/cron/{domainname}')
        
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
                          
                            
                            currentstorage=get_directory_size_in_mb(f'/home/{current}')

                            packagecc=package.objects.get(name=user.objects.get(username=current).hosting_package).storage

                            if int(packagecc) != 0:

                                if (int(currentstorage) > int(packagecc)):
                                    return JsonResponse({'status': 'exceed', 'message': 'Invalid request.'})
                            namm=domain.objects.get(domain=name)
                            main_directory = '/home/'+namm.dir
                            front='/home/'+namm.dir
                            mail="/var/mail/vhosts/"+namm.domain
                            open1='/etc/opendkim/keys/'+namm.domain
                            lets='/etc/letsencrypt/live/'+namm.domain
                            import datetime
                            zip_filename = "backup_"+namm.domain+"_"+str(datetime.datetime.today())
                            zip_filename=zip_filename.replace(" ", "_")
                            locations = [front,mail,open1,lets]
                            zip_multiple_locations_backup_user(main_directory, locations, zip_filename,current)
                            return JsonResponse({'status': 'success', 'message': 'Already Exist'})
    return JsonResponse({'status': 'error', 'message': 'Invalid request.'})


@login_required(login_url='/')
def filemanager(request):
    if request.user.is_superuser:
        current=request.session['name']
    else:
        current=request.user
    # nn=user.objects.get(username=current)
    file_path=request.GET.get('key', f'//home/{current}')
    last = file_path.rsplit('/', 1)[0]
  
    if not file_path.startswith(f'//home/{current}'):
         return redirect (f'/control/filemanager/?key=//home/{current}')
    if request.user.is_authenticated: 
           d={}
      
           d['main_dir']=file_path
           d['last']=last
        #    items = os.listdir(main_dir)
         
           result = get_file_info(file_path)
           d['items']=result['directories']
           d['files']=result['files']
           d['current']=current
           url = 'https://voidpanel.com/clientdocs/'  # Replace with your API URL
           response = requests.get(url)
           if response.status_code == 200:
                        dataee = response.json()  # Parse the JSON response
                        d['docs']=dataee
           return render(request,'control/filemanager.html',d)
    else: 
        return redirect('/')
    





@login_required(login_url='/')
def upload_files(request,file_path):
           if request.user.is_superuser:
                current=request.session['name']
           else:
                current=request.user
   

           d={}
           packagecc=package.objects.get(name=user.objects.get(username=current).hosting_package).storage
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
        
        if request.user.is_superuser:
                    current=request.session['name']
        else:
                    current=request.user
        
        d={}

    
        
        d['ip']=get_server_ip()
        d['os']=platform.system()
        d['cpu']=platform.processor()
        d['hostname']=socket.gethostbyname(socket.gethostname())
        url = 'https://voidpanel.com/admindocs/'  # Replace with your API URL
        response = requests.get(url)
        if response.status_code == 200:
            dataee = response.json()  # Parse the JSON response
            d['docs']=dataee
        
        return render(request,'control/domainterminal.html',d)

    

import pexpect
persistent_shell = pexpect.spawn('/bin/bash', encoding='utf-8')
persistent_shell.expect(r'[#$]') 
datahold=""
@csrf_exempt  
def terminalname(request):
    global datahold
    
    if request.user.is_superuser:
                    current=request.session['name']
    else:
                    current=request.user
    homedir='/home/'+current+datahold
    if request.method == 'POST':
        
        command = request.POST.get('command').lower()
        # if '&&' in command:
        #       return JsonResponse({"output": 'Don"t Use && command here'})
        if command.startswith('cd'):
              command=command.replace('cd','').strip()
            #   if not command.startswith(f'/home/{current}'):
              if f"/home/{current}" not in  command:
                    if command[0]!='/':
                          command="/"+command
                    datahold=command
                    command=homedir+command
                    homedir=command
                    command="cd "+command
        command = 'sudo -u ' + current + ' bash -c "cd '+homedir  + ' && ' + command + '"'
        try:
                # Send command to the persistent shell
                persistent_shell.sendline(command)
                # Wait for the next prompt to capture all output
                persistent_shell.expect(r'[#$]') 
                output = persistent_shell.before.strip()

                output=output.replace("/var/www/panel","")
                output=(output.splitlines())
                output[0]="#"+homedir

                output = "\n".join(output).strip()
        except Exception as e:
                output = f"Error: {str(e)}"
        return JsonResponse({"output":output})
    return JsonResponse({"output": "Invalid request"})


@login_required(login_url='/')
def setpython(request,data):

    if request.user.is_superuser:
                    current=request.session['name']
    else:
                    current=request.user
   
    if request.user.is_authenticated:
                try:
                    with open('/etc/dontdelete.txt','r') as f:
                                            adminpassword=f.read()
                                            adminpassword=adminpassword.strip()
                except:
                      adminpassword=""
                d={}
                d['primarydomain']=user.objects.get(username=current).domain
                d['primarydomainstatus']=domain.objects.get(domain=d['primarydomain']).sslstatus
                d['ipaddress']=get_server_ip()
                d['dir']=current
                d['rohan']=ftp.objects.get(id=1)
                d['avaiablestorage']=int(package.objects.get(name=user.objects.get(username=current).hosting_package).storage)
                d['remainingstorage']=int(get_directory_size_in_mb(f'/home/{current}'))
                if d['avaiablestorage'] == 0:
                    d['storagestatus']=True
                else:
                    d['storagestatus']=False
                    
                    d['percentagestorage']=(d['remainingstorage']/d['avaiablestorage'])*100
                d['totalemail']=int(package.objects.get(name=user.objects.get(username=current).hosting_package).email_accounts)
                if d['totalemail']==0:
                    d['totalemail']='∞'
                d['usedemail']=len(allemail.objects.filter(domain=user.objects.get(username=current).domain))

                d['totalsubdomain']=int(package.objects.get(name=user.objects.get(username=current).hosting_package).subdomain)
                if d['totalsubdomain']==0:
                    d['totalsubdomain']='∞'
                d['usedsubdomain']=len(subdomainname.objects.filter(domain=user.objects.get(username=current).domain))

                d['totaldb']=int(package.objects.get(name=user.objects.get(username=current).hosting_package).databases_allowed)
                if d['totaldb']==0:
                    d['totaldb']='∞'
                mainn=str(current)+'_'
                d['useddatabase']=len(get_database_names_with_filter(adminpassword,mainn))

                d['totalftp']=int(package.objects.get(name=user.objects.get(username=current).hosting_package).ftp)
                if d['totalftp']==0:
                    d['totalftp']='∞'
                d['usedftp']=len(ftpaccount.objects.filter(main=user.objects.get(username=current)))
                try:
                    
                    lold=domain.objects.get(domain=data)
                    d['domain']=data
                    d['python']=pythonname.objects.filter(main=lold.dir).all()     
                    url = 'https://voidpanel.com/admindocs/'  # Replace with your API URL
                    response = requests.get(url)
                    if response.status_code == 200:
                        dataee = response.json()  # Parse the JSON response
                        d['docs']=dataee
                    return render(request,'control/setpython.html',d)
                except Exception as e:
                    return redirect("/listwebsite/")
           
    else: 
        return redirect('/')


@login_required(login_url='/')
def createpython(request,data):
    if request.user.is_superuser:
                    current=request.session['name']
    else:
                    current=request.user
   
    if request.user.is_authenticated:
                try:
                    with open('/etc/dontdelete.txt','r') as f:
                                            adminpassword=f.read()
                                            adminpassword=adminpassword.strip()
                except:
                      adminpassword=""
                d={}
                d['primarydomain']=user.objects.get(username=current).domain
                d['primarydomainstatus']=domain.objects.get(domain=d['primarydomain']).sslstatus
                d['ipaddress']=get_server_ip()
                d['dir']=current
                d['rohan']=ftp.objects.get(id=1)
                d['avaiablestorage']=int(package.objects.get(name=user.objects.get(username=current).hosting_package).storage)
                d['remainingstorage']=int(get_directory_size_in_mb(f'/home/{current}'))
                if d['avaiablestorage'] == 0:
                    d['storagestatus']=True
                else:
                    d['storagestatus']=False
                    
                    d['percentagestorage']=(d['remainingstorage']/d['avaiablestorage'])*100
                d['totalemail']=int(package.objects.get(name=user.objects.get(username=current).hosting_package).email_accounts)
                if d['totalemail']==0:
                    d['totalemail']='∞'
                d['usedemail']=len(allemail.objects.filter(domain=user.objects.get(username=current).domain))

                d['totalsubdomain']=int(package.objects.get(name=user.objects.get(username=current).hosting_package).subdomain)
                if d['totalsubdomain']==0:
                    d['totalsubdomain']='∞'
                d['usedsubdomain']=len(subdomainname.objects.filter(domain=user.objects.get(username=current).domain))

                d['totaldb']=int(package.objects.get(name=user.objects.get(username=current).hosting_package).databases_allowed)
                if d['totaldb']==0:
                    d['totaldb']='∞'
                mainn=str(current)+'_'
                d['useddatabase']=len(get_database_names_with_filter(adminpassword,mainn))

                d['totalftp']=int(package.objects.get(name=user.objects.get(username=current).hosting_package).ftp)
                if d['totalftp']==0:
                    d['totalftp']='∞'
                d['usedftp']=len(ftpaccount.objects.filter(main=user.objects.get(username=current)))
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
                    return render(request,'control/createpython.html',d)
                except Exception as e:
                    return redirect("/listwebsite/")
           
    else: 
        return redirect('/')
        
