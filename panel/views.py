import json
from django.views.decorators.cache import never_cache
from django.shortcuts import render,redirect
from django.contrib.auth import authenticate
import requests
from django.contrib.auth import login,logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from control.models import mernname,portnumber,quick,domain,allemail,phpextentions,cron,subdomainname,phpversion,redir,package,firewall,ftp,user,ftpaccount,pythonname
from django.views.decorators.csrf import csrf_exempt
from function import start_service,stop_service,get_directory_size_in_mb,restart_service,get_service_status,get_php_versions,get_php_version,get_php_extensions,get_database_names,get_database_users,change_hostname,remove_zone_from_file,zip_multiple_locations_backup,create_bind_recordsforsubdomain,grant_mysql_user_privileges,change_mysql_user_password,delete_mysql_user,remove_database,get_database_names_with_filter,get_database_users_with_filter,create_mysql_user,is_website_live,parse_dns_zone_file,configure_opendkim,create_bind_records,generate_dkim_keys,create_nginx_ssl_conf,generate_ssl_certificates,hostnamessl,run_command,get_server_ip,get_random_port,get_file_info,zip_files_and_folders,extract_zip_with_error_handling,create_database_and_table
import psutil
import os
from django.http import FileResponse, Http404
from django.contrib.auth.models import User

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
        with open('/var/www/panel/api.txt','r') as f:
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

    import random
    random_code = ''.join(str(random.randint(0, 9)) for _ in range(12))
    
    if not username or not password:
        return Response({'status': 'error', 'message': 'Username and password are required'}, status=400)

    user = authenticate(username=username, password=password)
    
    if user:
        try:
             with open('/var/www/panel/api.txt','r') as f:
                  random_code=f.read()
                  
        except:
             import random
             random_code = ''.join(str(random.randint(0, 9)) for _ in range(12)) 
             with open('/var/www/panel/api.txt','w') as f:
                  f.write(random_code)
      
        return Response({'status': 'success', 'session_token': random_code})
    
    return Response({'status': 'error', 'message': 'Invalid credentials'}, status=403)

def background_create_account(username, password, domain, package):
    try:
        # Call your account creation logic
        addusermainapi(username, password, domain, package)
        # Optionally, log success here or take further action
    except Exception as e:
        # Log the error or handle it as needed
        pass


import threading
@api_view(['POST'])
def create_account(request):
    """Create a hosting account."""

    session_token = request.data.get('session_token')


    try:
        with open('/var/www/panel/api.txt','r') as f:
                    random_code=f.read()
    except:
         return Response({'status': 'error', 'message': 'All fields are required'}, status=400)
    if random_code != session_token:
        return Response({'status': 'error', 'message': 'Invalid session token'}, status=403)
    domain=request.data.get("domain"),
    username=request.data.get("username")
    password=request.data.get("password")
    package=request.data.get("package")

    if not all([domain, username, password, package]):
        return Response({'status': 'error', 'message': 'All fields are required'}, status=400)
    thread = threading.Thread(
        target=background_create_account,
        args=(username, password, domain, package)
    )
    thread.start()
    
    # Immediately return a response to the client
    return Response(
        {'status': 'success', 'message': 'Account created Successfull'} )


@api_view(['POST'])
def suspend_account(request):
    """Suspend a hosting account."""
    session_token = request.data.get('session_token')
    # if not CustomUser.objects.filter(api_token=session_token).exists():
    if 10>1:
        return Response({'status': 'error', 'message': 'Invalid session token'}, status=403)

    username = request.data.get('username')
    if not username:
        return Response({'status': 'error', 'message': 'Username is required'}, status=400)
    


@api_view(['POST'])
def unsuspend_account(request):
    """Unsuspend a hosting account."""
    session_token = request.data.get('session_token')
    # if not CustomUser.objects.filter(api_token=session_token).exists():
    if 10>20:
        return Response({'status': 'error', 'message': 'Invalid session token'}, status=403)

    username = request.data.get('username')
    if not username:
        return Response({'status': 'error', 'message': 'Username is required'}, status=400)
    
 
     
 
  




@api_view(['POST'])
def terminate_account(request):
    """Terminate a hosting account."""
    session_token = request.data.get('session_token')
    # if not CustomUser.objects.filter(api_token=session_token).exists():
    if 10>2:
        return Response({'status': 'error', 'message': 'Invalid session token'}, status=403)

    username = request.data.get('username')
    if not username:
        return Response({'status': 'error', 'message': 'Username is required'}, status=400)
    








def get_server_load(request):
    # Get CPU load
    cpu_load = psutil.cpu_percent(interval=1)
    
    # Get RAM usage
    memory_info = psutil.virtual_memory()
    memory_load = memory_info.percent
    
    # Get Disk usage
    disk_usage = psutil.disk_usage('/')
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
        show=False
        d={}
        try:
            quick_=quick.objects.get(id=1)
            if quick_.show == False:
                show=False
        except:
            show=True
        
        d['show']=show
        url = 'https://voidpanel.com/latest_messages/'  # Replace with your API URL
        response = requests.get(url)
        if response.status_code == 200:
            dataee = response.json()  # Parse the JSON response
            d['message']=dataee
        else:
            dataee = []  # Handle the case where the request fails
        
        url = 'https://voidpanel.com/admindocs/'  # Replace with your API URL
        response = requests.get(url)
        if response.status_code == 200:
            dataee = response.json()  # Parse the JSON response
            d['docs']=dataee

        d['serverip']=get_server_ip()

        
        return render(request,'panel/index.html',d)
    else: 
        return redirect('/')
    

from django.http import JsonResponse



def checkstatus(request):
    import requests
    if request.method == 'GET':

        url=request.GET['url']
        response = requests.get(url)
        if response.status_code == 200:
            return JsonResponse({'status': 'success'})
        else:
            return JsonResponse({'status': 'error'}, status=400)

    return JsonResponse({'status': 'error'}, status=400)

@login_required(login_url='/')
def activeterminal(request):
    
    if request.user.is_superuser:
        if request.method == 'GET':
             
                port=get_random_port({8080,8082,8090,8092,9000,9002})
                run_command(f'''sudo bash -c "cat > /etc/default/shellinabox <<EOL
SHELLINABOX_DAEMON_START=1
SHELLINABOX_PORT={port}
SHELLINABOX_ARGS=\'--disable-ssl --no-beep --service=/:root:root:/home/:/bin/bash\'
EOL"''') 
                run_command("sudo systemctl start shellinabox")
                run_command("sudo systemctl stop csf")
               
                

                


                
                return JsonResponse({'status': 'success'})
        return JsonResponse({'status': 'error'}, status=400)


def handle_user_event(request):

    if request.method == 'GET':

        action=request.GET['action']
        port=request.GET['port']
        if action == 'user_inactive':
            run_command('sudo systemctl stop shellinabox')
            run_command("sudo systemctl start csf")
            # run_command(f'''sudo sed -i '/^TCP_OUT/s/,{port}//g' /etc/csf/csf.conf''')
            # run_command(f'''sudo sed -i '/^TCP_IN/s/,{port}//g' /etc/csf/csf.conf''')
            # run_command(f'''sudo csf -d {get_server_ip()} {port}''')
      
            # run_command('sudo csf -r')
            
           
        elif action == 'tab_close':
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
    
    if request.user.is_superuser:
        
        d={}
        if request.is_secure():
             d['securehai']=True
        
        port=get_random_port({8080,8082,8090,8092,9000,9002})
        run_command(f'''sudo bash -c "cat > /etc/default/shellinabox <<EOL
SHELLINABOX_DAEMON_START=1
SHELLINABOX_PORT={port}
SHELLINABOX_ARGS=\'--disable-ssl --no-beep --service=/:root:root:/home/:/bin/bash\'
EOL"''') 
      
        try:

            run_command("sudo systemctl start shellinabox")
            run_command("sudo systemctl stop csf")
           
            # run_command(f"sudo csf -a {port}")
        except:
            pass
        d['port']=port
        storage_info = psutil.disk_usage('/')
        d['storage']=str(storage_info.total // (1024 ** 3)) +"GB"
        d['ip']=get_server_ip()
        d['os']=platform.system()
        d['cpu']=platform.processor()
        d['hostname']=socket.gethostbyname(socket.gethostname())
        d['ram']=str(round(psutil.virtual_memory().total / (1024.0 **3)))+" GB"
        url = 'https://voidpanel.com/admindocs/'  # Replace with your API URL
        response = requests.get(url)
        if response.status_code == 200:
            dataee = response.json()  # Parse the JSON response
            d['docs']=dataee
        
        return render(request,'panel/terminal.html',d)
    else: 
        return redirect('/')
    

@csrf_exempt  # Disable CSRF protection for simplicity, not recommended for production
def quicksetup(request):
    if request.method == 'POST':
         
        
       try:
           data=quick.objects.get(id=1)
           data.show=True
           data.save()
        
       
       except:
         
           data=quick.objects.create(show=True)
       
    
    return JsonResponse({'update': 'update'}, status=200)

    


@csrf_exempt  # Disable CSRF protection for simplicity, not recommended for production
def updatesetup(request):
    if request.method == 'POST':
      hostname=request.POST.get('hostname',"None")
      ns1=request.POST.get('ns1',"None")
      ns2=request.POST.get('ns2',"None")
      email=request.POST.get('email',"None")
      email=email.lower()
      try:
           data=quick.objects.get(id=1)
           data.show=False
           data.hostname=hostname
           data.nameserver1=ns1
           data.nameserver2=ns2
           data.email=email
           data.status=True
           hostnamessl(hostname,email,data.count)
           change_hostname(hostname)
           
           data.count=1
           data.save()
           run_command('sudo systemctl restart uwsgi')
           import time
           time.sleep(2)
        
      except:
         
           data=quick.objects.create(show=False,hostname=hostname,nameserver1=ns1,nameserver2=ns2,email=email,status=True)
           hostnamessl(hostname,email,data.count)
           change_hostname(hostname)

           data.count=1
           data.save()
           run_command('sudo systemctl restart uwsgi')
           import time
           time.sleep(2)
    return JsonResponse({'update': 'update'}, status=200)
    
@login_required(login_url='/')
def filemanager(request):
    import os
    file_path=request.GET.get('key', '/')
    last = file_path.rsplit('/', 1)[0]

    if request.user.is_superuser :
           try:
                current=request.session['name']
           except:
                current=request.user
           
         
               
           d={}
           d['main_dir']=file_path
           d['last']=last
        #    items = os.listdir(main_dir)
         
           result = get_file_info(file_path)
           d['items']=result['directories']
           d['files']=result['files']

          
           return render(request,'panel/filemanager.html',d)
    else: 
        return redirect('/')
    

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
 file_path=request.GET.get('key', '/')
 file_path=file_path.replace("//","/")
 if request.user.is_superuser or request.user.is_authenticated:
    if not os.path.isfile(file_path):
        raise Http404("File does not exist")

    # Open the file and create a FileResponse
    response = FileResponse(open(file_path, 'rb'))
  
    
    # Set the content type (optional, can be determined dynamically)
    response['Content-Type'] = 'application/octet-stream'
    
    # Set the content disposition to force download
    response['Content-Disposition'] = f'attachment; filename="{os.path.basename(file_path)}"'
    
    return response
 

@login_required(login_url='/')

def delete_file(request, file_path):
  import shutil

  if request.user.is_superuser or request.user.is_authenticated:
    
    if request.method == 'POST':
      
        
        
      
        try:
            os.remove(f'/{file_path}')
            return JsonResponse({'status':'success'})

        except Exception as e:
            #return JsonResponse({'error':'error'})
            pass
        try:
            os.rmdir(f'/{file_path}')
            return JsonResponse({'status':'success'})

        except Exception as e:
            pass
        try:
            shutil.rmtree(f'/{file_path}')
            return JsonResponse({'status':'success'})

        except Exception as e:
            return JsonResponse({'error':'error'})
        
  return JsonResponse({'error':'error'})

 
   
@login_required(login_url='/')
def editor_view(request,file_path):

    if request.user.is_superuser or request.user.is_authenticated:
        data={}
        extensions = {
        'python': ['.py'],
        'javascript': ['.js'],
        'java': ['.java'],
        'c++': ['.cpp', '.h'],
        'ruby': ['.rb'],
        'php': ['.php'],
        'swift': ['.swift'],
        'go': ['.go'],
        'kotlin': ['.kt', '.kts'],
        'typescript': ['.ts'],
        'r': ['.r', '.R'],
        'matlab': ['.m'],
        'scala': ['.scala'],
        'perl': ['.pl', '.pm'],
        'haskell': ['.hs'],
        'rust': ['.rs'],
        'dart': ['.dart'],
        'shell': ['.sh', '.bash'],
        'sql': ['.sql'],
        'html': ['.html', '.htm'],
        'css': ['.css'],
        'json': ['.json'],
        'yawl': ['.yaml', '.yml'],
        'xml': ['.xml'],
        'makrdown': ['.md'],
        'groovy': ['.groovy'],
        'rowershell': ['.ps1'],
        'tcl': ['.tcl'],
        'awk': ['.awk'],
        'rpg': ['.rpg'],
        'fortran': ['.f90', '.for'],
        # Add more languages and their extensions here
    }

     
        for language, exts in extensions.items():
         if file_path.endswith(tuple(exts)):
            data['language']=language
            break
        else:
             data['language']='unknown'

        try:
            
            f=open(f'/{file_path}')
            data1=f.read()
            data['data']=data1
            data['csrf_token']=request.META.get('CSRF_COOKIE', '')
            if not request.user.is_superuser:
                 if str(request.user) not in file_path:
                       return render(request, 'panel/500notfound.html')
                      
            return render(request, 'panel/editor.html',data)
        except :
            return render(request, 'panel/500notfound.html')
    else:
        return redirect("/")
    
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

        except Exception as e:
              return JsonResponse({'status': 'error', 'message': f'Error saving file: {str(e)}'})
    

@login_required(login_url='/')
def upload_file(request):

    if request.method == 'POST' and request.FILES.get('file'):
        uploaded_file = request.FILES['file']
        
     
        if not uploaded_file:
            uploaded_file="/"
        file_name = uploaded_file.name
        file_path = '/'+os.path.join(request.POST['file_path'], file_name)
        import time
       
        try: 
            with open(file_path, 'wb+') as destination:
                for chunk in uploaded_file.chunks():
                    destination.write(chunk)

            
            try:
                if request.user.iis_superuser():
                     run_command(f'sudo chown www-data:www-data {file_path}')
                else:
                    run_command(f'sudo chown {request.user}:www-data {file_path}')
            except:
                pass
            

        
                return JsonResponse({'status': 'success', 'message': 'File uploaded successfully!'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': e}, status=400)
    
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
   
    if request.user.is_superuser:
           d={}
          
           file_path=file_path.replace('////','')
           file_path=file_path.replace('//','')
           d['location']=file_path
           new="/"+file_path
           dataw = os.listdir(new)
           d['data']=dataw
           url = 'https://voidpanel.com/admindocs/'  # Replace with your API URL
           response = requests.get(url)
           if response.status_code == 200:
            dataee = response.json()  # Parse the JSON response
            d['docs']=dataee
           return render(request,'panel/upload.html',d)
    else: 
        return redirect('/')
    

@login_required(login_url='/')
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
                # os.system(f'touch {full_path}')
                with open(full_path, 'w') as file:
                    file.write('This is a new file.\n')
                try:
                    run_command(f"chown www-data:www-data {full_path}")
                except:
                     pass
                return JsonResponse({'status': 'success', 'message': 'File Create successfully!'})
               except Exception as e:
                   print(e)
                   return JsonResponse({'status': 'error', 'message': 'File Create Failed!'})
         return JsonResponse({'status': 'error', 'message': 'File Create Failed!'})
     elif request.user.is_authenticated: 
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
                # os.system(f'touch {full_path}')
                with open(full_path, 'w') as file:
                    file.write('This is a new file.\n')
                
                run_command(f'sudo chown {request.user}:{request.user} {full_path}')
                try:
                    run_command(f"chown {request.user}:www-data {full_path}")
                except:
                     pass
                return JsonResponse({'status': 'success', 'message': 'File Create successfully!'})
               except Exception as e:
                   print(e)
                   return JsonResponse({'status': 'error', 'message': 'File Create Failed!'})
          return JsonResponse({'status': 'error', 'message': 'File Create Failed!'})
          


@login_required(login_url='/')
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
                    run_command(f"chown www-data:www-data {full_path}")
                except:
                     pass
                return JsonResponse({'status': 'success', 'message': 'File uploaded successfully!'})
               except Exception as e:
                   print(e)
                   return JsonResponse({'status': 'error', 'message': 'File upload Failed!'})
         return JsonResponse({'status': 'error', 'message': 'File upload Failed!'})
     elif request.user.is_authenticated: 
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
                            
                                  
            
                                  run_command(f"chown {request.user}:www-data {full_path}")
             
                except:
                             pass
                run_command(f'sudo chown {request.user}:{request.user} {full_path}')
                return JsonResponse({'status': 'success', 'message': 'File uploaded successfully!'})
               except Exception as e:
                   print(e)
                   return JsonResponse({'status': 'error', 'message': 'File upload Failed!'})
          return JsonResponse({'status': 'error', 'message': 'File upload Failed!'})


@login_required(login_url='/')
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
                                  run_command(f"chown www-data:www-data {copy}")
                                  run_command(f"chown www-data:www-data {copy}/{i}")
                                  
                             else:
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
               packagecc=package.objects.get(name=user.objects.get(username=request.user).hosting_package).storage
               currentstorage=get_directory_size_in_mb(f'/home/{request.user}')
         
               if int(packagecc) != 0:

                if (int(currentstorage) > int(packagecc)):
                     return JsonResponse({'status': 'Overload', 'message': 'File Extracted successfully!'})
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
               if not copy.startswith(f'/home/{request.user}'):
                    copy=f'/home/{request.user}'+copy
               if  not os.path.isdir(copy):
                   return JsonResponse({'status': 'invalid', 'message': "Invalid Location"})
                   
               
               
               for i in selected_items:
                    try:
                        shutil.copytree(file_path+"/"+i,copy+i)
                        c=c+1
                        try:
                             if request.user.is_superuser():
                                  run_command(f"chown www-data:www-data {copy}")
                                  run_command(f"chown www-data:www-data {copy}/{i}")
                                  
                             else:
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
                                  run_command(f"chown www-data:www-data {copy}")
                                  run_command(f"chown www-data:www-data {copy}/{i}")
                                  
                             else:
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
                                  run_command(f"chown www-data:www-data {copy}")
                                  run_command(f"chown www-data:www-data {copy}/{i}")
                                  
                             else:
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
               packagecc=package.objects.get(name=user.objects.get(username=request.user).hosting_package).storage
               currentstorage=get_directory_size_in_mb(f'/home/{request.user}')
         
               if int(packagecc) != 0:

                if (int(currentstorage) > int(packagecc)):
                     return JsonResponse({'status': 'Overload', 'message': 'File Extracted successfully!'})
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
               if not copy.startswith(f'/home/{request.user}'):
                    copy=f'/home/{request.user}'+copy
               if  not os.path.isdir(copy):
                   return JsonResponse({'status': 'invalid', 'message': "Invalid Location"})
               for i in selected_items:
                    try:
                        import shutil
                        print(file_path+i,copy)
                        shutil.move(file_path+"/"+i,copy)
                        try:
                             if request.user.is_superuser():
                                  run_command(f"chown www-data:www-data {copy}")
                                  run_command(f"chown www-data:www-data {copy}/{i}")
                                  
                             else:
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
                         run_command(f"sudo chown -R www-data:www-data {file_path}")
                    except:
                         pass
                    return JsonResponse({'status': 'success', 'message': 'File Extracted successfully!'})
                 
               except Exception as e:
                    return JsonResponse({'status': 'error', 'message': 'File Extraction Failed!'})
               
         return JsonResponse({'status': 'error', 'message': 'File Extraction Failed!'})
     elif request.user.is_authenticated:
         packagecc=package.objects.get(name=user.objects.get(username=request.user).hosting_package).storage
         currentstorage=get_directory_size_in_mb(f'/home/{request.user}')
         
         if int(packagecc) != 0:

                if (int(currentstorage) > int(packagecc)):
                     return JsonResponse({'status': 'Overload', 'message': 'File Extracted successfully!'})
                                    
         if request.method =="POST":
               
               data = json.loads(request.body)  # Get the data from the request body
               selected_items = data.get('selected', [])
               file_path = data.get('path')
        
              
               if '/' !=file_path[0]:
                   file_path="/"+file_path
               
                 
               try:
                    
                    extract_zip_with_error_handling(file_path+'/'+selected_items[0], file_path)
                   
                    try:
                         run_command(f"sudo chown -R {request.user}:www-data {file_path}")
                    except:
                         pass
                    return JsonResponse({'status': 'success', 'message': 'File Extracted successfully!'})
                 
               except Exception as e:
                    print(e)
                    return JsonResponse({'status': 'error', 'message': 'File Extraction Failed!'})
               
         return JsonResponse({'status': 'error', 'message': 'File Extraction Failed!'})

@login_required(login_url='/')
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
                    if not request.user.is_superuser:
                    
                        packagecc=package.objects.get(name=user.objects.get(username=request.user).hosting_package).storage
                        currentstorage=get_directory_size_in_mb(f'/home/{request.user}')
                        
                        if int(packagecc) != 0:

                                if (int(currentstorage) > int(packagecc)):
                                    return JsonResponse({'status': 'Overload', 'message': 'File Extracted successfully!'})
                            
                    zip_files_and_folders(file_path, l)
                    if not request.user.is_superuser:
                         run_command(f'sudo chown {request.user}:{request.user} {file_path}')
                         
                 
                    return JsonResponse({'status': 'success', 'message': 'File Compressed successfully!'})
              
               except Exception as e:
                    print(e)
                    return JsonResponse({'status': 'error', 'message': 'File Compression Failed!'})
                
               
@login_required(login_url='/')
def ddeletedata(request):
     import os
     import shutil
     c=0
     if request.user.is_superuser or request.user.is_authenticated:
         if request.method =="POST":
               
               data = json.loads(request.body)  # Get the data from the request body
               selected_items = data.get('selected', [])
               file_path = data.get('path')
        
              
               if '/' !=file_path[0]:
                   file_path="/"+file_path
               if '/' !=file_path[-1]:
                   file_path=file_path+"/"
            
               for i in selected_items:
                 
                try:
                    
                    os.remove(file_path+i)
                    c=c+1
                    
                except Exception as e:
                    pass
                try:
                    os.rmdir(file_path+i)
                    c=c+1
                 

                except Exception as e:
                    pass
                try:
                    shutil.rmtree(file_path+i)
                    c=c+1
                   

                except Exception as e:
                    pass
               if c==len(selected_items):
                   return JsonResponse({'status': 'success', 'message': 'File Deleted successfully!'})
               else:
                   
                   return JsonResponse({'status': 'error', 'message': 'File Deletion Failed!'})
         return JsonResponse({'status': 'error', 'message': 'File Deletion Failed!'})


     

@login_required(login_url='/')
def deletedata(request):
     import os
     import shutil
     c=0

     if request.user.is_superuser or request.user.is_authenticated:
         if request.method =="POST":
               
               data = json.loads(request.body)  # Get the data from the request body
               selected_items = data.get('selected', [])
               file_path = data.get('path')
        
              
               if '/' !=file_path[0]:
                   file_path="/"+file_path
               if '/' !=file_path[-1]:
                   file_path=file_path+"/"
            
               for i in selected_items:
                 
                try:
                    
                    os.remove(file_path+i)
                    c=c+1
                    
                except Exception as e:
                    pass
                try:
                    os.rmdir(file_path+i)
                    c=c+1
                    return JsonResponse({'status':'success'})

                except Exception as e:
                    pass
                try:
                    shutil.rmtree(file_path+i)
                    c=c+1
                    return JsonResponse({'status':'success'})

                except Exception as e:
                    pass
               if c==len(selected_items):
                   return JsonResponse({'status': 'success', 'message': 'File Deleted successfully!'})
               else:
                   
                   return JsonResponse({'status': 'error', 'message': 'File Deletion Failed!'})
         return JsonResponse({'status': 'error', 'message': 'File Deletion Failed!'})
     

@login_required(login_url='/')
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
               data = json.loads(request.body)  # Get the data from the request body
             
               
               domain12 = data.get('web') 
               domain12=domain12.lower()
               email = data.get('email') 
               
               try:
                   x=domain.objects.get(domain=domain12)
                   
                   return JsonResponse({'status': 'already', 'message': 'Domain Already Exist'})
               except:
                   directories = os.listdir('/home')
                   domainname = domain12.split('.')[0].lower()
                   domainname=domainname.replace("*","")
                   domainname=domainname.replace("-","")
                   domainname=domainname.replace("_","")
                   domainname=domainname.replace("(","")
                   domainname=domainname.replace(")","")
                   domainname=domainname.replace("{","")
                   domainname=domainname.replace("}","")
                   domainname=domainname.replace("/","")
                   while domainname in directories:
                    domainname = domainname[:-1]
                   path="/home/"+domainname
                   os.mkdir(path)
                   os.mkdir(path+'/public_html')
                   
                   run_command(f'cp -r /var/www/panel/voidpanel/*  {path}/public_html/')
                   run_command(f'sudo ln -s /etc/nginx/sites-available/{domain12}.conf  /etc/nginx/sites-enabled/')
                   os.mkdir(path+'/ssl')
                   os.mkdir(f'/var/mail/vhosts/{domain12}')
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
                   file_path = f"/etc/nginx/sites-available/{domain12}.conf"
                   root_dir = path+'/public_html'
                 
                   cert_path, key_path = generate_ssl_certificates(domain12, path+'/ssl',path+'/logs')
                   if cert_path and key_path:
                             create_nginx_ssl_conf(file_path, domain12, root_dir, cert_path, key_path)
                   else:
                    
                       with open('/var/logs.txt','a') as f:
                                f.write(f"Cannot Genrate open ssl for domain {domain12}\n")
                       import shutil
                       shutil.rmtree(path)
                       return JsonResponse({'status': 'error', 'message': 'Domain Added!'})
                   key_dir = f'/etc/opendkim/keys/{domain12}'
                   zone_file_path = f'/etc/bind/db.{domain12}'
                   private_key_path, public_key_path = generate_dkim_keys(domain12, key_dir)
                   if private_key_path and public_key_path:
                      create_bind_records(domain12, key_dir, zone_file_path)
                      configure_opendkim(domain12, key_dir)
                      run_command("sudo systemctl restart opendkim")
                      run_command("sudo systemctl restart postfix")
                      with open('/var/logs.txt','a') as f:
                                f.write(f" Genareted Dkmi Record for domain {domain12}\n")
                   else:
                       with open('/var/logs.txt','a') as f:
                                f.write(f"Cannot Genarete Dkmi Record for domain {domain12}\n")
                       import shutil
                       shutil.rmtree(path)
                       return JsonResponse({'status': 'error', 'message': 'Domain Added!'})
                   run_command("sudo systemctl restart bind9")
                   run_command("sudo systemctl reload nginx")
                   import time
                   time.sleep(2)
                   domain.objects.create(domain=domain12,email=email,dir=domainname)
                   return JsonResponse({'status': 'success', 'message': 'Domain Added!'})
            
         return JsonResponse({'status': 'success', 'message': 'Domain Added!'})
            

@login_required(login_url='/')
@never_cache
def addusermain(request):
   
     
     if request.user.is_superuser:
         if request.method =="POST":
               data = json.loads(request.body)  # Get the data from the request body
             
               
               domain12 = data.get('web') 
               domain12=domain12.lower()
               email = data.get('email') 
               password = data.get('password') 
               package12 = data.get('package') 
               
               if package12 == 'Select':
                    package12='default'
               try:
                    fgf=package.objects.get(name=package12)

                    sto=str(fgf.storage)
               except:
                     return JsonResponse({'status': 'package', 'message': 'Domain Already Exist'})
            
                    
               try:
                   x=domain.objects.get(domain=domain12)  
                   return JsonResponse({'status': 'already', 'message': 'Domain Already Exist'})
               except:
                   directories = os.listdir('/home')
                   domainname = domain12.split('.')[0].lower()
                   
                   domainname=domainname.replace("*","")
                   domainname=domainname.replace("-","")
                   domainname=domainname.replace("_","")
                   domainname=domainname.replace("(","")
                   domainname=domainname.replace(")","")
                   domainname=domainname.replace("{","")
                   domainname=domainname.replace("}","")
                   domainname=domainname.replace("/","")
                   while domainname in directories:
                    domainname = domainname[:-1]
                
                   path="/home/"+domainname
               
                   os.mkdir(path)
                   os.mkdir(path+'/public_html')
                   
                   run_command(f'cp -r /var/www/panel/voidpanel/*  {path}/public_html/')
                   run_command(f'sudo ln -s /etc/nginx/sites-available/{domain12}.conf  /etc/nginx/sites-enabled/')
                   os.mkdir(path+'/ssl')
                   os.mkdir(f'/var/mail/vhosts/{domain12}')
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
                   file_path = f"/etc/nginx/sites-available/{domain12}.conf"
                   root_dir = path+'/public_html'
                 
                   cert_path, key_path = generate_ssl_certificates(domain12, path+'/ssl',path+'/logs')
                   if cert_path and key_path:
                             create_nginx_ssl_conf(file_path, domain12, root_dir, cert_path, key_path)
                   else:
                    
                       with open('/var/logs.txt','a') as f:
                                f.write(f"Cannot Genrate open ssl for domain {domain12}\n")
                       import shutil
                       shutil.rmtree(path)
                       return JsonResponse({'status': 'error', 'message': 'Domain Added!'})
                   key_dir = f'/etc/opendkim/keys/{domain12}'
                   zone_file_path = f'/etc/bind/db.{domain12}'
                   private_key_path, public_key_path = generate_dkim_keys(domain12, key_dir)
                   if private_key_path and public_key_path:
                      create_bind_records(domain12, key_dir, zone_file_path)
                      configure_opendkim(domain12, key_dir)
                      run_command("sudo systemctl restart opendkim")
                      run_command("sudo systemctl restart postfix")
                      with open('/var/logs.txt','a') as f:
                                f.write(f" Genareted Dkmi Record for domain {domain12}\n")
                   else:
                       with open('/var/logs.txt','a') as f:
                                f.write(f"Cannot Genarete Dkmi Record for domain {domain12}\n")
                       import shutil
                       shutil.rmtree(path)
                       return JsonResponse({'status': 'error', 'message': 'User Added!'})
                   run_command("sudo systemctl restart bind9")
                   run_command("sudo systemctl reload nginx")
                   import time
                   time.sleep(1)
                   domain.objects.create(domain=domain12,email=email,dir=domainname,userdomain=True)
                   user.objects.create(domain=domain12,email=email,username=domainname,hosting_package=package12)
                   User.objects.create_user(username=domainname,email=email,password=password)
                   

                   try:
                        
                        run_command(f'sudo useradd -m -s /usr/sbin/nologin {domainname} && sudo passwd -u {domainname} && echo "{domainname}:{password}" | sudo chpasswd')
                   except:
                        pass
                   run_command(f'sudo chown {domainname}:{domainname}  /home/{domainname}')
                   try:
                        run_command(f'sudo mount -o remount /')
                   except:
                        pass
                   try:
                        run_command(f'sudo setquota -u {domainname} {sto} {sto} 0 0 /')
                   except:
                        pass
                   return JsonResponse({'status': 'success', 'message': 'User Added!'})
                   
                   
            
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
                
                return render(request,'panel/viewwebsite.html',d)
           else:
               return redirect('/listwebsites')
    else: 
        return redirect('/')
    

@login_required(login_url='/')
def eadns(request):
    
   
    if request.user.is_superuser:
        
           domainname=request.GET.get('domain',None)
           if domainname:

                d={}
                try:

                    current_domain=domain.objects.get(domain=domainname)
                    d['domain']=current_domain
              
                    pat=f"/etc/bind/db.{current_domain}"
    
                  
                    data12=parse_dns_zone_file(pat)
               
                    
                    d['data']=data12[2:]
           
                

            
           
                except:

                    return redirect('/')
                url = 'https://voidpanel.com/admindocs/'  # Replace with your API URL
                response = requests.get(url)
                if response.status_code == 200:
                    dataee = response.json()  # Parse the JSON response
                    d['docs']=dataee
                
                
                return render(request,'panel/eadns.html',d)
           else:
               return redirect('/')
    else: 
        return redirect('/')
    
@login_required(login_url='/')
def deletedns(request):
   
    if request.user.is_superuser:
           domainname=request.GET.get('domain',None)
        
           name = request.GET.get('name')
           domain = request.GET.get('domain')
           record_type = request.GET.get('type')
           data = request.GET.get('data')
           ttl = request.GET.get('ttl',None)
           records = []
           deleted = False
           pat=f"/etc/bind/db.{domain}"

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
        return redirect('/')
    
@login_required(login_url='/')
def adddnsrecord(request):
    if request.user.is_superuser:
        if request.method == 'POST':
            # Extract data from the POST request
            name = request.POST.get('name')
           
            domainname = request.POST.get('domain')
            domainname=domainname.lower()
            record_class = request.POST.get('class')
            record_type = request.POST.get('type',None)
            ttl = request.POST.get('ttl')
            data = request.POST.get('data')

            if name and record_class and record_type and data and domainname:
                pat=f"/etc/bind/db.{domainname}"
            
           
                with open(pat, 'a') as zone_file:
                    zone_file.write(f"\n; {record_type} Record for {domainname}\n")
                    zone_file.write(f"{name} {ttl} {record_class} {record_type} {data}\n")
                run_command("sudo systemctl restart bind9")
                    
                return JsonResponse({'success': True})
            else:
                return JsonResponse({'success': False, 'error': 'Missing required fields'})

        return JsonResponse({'success': False, 'error': 'Invalid request method'})
    

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
               
               
       
              

def addemailaccount(request):
    import base64
    if request.user.is_superuser or request.user.is_authenticated:
        try:
            if request.user.is_superuser:
                current=request.session['name']
            else:
                current=request.user
        except:
             pass
        if request.method == 'POST':
            username = request.POST.get('username')
            username=username.lower()
            usernamex=username
            password = request.POST.get('password')
            domain = request.POST.get('domain')
            domain=domain.lower()
            username=username+"@"+domain

            try:
                                 weew=user.objects.get(username=current).hosting_package
                                 er=package.objects.get(name=weew)
                                 if er.email_accounts !='0':
                                    if   len(allemail.objects.filter(domain=domain)) >= int(er.email_accounts):
                                      return JsonResponse({'status': 'exceed', 'message': 'Already Exist'})

            except:
                                 pass
            try:
                fetch=allemail.objects.get(email=username)
                return JsonResponse({'status': 'error', 'message': 'Invalid request'})
            except:
                with open('/etc/postfix/virtual_domains','a') as f:
                    f.write(f"{domain}\n")
                with open('/etc/postfix/virtual_alias','a') as f:
                    f.write(f"{username} {username}\n")
                # run_command(f'sudo mkdir -p /var/mail/vhosts/{domain}/{usernamex}/tmp')
                run_command(f'sudo mkdir -p /var/mail/vhosts/{domain}/{usernamex}')
                run_command(f'sudo chown -R vmail:vmail /var/mail/vhosts/{domain}')
                run_command(f'sudo chown -R vmail:vmail /var/mail/vhosts/{domain}/{usernamex}')
                run_command("postmap /etc/postfix/virtual_alias")
                run_command(f"sh /var/www/panel/emailadd.sh {username} {password}")
                run_command("sudo chown -R vmail:vmail /var/mail/vhosts")
                run_command("sudo chmod -R 775 /var/mail/vhosts")


                password = base64.b64encode(password.encode('utf-8'))
                xxxx=allemail.objects.create(domain=domain,email=username,password=password)
                return JsonResponse({'status': 'success'})

        return JsonResponse({'status': 'error', 'message': 'Invalid request'})

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
                   maildir_path = f"/var/mail/vhosts/{i.domain}/{usernameemail}" 
                   new_dir = os.path.join(maildir_path, "new")
                   cur_dir = os.path.join(maildir_path, "cur")
                   new_emails_count = len(os.listdir(new_dir)) if os.path.exists(new_dir) else 0
                   cur_emails_count = len(os.listdir(cur_dir)) if os.path.exists(cur_dir) else 0
                   total_emails_count = new_emails_count + cur_emails_count
                #    command = f"grep 'status=sent' /var/log/mail.log | grep '{i.email}'"
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
            domain = request.POST.get('domain')
            domain=domain.lower()
            email = request.POST.get('emailname')
            email=email.lower()
            run_command(f'sed -i "s|^{email}:.*|{email}:$(doveadm pw -p {password})|" "/var/mail/vhosts/{domain}/shadow"')
            password = base64.b64encode(password.encode('utf-8'))
            print(email)
            
            xxxx=allemail.objects.get(email=email)
            xxxx.password=password
            xxxx.save()
            return JsonResponse({'status': 'success'})
        
        return JsonResponse({'status': 'error'})
    


@login_required(login_url='/')

def adddatabase(request):
    with open('/etc/dontdelete.txt','r') as f:
                                            adminpassword=f.read()
                                            adminpassword=adminpassword.strip()
    
    if request.user.is_superuser or request.user.is_authenticated:
        try:
            if request.user.is_superuser:
                current=request.session['name']
            else:
                current=request.user
        except:
             pass
        
        if request.method == 'POST':
            
           
            fromt = request.POST.get('front')
            name = request.POST.get('databasename')
            final=fromt+name
        
            
            
        
            try:
                                 weew=user.objects.get(username=current).hosting_package
                                 er=package.objects.get(name=weew)
                                 if er.databases_allowed !='0':
                                    mainn=str(current)+"_"
                                    
                                    if   len(get_database_names_with_filter(adminpassword,mainn)) >= int(er.databases_allowed):
                                      return JsonResponse({'status': 'exceed', 'message': 'Already Exist'})

            except:
                                 pass
            
      
            
            
            
            # Call the function and check the result
            if create_database_and_table(final, adminpassword):
                return JsonResponse({'status': 'success'})
            else:
             
                return JsonResponse({'status': 'error', 'message': 'Database creation failed'})
        else:
            return JsonResponse({'status': 'error', 'message': 'Database name is required'})

    return JsonResponse({'status': 'error', 'message': 'Invalid request method'})
            
@login_required(login_url='/')
def adddatabaseuser(request):
  with open('/etc/dontdelete.txt','r') as f:
                                            adminpassword=f.read()
                                            adminpassword=adminpassword.strip()
  if request.user.is_superuser or request.user.is_authenticated:
    if request.method == 'POST':
        username = request.POST.get('databaseuser')
        password = request.POST.get('password')
        domain = request.POST.get('domain')
        full=domain+'_'+username
        if create_mysql_user(full,password,adminpassword):
            return JsonResponse({'status': 'success'})
        else:
             return JsonResponse({'status': 'error', 'message': 'Invalid request'})
    else:
            return JsonResponse({'status': 'error', 'message': 'Database name is required'})
    


@login_required(login_url='/')
def dbconnect(request,data):
    with open('/etc/dontdelete.txt','r') as f:
                                            adminpassword=f.read()
                                            adminpassword=adminpassword.strip()
   
    if request.user.is_superuser:
                d={}
                try:
                    lold=domain.objects.get(domain=data)
                    cc=lold.dir
                    d['domain']=data
                    mainn=cc+"_"
                    d['database']=get_database_names_with_filter(adminpassword,mainn)
                    d['users']=get_database_users_with_filter(adminpassword,mainn)
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
def dbreomve(request,data,database):
    with open('/etc/dontdelete.txt','r') as f:
                                            adminpassword=f.read()
                                            adminpassword=adminpassword.strip()
   
    if request.user.is_superuser:
                d={}
                if data=='admin':
                    if remove_database(database, adminpassword):
                            return redirect(f'/fulldbwizard/')
                try:
                    lold=domain.objects.get(domain=data)
                    cc=lold.dir
                    if remove_database(database, adminpassword):
                    
                            return redirect(f'/dbconnect/{data}/')
                    else:
                        return redirect("/listwebsite/")

                except:
                    return redirect("/listwebsite/")
    elif request.user.is_authenticated:
   
                try:
                    lold=domain.objects.get(domain=data)
                    cc=lold.dir
                    if remove_database(database, adminpassword):
                    
                            return redirect(f'/control/dbconnect/{data}/')
                    else:
                        return redirect("/")

                except:
                    return redirect("/")
         
           
    else: 
        return redirect('/')
    
@login_required(login_url='/')
def dbuserremove(request,data,database):
    with open('/etc/dontdelete.txt','r') as f:
                                            adminpassword=f.read()
                                            adminpassword=adminpassword.strip()
   
    if request.user.is_superuser:
                d={}
                if data=='admin':
                    if delete_mysql_user(database, adminpassword):
                            return redirect(f'/fulldbwizard/')
                     
                try:
                    lold=domain.objects.get(domain=data)
                    if delete_mysql_user(database, adminpassword):
                    
                            return redirect(f'/dbconnect/{data}/')
                    else:
                        return redirect("/listwebsite/")

                except:
                    return redirect("/listwebsite/")
    elif request.user.is_authenticated:
     
                try:
                    lold=domain.objects.get(domain=data)
                    if delete_mysql_user(database, adminpassword):
                    
                            return redirect(f'/control/dbconnect/{data}/')
                    else:
                        return redirect("/")

                except:
                    return redirect("/")
           
    else: 
        return redirect('/')
    
@csrf_exempt
def changepasswordforuser(request):
    with open('/etc/dontdelete.txt','r') as f:
                                            adminpassword=f.read()
                                            adminpassword=adminpassword.strip()
    if request.user.is_superuser or request.user.is_authenticated:
        if request.method == 'POST':
            username = request.POST.get('databaseuser')
            new_password = request.POST.get('password')
            admin_password = adminpassword  # Replace with actual admin password logic

            if change_mysql_user_password(username, new_password, admin_password):
                return JsonResponse({'status': 'success'})
            else:
                return JsonResponse({'status': 'error', 'message': 'Password change failed.'})

        return JsonResponse({'status': 'error', 'message': 'Invalid request.'})

@csrf_exempt
def addpermissiontouser(request):
    with open('/etc/dontdelete.txt','r') as f:
                                            adminpassword=f.read()
                                            adminpassword=adminpassword.strip()
    if request.user.is_superuser or request.user.is_authenticated:
        priv=[]
        if request.method == 'POST':
            select=request.POST.get('select',None)
            database=request.POST.get('databasename',None)
            userdatabase=request.POST.get('databaseusername',None)
            select=request.POST.get('select',None)
            insert=request.POST.get('insert',None)
            update=request.POST.get('update',None)
            delete=request.POST.get('delete',None)
            execute=request.POST.get('execute',None)
            create=request.POST.get('create',None)
            drop=request.POST.get('drop',None)
            alter=request.POST.get('alter',None)
            index=request.POST.get('index',None)
            grant=request.POST.get('grant',None)
            revoke=request.POST.get('revoke',None)
            references=request.POST.get('references',None)
            trigger=request.POST.get('trigger',None)
            if select:
                priv.append(select)
            if insert:
                priv.append(insert)
            if update:
                priv.append(update)
            if delete:
                priv.append(delete)
            if execute:
                priv.append(execute)
            if create:
                priv.append(create)
            if drop:
                priv.append(drop)
            if alter:
                priv.append(alter)

            
            if  grant_mysql_user_privileges(userdatabase, database, priv,adminpassword):
                return JsonResponse({'status': 'success', 'message': 'Success.'})
            else:
                return JsonResponse({'status': 'error', 'message': 'failed.'})
            

        return JsonResponse({'status': 'error', 'message': 'Invalid request.'})
                      

@login_required(login_url='/')
def files(request,data):
    import os
    file_path=request.GET.get('key',None)
    if file_path is None:
        file_path="/home/"+data
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
def cronn(request,data):
   
    if request.user.is_superuser:
                d={}
                try:
                    lold=domain.objects.get(domain=data)
                    d['crondata']=cron.objects.filter(domain=data).all()
                    if request.method =="POST":
                        time=request.POST['time']
                        path=request.POST['path']
          
                        run_command(f'(echo "{time} {path}" ; crontab -l) | crontab -')
                        ccc=cron.objects.create(domain=data,path=path,duratioin=time)
                    url = 'https://voidpanel.com/admindocs/'  # Replace with your API URL
                    response = requests.get(url)
                    if response.status_code == 200:
                        dataee = response.json()  # Parse the JSON response
                        d['docs']=dataee
                    return render(request,'panel/cron.html',d)
                except:
                    return redirect("/listwebsite/")
           
    else: 
        return redirect('/')
    
@login_required(login_url='/')
def deletecron(request,data):
    if request.user.is_superuser:
        xxxx=cron.objects.get(id=data)
        domainname=xxxx.domain
        run_command(f"crontab -l | grep -v '{xxxx.path}' | crontab -")
        xxxx.delete()
        return redirect(f'/cron/{domainname}')
    
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
    
@csrf_exempt
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
                            name=request.POST['name']
                            name=name.lower()
                            data=request.POST['data']
                            data=data.lower()
                            lold=domain.objects.get(domain=data)
                            full=name+'.'+data
                            try:
                                 weew=user.objects.get(username=current).hosting_package
                                 er=package.objects.get(name=weew)
                                 if er.subdomain !='0':
                                    if   len(subdomainname.objects.filter(domain=data)) >= int(er.subdomain):
                                      return JsonResponse({'status': 'exceed', 'message': 'Already Exist'})

                            except:
                                 pass
                            try:
                                cc=subdomainname.objects.get(subdomain=full)
                                return JsonResponse({'status': 'error', 'message': 'Already Exist'})
                            except:
                                path="/home/"+lold.dir+'/public_html/'+name   
                                oldpath="/home/"+lold.dir  
                                os.mkdir(path)
                                run_command(f'cp -r /var/www/panel/voidpanel/*  {path}/')
                                run_command(f'sudo ln -s /etc/nginx/sites-available/{full}.conf  /etc/nginx/sites-enabled/')
                                file_path = f"/etc/nginx/sites-available/{full}.conf"
                                root_dir = path
                                cert_path, key_path = generate_ssl_certificates(full, oldpath+'/ssl',oldpath+'/logs')
                                if cert_path and key_path:
                                        create_nginx_ssl_conf(file_path, full, root_dir, cert_path, key_path)
                                else:
                        
                                            with open('/var/logs.txt','a') as f:
                                                    f.write(f"Cannot Genrate open ssl for domain {full}\n")
                                zone_file_path = f'/etc/bind/db.{lold.domain}'
                                create_bind_recordsforsubdomain(name,zone_file_path)
                                run_command("sudo systemctl restart bind9")
                                run_command("sudo systemctl restart nginx")
                                import time
                                time.sleep(2)
                                cce=subdomainname.objects.create(subdomain=full,name=name,domain=data)
                                return JsonResponse({'status': 'success', 'message': 'Already Exist'})
    
        return JsonResponse({'status': 'error', 'message': 'Invalid request.'})
    

@login_required(login_url='/')
def deletesubdomain(request,data):
    if request.user.is_superuser :
        xxxx=subdomainname.objects.get(subdomain=data)
        maindir=lold=domain.objects.get(domain=xxxx.domain).dir
        path="/home/"+maindir+"/public_html/"+xxxx.name
        import shutil
        shutil.rmtree(path)
        domainname=xxxx.domain
        xxxx.delete()
        return redirect(f'/subdomain/{domainname}')
    elif request.user.is_authenticated:
        xxxx=subdomainname.objects.get(subdomain=data)
        maindir=lold=domain.objects.get(domain=xxxx.domain).dir
        path="/home/"+maindir+"/public_html/"+xxxx.name
        import shutil
        shutil.rmtree(path)
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
                    path='/home/'+lold.dir+"/logs/ssl.txt"
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


@csrf_exempt
def runsslfordoamin(request):
    import subprocess
    if request.method == 'POST':
                        name=request.POST['domain']
                        name=name.lower()
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
def runsslfordoamin1(request):
    import subprocess
    lol=None
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

@csrf_exempt
def changephpversion(request):
    if request.user.is_superuser or request.user.is_authenticated:
        if request.method=="POST":
                            name=request.POST['name']
                            php=request.POST['php']
                            try:
                                namm=domain.objects.get(domain=name)
                                run_command(f"sed -i 's/{namm.php}/{php}/' /etc/nginx/sites-enabled/{namm}.conf")
                                run_command("sudo systemctl reload nginx")
                                import time
                                time.sleep(2)
                                namm.php=php
                                namm.save()
                                return JsonResponse({'status': 'success', 'message': 'Already Exist'})
                                
                            except:
                                namm=subdomainname.objects.get(subdomain=name)
                                run_command(f"sed -i 's/{namm.php}/{php}/' /etc/nginx/sites-enabled/{namm}.conf")
                                run_command("sudo systemctl reload nginx")
                                import time
                                time.sleep(2)
                                namm.php=php
                                namm.save()
                                return JsonResponse({'status': 'success', 'message': 'Already Exist'})
    
                    
    
        return JsonResponse({'status': 'error', 'message': 'Invalid request.'})


@never_cache
@login_required(login_url='/')
def phpini(request,data):
   
    if request.user.is_superuser:
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

@csrf_exempt
def addredirectionnn(request):
    if request.user.is_superuser or request.user.is_authenticated:
        if request.method=="POST":
                            name=request.POST['domain']
                            name=name.lower()
                            pathlocation=request.POST['path']
                            newpathlocation=request.POST['newpath']
                            maindomain=request.POST['maindomain']
                            maindomain=maindomain.lower()
                           
                            if pathlocation == '/phpmyadmin' or pathlocation == '/phpmyadmin/' or pathlocation == 'phpmyadmin':
                                 return JsonResponse({'status': 'c', 'message': 'Already Exist'})
                            if pathlocation == '/static' or pathlocation == '/sttaic/' or pathlocation == 'static':
                                 return JsonResponse({'status': 'c', 'message': 'Already Exist'})
                            
                            if newpathlocation[0]!="/":
                                newpathlocation="/"+newpathlocation
                            with open(f'/etc/nginx/sites-available/{name}.conf', 'r') as file:
                                for line in file:
                                    if line.strip() == f'location {pathlocation} {{':
                                        return JsonResponse({'status': 'error', 'message': 'Already Exist'})
                            nginx_conf_path = f'/etc/nginx/sites-available/{name}.conf'
                    
                            redirect_rule = f'''
        location {pathlocation} {{
            return 301 https://{name}{newpathlocation};
        }}
    '''
                            try:
                                xxxxxx=redir.objects.get(domain=name,path=pathlocation)
                                
                                return JsonResponse({'status': 'error', 'message': 'Already Exist'})
                            except:
                                pass
                        
                            try:
                                namm=domain.objects.get(domain=name)
                                with open(nginx_conf_path, 'r') as file:
                                        config_data = file.readlines()

                        
                                if redirect_rule.strip() not in ''.join(config_data):
                            
                                    inserted = False
                                    for index, line in enumerate(config_data):
                                        if line.strip() == '}':
                                            # Insert the redirect rule just before the last closing `}`
                                            config_data.insert(index+1, redirect_rule)
                                            inserted = True
                                            break

                                    if inserted:
                                        # Write the modified configuration back to the file
                                        with open(nginx_conf_path, 'w') as file:
                                            file.writelines(config_data)

                                        dataaaa=redir.objects.create(maindomain=maindomain,domain=name,path=pathlocation,newpath=newpathlocation)
                                        run_command(f'sudo ln -s /etc/nginx/sites-available/{name}.conf /etc/nginx/sites-enabled/{name}.conf')
                                        run_command('sudo systemctl reload nginx')
                                        import time
                                        time.sleep(2)
                                        
                                        return JsonResponse({'status': 'success', 'message': 'Already Exist'})
                                    else:
                                        return JsonResponse({'status': 'error', 'message': 'Already Exist'})
                                
                                
                                
                                
                            except:
                                namm=subdomainname.objects.get(subdomain=name)
                                with open(nginx_conf_path, 'r') as file:
                                        config_data = file.readlines()

                                    # Check if the redirect rule already exists to avoid duplication
                                if redirect_rule.strip() not in ''.join(config_data):
                                    # Find where to insert the redirect rule
                                    inserted = False
                                    for index, line in enumerate(config_data):
                                        if line.strip() == '}':
                                            # Insert the redirect rule just before the last closing `}`
                                            config_data.insert(index+1, redirect_rule)
                                            inserted = True
                                            break

                                    if inserted:
                                        # Write the modified configuration back to the file
                                        with open(nginx_conf_path, 'w') as file:
                                            file.writelines(config_data)

                                        dataaaa=redir.objects.create(maindomain=maindomain,domain=name,path=pathlocation,newpath=newpathlocation)
                                        run_command(f'sudo ln -s /etc/nginx/sites-available/{name}.conf /etc/nginx/sites-enabled/{name}.conf') 
                                        run_command('sudo systemctl reload nginx')
                                        import time
                                        time.sleep(2)
                                        
                                        return JsonResponse({'status': 'success', 'message': 'Already Exist'})
                                    else:
                                        return JsonResponse({'status': 'error', 'message': 'Already Exist'})                  
        return JsonResponse({'status': 'error', 'message': 'Invalid request.'})



@csrf_exempt
def delredirectionnn(request):
    if request.user.is_superuser or request.user.is_authenticated:
        if request.method=="POST":
                            data = json.loads(request.body)
                            name=data.get('domain').strip(' ')
                        
                            pathlocation=data.get('path').strip(' ')
                            newpathlocation=data.get('newpath').strip(' ')
                            
                            
                            nginx_conf_path = f'/etc/nginx/sites-available/{name}.conf'
                            
                            redirect_rule_start ='location '+pathlocation
                            redirect_rule_end = '}'
                            
                        
                            try:
                                
                                namm=domain.objects.get(domain=name)

                                with open(nginx_conf_path, 'r') as file:
                                        config_data = file.readlines()

                                    # Check if the redirect rule already exists to avoid duplication
                                in_redirect_block = False
                                new_config_data = []
                                for line in config_data:
                                    # Check if the current line starts the redirect rule
                                    if redirect_rule_start in line:
                                        in_redirect_block = True  # Start ignoring lines in this block
                                    elif in_redirect_block and redirect_rule_end in line:
                                        in_redirect_block = False  # End ignoring once we close the location block
                                        continue  # Skip the current closing line
                                    elif not in_redirect_block:
                                        new_config_data.append(line)

                                
                        
                                with open(nginx_conf_path, 'w') as file:
                                        file.writelines(new_config_data)

                                run_command('sudo systemctl reload nginx')
                                import time
                                time.sleep(2)
                            
                                xxxxxx=redir.objects.get(domain=name, path=pathlocation)
                                xxxxxx.delete()
                                        
                                return JsonResponse({'status': 'success', 'message': 'Already Exist'})
                        
                                
                                
                                
                                
                            except:
                                namm=subdomainname.objects.get(subdomain=name)
                                with open(nginx_conf_path, 'r') as file:
                                        config_data = file.readlines()

                                    # Check if the redirect rule already exists to avoid duplication
                                in_redirect_block = False
                                new_config_data = []
                                for line in config_data:
                                    # Check if the current line starts the redirect rule
                                    if redirect_rule_start in line:
                                        in_redirect_block = True  # Start ignoring lines in this block
                                    elif in_redirect_block and redirect_rule_end in line:
                                        in_redirect_block = False  # End ignoring once we close the location block
                                        continue  # Skip the current closing line
                                    elif not in_redirect_block:
                                        new_config_data.append(line)

                                
                        
                                with open(nginx_conf_path, 'w') as file:
                                        file.writelines(new_config_data)
                                xxxxxx=redir.objects.get(domain=name, path=pathlocation)
                                xxxxxx.delete()


                                run_command('sudo systemctl reload nginx')
                                        
                                import time
                                time.sleep(2)
                                return JsonResponse({'status': 'success', 'message': 'Already Exist'})             
        return JsonResponse({'status': 'error', 'message': 'Invalid request.'})






@login_required(login_url='/')
def terminate(request,data):
   
    if request.user.is_superuser:
                d={}
                try:
                    
                    lold=domain.objects.get(domain=data)
                    mainusername=lold.dir
                    dub=subdomainname.objects.filter(domain=data).all()
                    import shutil
                    file_path='/home/'+lold.dir
                    shutil.rmtree(file_path)
                    file_path_="/etc/nginx/sites-enabled/"+data+".conf"
                    os.remove(file_path_)
                    for i in dub:
                         file_path_="/etc/nginx/sites-enabled/"+i.subdomain+".conf"
                         os.remove(file_path_)
                    file_path_="/etc/bind/"+"db."+data
                    os.remove(file_path_)

                    file_path='/etc/opendkim/keys/'+lold.domain
                    shutil.rmtree(file_path)
                    try:
                        for yo in subdomainname.object.filter(domain=lold.domain):
                            file_path='/etc/opendkim/keys/'+yo.subdomain
                            shutil.rmtree(file_path)
                    except:
                         pass
                    try:
                         
                        file_path='/etc/letsencrypt/live/'+lold.domain
                        shutil.rmtree(file_path)
                    except:
                         pass
                    try:
                        for yo in subdomainname.object.filter(domain=lold.domain):
                            file_path='/etc/letsencrypt/live/'+yo.subdomain
                            shutil.rmtree(file_path)
                    except:
                         pass
                    try:
                        file_path='/var/mail/vhosts/'+lold.domain
                        shutil.rmtree(file_path)
                    except:
                         pass
                    sub=subdomainname.objects.filter(domain=lold.domain)
                    sub.delete()
                    ema=allemail.objects.filter(domain=lold.domain)
                   
                    ema.delete()
                    cro=cron.objects.filter(domain=lold.domain)
                    cro.delete()
                    redirrr=redir.objects.filter(domain=lold.domain)
                    redirrr.delete() 
                    lold.delete()
                    # Usage
                    config_file_path = '/etc/bind/named.conf'  
                    remove_zone_from_file(config_file_path, lold.domain)
                    run_command('sudo systemctl reload bind9')
                    try:
                         ft=ftpaccount.objects.filter(main=mainusername)
                         for i in ft:
                            run_command(f'sudo deluser {i.main}')
                         ft.delete()
                         use=user.objects.get(username=mainusername)
                         use.delete()
                         userf = User.objects.get(username=mainusername)
                         userf.delete()
                         try:
                            df=pythonname.objects.get(domain=lold.domain)
                            name=df.name
                            df.delete()
                            os.remove(f'/etc/systemd/system/{name}.service')
                         except:
                           pass
                         try:
                            df=mernname.objects.get(domain=lold.domain)
                            try:
                                 
                                name=df.name
                            except:
                                 pass
                            df.delete()
                            try:
                                os.remove(f'/var/run/{name}.sock')
                            except:
                                pass
                  
                         except:
                           pass
                         try:
                                for yo in subdomainname.object.filter(domain=lold.domain):
                                    try:
                                        df=pythonname.objects.get(domain=yo.subdomain)
                                        name=df.name
                                        df.delete()
                                        os.remove(f'/etc/systemd/system/{name}.service')
                                    except:
                                      pass
                                    
                         except:
                                pass
                         return redirect("/listusers/")  



                    except:
                        return redirect("/listwebsite/")            
                except Exception as e:
                    return redirect("/listwebsite/")
           
    else: 
        return redirect('/')
    


@login_required(login_url='/')
def suspend(request,data):
   
    if request.user.is_superuser:
                d={}
                try:
                    
                    lold=domain.objects.get(domain=data)
                    dub=subdomainname.objects.filter(domain=data).all()
                    file_path_="/etc/nginx/sites-enabled/"+data+".conf"
                    
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
                            file_path_="/etc/nginx/sites-enabled/"+iu.subdomain+".conf"
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
                    file_path_="/etc/nginx/sites-enabled/"+data+".conf"
                    
                    with open(file_path_, 'r') as file:
                        config_data = file.readlines()
                    root_updated = False
                    for i, line in enumerate(config_data):
                        if line.strip().startswith('root '):
                            config_data[i] = f"    root /home/{lold.dir}/public_html;\n"
                            root_updated = True
                            break
                    if root_updated:
   
                        with open(file_path_, 'w') as file:
                            file.writelines(config_data)
                    for iu in dub:
                            file_path_="/etc/nginx/sites-enabled/"+iu.subdomain+".conf"
                            with open(file_path_, 'r') as file:
                                config_data = file.readlines()
                            root_updated = False
                            for i, line in enumerate(config_data):
                                if line.strip().startswith('root '):
                                    config_data[i] = f"    root /home/{lold.dir}/public_html/{iu.name};\n"
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
    

@csrf_exempt
def backupdata(request):
    if request.method=="POST":
                            data = json.loads(request.body)
                         
                            name=data.get('domain').strip(' ')
                  
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
                            zip_multiple_locations_backup(main_directory, locations, zip_filename)
                            return JsonResponse({'status': 'success', 'message': 'Already Exist'})
    return JsonResponse({'status': 'error', 'message': 'Invalid request.'})


@login_required(login_url='/')
def packagewizard(request):
    
   
    if request.user.is_superuser:
                
                d={}
                d['packages']=package.objects.all()
                if request.method=="POST":
                        package_name = request.POST['package']  
                        storage = request.POST.get('storage')
                        if storage == 'unlimited':
                             storage='0'
                        ftp = request.POST.get('ftp')
                        if ftp == 'unlimited':
                             ftp='0'
                        bandwidth = request.POST.get('bandwidth')
                        if bandwidth == 'unlimited':
                             bandwidth='0'
                        subdomain = request.POST.get('subdomain')
                        if subdomain == 'unlimited':
                             subdomain='0'
                        # addondomain = request.POST.get('addondomain')
                        database = request.POST.get('database')
                        if database == 'unlimited':
                             database='0'
                        
                        email = request.POST.get('email')
                        if email == 'unlimited':
                             email='0'
                      
                        try:
                             cc=package.objects.get(name=package_name)
                             messages.success(request,"Same package Already Esist")
                        except:
                             newpac=package.objects.create(name=package_name,storage=storage,ftp=ftp,subdomain=subdomain,bandwidth=bandwidth,email_accounts=email,databases_allowed=database)

                url = 'https://voidpanel.com/admindocs/'  # Replace with your API URL
                response = requests.get(url)
                if response.status_code == 200:
                    dataee = response.json()  # Parse the JSON response
                    d['docs']=dataee
                return render(request,'panel/package.html',d)
                
           
    else: 
        return redirect('/')
    

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
                         with open('/etc/version.txt','r') as f:
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
    
@csrf_exempt
def updatepanel(request):

    if request.method == 'POST':
                    run_command('curl https://voidpanel.com/updatepanel.sh | bash')
                    return JsonResponse({'status': 'success', 'message': 'Already Exist'})
   
    return JsonResponse({'status': 'error', 'message': 'Invalid request.'})

    

@login_required(login_url='/')
def maincron(request):
    
   
    if request.user.is_superuser:
                d={}
                try:
           
                    d['crondata']=cron.objects.all()
                    if request.method =="POST":
                        time=request.POST['time']
                        path=request.POST['path']
          
                        run_command(f'(echo "{time} {path}" ; crontab -l) | crontab -')
                        ccc=cron.objects.create(domain='admin',path=path,duratioin=time)
                    url = 'https://voidpanel.com/admindocs/'  # Replace with your API URL
                    response = requests.get(url)
                    if response.status_code == 200:
                        dataee = response.json()  # Parse the JSON response
                        d['docs']=dataee
                    return render(request,'panel/maincron.html',d)
                except:
                    return redirect("/panel")
                
           
    else: 
        return redirect('/')
    
@login_required(login_url='/')
def chpass(request):
    
   
    if request.user.is_superuser:
                d={}
                try:
           
    
                    if request.method =="POST":
                        password=request.POST['password']

                        from django.contrib.auth.models import User
                        user = User.objects.get(username='admin')
                        user.set_password(password)
                        user.save()
                        file_path = '/etc/details.txt'
     


                        with open(file_path, 'r') as file:
                                lines = file.readlines()

                            # Search for 'admin' and modify the next line
                        for i, line in enumerate(lines):
                                if 'admin' in line:
                                   
                                    lines[i + 1] = f'VoidPanel_Password="{password}"\n'
                                    break

                            # Write the changes back to the file
                        with open(file_path, 'w') as file:
                                file.writelines(lines)

                        logout(request)
                        return redirect("/")
                    url = 'https://voidpanel.com/admindocs/'  # Replace with your API URL
                    response = requests.get(url)
                    if response.status_code == 200:
                        dataee = response.json()  # Parse the JSON response
                        d['docs']=dataee
                    return render(request,'panel/chpass.html',d)
                except:
                    return redirect("/panel")
                
           
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
                    path='/var/log/ssl.txt'
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


@csrf_exempt
def runsslforall(request):
    import subprocess
    if request.method == 'POST':
                      
                    lold=domain.objects.filter(sslstatus=False)

                    for name in lold:
                     try:
                        
                        command = [
                            "sudo", "certbot", "--nginx",
                            "-d", name.domain, "-d", f'www.{name.domain}', 
                            "--non-interactive",                   
                            "--agree-tos",                          
                            "--email", f'{name.email}',    
                            "--redirect",                          
                            "--no-eff-email"                       
                        ]
                        
                        
                        
                        #subdomain2=subdomainname.objects.filter(domain=name.domain).all()
                        path='/var/log/ssl.txt'
                        
                        try:
                            result = subprocess.run(command, capture_output=True, text=True, check=True)
                            with open(path,'a+') as f:
                                f.write("\n")
                                f.write(f"AutoSSl Completed for domain {name.domain}")
                                name.sslstatus=True
                                name.save()

                        except Exception as e:
                             with open(path,'a+') as f:
                                f.write("\n")
                                f.write(f"Error Occur for domain {name.domain}")
                        # with open(path, 'a+') as out_log:
                        #         process = subprocess.Popen(command, stdout=out_log, stderr=out_log)
                        
                        # for i in subdomain2:
                           
                        #     command = [
                        #             "sudo", "certbot", "--nginx",
                        #             "-d",  i.subdomain,   # Domains
                        #             "--non-interactive",                    # No interaction
                        #             "--agree-tos",                          # Automatically agree to terms of service
                        #             "--email", f'{i.name}@example.com',    # Provide email for notifications
                        #             "--redirect",                           # Automatically redirect HTTP to HTTPS
                        #             "--no-eff-email"                        # Disable the EFF email subscription prompt
                        #             ]
                          
                            # try:
                                
                            #     result = subprocess.run(command, capture_output=True, text=True, check=True)
                            #     with open(path,'a+') as f:
                            #         f.write("\n")
                            #         f.write(f"AutoSSl Completed for domain {i.subdomain}")
                            #         i.sslstatus=True
                            #         i.save()
                            # except Exception as e:
                            #  with open(path,'a+') as f:
                            #     f.write("\n")
                            #     f.write(f"Error Occur for domain {i.subdomain}")
                            #     f.write(e)   
                            # with open(path, 'a+') as out_log:
                            #     process = subprocess.Popen(command, stdout=out_log, stderr=out_log)
                     except:
                          pass
                    return JsonResponse({'status': 'success', 'message': 'Already Exist'})
   
    return JsonResponse({'status': 'error', 'message': 'Invalid request.'})



@csrf_exempt
def runsslforall1(request):
    import subprocess
    lol=None
    if request.method == 'POST':
                            data = json.loads(request.body)
                            name=data.get('name').strip(' ')
                            
                       
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
                           
                      

                            
                    
                            path='/var/log/ssl.txt'
                      
                            try:
                                result = subprocess.run(command, capture_output=True, text=True, check=True)
                                with open(path,'a+') as f:
                                    f.write("\n")
                                    f.write(f"AutoSSl Completed for  domain {name}")
                                
                                uuu=domain.objects.get(domain=name)
                                uuu.sslstatus=True
                                uuu.save()

                            
                                

                            except Exception as e:
                                with open(path,'a+') as f:
                                    f.write("\n")
                                    f.write(f"Error Occur for domain {name}")
                                    f.write(e)
                        
                            
                            return JsonResponse({'status': 'success', 'message': 'Already Exist'})
   
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
    with open('/etc/dontdelete.txt','r') as f:
                                            adminpassword=f.read()
                                            adminpassword=adminpassword.strip()
    
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
def deleteemail(request,data):
   
    if request.user.is_superuser:
                d={}
                import shutil
                try:
                    lold=allemail.objects.get(email=data)
                    try:
                        file_path='/var/mail/vhosts/'+lold.domain
                        shutil.rmtree(file_path)
                    except:
                         pass

                    lold.delete()
                    return redirect('/allemailwizard')
                   
                    

                except:
                    return redirect("/")
           
    else: 
        return redirect('/')
    
@login_required(login_url='/')
def deleteemai(request,data):
   
    if request.user.is_superuser or request.user.is_authenticated:
                d={}
                import shutil
                try:
                    lold=allemail.objects.get(email=data)
                    try:
                        file_path='/var/mail/vhosts/'+lold.domain
                        shutil.rmtree(file_path)
                    except:
                         pass
                    lold.delete()
                    return redirect('/')
                   
                    

                except:
                    return redirect("/")
           
    else: 
        return redirect('/')
    

@login_required(login_url='/')
def phpsetting(request):
    
    if request.user.is_superuser:
      
        d={}
        installed=phpversion.objects.all()
        available=['5.6','7.1','7.2','7.3','7.4','8.1','8.2','8.3','8.4']
        for i in installed:
             if i.name in available:
                  available.remove(i.name)
        d['installed']=installed
        d['available']=available
        # php_binaries = get_php_versions()
    
        # output_list = []  # List to hold the formatted output
        phpextentionsss=phpextentions.objects.all()
        dictphpextentionsss={}
        for ie in phpextentionsss:
             dictphpextentionsss[ie.name]=(eval(ie.extentions))
        d['extentionname']=dictphpextentionsss
        # for php_bin in php_binaries:
        #     php_version = get_php_version(php_bin)
        #     php_extensions = get_php_extensions(php_bin)

        #     if php_version:
        #         for ext in php_extensions:
        #             # Format output as php<version>-<extension>
        #             formatted_output = f"php{php_version}-{ext}"
        #             output_list.append(formatted_output)
   

        # d['extention']=output_list
        phpini={}
      
        for i in installed:
            with open(f'/etc/php/{i.name}/fpm/php.ini','r') as f:
                  newdata=f.read()
            phpini[i.name]=newdata
        d['phpini']=phpini
        # print(phpini.keys())
        # print(phpini.keys())
                  
        url = 'https://voidpanel.com/admindocs/'  # Replace with your API URL
        response = requests.get(url)
        if response.status_code == 200:
            dataee = response.json()  # Parse the JSON response
            d['docs']=dataee
        if request.method=="POST":
          
            try:
                
                name=request.POST['8.3']

                with open(f'/etc/php/8.3/fpm/php.ini','w') as f:
                    f.write(name)
                  
            except:
             pass


            try:
                
                name=request.POST['8.4']

                with open(f'/etc/php/8.4/fpm/php.ini','w') as f:
                    f.write(name)
                  
            except:
             pass
            try:
                
                name=request.POST['8.2']

                with open(f'/etc/php/8.2/fpm/php.ini','w') as f:
                    f.write(name)
                  
            except:
             pass

            try:
                
                name=request.POST['8.1']

                with open(f'/etc/php/8.1/fpm/php.ini','w') as f:
                    f.write(name)
                  
            except:
             pass

            try:
                
                name=request.POST['7.4']

                with open(f'/etc/php/7.4/fpm/php.ini','w') as f:
                    f.write(name)
                  
            except:
             pass

            try:
                
                name=request.POST['7.3']

                with open(f'/etc/php/7.3/fpm/php.ini','w') as f:
                    f.write(name)
                  
            except:
             pass
            try:
                
                name=request.POST['7.2']

                with open(f'/etc/php/7.2/fpm/php.ini','w') as f:
                    f.write(name)
                  
            except:
             pass

            try:
                
                name=request.POST['7.1']

                with open(f'/etc/php/7.1/fpm/php.ini','w') as f:
                    f.write(name)
                  
            except:
             pass

            try:
                
                name=request.POST['5.6']

                with open(f'/etc/php/5.6/fpm/php.ini','w') as f:
                    f.write(name)
                  
            except:
             pass
            

                  
        return render(request,'panel/phpsetting.html',d)
    else: 
        return redirect('/')
    




@csrf_exempt
def installphpversion(request):
    if request.user.is_superuser:
      
        d={}

        if request.method=="POST":
            php=request.POST['php']
            try:
                run_command('sudo apt  update -y  && sudo apt upgrade -y')
                run_command(f'sudo apt install -y php{php} php{php}-fpm')
            except:
                run_command('yum apt  update -y  && yum apt upgrade -y')
                run_command(f'sudo yum install -y php{php} php{php}-fpm')
            dd=phpversion.objects.create(name=php)
            return JsonResponse({'status': 'success', 'message': 'Already Exist'})
    return JsonResponse({'status': 'error', 'message': 'Invalid request.'})


@csrf_exempt
def installphpextention(request):
    status=False
    if request.user.is_superuser:
      
        d={}

        if request.method=="POST":
            data = json.loads(request.body)
            php=data.get('name').strip()
            option=data.get('option').strip()
        
            phpname=data.get('phpname').strip()
            ffd=phpextentions.objects.get(name=phpname)
            kjnre=eval(ffd.extentions)
          

       
            if option == 'on':
                try:
                    
                    run_command(f'sudo apt install -y {php} ')
                    status=True
                except:
                    pass
                try:
                    
                    run_command(f'sudo yum install -y {php} ')
                    status=True
                except:
                    pass
                kjnre[php]=1
            else:
                try:
                    
                    run_command(f'sudo apt remove -y {php} ')
                    status=True
                except:
                    pass
                try:
                    
                    run_command(f'sudo yum remove -y {php} ')
                    status=True
                except:
                    pass
                kjnre[php]=0
            ffd.extentions=kjnre
            ffd.save()
          

    
           
            
                    
            if status:
                 return JsonResponse({'status': 'success', 'message': 'Already Exist'})
            else:
                 return JsonResponse({'status': 'cannot', 'message': 'Already Exist'})
            
                
            
    return JsonResponse({'status': 'error', 'message': 'Invalid request.'})



@login_required(login_url='/')
def cpbruteforce(request):
    
    if request.user.is_superuser:
      
        d={}
        d['firewall']=firewall.objects.get(id=1)
        url = 'https://voidpanel.com/admindocs/'  # Replace with your API URL
        response = requests.get(url)
        if response.status_code == 200:
            dataee = response.json()  # Parse the JSON response
            d['docs']=dataee
        return render(request,'panel/cpbruteforce.html',d)
    else: 
        return redirect('/')
    
@csrf_exempt
def cpbrute(request):
    if request.user.is_superuser:
      
        d={}

        if request.method=="POST":


            
            e=firewall.objects.get(id=1)
            if e.status:
                 run_command('''sudo sed -i 's/^TESTING = "0"/TESTING = "1"/' /etc/csf/csf.conf''')
                
                 e.status=False
                 e.save()
            else:
                 run_command('''sudo sed -i 's/^TESTING = "1"/TESTING = "0"/' /etc/csf/csf.conf''')
                 run_command('sudo systemctl start lfd')
                 e.status=True
                 e.save()
            
           
       
           
            return JsonResponse({'status': 'success', 'message': 'Already Exist'})
    return JsonResponse({'status': 'error', 'message': 'Invalid request.'})


@csrf_exempt
def allowip(request):
    if request.user.is_superuser:
      
        d={}

        if request.method=="POST":
            php=request.POST['allow']
            run_command(f'csf -a {php} ')
            run_command('csf -r')
            return JsonResponse({'status': 'success', 'message': 'Already Exist'})
    return JsonResponse({'status': 'error', 'message': 'Invalid request.'})

@csrf_exempt
def denyip(request):
    if request.user.is_superuser:
      
        d={}

        if request.method=="POST":
            php=request.POST['allow']
            run_command(f'csf --deny {php} ')
            run_command('csf -r')
            return JsonResponse({'status': 'success', 'message': 'Already Exist'})
    return JsonResponse({'status': 'error', 'message': 'Invalid request.'})

@csrf_exempt
def ignoreip(request):
    if request.user.is_superuser:
      
        d={}

        if request.method=="POST":
            php=request.POST['allow']
            run_command(f'csf -a {php} ')
            run_command('csf -r')
            return JsonResponse({'status': 'success', 'message': 'Already Exist'})
    return JsonResponse({'status': 'error', 'message': 'Invalid request.'})

@csrf_exempt
def unblockip(request):
    if request.user.is_superuser:
      
        d={}

        if request.method=="POST":
            php=request.POST['allow']
            run_command(f'csf -dr {php} ')
            run_command('csf -r')
            return JsonResponse({'status': 'success', 'message': 'Already Exist'})
    return JsonResponse({'status': 'error', 'message': 'Invalid request.'})

@csrf_exempt
def blockip(request):
    if request.user.is_superuser:
      
        d={}

        if request.method=="POST":
            php=request.POST['allow']
            run_command(f'csf -d {php} "Suspicious activity" ')
            run_command('csf -r')
            return JsonResponse({'status': 'success', 'message': 'Already Exist'})
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
    

@csrf_exempt
def ftp12(request):
    if request.user.is_superuser:
      
        d={}

        if request.method=="POST":
            e=ftp.objects.get(id=1)

            if e.status:
                 run_command("sudo systemctl stop vsftpd")
                 run_command("sudo systemctl disable vsftpd") 
                 e.status=False
                 e.save()
            else:
                 run_command("sudo systemctl start vsftpd")
                 run_command("sudo systemctl enable vsftpd")
                 e.status=True
                 e.save()   
            return JsonResponse({'status': 'success', 'message': 'Already Exist'})
    return JsonResponse({'status': 'error', 'message': 'Invalid request.'})



@login_required(login_url='/')
def delpackage(request,data):
    
    if request.user.is_superuser:
      
        ew=package.objects.get(name=data)
        try:
            erer=user.objects.filter(hosting_package=data)
        except:
             pass
        if erer:
             messages.success(request,"cannot delete Package,As users are Using It")
             return redirect('/package/')
        else:
             messages.success(request,"Package deleted")
             ew.delete()
             return redirect('/package/')
       
    else: 
        return redirect('/')
    

@csrf_exempt
def cwtd(request):
    if request.user.is_superuser:
      
        d={}

        if request.method=="POST":
                domainaname=request.POST['domain']
                domainaname=domainaname.lower()
                package12=request.POST['package']
                ded=package.objects.get(name=package12)
                sto=str(ded.storage)
                fddf=domain.objects.get(domain=domainaname)
                import secrets; password = secrets.token_urlsafe(12)
                user.objects.create(domain=fddf.domain,email=fddf.email,username=fddf.dir,hosting_package=package12)

                User.objects.create_user(username=fddf.dir,email=fddf.email,password=password)
                fddf.userdomain=True
                fddf.save()
                try:
                    run_command(f'sudo useradd -m -s /usr/sbin/nologin {fddf.dir} && sudo passwd -u {fddf.dir} && echo "{fddf.dir}:{password}" | sudo chpasswd')
                except:
                     pass
                
                run_command(f'sudo chown {fddf.dir}:{fddf.dir}  /home/{fddf.dir}')
                try:
                        run_command(f'sudo mount -o remount /')
                except:
                        pass
                try:
                        run_command(f'sudo setquota -u {fddf.dir} {sto} {sto} 0 0 /')
                except:
                        pass
                


                #
                return JsonResponse({'status': 'success', 'message': 'Already Exist'})
    return JsonResponse({'status': 'error', 'message': 'Invalid request.'})


@login_required(login_url='/')
def serverstatus(request):
    with open('/etc/dontdelete.txt','r') as f:
                                            adminpassword=f.read()
                                            adminpassword=adminpassword.strip()
    
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
    
@csrf_exempt
def restart_now(request):
    if request.user.is_superuser:
        
        if request.method=="POST":
            data = json.loads(request.body)  # Get the data from the request body
            service = data.get('service') 
            if service == 'nginx':
                 run_command("systemctl reload nginx")
                 import time
                 time.sleep(2)
                 return JsonResponse({'status': 'success', 'message': 'Already Exist'})
            if restart_service(service):
                 return JsonResponse({'status': 'success', 'message': 'Already Exist'})
            else:
                 return JsonResponse({'status': 'success', 'message': 'Already Exist'})
    return JsonResponse({'status': 'error', 'message': 'Invalid request.'})

@csrf_exempt
def start_now(request):
    if request.user.is_superuser:
        
        if request.method=="POST":
            data = json.loads(request.body)  # Get the data from the request body
            service = data.get('service') 
            if start_service(service):
                 return JsonResponse({'status': 'success', 'message': 'Already Exist'})
            else:
                 return JsonResponse({'status': 'success', 'message': 'Already Exist'})
    return JsonResponse({'status': 'error', 'message': 'Invalid request.'})

@csrf_exempt
def start_now_python(request):
    if request.user.is_authenticated:
        if request.method=="POST":
            data = json.loads(request.body)  # Get the data from the request body
            domainname = data.get('domain').strip()
            name = data.get('name').strip()
            if start_service(name):
                 return JsonResponse({'status': 'success', 'message': 'Already Exist'})
            else:
                 return JsonResponse({'status': 'error', 'message': 'Already Exist'})
    return JsonResponse({'status': 'error', 'message': 'Invalid request.'})

@csrf_exempt
def restart_now_python(request):
    if request.user.is_authenticated:
        if request.method=="POST":
            data = json.loads(request.body)  # Get the data from the request body
            domainname = data.get('domain').strip()
            name = data.get('name').strip()
        
            if restart_service(name):
                 return JsonResponse({'status': 'success', 'message': 'Already Exist'})
            else:
                 return JsonResponse({'status': 'error', 'message': 'Already Exist'})
    return JsonResponse({'status': 'error', 'message': 'Invalid request.'})

@csrf_exempt
def stop_now(request):
    if request.user.is_superuser:
        
        if request.method=="POST":
            data = json.loads(request.body)  # Get the data from the request body
            service = data.get('service') 
            if stop_service(service):
                 return JsonResponse({'status': 'success', 'message': 'Already Exist'})
            else:
                 return JsonResponse({'status': 'success', 'message': 'Already Exist'})
    return JsonResponse({'status': 'error', 'message': 'Invalid request.'})


@csrf_exempt
def stop_now_python(request):
    if request.user.is_authenticated:
        if request.method=="POST":
            data = json.loads(request.body)  # Get the data from the request body
            domainname = data.get('domain').strip()
            name = data.get('name').strip()
            if stop_service(name):
                 return JsonResponse({'status': 'success', 'message': 'Already Exist'})
            else:
                 return JsonResponse({'status': 'error', 'message': 'Already Exist'})
    return JsonResponse({'status': 'error', 'message': 'Invalid request.'})


@csrf_exempt
def shutdown(request):
    if request.user.is_superuser:
         run_command('sudo shutdown now')
         return JsonResponse({'status': 'success', 'message': 'Already Exist'})
    
@csrf_exempt
def restart(request):
    if request.user.is_superuser:
         run_command('sudo reboot')
         return JsonResponse({'status': 'success', 'message': 'Already Exist'})
    
@csrf_exempt
def restartservice(request):
    if request.user.is_superuser:
         service=['mysql','postfix','dovecot','uwsgi','bind9','csf']
         for i in service:
            restart_service(i)
  
         return JsonResponse({'status': 'success', 'message': 'Already Exist'})
    
@csrf_exempt
def chpassuser(request):
    if request.user.is_superuser:
         if request.method=="POST":
            password=request.POST['password']
            username=request.POST['user']
            username=username.lower()
            sd=User.objects.get(username=username)
            sd.set_password(password)
            sd.save()
            try:
                run_command(f'echo "{username}:{password}" | sudo chpasswd')
                
            except:
                 pass
            return JsonResponse({'status': 'success', 'message': 'Already Exist'})
    
@csrf_exempt
def chpackageuser(request):
    if request.user.is_superuser:
         if request.method=="POST":
       
            packagee=request.POST['package']
            username=request.POST['user']
            username=username.lower()
            userd=user.objects.get(username=username)
            userd.hosting_package=packagee
            e=package.objects.get(name=packagee).storage

            userd.save()
            try:
                        run_command(f'sudo setquota -u {username} {e} {e} 0 0 /')
            except:
                        pass

            

            return JsonResponse({'status': 'success', 'message': 'Already Exist'})
         

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
   
     
     if request.user.is_authenticated:
         if request.method =="POST":
                data = json.loads(request.body)  # Get the data from the request body
                domain1 = data.get('domain') 
                name = data.get('name')  
                try:
                    ler=pythonname.objects.get(name=name)
                    return JsonResponse({'status': 'already1', 'message': 'Domain Added!'})
                except:
                     pass
             
                try:
                        er=pythonname.objects.get(domain=domain1)
                        return JsonResponse({'status': 'already', 'message': 'Domain Added!'})
                except:
                        pass   
                try:
                        fre=domain.objects.get(domain=domain1)
                except:
                        free=subdomainname.objects.get(subdomain=domain1).domain
                        fre=domain.objects.get(domain=free)
                try:
                    run_command(f'mkdir -p /home/{fre.dir}/{name}')
                    run_command(f'mkdir -p /home/{fre.dir}/{name}/static')
                except:
                     pass
                try:
                    run_command(f'bash /var/www/panel/createpython.sh {fre.dir} /home/{fre.dir}/{name} {name}')
                except:
                     pass
                try:
                    run_command(f'sudo chown -R {fre.dir}:{fre.dir} /home/{fre.dir}/{name}')
                except:
                     pass
                new_location_block = f"""
                location / {{
                    include uwsgi_params;
                    uwsgi_pass unix:/home/{fre.dir}/{name}/{name}.sock;
                }}

                   location /static/ {{
                   alias /home/{fre.dir}/{name}/static/;
                 
                }}
                """
                # Read the existing configuration
                with open(f'/etc/nginx/sites-enabled/{domain1}.conf', 'r') as file:
                    lines = file.readlines()

                updated_lines = []
                location_overwritten = False

                for i, line in enumerate(lines):
                    # If we find an existing `location /` block, overwrite it with `new_location_block`
                    if line.strip().startswith('location / {') and not location_overwritten:
                        updated_lines.append(new_location_block)
                        location_overwritten = True
                        # Skip to the end of this `location /` block
                        while i < len(lines) - 1 and lines[i].strip() != '}':
                            i += 1
                        continue

                    # Insert `new_location_block` right before `location ~ /\.ht {` if not already added
                    if line.strip() == 'location ~ /\.ht {' and not location_overwritten:
                        updated_lines.append(new_location_block)
                        location_overwritten = True

                    # Append the current line
                    updated_lines.append(line)

                # If no `location /` block was found or added, add `new_location_block` at the end
                if not location_overwritten:
                    updated_lines.append(new_location_block)

                # Write the modified configuration back to the file
                with open(f'/etc/nginx/sites-enabled/{domain1}.conf', 'w') as file:
                    file.writelines(updated_lines)
                fd=pythonname.objects.create(domain=domain1,name=name,main=fre.dir)
                run_command(f'sudo systemctl start {name} && sudo systemctl enable {name}')
                run_command('sudo systemctl reload nginx')
                run_command('sudo systemctl daemon-reload')
                import time 
                time.sleep(2)
                return JsonResponse({'status': 'success', 'message': 'Domain Added!'})
         return JsonResponse({'status': 'success', 'message': 'Domain Added!'})
     
@csrf_exempt
def delete_mern(request):
    if request.user.is_authenticated:
        
        if request.method=="POST":
            data = json.loads(request.body)  # Get the data from the request body
            domainname = data.get('domain').strip()
            name = data.get('name').strip()
            try:
                iwefj=domain.objects.get(domain=domainname).dir
            except:
                 lololol=subdomainname.objects.get(subdomain=domainname).domain
                 iwefj=domain.objects.get(domain=lololol).dir

            try:
                import shutil
                directory_path = f'/home/{iwefj}/{name}'
                shutil.rmtree(directory_path)
            except:
                 pass
  
            try:
                os.remove(f'/var/run/{name}.sock')
            except:
                 pass
            
            redirect_rule_start ='location / {'
            redirect_rule_end = '}'
            try:
             with open(f'/etc/nginx/sites-enabled/{domainname}.conf', 'r') as file:
                                config_data = file.readlines()
                                in_redirect_block = False
                                new_config_data = []
                                for line in config_data:
                                    if redirect_rule_start in line.strip():
                                        in_redirect_block = True 
                                    elif in_redirect_block and redirect_rule_end in line:
                                        in_redirect_block = False  
                                        continue  
                                    elif not in_redirect_block:
                                        new_config_data.append(line)
            
             with open(f'/etc/nginx/sites-enabled/{domainname}.conf', 'w') as file:
                                        file.writelines(new_config_data)
            except:
              pass

            redirect_rule_start ='location '+'/static/'
            redirect_rule_end = '}'
            try:
                with open(f'/etc/nginx/sites-enabled/{domainname}.conf', 'r') as file:
                                config_data = file.readlines()
                                in_redirect_block = False
                                new_config_data = []
                                for line in config_data:
                                    if redirect_rule_start in line:
                                        in_redirect_block = True 
                                    elif in_redirect_block and redirect_rule_end in line:
                                        in_redirect_block = False  
                                        continue  
                                    elif not in_redirect_block:
                                        new_config_data.append(line)
                with open(f'/etc/nginx/sites-enabled/{domainname}.conf', 'w') as file:
                                        file.writelines(new_config_data)
            except:
                 pass

            redirect_rule_start ='location '+'/api/'
            redirect_rule_end = '}'
            try:
                with open(f'/etc/nginx/sites-enabled/{domainname}.conf', 'r') as file:
                                config_data = file.readlines()
                                in_redirect_block = False
                                new_config_data = []
                                for line in config_data:
                                    if redirect_rule_start in line:
                                        in_redirect_block = True 
                                    elif in_redirect_block and redirect_rule_end in line:
                                        in_redirect_block = False  
                                        continue  
                                    elif not in_redirect_block:
                                        new_config_data.append(line)
                with open(f'/etc/nginx/sites-enabled/{domainname}.conf', 'w') as file:
                                        file.writelines(new_config_data)
            except:
                 pass
            
    
            try:
                 run_command(f"sed -i 's|root /home/{iwefj}/{name}/frontend/build;|root /home/{iwefj}/public_html;|' /etc/nginx/sites-enabled/{domainname}.conf")
            except:
                 pass


            df=mernname.objects.get(domain=domainname,name=name)
            df.delete()
           
            run_command('sudo systemctl reload nginx')
            run_command('sudo systemctl daemon-reload')
            import time
            time.sleep(2)
            return JsonResponse({'status': 'success', 'message': 'Already Exist'})
    return JsonResponse({'status': 'error', 'message': 'Invalid request.'})

@login_required(login_url='/')
@never_cache
def addmern(request):
   
     
     if request.user.is_authenticated:
         if request.method =="POST":
                data = json.loads(request.body)  # Get the data from the request body
                domain1 = data.get('domain') 
                name = data.get('name')  
                try:
                    ler=mernname.objects.get(name=name)
                    return JsonResponse({'status': 'already1', 'message': 'Domain Added!'})
                except:
                     pass
             
                try:
                        er=mernname.objects.get(domain=domain1)
                        return JsonResponse({'status': 'already', 'message': 'Domain Added!'})
                except:
                        pass   
                try:
                        fre=domain.objects.get(domain=domain1)
                except:
                        free=subdomainname.objects.get(subdomain=domain1).domain
                        fre=domain.objects.get(domain=free)
                
                to_get = mernname.objects.all()
                last_object = to_get.last()  # Efficiently fetches the last object
                if last_object:
                        pasport = str(int(last_object.port) + 1)
                else:
                    pasport = '3000'

               
                try:
                    run_command(f'bash /var/www/panel/mern.sh {name} /home/{fre.dir}/{name}/frontend /home/{fre.dir}/{name} {pasport}')
                except:
                     pass

                new_location_block = f"""
                location / {{
                     try_files $uri /index.html;  # This ensures React's routing works
                }}
                   location /static/ {{
                   alias /home/{fre.dir}/{name}/frontend/build/static/;
                }}
                location /api/ {{
        proxy_pass http://unix:/var/run/{name}.sock;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host \$host;
        proxy_cache_bypass \$http_upgrade;
    }}
                """
                # Read the existing configuration
                with open(f'/etc/nginx/sites-enabled/{domain1}.conf', 'r') as file:
                    lines = file.readlines()

                updated_lines = []
                location_overwritten = False

                for i, line in enumerate(lines):
                    # If we find an existing `location /` block, overwrite it with `new_location_block`
                    if line.strip().startswith('location / {') and not location_overwritten:
                        updated_lines.append(new_location_block)
                        location_overwritten = True
                        # Skip to the end of this `location /` block
                        while i < len(lines) - 1 and lines[i].strip() != '}':
                            i += 1
                        continue

                    # Insert `new_location_block` right before `location ~ /\.ht {` if not already added
                    if line.strip() == 'location ~ /\.ht {' and not location_overwritten:
                        updated_lines.append(new_location_block)
                        location_overwritten = True

                    # Append the current line
                    updated_lines.append(line)

                # If no `location /` block was found or added, add `new_location_block` at the end
                if not location_overwritten:
                    updated_lines.append(new_location_block)

                # Write the modified configuration back to the file
                with open(f'/etc/nginx/sites-enabled/{domain1}.conf', 'w') as file:
                    file.writelines(updated_lines)
                run_command(f"sed -i 's|root /home/{fre.dir}/public_html;|root /home/{fre.dir}/{name}/frontend/build;|' /etc/nginx/sites-enabled/{domain1}.conf")
                fd=mernname.objects.create(domain=domain1,name=name,main=fre.dir)
                run_command('sudo systemctl reload nginx')
                import time 
                time.sleep(2)
                return JsonResponse({'status': 'success', 'message': 'Domain Added!'})
         return JsonResponse({'status': 'success', 'message': 'Domain Added!'})


@csrf_exempt
def delete_python(request):
    if request.user.is_authenticated:
        
        if request.method=="POST":
            data = json.loads(request.body)  # Get the data from the request body
            domainname = data.get('domain').strip()
            name = data.get('name').strip()
            try:
                iwefj=domain.objects.get(domain=domainname).dir
            except:
                 lololol=subdomainname.objects.get(subdomain=domainname).domain
                 iwefj=domain.objects.get(domain=lololol).dir
            import shutil
            directory_path = f'/home/{iwefj}/{name}'
            shutil.rmtree(directory_path)
            os.remove(f'/etc/systemd/system/{name}.service')
            redirect_rule_start ='location / {'
            redirect_rule_end = '}'
            with open(f'/etc/nginx/sites-enabled/{domainname}.conf', 'r') as file:
                                config_data = file.readlines()
                                in_redirect_block = False
                                new_config_data = []
                                for line in config_data:
                                    if redirect_rule_start in line.strip():
                                        in_redirect_block = True 
                                    elif in_redirect_block and redirect_rule_end in line:
                                        in_redirect_block = False  
                                        continue  
                                    elif not in_redirect_block:
                                        new_config_data.append(line)
            
            with open(f'/etc/nginx/sites-enabled/{domainname}.conf', 'w') as file:
                                        file.writelines(new_config_data)

            redirect_rule_start ='location '+'/static/'
            redirect_rule_end = '}'
            with open(f'/etc/nginx/sites-enabled/{domainname}.conf', 'r') as file:
                                config_data = file.readlines()
                                in_redirect_block = False
                                new_config_data = []
                                for line in config_data:
                                    if redirect_rule_start in line:
                                        in_redirect_block = True 
                                    elif in_redirect_block and redirect_rule_end in line:
                                        in_redirect_block = False  
                                        continue  
                                    elif not in_redirect_block:
                                        new_config_data.append(line)

                                
                        
            with open(f'/etc/nginx/sites-enabled/{domainname}.conf', 'w') as file:
                                        file.writelines(new_config_data)
            df=pythonname.objects.get(domain=domainname,name=name)
            df.delete()
           
            run_command('sudo systemctl reload nginx')
            run_command('sudo systemctl daemon-reload')
            import time
            time.sleep(2)
            return JsonResponse({'status': 'success', 'message': 'Already Exist'})
    return JsonResponse({'status': 'error', 'message': 'Invalid request.'})

import pexpect
persistent_shell = pexpect.spawn('/bin/bash', encoding='utf-8')
persistent_shell.expect(r'[#$]') 
datahold=""

@never_cache
@csrf_exempt 
def terminalname(request):
    global datahold
    
    if request.user.is_superuser:
                    
                    current=request.session['name']
    else:
                    current=request.user
    homedir='/home/'+current+datahold
    
    if request.method == 'POST':
        command = request.POST.get('command')
        name = request.POST.get('name')
        dir = request.POST.get('dir')
        
        if command.startswith('pip') or command.startswith('python'):
             # Construct the command to run a Python module (like Django) in the virtual environment as a specific user
             if 'pip' not in command and 'django' in command or 'flask' in command:
                  command = f"/home/{current}/{name}/venv/bin/{command} /home/{current}/{name} "
             else:  
                command = f"/home/{current}/{name}/venv/bin/{command} "
           

            #f"sudo -u voidpanel /home/voidpanel/naku/venv/bin/pip install django"
        elif command.startswith('cd'):
              command=command.replace('cd','').strip()
              if f"/home/{current}" not in  command:
                    if command[0]!='/':
                          command="/"+command
                    datahold=command
                    command=homedir+command
                    homedir=command
                    command="cd "+command
              command = 'sudo -u ' + current + ' bash -c "cd '+homedir  + ' && ' + command + '"'
        else:
             command = 'sudo -u ' + current + ' bash -c "cd '+homedir  + ' && ' + command + '"'
        try:
            
                persistent_shell.sendline(command)
                persistent_shell.expect(r'[#$]') 
                output = persistent_shell.before.strip()
                output=output.replace("/var/www/panel","")
                # output=(output.splitlines())
                # output[0]="#"+homedir
                # output = "\n".join(output).strip()
        except Exception as e:
                output = f"Error: {str(e)}"
        return JsonResponse({"output":output})
    return JsonResponse({"output": "Invalid request"})

@never_cache
@csrf_exempt 
def terminalnamenpm(request):
    global datahold
    
    if request.user.is_superuser:
                    
                    current=request.session['name']
    else:
                    current=request.user
    homedir='/home/'+current+datahold
    
    if request.method == 'POST':
        command = request.POST.get('command')
        name = request.POST.get('name')
        dir = request.POST.get('dir')
        
 
        if command.startswith('cd'):
              command=command.replace('cd','').strip()
              if f"/home/{current}" not in  command:
                    if command[0]!='/':
                          command="/"+command
                    datahold=command
                    command=homedir+command
                    homedir=command
                    command="cd "+command
              command = 'sudo -u ' + current + ' bash -c "cd '+homedir  + ' && ' + command + '"'
        else:
             command = command 
        try:
            
                persistent_shell.sendline(command)
                persistent_shell.expect(r'[#$]') 
                output = persistent_shell.before.strip()
                output=output.replace("/var/www/panel","")
                # output=(output.splitlines())
                # output[0]="#"+homedir
                # output = "\n".join(output).strip()
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
                   directories = os.listdir('/home')
                   domainname=username
                   path="/home/"+domainname
                   os.mkdir(path)
                   os.mkdir(path+'/public_html')
                   run_command(f'cp -r /var/www/panel/voidpanel/*  {path}/public_html/')
                   run_command(f'sudo ln -s /etc/nginx/sites-available/{domain12}.conf  /etc/nginx/sites-enabled/')
                   os.mkdir(path+'/ssl')
                   os.mkdir(f'/var/mail/vhosts/{domain12}')
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
                   file_path = f"/etc/nginx/sites-available/{domain12}.conf"
                   root_dir = path+'/public_html'
                 
                   cert_path, key_path = generate_ssl_certificates(domain12, path+'/ssl',path+'/logs')
                   if cert_path and key_path:
                             create_nginx_ssl_conf(file_path, domain12, root_dir, cert_path, key_path)
                   else:
                    
                       with open('/var/logs.txt','a') as f:
                                f.write(f"Cannot Genrate open ssl for domain {domain12}\n")
                       import shutil
                       shutil.rmtree(path)
                       return False
                   key_dir = f'/etc/opendkim/keys/{domain12}'
                   zone_file_path = f'/etc/bind/db.{domain12}'
                   private_key_path, public_key_path = generate_dkim_keys(domain12, key_dir)
                   if private_key_path and public_key_path:
                      create_bind_records(domain12, key_dir, zone_file_path)
                      configure_opendkim(domain12, key_dir)
                    
                      with open('/var/logs.txt','a') as f:
                                f.write(f" Genareted Dkmi Record for domain {domain12}\n")
                   else:
                       with open('/var/logs.txt','a') as f:
                                f.write(f"Cannot Genarete Dkmi Record for domain {domain12}\n")
                       import shutil
                       shutil.rmtree(path)
                       return False
                   domain.objects.create(domain=domain12,email=email,dir=domainname,userdomain=True)
                   user.objects.create(domain=domain12,email=email,username=domainname,hosting_package=package12)
                   User.objects.create_user(username=domainname,email=email,password=password)
                   try:
                        
                        run_command(f'sudo useradd -m -s /usr/sbin/nologin {domainname} && sudo passwd -u {domainname} && echo "{domainname}:{password}" | sudo chpasswd')
                   except:
                        pass
                   run_command(f'sudo chown {domainname}:{domainname}  /home/{domainname}')
                   try:
                        run_command(f'sudo mount -o remount /')
                   except:
                        pass
                   try:
                        run_command(f'sudo setquota -u {domainname} {sto} {sto} 0 0 /')
                   except:
                        pass
                   
                   run_command("sudo systemctl restart opendkim")
                   run_command("sudo systemctl restart bind9")
                   run_command("sudo systemctl restart postfix")
                   run_command("sudo systemctl reload nginx")
                   return "rohan"
                   
                   
            
         
