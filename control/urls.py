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
    path('editdnsrecord/', views.editdnsrecord, name='editdnsrecord'),
     path('createpython/<str:data>', views.createpython, name='createpython'),
     path('deletedns/', views.deletedns, name='deletedns'),
      path('python/<str:data>', views.setpython, name='python'),
      path('mern/<str:data>', views.setmern, name='mern'),
      path('createmern/<str:data>', views.createmern, name='createmern'),
      path('analytics/<str:data>/', views.analytics_control, name='analytics_control'),
     path('runssl/<str:data>/', views.runssl, name='runssl'),
     path('cron/<str:data>', views.cronn, name='cron'),
     path('deletecron/<str:data>/', views.deletecron, name='deletecron'),
     path('backup/<str:data>/', views.backup, name='backup'),
     path('backupdata/', views.backupdata, name='backupdata'),
     path('backup_status/<str:data>/', views.backup_status, name='backup_status'),
     path('delete_backup/', views.delete_backup, name='delete_backup'),
     path('download_backup/<str:filename>/', views.download_backup, name='download_backup'),
     path('filemanager/', views.filemanager, name='filemanager'),
     path('upload/<path:file_path>/', views.upload_files),
     path('dbconnect/<str:data>/', views.dbconnect, name='dbconnect'),
     path('fulldbwizard/<str:data>/', views.fulldbwizard, name='fulldbwizard'),
     path('pma_login/<str:data>/', views.pma_login, name='pma_login'),
     path('listemail/<str:data>/', views.listemail),
     path('roundcube_login/<str:email>/', views.roundcube_login, name='roundcube_login'),
     path('email_analysis/<str:data>/', views.email_analysis, name='email_analysis'),
     path('api/email/delivery-report/', views.api_email_delivery_report, name='api_email_delivery_report'),
     path('email_delivery_report/<str:email>/', views.email_delivery_report, name='email_delivery_report'),
     path('phpini/<str:data>/', views.phpini, name='phpini'),
     path('subdomain/<str:data>', views.subdomain, name='cron'),
     path('addredirect/<str:data>/', views.addredirect, name='addredirect'),
     path('ftp/<str:data>/', views.ftp122, name='ftp'),
     path('ftpadd/', views.ftpadd, name='ftpadd'),
    path('terminal/',views.domainterminal),
    path('activitylog/<str:data>/', views.activitylog_control, name='activitylog_control'),
     path('deleteemail/<str:data>/', views.deleteemail_control, name='ctrl_deleteemail'),
     path('deleteemai/<str:data>/', views.deleteemail_control, name='ctrl_deleteemai'),
   

     path('chstorageftp/', views.chstorageftp, name='chstorageftp'),
     path('chpasswordftp/', views.chpasswordftp, name='chpasswordftp'),
     path('deleteftp/<str:data>/', views.deleteftp, name='ftp'),
     path('subdomain/<str:data>', views.subdomain, name='subdomain'),
     path('api/site-config/get/', views.user_api_get_site_config, name='user_api_get_site_config'),
     path('api/site-config/save/', views.user_api_save_site_config, name='user_api_save_site_config'),
      path('runsslfordomain/', views.runsslfordoamin, name='runsslfordoamin'),
    path('runsslfordomain1/', views.runsslfordoamin1, name='runsslfordoamin1'),
          path('subdomain/<str:data>', views.subdomain, name='subdomain'),

    # Cloud Backup Sync
    path('cloud-backup-config/<str:data>/', views.cloud_backup_config, name='cloud_backup_config'),
    path('cloud-backup-sync/<str:data>/<str:filename>/', views.cloud_backup_sync, name='cloud_backup_sync'),
    path('cloud-backup-auto/<str:data>/', views.cloud_backup_auto, name='cloud_backup_auto'),

    # One-Click App Installer
    path('app-installer/install/', views.app_installer_install, name='app_installer_install'),
    path('app-installer/delete/<int:record_id>/', views.app_installer_delete, name='app_installer_delete'),
    path('app-installer/status/<int:record_id>/', views.app_installer_status, name='app_installer_status'),
    path('app-installer/settings/<int:record_id>/', views.app_installer_settings, name='app_installer_settings'),
    path('app-installer/change-password/<int:record_id>/', views.app_installer_change_password, name='app_installer_change_password'),
    path('app-installer/<str:domain>/', views.app_installer, name='app_installer'),

    # ── Social Media Management ──────────────────────────────────────
    path('social/<str:domain>/',                              views.social_home,           name='social_home'),
    path('social/<str:domain>/connect/<str:platform>/',       views.social_connect,        name='social_connect'),
    path('social/callback/<str:platform>/',                   views.social_callback,       name='social_callback'),
    path('social/<str:domain>/disconnect/<int:account_id>/',  views.social_disconnect,     name='social_disconnect'),
    path('social/<str:domain>/post/create/',                  views.social_post_create,    name='social_post_create'),
    path('social/<str:domain>/post/<int:post_id>/delete/',    views.social_post_delete,    name='social_post_delete'),
    path('social/<str:domain>/post/<int:post_id>/reschedule/',views.social_post_reschedule,name='social_post_reschedule'),
    path('social/<str:domain>/analytics/json/',               views.social_analytics_json, name='social_analytics_json'),
    path('social/<str:domain>/inbox/',                        views.social_inbox,          name='social_inbox'),
    path('social/<str:domain>/inbox/reply/',                  views.social_inbox_reply,    name='social_inbox_reply'),
    path('social/<str:domain>/media/upload/',                 views.social_media_upload,   name='social_media_upload'),
    path('social/<str:domain>/ai/caption/',                   views.social_ai_caption,     name='social_ai_caption'),
    path('social/<str:domain>/export/',                       views.social_export_csv,     name='social_export_csv'),
    path('social/<str:domain>/sync-stats/<int:account_id>/', views.social_sync_stats,     name='social_sync_stats'),
    # Social Media Standalone Portal (new tab)
    path('social-portal/<str:domain>/',                    views.social_portal_home,       name='social_portal_home'),
    path('social-portal/<str:domain>/api-config/save/',    views.social_api_config_save,   name='social_api_config_save'),
    path('social-portal/<str:domain>/api-config/get/',     views.social_api_config_get,    name='social_api_config_get'),


    # ── Marketing Hub ──────────────────────────────────────────────────────────
    path('marketing/<str:domain>/',                views.marketing_home,          name='marketing_home'),
    path('marketing/<str:domain>/email/send/',     views.marketing_email_send,    name='marketing_email_send'),
    path('marketing/<str:domain>/email/smtp/save/', views.marketing_custom_smtp_save, name='marketing_custom_smtp_save'),
    path('marketing/<str:domain>/campaign/save/',  views.marketing_campaign_save, name='marketing_campaign_save'),
    path('marketing/<str:domain>/campaign/<int:campaign_id>/', views.marketing_campaign_detail, name='marketing_campaign_detail'),
    path('marketing/<str:domain>/campaign/<int:campaign_id>/delete/', views.marketing_campaign_delete, name='marketing_campaign_delete'),
    path('marketing/<str:domain>/campaign/<int:campaign_id>/toggle-status/', views.marketing_campaign_status_toggle, name='marketing_campaign_status_toggle'),
    path('marketing/<str:domain>/track/<int:recipient_id>/open.png', views.marketing_email_track_open, name='marketing_email_track_open'),
    path('marketing/<str:domain>/sms/gateway/save/', views.marketing_sms_gateway_save, name='marketing_sms_gateway_save'),
    path('marketing/<str:domain>/sms/gateway/test/', views.marketing_sms_gateway_test, name='marketing_sms_gateway_test'),
    path('marketing/<str:domain>/settings/whatsapp/save/', views.marketing_whatsapp_config_save, name='marketing_whatsapp_config_save'),
    path('marketing/<str:domain>/settings/whatsapp-web/status/', views.marketing_whatsapp_web_status, name='marketing_whatsapp_web_status'),
    path('marketing/<str:domain>/settings/whatsapp-web/qr-auth/', views.marketing_whatsapp_web_qr_auth, name='marketing_whatsapp_web_qr_auth'),
    path('marketing/<str:domain>/settings/whatsapp-web/simulate-connect/', views.marketing_whatsapp_web_simulate_connect, name='marketing_whatsapp_web_simulate_connect'),
    path('marketing/<str:domain>/settings/whatsapp-web/disconnect/', views.marketing_whatsapp_web_disconnect, name='marketing_whatsapp_web_disconnect'),
    # ── Native self-hosted WhatsApp Web (Baileys microservice on localhost:3001) ──
    path('marketing/<str:domain>/settings/wa-native/qr/', views.wa_native_qr, name='wa_native_qr'),
    path('marketing/<str:domain>/settings/wa-native/status/', views.wa_native_status, name='wa_native_status'),
    path('marketing/<str:domain>/settings/wa-native/logout/', views.wa_native_logout, name='wa_native_logout'),
    path('marketing/<str:domain>/settings/wa-native/install-check/', views.wa_native_service_install_check, name='wa_native_service_install_check'),
    path('marketing/<str:domain>/wa-native/send/', views.wa_native_send, name='wa_native_send'),
    path('marketing/<str:domain>/wa-native/send-media/', views.wa_native_send_media, name='wa_native_send_media'),
    path('marketing/<str:domain>/wa-native/broadcast/', views.wa_native_broadcast, name='wa_native_broadcast'),
    path('marketing/<str:domain>/wa-native/incoming/', views.wa_native_incoming, name='wa_native_incoming'),
    # ── WhatsApp persistent chat + campaign API ───────────────────────────────
    path('marketing/<str:domain>/wa/conversations/', views.wa_conversations_list, name='wa_conversations_list'),
    path('marketing/<str:domain>/wa/messages/<str:phone>/', views.wa_messages_load, name='wa_messages_load'),
    path('marketing/<str:domain>/wa/message/save/', views.wa_message_save, name='wa_message_save'),
    path('marketing/<str:domain>/wa/message/mark-read/', views.wa_message_mark_read, name='wa_message_mark_read'),
    path('marketing/<str:domain>/wa/stats/', views.wa_dashboard_stats, name='wa_dashboard_stats'),
    path('marketing/<str:domain>/wa/campaigns/', views.wa_campaigns_list, name='wa_campaigns_list'),
    path('marketing/<str:domain>/wa/campaign/create/', views.wa_campaign_create, name='wa_campaign_create'),
    path('marketing/<str:domain>/wa/campaign/<int:campaign_id>/send/', views.wa_campaign_send, name='wa_campaign_send'),
    path('marketing/<str:domain>/wa/media/upload/', views.wa_media_upload, name='wa_media_upload'),
    path('marketing/<str:domain>/sms/send/', views.marketing_sms_send, name='marketing_sms_send'),
    path('marketing/<str:domain>/ai/copy/',        views.marketing_ai_copy,       name='marketing_ai_copy'),
    path('marketing/<str:domain>/leads/',          views.marketing_leads,         name='marketing_leads'),
    path('marketing/<str:domain>/ab-test/save/',   views.marketing_ab_save,       name='marketing_ab_save'),
    path('marketing/<str:domain>/templates/list/', views.marketing_templates_list, name='marketing_templates_list'),
    path('marketing/<str:domain>/template/save/', views.marketing_template_save, name='marketing_template_save'),
    path('marketing/<str:domain>/template/<int:template_id>/delete/', views.marketing_template_delete, name='marketing_template_delete'),

    # ── Marketing Automation Workflows API ──────────────────────────────────────
    path('marketing/<str:domain>/automation/workflows/', views.marketing_workflows_list, name='marketing_workflows_list'),
    path('marketing/<str:domain>/automation/workflows/create/', views.marketing_workflow_create, name='marketing_workflow_create'),
    path('marketing/<str:domain>/automation/workflows/<int:workflow_id>/toggle/', views.marketing_workflow_toggle, name='marketing_workflow_toggle'),
    path('marketing/<str:domain>/automation/workflows/<int:workflow_id>/delete/', views.marketing_workflow_delete, name='marketing_workflow_delete'),

    # ── SEO Suite (Ahrefs / SEMrush) ──────────────────────────────────────────
    path('seo/<str:domain>/', views.seo_suite_home, name='seo_suite_home'),
    path('seo/<str:domain>/analyze/', views.seo_suite_analyze, name='seo_suite_analyze'),
    # Standalone SEO Portal (new tab, no panel chrome)
    path('seo-portal/<str:domain>/', views.seo_portal_home, name='seo_portal_home'),
    # Competitor Battle API
    path('seo/<str:domain>/battle/', views.seo_competitor_battle, name='seo_competitor_battle'),


    # ── Reseller Hosting Management ────────────────────────────────────────────
    path('reseller/',                                  views.reseller_dashboard,       name='reseller_dashboard'),
    path('reseller/accounts/',                         views.reseller_list_accounts,   name='reseller_list_accounts'),
    path('reseller/create-account/',                   views.reseller_create_account,  name='reseller_create_account'),
    path('reseller/delete-account/<str:acc_username>/',views.reseller_delete_account,  name='reseller_delete_account'),
    path('reseller/suspend-account/<str:acc_username>/',views.reseller_suspend_account, name='reseller_suspend_account'),
    path('reseller/unsuspend-account/<str:acc_username>/',views.reseller_unsuspend_account, name='reseller_unsuspend_account'),
    path('reseller/package/save/',                     views.reseller_package_save,    name='reseller_package_save'),
    path('reseller/package/delete/<int:pkg_id>/',      views.reseller_package_delete,  name='reseller_package_delete'),
    path('api/reseller/provision/',                    views.reseller_api_provision,   name='reseller_api_provision'),

    # ── SSO Auto-Login (accessible at /control/autologin/ for portal compatibility) ──
    # Also handles /control/control/autologin/ when server.url includes /control/
    path('autologin/', __import__('panel.views', fromlist=['autologin']).autologin, name='control_autologin'),
    path('control/autologin/', __import__('panel.views', fromlist=['autologin']).autologin, name='control_control_autologin'),

    # ── Docker Container Management ──────────────────────────────────
    path('docker/<str:domain>/', views.docker_dashboard, name='docker_dashboard'),
    path('docker/<str:domain>/install/', views.docker_install_engine, name='docker_install_engine'),
    path('docker/<str:domain>/create/', views.docker_container_create, name='docker_container_create'),
    path('docker/<str:domain>/action/<str:container_name>/<str:action>/', views.docker_container_action, name='docker_container_action'),
    path('docker/<str:domain>/logs/<str:container_name>/', views.docker_container_logs, name='docker_container_logs'),
    path('docker/<str:domain>/image/pull/', views.docker_image_pull, name='docker_image_pull'),
    path('docker/<str:domain>/image/delete/', views.docker_image_delete, name='docker_image_delete'),

    # ── Cloudflare CDN Integration ──────────────────────────────────
    path('cloudflare/<str:domain>/', views.cloudflare_dashboard, name='cloudflare_dashboard'),
    path('cloudflare/<str:domain>/config/save/', views.cloudflare_save_config, name='cloudflare_save_config'),
    path('cloudflare/<str:domain>/dns/create/', views.cloudflare_dns_create, name='cloudflare_dns_create'),
    path('cloudflare/<str:domain>/dns/edit/<str:record_id>/', views.cloudflare_dns_edit, name='cloudflare_dns_edit'),
    path('cloudflare/<str:domain>/dns/delete/<str:record_id>/', views.cloudflare_dns_delete, name='cloudflare_dns_delete'),
    path('cloudflare/<str:domain>/dns/toggle-proxy/<str:record_id>/', views.cloudflare_dns_toggle_proxy, name='cloudflare_dns_toggle_proxy'),
    path('cloudflare/<str:domain>/cache/purge/', views.cloudflare_purge_cache, name='cloudflare_purge_cache'),

    # ══ Suite Platform ══════════════════════════════════════════════
    # Hosting panel → SSO launch (hosting user clicks "Launch Social Studio")
    path('suite-sso/<str:domain>/<str:suite>/',    views.hosting_suite_sso,       name='hosting_suite_sso'),
    # SSO token validation (after redirect from hosting panel)
    path('suite/sso/<uuid:token>/',                views.suite_sso_validate,      name='suite_sso_validate'),
    # Standalone suite login / logout (suite-only customers)
    path('suite/login/',                           views.suite_login,             name='suite_login'),
    path('suite/logout/',                          views.suite_logout,            name='suite_logout'),
    # Suite portals — accessible via SSO or direct login
    path('suite/social/',                          views.suite_social_portal,     name='suite_social_portal'),
    path('suite/seo/',                             views.suite_seo_portal,        name='suite_seo_portal'),
    path('suite/marketing/',                       views.suite_marketing_portal,  name='suite_marketing_portal'),
    # Admin — manage plans and subscriptions
    path('admin/suite/plans/',                     views.suite_admin_plans,       name='suite_admin_plans'),
    path('admin/suite/plans/save/',                views.suite_plan_save,         name='suite_plan_save'),
    path('admin/suite/plans/<int:plan_id>/delete/',views.suite_plan_delete,       name='suite_plan_delete'),
    path('admin/suite/subscriptions/',             views.suite_admin_subs,        name='suite_admin_subs'),
    path('admin/suite/subscriptions/save/',        views.suite_sub_save,          name='suite_sub_save'),
    path('admin/suite/subscriptions/<int:sub_id>/delete/', views.suite_sub_delete, name='suite_sub_delete'),
    path('admin/suite/subscriptions/<int:sub_id>/toggle/', views.suite_sub_toggle, name='suite_sub_toggle'),

    # ── Suite Public API (for voidpanel.com website & external integrations) ────
    path('api/suite/create-account/',              views.suite_api_create,        name='suite_api_create'),
    path('api/suite/sso-token/',                   views.suite_api_sso_token,     name='suite_api_sso_token'),
    path('api/suite/plans/',                       views.suite_api_plans,         name='suite_api_plans'),
    path('api/suite/toggle-status/',               views.suite_api_toggle_status, name='suite_api_toggle_status'),
]



