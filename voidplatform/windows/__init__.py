"""Windows platform backend for VoidPanel."""
from ..base import Platform
from .services import WindowsServiceManager
from .users import WindowsUserManager
from .web import WindowsWebServerManager
from .dns import WindowsDNSManager
from .mail import WindowsMailManager
from .ftp import WindowsFTPManager
from .firewall import WindowsFirewallManager
from .ssl import WindowsSSLManager
from .php import WindowsPHPManager
from .terminal import WindowsTerminalManager


class WindowsPlatform(Platform):
    def __init__(self):
        self._services = WindowsServiceManager()
        self._users = WindowsUserManager()
        self._web = WindowsWebServerManager()
        self._dns = WindowsDNSManager()
        self._mail = WindowsMailManager()
        self._ftp = WindowsFTPManager()
        self._firewall = WindowsFirewallManager()
        self._ssl = WindowsSSLManager()
        self._php = WindowsPHPManager()
        self._terminal = WindowsTerminalManager()

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
