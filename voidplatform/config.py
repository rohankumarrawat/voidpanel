"""Cross-platform path and configuration constants for VoidPanel."""
import os
from . import detector


class LinuxPaths:
    """Standard Linux paths used by VoidPanel."""
    PANEL_ROOT       = '/var/www/panel'
    HOME_BASE        = '/home'
    LOG_DIR          = '/var/log/voidpanel'
    NGINX_SITES_AVAILABLE = '/etc/nginx/sites-available'
    NGINX_SITES_ENABLED   = '/etc/nginx/sites-enabled'
    NGINX_CONF       = '/etc/nginx/nginx.conf'
    BIND_CONF        = '/etc/bind/named.conf'
    BIND_CONF_LOCAL  = '/etc/bind/named.conf.local'
    BIND_CONF_OPTIONS = '/etc/bind/named.conf.options'
    BIND_ZONE_DIR    = '/etc/bind'
    POSTFIX_MAIN_CF  = '/etc/postfix/main.cf'
    POSTFIX_VIRTUAL_DOMAINS   = '/etc/postfix/virtual_domains'
    POSTFIX_VIRTUAL_MAILBOX   = '/etc/postfix/vmailbox'
    POSTFIX_VIRTUAL_ALIAS     = '/etc/postfix/virtual_alias'
    DOVECOT_CONF     = '/etc/dovecot/dovecot.conf'
    DOVECOT_USERS    = '/etc/dovecot/users'
    VSFTPD_CONF      = '/etc/vsftpd.conf'
    VSFTPD_USERLIST  = '/etc/vsftpd.userlist'
    OPENDKIM_KEY_DIR = '/etc/opendkim/keys'
    OPENDKIM_KEYTABLE     = '/etc/opendkim/KeyTable'
    OPENDKIM_SIGNINGTABLE = '/etc/opendkim/SigningTable'
    OPENDKIM_TRUSTEDHOSTS = '/etc/opendkim/TrustedHosts'
    CSF_CONF         = '/etc/csf/csf.conf'
    SYSTEMD_DIR      = '/etc/systemd/system'
    LETSENCRYPT_LIVE = '/etc/letsencrypt/live'
    MAIL_VHOSTS      = '/var/mail/vhosts'
    MYSQL_PASSWORD_FILE = '/etc/dontdelete.txt'
    PHP_FPM_SOCK     = '/var/run/php/php{version}-fpm.sock'
    NOLOGIN_SHELL    = '/usr/sbin/nologin'
    HOSTS_FILE       = '/etc/hosts'
    CREDENTIALS_FILE = '/root/voidpanel_access.txt'
    SSL_DUMMY_CERT   = '/etc/nginx/dummy.crt'
    SSL_DUMMY_KEY    = '/etc/nginx/dummy.key'
    API_FILE         = '/var/www/panel/api.txt'
    VERSION_FILE     = '/etc/version.txt'
    DETAILS_FILE     = '/etc/details.txt'
    PANEL_LOG_FILE   = '/var/logs.txt'
    MAIL_LOG         = '/var/log/mail.log'
    SSL_LOG          = '/var/log/voidpanel/ssl.txt'
    PHP_FPM_INI_DIR  = '/etc/php'
    SHELLINABOX_DEFAULT = '/etc/default/shellinabox'
    SUSPEND_ROOT     = '/var/www/suspend'
    RUN_DIR          = '/var/run'


class WindowsPaths:
    """Windows-native paths for VoidPanel services."""
    _BASE = os.environ.get('VOIDPANEL_BASE', r'C:\VoidPanel')

    PANEL_ROOT       = os.path.join(_BASE, 'panel')
    HOME_BASE        = os.path.join(_BASE, 'homes')
    LOG_DIR          = os.path.join(_BASE, 'logs')

    # nginx for Windows
    NGINX_DIR        = os.path.join(_BASE, 'nginx')
    NGINX_SITES_AVAILABLE = os.path.join(_BASE, 'nginx', 'conf', 'sites-available')
    NGINX_SITES_ENABLED   = os.path.join(_BASE, 'nginx', 'conf', 'sites-enabled')
    NGINX_CONF       = os.path.join(_BASE, 'nginx', 'conf', 'nginx.conf')

    # BIND9 for Windows
    BIND_CONF        = os.path.join(_BASE, 'bind', 'etc', 'named.conf')
    BIND_CONF_LOCAL  = os.path.join(_BASE, 'bind', 'etc', 'named.conf.local')
    BIND_CONF_OPTIONS = os.path.join(_BASE, 'bind', 'etc', 'named.conf.options')
    BIND_ZONE_DIR    = os.path.join(_BASE, 'bind', 'zones')

    # hMailServer
    POSTFIX_MAIN_CF  = ''
    POSTFIX_VIRTUAL_DOMAINS   = os.path.join(_BASE, 'mail', 'virtual_domains')
    POSTFIX_VIRTUAL_MAILBOX   = os.path.join(_BASE, 'mail', 'vmailbox')
    POSTFIX_VIRTUAL_ALIAS     = os.path.join(_BASE, 'mail', 'virtual_alias')
    DOVECOT_CONF     = ''
    DOVECOT_USERS    = os.path.join(_BASE, 'mail', 'users')

    # FileZilla Server
    VSFTPD_CONF      = os.path.join(_BASE, 'FileZillaServer', 'FileZilla Server.xml')
    VSFTPD_USERLIST  = os.path.join(_BASE, 'FileZillaServer', 'userlist.txt')

    # DKIM (hMailServer built-in)
    OPENDKIM_KEY_DIR = os.path.join(_BASE, 'mail', 'dkim', 'keys')
    OPENDKIM_KEYTABLE     = ''
    OPENDKIM_SIGNINGTABLE = ''
    OPENDKIM_TRUSTEDHOSTS = ''

    # Firewall / Services
    CSF_CONF         = ''
    SYSTEMD_DIR      = ''

    # SSL
    LETSENCRYPT_LIVE = os.path.join(_BASE, 'ssl', 'live')

    # Mail
    MAIL_VHOSTS      = os.path.join(_BASE, 'mail', 'vhosts')

    # Credentials
    MYSQL_PASSWORD_FILE = os.path.join(_BASE, 'credentials', 'mysql_password.txt')
    CREDENTIALS_FILE    = os.path.join(_BASE, 'credentials', 'voidpanel_access.txt')

    # PHP
    PHP_DIR          = os.path.join(_BASE, 'php')
    PHP_FPM_SOCK     = ''
    PHP_CGI_PORT     = 9123

    # Misc
    NOLOGIN_SHELL    = ''
    HOSTS_FILE       = r'C:\Windows\System32\drivers\etc\hosts'
    SSL_DUMMY_CERT   = os.path.join(_BASE, 'nginx', 'conf', 'dummy.crt')
    SSL_DUMMY_KEY    = os.path.join(_BASE, 'nginx', 'conf', 'dummy.key')
    API_FILE         = os.path.join(_BASE, 'panel', 'api.txt')
    VERSION_FILE     = os.path.join(_BASE, 'version.txt')
    DETAILS_FILE     = os.path.join(_BASE, 'credentials', 'details.txt')
    PANEL_LOG_FILE   = os.path.join(_BASE, 'logs', 'panel.log')
    MAIL_LOG         = os.path.join(_BASE, 'logs', 'mail.log')
    SSL_LOG          = os.path.join(_BASE, 'logs', 'ssl.log')
    PHP_FPM_INI_DIR  = os.path.join(_BASE, 'php')
    SHELLINABOX_DEFAULT = ''
    SUSPEND_ROOT     = os.path.join(_BASE, 'nginx', 'html', 'suspend')
    RUN_DIR          = os.path.join(_BASE, 'run')


def get_paths():
    """Return the correct path configuration for the current OS."""
    if detector.is_windows():
        return WindowsPaths()
    return LinuxPaths()


paths = get_paths()
