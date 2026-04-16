"""Windows service management via sc.exe and PowerShell."""
import subprocess
from ..base import ServiceManager, CommandResult

# Maps VoidPanel service names to Windows service names
SERVICE_MAP = {
    'nginx':    'nginx',
    'mysql':    'MySQL80',
    'bind9':    'named',
    'named':    'named',
    'redis':    'Redis',
    'postfix':  'hMailServer',
    'dovecot':  'hMailServer',
    'vsftpd':   'FileZilla Server',
    'opendkim': 'hMailServer',
    'uwsgi':    'VoidPanel',
    'php8.3-fpm': 'php-cgi',
}


def _run(cmd, **kwargs):
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=30,
                           creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0),
                           **kwargs)
        return CommandResult(success=r.returncode == 0, output=r.stdout.strip(),
                             error=r.stderr.strip(), return_code=r.returncode)
    except Exception as e:
        return CommandResult(success=False, error=str(e), return_code=-1)


def _win_svc_name(service):
    """Resolve a Linux service name to its Windows equivalent."""
    return SERVICE_MAP.get(service, service)


class WindowsServiceManager(ServiceManager):
    def start(self, service):
        return _run(['sc', 'start', _win_svc_name(service)])

    def stop(self, service):
        return _run(['sc', 'stop', _win_svc_name(service)])

    def restart(self, service):
        self.stop(service)
        import time
        time.sleep(2)
        return self.start(service)

    def reload(self, service):
        name = _win_svc_name(service)
        # nginx supports reload signal on Windows
        if name == 'nginx':
            return _run(['nginx', '-s', 'reload'])
        # Most Windows services need a full restart to pick up config changes
        return self.restart(service)

    def enable(self, service):
        return _run(['sc', 'config', _win_svc_name(service), 'start=', 'auto'])

    def disable(self, service):
        return _run(['sc', 'config', _win_svc_name(service), 'start=', 'disabled'])

    def is_active(self, service):
        r = _run(['sc', 'query', _win_svc_name(service)])
        return r.success and 'RUNNING' in r.output
