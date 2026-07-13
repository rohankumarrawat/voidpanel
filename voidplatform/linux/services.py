"""Linux service management via systemctl."""
import subprocess
from ..base import ServiceManager, CommandResult


def _run(cmd, **kwargs):
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=30, **kwargs)
        return CommandResult(success=r.returncode == 0, output=r.stdout.strip(),
                             error=r.stderr.strip(), return_code=r.returncode)
    except Exception as e:
        return CommandResult(success=False, error=str(e), return_code=-1)


class LinuxServiceManager(ServiceManager):
    def start(self, service):
        return _run(['sudo', 'systemctl', 'start', service])

    def stop(self, service):
        return _run(['sudo', 'systemctl', 'stop', service])

    def restart(self, service):
        return _run(['sudo', 'systemctl', 'restart', service])

    def reload(self, service):
        return _run(['sudo', 'systemctl', 'reload', service])

    def enable(self, service):
        return _run(['sudo', 'systemctl', 'enable', service])

    def disable(self, service):
        return _run(['sudo', 'systemctl', 'disable', service])

    def is_active(self, service):
        try:
            r = subprocess.check_output(
                ['sudo', 'systemctl', 'is-active', service],
                text=True, timeout=10)
            return r.strip() == 'active'
        except Exception:
            return False
