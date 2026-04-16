"""Linux user management via useradd/userdel/chpasswd/setquota."""
import subprocess
from ..base import UserManager, CommandResult


def _run(cmd, **kwargs):
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=30, **kwargs)
        return CommandResult(success=r.returncode == 0, output=r.stdout.strip(),
                             error=r.stderr.strip(), return_code=r.returncode)
    except Exception as e:
        return CommandResult(success=False, error=str(e), return_code=-1)


class LinuxUserManager(UserManager):
    def create_user(self, username, password, shell='', home_dir=''):
        shell = shell or '/usr/sbin/nologin'
        cmd = ['sudo', 'useradd', '-m', '-s', shell]
        if home_dir:
            cmd += ['-d', home_dir]
        cmd.append(username)
        result = _run(cmd)
        if result.success and password:
            self.change_password(username, password)
        return result

    def delete_user(self, username, remove_home=True):
        if remove_home:
            return _run(['sudo', 'userdel', '-r', username])
        return _run(['sudo', 'userdel', username])

    def change_password(self, username, password):
        try:
            proc = subprocess.Popen(['sudo', 'chpasswd'], stdin=subprocess.PIPE,
                                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            stdout, stderr = proc.communicate(f'{username}:{password}\n', timeout=10)
            return CommandResult(success=proc.returncode == 0, output=stdout,
                                 error=stderr, return_code=proc.returncode)
        except Exception as e:
            return CommandResult(success=False, error=str(e), return_code=-1)

    def set_quota(self, username, soft_limit, hard_limit, inode_soft=0, inode_hard=0):
        return _run(['sudo', 'setquota', '-u', username,
                      str(soft_limit), str(hard_limit),
                      str(inode_soft), str(inode_hard), '/'])

    def user_exists(self, username):
        return _run(['id', username]).success
