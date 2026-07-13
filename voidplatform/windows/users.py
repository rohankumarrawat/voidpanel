"""Windows user management via net user."""
import subprocess
import os
from ..base import UserManager, CommandResult
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


class WindowsUserManager(UserManager):
    def create_user(self, username, password, shell='', home_dir=''):
        # Create Windows local user
        result = _run(['net', 'user', username, password, '/add'])
        if not result.success:
            return result
        # Create home directory under VoidPanel homes
        home = home_dir or os.path.join(paths.HOME_BASE, username)
        os.makedirs(home, exist_ok=True)
        public_html = os.path.join(home, 'public_html')
        os.makedirs(public_html, exist_ok=True)
        # Grant user full control of their home directory
        _run(['icacls', home, '/grant', f'{username}:(OI)(CI)F', '/T'])
        return result

    def delete_user(self, username, remove_home=True):
        result = _run(['net', 'user', username, '/delete'])
        if remove_home:
            home = os.path.join(paths.HOME_BASE, username)
            if os.path.isdir(home):
                import shutil
                shutil.rmtree(home, ignore_errors=True)
        return result

    def change_password(self, username, password):
        return _run(['net', 'user', username, password])

    def set_quota(self, username, soft_limit, hard_limit,
                  inode_soft=0, inode_hard=0):
        # Windows NTFS quotas via fsutil (requires volume letter)
        # This sets a quota on the C: volume for the user
        volume = os.environ.get('VOIDPANEL_QUOTA_VOLUME', 'C:')
        r = _run(['fsutil', 'quota', 'modify', volume,
                   str(soft_limit * 1024), str(hard_limit * 1024), username])
        if not r.success:
            # fsutil might need different format — try PowerShell fallback
            ps_cmd = (f"$vol = Get-WmiObject Win32_Volume -Filter \"DriveLetter='{volume}'\"; "
                      f"Enable-FsrmQuota -Path '{volume}\\' -ErrorAction SilentlyContinue")
            return _run(['powershell', '-NoProfile', '-Command', ps_cmd])
        return r

    def user_exists(self, username):
        r = _run(['net', 'user', username])
        return r.success
