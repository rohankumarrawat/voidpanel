from django.contrib import admin
from django.urls import path, include
from . import views
from . import ai_api
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.index),
    path('docs/', views.docs),
    path('web-hosting/', views.pricing),
    path('web-hosting/order-summary/', views.order_summary),
    path('wordpress-hosting/', views.wordpress_hosting, name='wordpress_hosting'),
    path('reseller-hosting/', views.reseller_hosting, name='reseller_hosting'),
    path('reseller-hosting/configure/', views.reseller_configure, name='reseller_configure'),
    path('reseller-hosting/order/', views.reseller_order_checkout, name='reseller_order'),
    path('pricing/', views.pricing),
    path('pricing/order-summary/', views.order_summary),
    path('domain-registration/', views.domain_registration),
    path('domain-registration/order/', views.domain_order_checkout),
    path('api/domain/check/', views.api_domain_check),
    path('api/domain/check-bulk/', views.api_domain_check_bulk),
    path('api/coupon/validate/', views.api_coupon_validate),
    path('blogs/', views.blog_list_public),
    path('blog/<slug:slug>/', views.blog_detail_public),
    path('aboutus/', views.aboutus),
    path('db/', views.db),
    path('positive/', views.positive, name='positive'),
    path('negative/', views.negative, name='negative'),
    path('livechat/', include('chatting.urls')),
    path('overview/', views.overview),
    path('chpass/', views.chpass),
    path('addweb/', views.addweb),
    path('notifications/', views.notifications),
    path('latest_messages/', views.latest_messages),
    path('version_name/', views.update),
    path('version_migration_path/', views.version_migration_path),
    path('updatepanel.sh', views.serve_update_script),
    path('install.sh', views.serve_install_script),
    path('static/updates/<str:version>/update.sh', views.serve_version_script),
    path('updates/<str:version>/update.sh', views.serve_version_script),
    path('releases/<str:version>', views.serve_release_package),
    path('admindocs/', views.admindocs),
    path('clientdocs/', views.clientdocs),
    path('api/increment/', views.increment_number, name='increment-number'),
    path('login/', views.loginn),
    path('logout/', views.logout_view),
    path('register/', views.register),
    path('register/verify/', views.register_verify, name='register_verify'),
    path('register/resend/', views.register_resend_otp, name='register_resend_otp'),

    # ── Client Portal ──────────────────────────────────────────────────────────
    path('portal/', views.portal),
    path('portal/blog/write/', views.portal_blog_write),
    path('portal/ticket/new/', views.portal_ticket_new, name='portal_ticket_new'),
    path('portal/service/<int:service_id>/wordpress/',        views.portal_manage_wordpress,  name='portal_manage_wordpress'),
    path('portal/service/<int:service_id>/wordpress/action/', views.portal_wordpress_action,  name='portal_wordpress_action'),
    path('portal/email/<int:service_id>/',                    views.portal_manage_email,       name='portal_manage_email'),
    path('portal/email/<int:service_id>/action/',             views.portal_email_action,       name='portal_email_action'),
    path('portal/ssl/<int:service_id>/',                      views.portal_manage_ssl,         name='portal_manage_ssl'),
    path('portal/ssl/<int:service_id>/action/',               views.portal_ssl_action,         name='portal_ssl_action'),
    path('portal/ssl/<int:service_id>/download/<str:file_type>/', views.portal_ssl_download, name='portal_ssl_download'),
    path('portal/ticket/<int:ticket_id>/', views.portal_ticket_detail, name='portal_ticket_detail'),
    path('portal/service/<int:service_id>/',        views.portal_service_detail,   name='portal_service_detail'),
    path('portal/service/<int:service_id>/login/',   views.portal_service_autologin, name='portal_service_autologin'),
    path('portal/service/<int:service_id>/manage/',  views.portal_service_manage,   name='portal_service_manage'),
    path('portal/invoice/<int:inv_id>/pay/',          views.invoice_pay, name='invoice_pay'),
    path('portal/order-complete/',                    views.order_complete, name='order_complete'),
    path('portal/license/<int:license_id>/',          views.portal_license_detail, name='portal_license_detail'),
    path('portal/license/<int:license_id>/remote-install/start/', views.portal_remote_install_start, name='portal_remote_install_start'),
    path('portal/license/<int:license_id>/remote-install/status/<int:job_id>/', views.portal_remote_install_status, name='portal_remote_install_status'),

    # ── SSO Token Validation (called by VoidPanel panel server) ───────────
    path('api/sso/validate/', views.api_sso_validate, name='api_sso_validate'),

    # ── Get VoidPanel (license acquisition) ───────────────────────────────────
    path('get-voidpanel/', views.get_voidpanel, name='get_voidpanel'),
    path('license/subscribe/', views.license_subscribe, name='license_subscribe'),
    path('api/license/create-order/', views.api_license_create_order, name='api_license_create_order'),
    path('api/license/verify-order/', views.api_license_verify_order, name='api_license_verify_order'),

    # ── Cart & Checkout ────────────────────────────────────────────────────────
    path('cart/<slug:slug>/', views.cart_config, name='cart_config'),

    # ── Super Admin ────────────────────────────────────────────────────────────
    path('super-admin/', views.super_admin_portal),
    path('super-admin/servers/', views.super_admin_servers),
    path('super-admin/staff/', views.super_admin_staff),
    path('super-admin/roles/', views.super_admin_roles),
    path('super-admin/emails/', views.super_admin_emails),
    path('super-admin/hosting/', views.super_admin_hosting),
    path('super-admin/reseller/', views.super_admin_reseller),
    path('super-admin/domain-api/', views.super_admin_domain_api),
    path('super-admin/coupons/', views.super_admin_coupons),
    path('super-admin/signals/', views.super_admin_signals),
    path('super-admin/clients/', views.super_admin_clients),
    path('super-admin/billing/', views.super_admin_billing),
    path('super-admin/tickets/', views.super_admin_tickets),
    path('super-admin/tickets/<int:ticket_id>/', views.super_admin_ticket_detail),
    path('super-admin/licenses/', views.super_admin_licenses),
    path('super-admin/licenses/action/', views.super_admin_license_action),
    path('super-admin/payment-gateway/', views.super_admin_payment_gateway),
    path('super-admin/livechat/', views.super_admin_livechat_dashboard),
    path('super-admin/livechat/<int:session_id>/', views.super_admin_livechat_detail),
    path('super-admin/livechat/<int:session_id>/assign/', views.super_admin_livechat_assign),
    path('super-admin/blogs/', views.super_admin_blogs),
    path('super-admin/blogs/write/', views.super_admin_blog_write),
    path('super-admin/blogs/<int:post_id>/action/', views.super_admin_blog_action),
    path('super-admin/notifications/', views.super_admin_notifications),
    path('super-admin/auto-suspend/',  views.super_admin_auto_suspend),
    path('super-admin/chips/',         views.super_admin_chips,        name='super_admin_chips'),
    path('super-admin/email-plans/',   views.super_admin_email_plans,  name='super_admin_email_plans'),
    path('super-admin/ssl-plans/',     views.super_admin_ssl_plans,    name='super_admin_ssl_plans'),
    path('super-admin/ssl-services/',  views.super_admin_ssl_services, name='super_admin_ssl_services'),
    path('super-admin/services/',      views.super_admin_services,     name='super_admin_services'),
    path('super-admin/whatsapp/',      views.super_admin_whatsapp,     name='super_admin_whatsapp'),
    path('super-admin/base-email/',    views.super_admin_base_email,   name='super_admin_base_email'),

    # ── Public Product Pages ───────────────────────────────────────────────────
    path('professional-email/',  views.professional_email_page, name='professional_email'),
    path('professional-email/order/<str:plan_id>/', views.email_configure, name='email_configure'),
    path('professional-email/checkout/',             views.email_checkout,  name='email_checkout'),
    path('ssl-certificates/', views.ssl_certificate_page, name='ssl_certificates'),
    path('ssl-certificates/order/<str:plan_id>/', views.ssl_configure, name='ssl_configure'),
    path('ssl-certificates/checkout/',             views.ssl_checkout,  name='ssl_checkout'),
    path('super-admin/social-api/',    views.super_admin_social_api,       name='super_admin_social_api'),
    path('api/social/platform-config/', views.api_social_platform_config,  name='api_social_platform_config'),

    # ── Social OAuth Relay (panels redirect users here) ────────────────────────
    path('social/oauth/connect/<str:platform>/',  views.social_oauth_connect,      name='social_oauth_connect'),
    path('social/oauth/callback/<str:platform>/', views.social_oauth_callback,     name='social_oauth_callback'),
    path('api/social/retrieve-tokens/',           views.api_social_retrieve_tokens, name='api_social_retrieve_tokens'),
    path('api/social/refresh-token/',             views.api_social_refresh_token,   name='api_social_refresh_token'),

    # ── Agentic AI Key Management ──────────────────────────────────
    path('super-admin/ai-keys/', views.super_admin_ai_keys, name='super_admin_ai_keys'),
    path('super-admin/update-manager/', views.super_admin_update_manager, name='super_admin_update_manager'),
    path('super-admin/push-update/',    views.super_admin_push_update,    name='super_admin_push_update'),
    path('api/admin/server/test/', views.api_admin_server_test, name='api_admin_server_test'),

    # ── License API (called by installed panels) ───────────────────────────────
    path('api/license/register/', views.api_license_register),
    path('api/license/validate/', views.api_license_validate),
    path('api/marketing/global-templates/', views.api_global_templates, name='api_global_templates'),

    # ── Panel Ticket API (called by installed VoidPanel instances) ─────────────
    path('api/panel/ticket/create/', views.api_panel_ticket_create),
    path('api/panel/ticket/list/', views.api_panel_ticket_list),
    path('api/panel/ticket/reply/', views.api_panel_ticket_reply),

    # ── Agentic AI Central API (called by installed VoidPanel instances) ───────
    path('api/ai/chat', ai_api.api_ai_chat),
    path('api/ai/chat/', ai_api.api_ai_chat),

    # ── Razorpay Payment API ────────────────────────────────────────────────
    path('api/payment/razorpay/create-order/', views.api_razorpay_create_order),
    path('api/payment/razorpay/verify/', views.api_razorpay_verify),
    path('api/payment/razorpay/webhook/', views.api_razorpay_webhook),
    path('api/payment/wallet/pay/', views.api_wallet_pay, name='api_wallet_pay'),
    path('portal/wallet/deposit/', views.wallet_deposit, name='wallet_deposit'),
    path('portal/wallet/buy_chips/', views.wallet_buy_chips, name='wallet_buy_chips'),


    # ── Try VoidPanel Live Demo ───────────────────────────────────────────────
    path('try-voidpanel/', views.try_voidpanel, name='try_voidpanel'),
    path('super-admin/try-voidpanel/', views.super_admin_try_voidpanel, name='super_admin_try_voidpanel'),
    path('portal/delete-service/', views.portal_delete_service, name='portal_delete_service'),
    path('terms-and-conditions/', views.terms_and_conditions, name='terms_and_conditions'),
    path('privacy-policy/', views.privacy_policy, name='privacy_policy'),

    # ── Blog / Legacy ──────────────────────────────────────────────────────────
    path('addemail/', views.addemail),
    path('whmcs/', views.whmcs),
    path('whmcs/module/', views.whmcs_module),

    # ── Digital Suites — Public Landing Pages ────────────────────────────────
    path('social-media-suite/',  views.social_media_suite_page, name='social_suite'),
    path('seo-suite/',           views.seo_suite_page,          name='seo_suite'),
    path('marketing-suite/',     views.marketing_suite_page,    name='marketing_suite'),

    # ── Digital Suites — Buy Flow ─────────────────────────────────────────────
    path('suite/<str:suite>/order/<int:plan_id>/', views.suite_order_configure, name='suite_order_configure'),
    path('suite/checkout/',                        views.suite_checkout,        name='suite_checkout'),

    # ── Digital Suites — Portal SSO ───────────────────────────────────────────
    path('portal/suite-sso/<int:service_id>/', views.portal_suite_sso, name='portal_suite_sso'),

    # ── Digital Suites — Super-Admin ──────────────────────────────────────────
    path('super-admin/suite-plans/', views.super_admin_suite_plans, name='super_admin_suite_plans'),

]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
