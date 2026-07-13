from django.urls import path
from . import views

urlpatterns = [
    path('start/', views.chat_start, name='chat_start'),
    path('<int:session_id>/send/', views.chat_send, name='chat_send'),
    path('<int:session_id>/poll/', views.chat_poll, name='chat_poll'),
    path('<int:session_id>/close/', views.chat_close, name='chat_close'),
    path('<int:session_id>/no-agent/', views.chat_no_agent, name='chat_no_agent'),
    path('admin/notify/', views.admin_notify_poll, name='admin_notify_poll'),
]