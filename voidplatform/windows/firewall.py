"""Windows Firewall management via netsh advfirewall."""
import subprocess
from ..base import FirewallManager, CommandResult


def _run(cmd, **kwargs):
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=30,
                           creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0),
                           **kwargs)
        return CommandResult(success=r.returncode == 0, output=r.stdout.strip(),
                             error=r.stderr.strip(), return_code=r.returncode)
    except Exception as e:
        return CommandResult(success=False, error=str(e), return_code=-1)


class WindowsFirewallManager(FirewallManager):
    def allow_port(self, port, protocol='tcp'):
        name = f'VoidPanel-Allow-{protocol.upper()}-{port}'
        # Remove existing rule first (idempotent)
        _run(['netsh', 'advfirewall', 'firewall', 'delete', 'rule', f'name={name}'])
        return _run([
            'netsh', 'advfirewall', 'firewall', 'add', 'rule',
            f'name={name}', 'dir=in', 'action=allow',
            f'protocol={protocol}', f'localport={port}',
        ])

    def deny_port(self, port, protocol='tcp'):
        name = f'VoidPanel-Block-{protocol.upper()}-{port}'
        _run(['netsh', 'advfirewall', 'firewall', 'delete', 'rule', f'name={name}'])
        return _run([
            'netsh', 'advfirewall', 'firewall', 'add', 'rule',
            f'name={name}', 'dir=in', 'action=block',
            f'protocol={protocol}', f'localport={port}',
        ])

    def allow_ip(self, ip):
        name = f'VoidPanel-Allow-IP-{ip}'
        _run(['netsh', 'advfirewall', 'firewall', 'delete', 'rule', f'name={name}'])
        return _run([
            'netsh', 'advfirewall', 'firewall', 'add', 'rule',
            f'name={name}', 'dir=in', 'action=allow',
            f'remoteip={ip}',
        ])

    def deny_ip(self, ip):
        name = f'VoidPanel-Block-IP-{ip}'
        _run(['netsh', 'advfirewall', 'firewall', 'delete', 'rule', f'name={name}'])
        return _run([
            'netsh', 'advfirewall', 'firewall', 'add', 'rule',
            f'name={name}', 'dir=in', 'action=block',
            f'remoteip={ip}',
        ])

    def reload(self):
        # Windows Firewall applies rules immediately — no reload needed
        return CommandResult(success=True, output="Windows Firewall rules are active immediately")
