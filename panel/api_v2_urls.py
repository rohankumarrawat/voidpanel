"""
panel/api_v2_urls.py — All REST API v2 URL patterns

Authentication: X-API-Token: <token>
Base path: /api/v2/

WHMCS Module Integration: All endpoints below are WHMCS-compatible.
"""
from django.urls import path
from . import api_v2

urlpatterns = [

    # ── Ping / Health Check ──────────────────────────────────────────────────
    path('ping/', api_v2.api_ping, name='api_v2_ping'),

    # ── Accounts ────────────────────────────────────────────────────────────
    path('accounts/list/',            api_v2.accounts_list,            name='api_v2_accounts_list'),
    path('accounts/get/',             api_v2.accounts_get,             name='api_v2_accounts_get'),
    path('accounts/create/',          api_v2.accounts_create,          name='api_v2_accounts_create'),
    path('accounts/suspend/',         api_v2.accounts_suspend,         name='api_v2_accounts_suspend'),
    path('accounts/unsuspend/',       api_v2.accounts_unsuspend,       name='api_v2_accounts_unsuspend'),
    path('accounts/terminate/',       api_v2.accounts_terminate,       name='api_v2_accounts_terminate'),
    path('accounts/change-package/',  api_v2.accounts_change_package,  name='api_v2_accounts_change_package'),
    path('accounts/change-password/', api_v2.accounts_change_password, name='api_v2_accounts_change_password'),

    # ── DNS ──────────────────────────────────────────────────────────────────
    path('dns/list/',   api_v2.dns_list,   name='api_v2_dns_list'),
    path('dns/create/', api_v2.dns_create, name='api_v2_dns_create'),
    path('dns/delete/', api_v2.dns_delete, name='api_v2_dns_delete'),

    # ── Email ────────────────────────────────────────────────────────────────
    path('email/list/',            api_v2.email_list,            name='api_v2_email_list'),
    path('email/create/',          api_v2.email_create,          name='api_v2_email_create'),
    path('email/delete/',          api_v2.email_delete,          name='api_v2_email_delete'),
    path('email/change-password/', api_v2.email_change_password, name='api_v2_email_change_password'),

    # ── Databases ────────────────────────────────────────────────────────────
    path('database/list/',   api_v2.database_list,   name='api_v2_database_list'),
    path('database/create/', api_v2.database_create, name='api_v2_database_create'),

    # ── SSL ──────────────────────────────────────────────────────────────────
    path('ssl/status/', api_v2.ssl_status, name='api_v2_ssl_status'),
    path('ssl/issue/',  api_v2.ssl_issue,  name='api_v2_ssl_issue'),
    path('ssl/download/', api_v2.ssl_download, name='api_v2_ssl_download'),

    # ── Subdomains ───────────────────────────────────────────────────────────
    path('subdomains/list/',   api_v2.subdomains_list,   name='api_v2_subdomains_list'),
    path('subdomains/create/', api_v2.subdomains_create, name='api_v2_subdomains_create'),
    path('subdomains/delete/', api_v2.subdomains_delete, name='api_v2_subdomains_delete'),

    # ── FTP ──────────────────────────────────────────────────────────────────
    path('ftp/list/',   api_v2.ftp_list,   name='api_v2_ftp_list'),
    path('ftp/create/', api_v2.ftp_create, name='api_v2_ftp_create'),
    path('ftp/delete/', api_v2.ftp_delete, name='api_v2_ftp_delete'),

    # ── Cron Jobs ────────────────────────────────────────────────────────────
    path('cron/list/',   api_v2.cron_list,   name='api_v2_cron_list'),
    path('cron/create/', api_v2.cron_create, name='api_v2_cron_create'),
    path('cron/delete/', api_v2.cron_delete, name='api_v2_cron_delete'),

    # ── Backups ──────────────────────────────────────────────────────────────
    path('backups/list/',   api_v2.backups_list,   name='api_v2_backups_list'),
    path('backups/create/', api_v2.backups_create, name='api_v2_backups_create'),

    # ── PHP ──────────────────────────────────────────────────────────────────
    path('php/get/', api_v2.php_get, name='api_v2_php_get'),
    path('php/set/', api_v2.php_set, name='api_v2_php_set'),

    # ── Packages & Server ────────────────────────────────────────────────────
    path('packages/list/',  api_v2.packages_list, name='api_v2_packages_list'),
    path('server/status/',  api_v2.server_status, name='api_v2_server_status'),

    # ── WordPress App Installer ───────────────────────────────────────────────
    path('wordpress/status/',         api_v2.wordpress_status,         name='api_v2_wp_status'),
    path('wordpress/install/',        api_v2.wordpress_install,        name='api_v2_wp_install'),
    path('wordpress/uninstall/',      api_v2.wordpress_uninstall,      name='api_v2_wp_uninstall'),
    path('wordpress/reset-password/', api_v2.wordpress_reset_password, name='api_v2_wp_reset_pass'),
]
