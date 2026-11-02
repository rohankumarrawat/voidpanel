from django.urls import path
from . import views

urlpatterns = [
    path('send/', views.SendEmailAPIView.as_view(), name='api_send_email'),
    path('domains/', views.DomainListCreateAPIView.as_view(), name='api_domains'),
    path('mailboxes/', views.MailboxListCreateAPIView.as_view(), name='api_mailboxes'),
    path('ai/chat/', views.AiChatProxyAPIView.as_view(), name='api_ai_chat'),
]
