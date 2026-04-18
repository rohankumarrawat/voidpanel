"""
URL configuration for voidpanel project.

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
from . import views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.index),
    path('docs/', views.docs),
    path('blog/', views.blog),
    path('blogs/', views.blogs),
    path('addssl/', views.ssl),
    path('cloud-computing/', views.blog2),
    path('voidpanel-info/', views.voidpanelinfo),
    path('alternative-of-cpanel/', views.blog3),
    path('aboutus/', views.aboutus),
    path('db/', views.db),
    path('positive/', views.positive, name='positive'),
    path('negative/', views.negative, name='negative'),
    path('ai/', include('chatting.urls')),
    path('overview/', views.overview),
    path('chpass/', views.chpass),
    path('addweb/', views.addweb),
    path('notifications/', views.notifications),
    path('latest_messages/', views.latest_messages),
    path('version_name/', views.update),
    path('admindocs/', views.admindocs),
    path('clientdocs/', views.clientdocs),
    path('api/increment/', views.increment_number, name='increment-number'),
    path('login/', views.loginn),
    path('logout/', views.logout_view),
    path('register/', views.register),
    path('portal/', views.portal),
    path('super-admin/', views.super_admin_portal),
    path('blog1/', views.blog1),
    path('addemail/', views.addemail),
    path('whmcs/', views.whmcs),
    path('whmcs/module/', views.whmcs_module),
]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL,
                          document_root=settings.MEDIA_ROOT)
