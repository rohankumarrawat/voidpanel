"""Linux platform backend for VoidPanel."""
from ..base import Platform
from .services import LinuxServiceManager
from .users import LinuxUserManager
from .web import LinuxWebServerManager
from .dns import LinuxDNSManager
from .mail import LinuxMailManager
from .ftp import LinuxFTPManager
from .firewall import LinuxFirewallManager
from .ssl import LinuxSSLManager
from .php import LinuxPHPManager
from .terminal import LinuxTerminalManager


class LinuxPlatform(Platform):
    def __init__(self):
        self._services = LinuxServiceManager()
        self._users = LinuxUserManager()
        self._web = LinuxWebServerManager()
        self._dns = LinuxDNSManager()
        self._mail = LinuxMailManager()
        self._ftp = LinuxFTPManager()
        self._firewall = LinuxFirewallManager()
        self._ssl = LinuxSSLManager()
        self._php = LinuxPHPManager()
        self._terminal = LinuxTerminalManager()

    @property
    def services(self): return self._services
    @property
    def users(self): return self._users
    @property
    def web(self): return self._web
    @property
    def dns(self): return self._dns
    @property
    def mail(self): return self._mail
    @property
    def ftp(self): return self._ftp
    @property
    def firewall(self): return self._firewall
    @property
    def ssl(self): return self._ssl
    @property
    def php(self): return self._php
    @property
    def terminal(self): return self._terminal
