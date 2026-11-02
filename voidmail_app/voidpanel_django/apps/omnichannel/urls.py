from django.urls import path
from . import views

urlpatterns = [
    path('webhook/whatsapp/', views.whatsapp_webhook, name='whatsapp_webhook'),
    path('api/vip-alert/', views.trigger_vip_alert, name='trigger_vip_alert'),
]
