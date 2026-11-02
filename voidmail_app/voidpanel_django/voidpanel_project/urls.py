"""
Root URL Configuration for VoidPanel & VoidOnyx Workspace.
"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # Core Public Views
    path('', include('apps.core.urls')),
    
    # Direct VoidPanel Compatibility Endpoint
    path('addemailaccount/', include('apps.mail_engine.urls')),
    
    # Mail Engine & DNS
    path('mail/', include('apps.mail_engine.urls')),
    
    # Superadmin Workspace Portal
    path('superadmin/', include('apps.superadmin.urls')),
    
    # Sales & Power-User Tools (Tracking, Thread Sharing, Snippets)
    path('', include('apps.sales_tools.urls')),
    
    # AI Engine (Smart Reply, Summaries, Tasks)
    path('', include('apps.ai_engine.urls')),
    
    # VoidDrive File Storage
    path('drive/', include('apps.drive.urls')),
    
    # Omnichannel (WhatsApp Webhook, SMS Alerts)
    path('', include('apps.omnichannel.urls')),
    
    # Security & Privacy Shield (Burn-on-read, VoidMask)
    path('', include('apps.security_shield.urls')),
    
    # Collaboration & Productivity (VoidMeet, Booking, VoidSign)
    path('', include('apps.collaboration.urls')),
    
    # Developer REST API
    path('api/v1/', include('apps.api.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
