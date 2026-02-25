"""
URL configuration for panel project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path,include
from django.conf import settings
from django.conf.urls.static import static
from . import views
from django.contrib.auth.decorators import login_required

  
urlpatterns = [

  path('admin/', admin.site.urls),
    path('',views.login_user),
       path('logout/', views.logoutt, name='logout'),
    path('panel/',views.panel),
    path('control/',include('control.urls')),
    path('ai/',include('chatting.urls')),
    path('terminal/',views.terminal),
    # path('domainterminal/',views.domainterminal),
     path('quicksetup/', views.quicksetup, name='quicksetup'),
     path('updatesetup/', views.updatesetup, name='updatesetup'),
     path('addwebsite/', views.addwebsite, name='addwebsite'),
   
      path('viewwebsite/', views.viewwebsite, name='viewwebsite'),
       path('eadns/', views.eadns, name='eadns'),
     path('addweb/', views.addweb, name='addweb'),
     path('server-load/', views.get_server_load, name='server_load'),
     path('webshell/', views.handle_user_event, name='handle_user_event'),
        path('deletedns/', views.deletedns, name='deletedns'),
     path('checkstatus/', views.checkstatus, name='checktsatus'),
     path('activeterminal/', views.activeterminal, name='activeterminal'),
    path('filemanager/', views.filemanager, name='filemanager'),
     path('files/<str:data>/', views.files, name='files'),
     path('listwebsite/', views.listwebsite, name='listwebsite'),
     path('listusers/', views.listusers, name='listusers'),
     path('listdns/', views.listdns, name='listdns'),
    path('adddnsrecord/', views.adddnsrecord, name='adddnsrecord'),
    path('addemailaccount/', views.addemailaccount, name='addemailaccount'),
    path('loginuser/', views.loginuser, name='loginuser'),

    path('download/', views.download_file, name='download_file'),
    path('deletefile/<path:file_path>/', views.delete_file, name='download_file'),
    path('editor_view/<path:file_path>/', views.editor_view, name='editor'),
    path('save/', views.save_file, name='save_file'),
     path('updatepanel/', views.updatepanel, name='updatepanel'),
     path('upload/<path:file_path>/', views.upload_files),
     path('listemail/<str:data>/', views.listemail),
     path('emailmarketing/<str:data>/', views.emailmarketing),
     path('upload/', views.upload_file, name='upload_file'),
     path('create-file/', views.create_file, name='create_file'),
     path('create-folder/', views.create_folder, name='create_folder'),
     path('copydata/', views.copydata, name='copydata'),
     path('movedata/', views.movedata, name='movedata'),
      path('extractdata/', views.extractdata, name='extractdata'),
      path('compressdata/', views.compressdata, name='compressdata'),
        path('deletedata/', views.deletedata, name='deletedata'),
          path('ddeletedata/', views.ddeletedata, name='ddeletedata'),
    path('renamedata/', views.renamedata, name='renamedata'),
    path('permissiondata/', views.permissiondata, name='permissiondata'),
      path('changeemailpassword/', views.changeemailpassword, name='changeemailpassword'),
      path('adddatabase/', views.adddatabase, name='adddatabase'),
      path('addpython/', views.addpython, name='addpython'),
      path('addmern/', views.addmern, name='addmern'),
       path('adddatabaseuser/', views.adddatabaseuser, name='adddatabaseuser'),
       path('dbconnect/<str:data>/', views.dbconnect, name='dbconnect'),
       path('dbreomve/<str:data>/<str:database>/', views.dbreomve, name='dbreomve'),
       path('dbuserremove/<str:data>/<str:database>/', views.dbuserremove, name='dbreomve'),
        path('changepasswordforuser/', views.changepasswordforuser, name='changepasswordforuser'),
        path('addpermissiontouser/', views.addpermissiontouser, name='addpermissiontouser'),
        path('cron/<str:data>', views.cronn, name='cron'),
        path('subdomain/<str:data>', views.subdomain, name='subdomain'),

        path('python/<str:data>', views.setpython, name='python'),
        path('mern/<str:data>', views.setmern, name='mern'),
        path('createpython/<str:data>', views.createpython, name='createpython'),
          path('createmern/<str:data>', views.createmern, name='createmern'),
         path('createemailmarketing/<str:data>', views.createemailmarketing, name='createemailmarketing'),
        path('deletecron/<str:data>/', views.deletecron, name='deletecron'),
         path('deletesubdomain/<str:data>/', views.deletesubdomain, name='deletesubdomain'),
         path('subdomainprocess/', views.subdomainprocess, name='subdomainprocess'),
         path('runsslfordomain/', views.runsslfordoamin, name='runsslfordoamin'),
          path('runsslfordomain1/', views.runsslfordoamin1, name='runsslfordoamin1'),
          path('runssl/<str:data>/', views.runssl, name='runssl'),
          path('phpini/<str:data>/', views.phpini, name='phpini'),
           path('changephpversion/', views.changephpversion, name='changephpversion'),
           path('addredirect/<str:data>/', views.addredirect, name='addredirect'),
           path('addredirectionnn/', views.addredirectionnn, name='addredirectionnn'),
           path('delredirectionnn/', views.delredirectionnn, name='delredirectionnn'),
           path('terminate/<str:data>/', views.terminate, name='terminate'),
           path('suspend/<str:data>/', views.suspend, name='suspend'),
           path('unsuspend/<str:data>/', views.unsuspend, name='unsuspend'),
           path('backup/<str:data>/', views.backup, name='backup'),
           path('backupdata/', views.backupdata, name='backupdata'),
           path('package/', views.packagewizard, name='package'),
           path('update/', views.update, name='update'),
           path('maincron/', views.maincron, name='maincron'),
           path('chpass/', views.chpass, name='chpass'),
            path('download_zip_backup/<str:filename>/<str:user>/', views.download_zip_backup, name='download_zip_backup'),
             path('runsslforall/', views.runsslforall, name='runsslforall'),
             path('runsslforall1/', views.runsslforall1, name='runsslforall1'),
             path('runsslall/', views.runsslall, name='runsslall'),
              path('hostname/', views.hostname, name='hostname'),
              path('installphpversion/', views.installphpversion, name='installphpversion'),

               path('cpbrute/', views.cpbrute, name='cpbrute'),
               path('fulldbwizard/', views.fulldbwizard, name='fulldbwizard'),
               path('allemailwizard/', views.allemailwizard, name='allemailwizard'),
                path('phpsetting/', views.phpsetting, name='phpsetting'),
                path('allowip/', views.allowip, name='allowip'),
                path('denyip/', views.denyip, name='denyip'),
                path('ignoreip/', views.ignoreip, name='ignoreip'),
                 path('unblockip/', views.unblockip, name='unblockip'),
                 path('blockip/', views.blockip, name='blockip'),


                 path('cpbruteforce/', views.cpbruteforce, name='cpbruteforce'),
               path('deleteemail/<str:data>/', views.deleteemail, name='deleteer'),
               path('deleteemai/<str:data>/', views.deleteemai, name='deletere'),
           
               path('ftpserver/', views.ftpserver, name='ftpserver'),
               path('ftp/', views.ftp12, name='ftp'),
               path('adduser/', views.adduser, name='adduser'),
               path('addusermain/', views.addusermain, name='addusermain'),
               path('installphpextention/', views.installphpextention, name='installphpextention'),

               path('convertwebsite/', views.convertwebsite, name='convertwebsite'),
               path('delpackage/<str:data>/', views.delpackage, name='delpackage'),
               path('cwtd/', views.cwtd, name='cwtd'),
               path('serverstatus/', views.serverstatus, name='serverstatus'),
               path('restart_now/', views.restart_now, name='restart_now'),
               path('start_now/', views.start_now, name='start_now'),
               path('start_now_python/', views.start_now_python, name='start_now_python'),
               path('restart_now_python/', views.restart_now_python, name='restart_now_python'),
                  path('stop_now_python/', views.stop_now_python, name='stop_now_python'),
               path('stop_now/', views.stop_now, name='stop_now'),
               path('delete_python/', views.delete_python, name='delete_python'),
               path('delete_mern/', views.delete_mern, name='delete_mern'),
               path('restart/', views.restart, name='restart'),
               path('shutdown/', views.shutdown, name='shutdown'),
               path('restartservice/', views.restartservice, name='restartservice'),
               path('chpassuser/', views.chpassuser, name='chpassuser'),
     path('chpackageuser/', views.chpackageuser, name='chpackageuser'),
       path('terminalname/', views.terminalname, name='terminalnamename'),
       path('terminalnamenpm/', views.terminalnamenpm, name='terminalnamenamenpm'),


       path('api/auth/', views.authenticate_user, name='authenticate_user'),
    path('api/create-account/', views.create_account, name='create_account'),
    path('api/list-packages/', views.list_packages, name='list_packages'),
    path('api/suspend-account/', views.suspend_account, name='suspend_account'),
    path('api/unsuspend-account/', views.unsuspend_account, name='unsuspend_account'),
    path('api/terminate-account/', views.terminate_account, name='terminate_account'),
       

    

    
]
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)