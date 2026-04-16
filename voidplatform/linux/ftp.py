"""Linux vsftpd FTP management."""
import subprocess
from ..base import FTPManager, CommandResult
from ..config import LinuxPaths as paths


def _run(cmd, **kwargs):
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=30, **kwargs)
        return CommandResult(success=r.returncode == 0, output=r.stdout.strip(),
                             error=r.stderr.strip(), return_code=r.returncode)
    except Exception as e:
        return CommandResult(success=False, error=str(e), return_code=-1)


class LinuxFTPManager(FTPManager):
    def add_user(self, username, password, home_dir):
        try:
            with open(paths.VSFTPD_USERLIST, 'a') as f:
                f.write(f'{username}\n')
            return self.reload()
        except Exception as e:
            return CommandResult(success=False, error=str(e))

    def remove_user(self, username):
        try:
            with open(paths.VSFTPD_USERLIST, 'r') as f:
                lines = f.readlines()
            with open(paths.VSFTPD_USERLIST, 'w') as f:
                f.writelines(l for l in lines if l.strip() != username)
            return self.reload()
        except Exception as e:
            return CommandResult(success=False, error=str(e))

    def change_password(self, username, password):
        try:
            proc = subprocess.Popen(['sudo', 'chpasswd'], stdin=subprocess.PIPE,
                                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            stdout, stderr = proc.communicate(f'{username}:{password}\n', timeout=10)
            return CommandResult(success=proc.returncode == 0, output=stdout,
                                 error=stderr, return_code=proc.returncode)
        except Exception as e:
            return CommandResult(success=False, error=str(e), return_code=-1)

    def reload(self):
        return _run(['sudo', 'systemctl', 'restart', 'vsftpd'])
