"""Windows PHP management (php-cgi.exe with nginx FastCGI)."""
import os
import subprocess
from ..base import PHPManager, CommandResult
from ..config import WindowsPaths as paths


def _run(cmd, **kwargs):
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=30,
                           creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0),
                           **kwargs)
        return CommandResult(success=r.returncode == 0, output=r.stdout.strip(),
                             error=r.stderr.strip(), return_code=r.returncode)
    except Exception as e:
        return CommandResult(success=False, error=str(e), return_code=-1)


class WindowsPHPManager(PHPManager):
    def _php_dir(self, version=''):
        """Return directory for a specific PHP version, e.g. C:\\VoidPanel\\php\\8.3"""
        if version:
            return os.path.join(paths.PHP_DIR, version)
        return paths.PHP_DIR

    def _php_cgi(self, version=''):
        """Return path to php-cgi.exe for a version."""
        if version:
            return os.path.join(self._php_dir(version), 'php-cgi.exe')
        # Find any available version
        for v in reversed(self.get_installed_versions()):
            exe = os.path.join(self._php_dir(v), 'php-cgi.exe')
            if os.path.exists(exe):
                return exe
        return 'php-cgi.exe'  # Hope it's in PATH

    def get_installed_versions(self):
        versions = []
        if not os.path.isdir(paths.PHP_DIR):
            return versions
        for entry in os.listdir(paths.PHP_DIR):
            exe = os.path.join(paths.PHP_DIR, entry, 'php-cgi.exe')
            if os.path.exists(exe):
                versions.append(entry)
        return sorted(versions)

    def get_active_version(self, domain=''):
        # Check which php-cgi is running
        r = _run(['php', '-v'])
        if r.success:
            parts = r.output.split('\n')[0].split()
            if len(parts) >= 2:
                return '.'.join(parts[1].split('.')[:2])
        # Check installed versions
        versions = self.get_installed_versions()
        return versions[-1] if versions else ''

    def switch_version(self, domain, version):
        """Switch PHP version by restarting php-cgi with the new binary.

        On Windows, nginx connects to php-cgi via TCP FastCGI (127.0.0.1:9123).
        Switching versions means killing the current php-cgi and starting the
        new version's binary.
        """
        # Kill existing php-cgi processes
        _run(['taskkill', '/F', '/IM', 'php-cgi.exe'])

        # Start the new version
        php_cgi = self._php_cgi(version)
        if not os.path.exists(php_cgi):
            return CommandResult(success=False,
                                 error=f"PHP {version} not installed at {php_cgi}")

        port = paths.PHP_CGI_PORT
        # Start php-cgi in background
        try:
            subprocess.Popen(
                [php_cgi, '-b', f'127.0.0.1:{port}'],
                creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0) |
                              getattr(subprocess, 'DETACHED_PROCESS', 0),
            )
            return CommandResult(success=True,
                                 output=f"PHP {version} started on port {port}")
        except Exception as e:
            return CommandResult(success=False, error=str(e))

    def get_modules(self, version):
        php_cgi = self._php_cgi(version)
        r = _run([php_cgi, '-m'])
        if r.success:
            return [m.strip() for m in r.output.split('\n')
                    if m.strip() and not m.startswith('[')]
        return []
