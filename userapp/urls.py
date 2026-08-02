"""
VoidApp API URL Configuration.

All endpoints are prefixed with /api/v1/ (mounted at /api/v1/ in panel/urls.py).
"""

from django.urls import path

from userapp.views import (
    auth, dashboard, email, ftp, database,
    subdomain, ssl, cron, backup, dns, activity
)

app_name = 'userapp'

urlpatterns = [
    # ── Authentication ───────────────────────────────────────────────────
    path('auth/login/', auth.api_login, name='api_login'),
    path('auth/me/', auth.api_me, name='api_me'),
    path('auth/logout/', auth.api_logout, name='api_logout'),

    # ── Dashboard ────────────────────────────────────────────────────────
    path('dashboard/', dashboard.api_dashboard, name='api_dashboard'),

    # ── Email Management ─────────────────────────────────────────────────
    path('emails/', email.api_email_list, name='api_email_list'),
    path('emails/create/', email.api_email_create, name='api_email_create'),
    path('emails/delete/', email.api_email_delete, name='api_email_delete'),
    path('emails/change-password/', email.api_email_change_password, name='api_email_change_password'),

    # ── FTP Management ───────────────────────────────────────────────────
    path('ftp/', ftp.api_ftp_list, name='api_ftp_list'),
    path('ftp/create/', ftp.api_ftp_create, name='api_ftp_create'),
    path('ftp/delete/', ftp.api_ftp_delete, name='api_ftp_delete'),
    path('ftp/change-password/', ftp.api_ftp_change_password, name='api_ftp_change_password'),
    path('ftp/change-storage/', ftp.api_ftp_change_storage, name='api_ftp_change_storage'),

    # ── Database Management ──────────────────────────────────────────────
    path('databases/', database.api_database_list, name='api_database_list'),
    path('databases/create/', database.api_database_create, name='api_database_create'),
    path('databases/delete/', database.api_database_delete, name='api_database_delete'),
    path('databases/users/create/', database.api_database_user_create, name='api_database_user_create'),

    # ── Subdomain Management ─────────────────────────────────────────────
    path('subdomains/', subdomain.api_subdomain_list, name='api_subdomain_list'),
    path('subdomains/create/', subdomain.api_subdomain_create, name='api_subdomain_create'),
    path('subdomains/delete/', subdomain.api_subdomain_delete, name='api_subdomain_delete'),

    # ── SSL Management ───────────────────────────────────────────────────
    path('ssl/status/', ssl.api_ssl_status, name='api_ssl_status'),
    path('ssl/install/', ssl.api_ssl_install, name='api_ssl_install'),
    path('ssl/log/', ssl.api_ssl_log, name='api_ssl_log'),

    # ── Cron Jobs ────────────────────────────────────────────────────────
    path('cron/', cron.api_cron_list, name='api_cron_list'),
    path('cron/create/', cron.api_cron_create, name='api_cron_create'),
    path('cron/delete/', cron.api_cron_delete, name='api_cron_delete'),

    # ── Backups ──────────────────────────────────────────────────────────
    path('backups/', backup.api_backup_list, name='api_backup_list'),
    path('backups/create/', backup.api_backup_create, name='api_backup_create'),
    path('backups/status/', backup.api_backup_status, name='api_backup_status'),
    path('backups/delete/', backup.api_backup_delete, name='api_backup_delete'),

    # ── DNS Zone ─────────────────────────────────────────────────────────
    path('dns/records/', dns.api_dns_list, name='api_dns_list'),
    path('dns/records/create/', dns.api_dns_add, name='api_dns_add'),
    path('dns/records/delete/', dns.api_dns_delete, name='api_dns_delete'),

    # ── Activity Log ─────────────────────────────────────────────────────
    path('activity/', activity.api_activity_list, name='api_activity_list'),
]
