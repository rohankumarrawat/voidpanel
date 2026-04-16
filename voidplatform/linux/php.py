"""Linux PHP-FPM management."""
import os
import subprocess
from ..base import PHPManager, CommandResult


def _run(cmd, **kwargs):
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=30, **kwargs)
        return CommandResult(success=r.returncode == 0, output=r.stdout.strip(),
                             error=r.stderr.strip(), return_code=r.returncode)
    except Exception as e:
        return CommandResult(success=False, error=str(e), return_code=-1)


class LinuxPHPManager(PHPManager):
    def get_installed_versions(self):
        versions = []
        for v in ['7.4', '8.0', '8.1', '8.2', '8.3', '8.4']:
            if os.path.exists(f'/usr/bin/php{v}'):
                versions.append(v)
        return versions

    def get_active_version(self, domain=''):
        r = _run(['php', '-v'])
        if r.success:
            parts = r.output.split('\n')[0].split()
            if len(parts) >= 2:
                return '.'.join(parts[1].split('.')[:2])
        return ''

    def switch_version(self, domain, version):
        return _run(['sudo', 'systemctl', 'reload', f'php{version}-fpm'])

    def get_modules(self, version):
        r = _run([f'/usr/bin/php{version}', '-m'])
        if r.success:
            return [m.strip() for m in r.output.split('\n')
                    if m.strip() and not m.startswith('[')]
        return []
