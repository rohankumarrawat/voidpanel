"""Linux CSF firewall management."""
import subprocess
from ..base import FirewallManager, CommandResult


def _run(cmd, **kwargs):
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=30, **kwargs)
        return CommandResult(success=r.returncode == 0, output=r.stdout.strip(),
                             error=r.stderr.strip(), return_code=r.returncode)
    except Exception as e:
        return CommandResult(success=False, error=str(e), return_code=-1)


class LinuxFirewallManager(FirewallManager):
    def allow_port(self, port, protocol='tcp'):
        return _run(['sudo', 'csf', '-atr', str(port), protocol])

    def deny_port(self, port, protocol='tcp'):
        return _run(['sudo', 'csf', '-dtr', str(port), protocol])

    def allow_ip(self, ip):
        return _run(['sudo', 'csf', '-a', ip])

    def deny_ip(self, ip):
        return _run(['sudo', 'csf', '-d', ip])

    def reload(self):
        return _run(['sudo', 'csf', '-r'])
