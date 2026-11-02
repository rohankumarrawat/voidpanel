from django.urls import path
from . import views

urlpatterns = [
    path('dns-records/', views.get_dns_records, name='get_dns_records'),
    path('add/', views.addemailaccount, name='add_email_account'),
    path('check-send-limit/', views.check_send_limit, name='check_send_limit'),
    path('send-mail/', views.send_email_workspace, name='send_email_workspace'),
    path('save-draft/', views.save_draft_workspace, name='save_draft_workspace'),
    path('delete-draft/', views.delete_draft_workspace, name='delete_draft_workspace'),
    path('delete-email/', views.delete_email_workspace, name='delete_email_workspace'),
    path('empty-trash/', views.empty_trash_api, name='empty_trash_api'),
    path('mark-read/', views.mark_email_read_api, name='mark_email_read_api'),
    path('api/inbox-emails/', views.get_inbox_emails_api, name='get_inbox_emails_api'),
    
    # In-Workspace Multi-Account Manager
    path('api/accounts/list/', views.list_linked_accounts_api, name='mail_accounts_list'),
    path('api/accounts/test-connection/', views.test_account_connection_api, name='mail_accounts_test_connection'),
    path('api/accounts/add/', views.add_linked_account_api, name='mail_accounts_add'),
    path('api/accounts/switch/', views.switch_active_account_api, name='mail_accounts_switch'),
    path('api/accounts/remove/', views.remove_linked_account_api, name='mail_accounts_remove'),

    # Email Aliases Manager
    path('api/aliases/list/', views.list_aliases_api, name='mail_aliases_list'),
    path('api/aliases/create/', views.create_alias_api, name='mail_aliases_create'),
    path('api/aliases/delete/', views.delete_alias_api, name='mail_aliases_delete'),

    # Email Attachment Viewer & Downloader
    path('api/attachment/', views.download_attachment_api, name='mail_attachment_api'),
    path('api/attachment/download/', views.download_attachment_api, name='mail_attachment_download_api'),

    # 1. Unanswered Emails (AI Tracker)
    path('api/unanswered/', views.get_unanswered_emails_api, name='get_unanswered_emails_api'),
    path('api/unanswered/mark-answered/', views.mark_email_answered_api, name='mark_email_answered_api'),

    # 1.5. WhatsApp VIP Domain & Email Alerts
    path('api/whatsapp/rules/', views.get_whatsapp_alert_rules_api, name='whatsapp_alert_rules_api'),
    path('api/whatsapp/rules/add/', views.add_whatsapp_alert_rule_api, name='whatsapp_alert_rule_add_api'),
    path('api/whatsapp/rules/delete/', views.delete_whatsapp_alert_rule_api, name='whatsapp_alert_rule_delete_api'),
    path('api/whatsapp/rules/toggle/', views.toggle_whatsapp_alert_rule_api, name='whatsapp_alert_rule_toggle_api'),
    path('api/whatsapp/test-alert/', views.send_test_whatsapp_alert_api, name='whatsapp_send_test_alert_api'),

    # 2. Mini CRM
    path('api/crm/overview/', views.crm_overview_api, name='crm_overview_api'),
    path('api/crm/contact/save/', views.crm_contact_save_api, name='crm_contact_save_api'),
    path('api/crm/deal/save/', views.crm_deal_save_api, name='crm_deal_save_api'),
    path('api/crm/deal/move-stage/', views.crm_deal_move_stage_api, name='crm_deal_move_stage_api'),
    path('api/crm/extract-from-email/', views.crm_extract_from_email_api, name='crm_extract_from_email_api'),

    # 3. Calendar & Scheduling
    path('api/calendar/events/', views.calendar_events_api, name='calendar_events_api'),
    path('api/calendar/save/', views.calendar_event_save_api, name='calendar_event_save_api'),
    path('api/calendar/delete/', views.calendar_event_delete_api, name='calendar_event_delete_api'),
    path('api/calendar/delete/<int:event_id>/', views.calendar_event_delete_api, name='calendar_event_delete_by_id_api'),
    path('api/calendar/schedule-from-email/', views.calendar_schedule_from_email_api, name='calendar_schedule_from_email_api'),

    # 4. Security Center & 2FA
    path('api/security/overview/', views.security_overview_api, name='security_overview_api'),
    path('api/security/session/revoke/', views.security_session_revoke_api, name='security_session_revoke_api'),
    path('api/security/2fa/status/', views.get_2fa_security_status_api, name='api_2fa_security_status'),
    path('api/security/2fa/toggle/', views.toggle_2fa_api, name='api_2fa_toggle'),
    path('api/security/2fa/add-key/', views.add_security_key_api, name='api_2fa_add_key'),
    path('api/security/2fa/delete-key/', views.delete_security_key_api, name='api_2fa_delete_key'),

    # 5. Business Dashboard
    path('api/dashboard/overview/', views.dashboard_overview_api, name='dashboard_overview_api'),

    # 6. Layer 11: AI Stylometric Persona & Impersonation Shield
    path('api/security/stylometry-scan/', views.stylometry_scan_api, name='stylometry_scan_api'),
    path('api/security/stylometry-train/', views.stylometry_train_api, name='stylometry_train_api'),
]

