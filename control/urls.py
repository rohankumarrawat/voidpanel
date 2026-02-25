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

    path('',views.index),
    path('eadns/', views.eadns, name='eadns'),
    path('adddnsrecord/', views.adddnsrecord, name='adddnsrecord'),
     path('createpython/<str:data>', views.createpython, name='createpython'),
     path('deletedns/', views.deletedns, name='deletedns'),
      path('python/<str:data>', views.setpython, name='python'),
     path('runssl/<str:data>/', views.runssl, name='runssl'),
     path('cron/<str:data>', views.cronn, name='cron'),
     path('deletecron/<str:data>/', views.deletecron, name='deletecron'),
     path('backup/<str:data>/', views.backup, name='backup'),
     path('backupdata/', views.backupdata, name='backupdata'),
     path('filemanager/', views.filemanager, name='filemanager'),
     path('upload/<path:file_path>/', views.upload_files),
     path('dbconnect/<str:data>/', views.dbconnect, name='dbconnect'),
     path('listemail/<str:data>/', views.listemail),
     path('phpini/<str:data>/', views.phpini, name='phpini'),
     path('subdomain/<str:data>', views.subdomain, name='cron'),
     path('addredirect/<str:data>/', views.addredirect, name='addredirect'),
     path('ftp/<str:data>/', views.ftp122, name='ftp'),
     path('ftpadd/', views.ftpadd, name='ftpadd'),
    path('terminal/',views.domainterminal),
    path('terminalname/', views.terminalname, name='terminalname'),
   

     path('chstorageftp/', views.chstorageftp, name='chstorageftp'),
     path('chpasswordftp/', views.chpasswordftp, name='chpasswordftp'),
     path('deleteftp/<str:data>/', views.deleteftp, name='ftp'),
     path('subdomain/<str:data>', views.subdomain, name='subdomain'),
      path('runsslfordomain/', views.runsslfordoamin, name='runsslfordoamin'),
          path('runsslfordomain1/', views.runsslfordoamin1, name='runsslfordoamin1'),
          path('subdomain/<str:data>', views.subdomain, name='subdomain'),
    
 

    
]
