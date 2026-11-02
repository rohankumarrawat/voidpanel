from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard_view, name='superadmin_dashboard'),
    path('create-mailbox/', views.create_mailbox_ajax, name='superadmin_create_mailbox'),
    path('sync-live-server/', views.sync_live_server, name='superadmin_sync_live_server'),
    path('export-json/', views.export_database_json, name='superadmin_export_json'),
    path('update-whatsapp-settings/', views.update_whatsapp_settings, name='superadmin_update_whatsapp_settings'),
    path('api/test-whatsapp/', views.test_whatsapp_api, name='superadmin_test_whatsapp_api'),
    path('update-email-sending-limit/', views.update_email_sending_limit, name='superadmin_update_email_sending_limit'),
    path('update-global-sending-limit/', views.update_global_sending_limit, name='superadmin_update_global_sending_limit'),
    path('api/hf-keys/', views.get_hf_keys_ajax, name='superadmin_get_hf_keys'),
    path('api/hf-keys/add/', views.add_hf_key_ajax, name='superadmin_add_hf_key'),
    path('api/hf-keys/delete/', views.delete_hf_key_ajax, name='superadmin_delete_hf_key'),
    path('api/hf-keys/toggle/', views.toggle_hf_key_ajax, name='superadmin_toggle_hf_key'),
    path('api/hf-keys/test/', views.test_hf_key_ajax, name='superadmin_test_hf_key'),
    
    # AI Access & Auto-Upgrade Management
    path('api/ai-settings/update-auto-approve/', views.update_ai_auto_approve_setting, name='superadmin_update_ai_auto_approve'),
    path('api/ai-access/update-setting/', views.update_ai_auto_approve_setting, name='superadmin_update_ai_setting'),
    path('api/ai-access/list/', views.list_ai_access_api, name='superadmin_list_ai_access'),
    path('api/ai-access/approve-domain/', views.approve_domain_ai_api, name='superadmin_approve_domain_ai'),
    path('api/ai-access/approve-user/', views.approve_user_ai_api, name='superadmin_approve_user_ai'),
    path('api/ai-access/handle-request/', views.handle_upgrade_request_api, name='superadmin_handle_upgrade_request'),
    path('api/ai-access/handle-upgrade-request/', views.handle_upgrade_request_api, name='superadmin_handle_upgrade_request_alias'),
]
