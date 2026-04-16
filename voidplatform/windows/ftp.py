"""Windows FTP management via FileZilla Server."""
import os
import subprocess
import xml.etree.ElementTree as ET
from ..base import FTPManager, CommandResult
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


class WindowsFTPManager(FTPManager):
    def _config_path(self):
        return paths.VSFTPD_CONF  # Points to FileZilla Server.xml

    def _userlist_path(self):
        return paths.VSFTPD_USERLIST

    def add_user(self, username, password, home_dir):
        # Add to userlist tracking file
        os.makedirs(os.path.dirname(self._userlist_path()), exist_ok=True)
        try:
            with open(self._userlist_path(), 'a') as f:
                f.write(f'{username}\n')
        except Exception as e:
            return CommandResult(success=False, error=str(e))

        # Add user to FileZilla Server config XML
        config_path = self._config_path()
        if os.path.exists(config_path):
            try:
                tree = ET.parse(config_path)
                root = tree.getroot()
                users = root.find('Users')
                if users is None:
                    users = ET.SubElement(root, 'Users')

                user_elem = ET.SubElement(users, 'User', Name=username)
                ET.SubElement(user_elem, 'Option', Name='Pass').text = password
                ET.SubElement(user_elem, 'Option', Name='Group').text = ''
                perm = ET.SubElement(user_elem, 'Permissions')
                dir_elem = ET.SubElement(perm, 'Permission', Dir=home_dir)
                for opt_name in ('FileRead', 'FileWrite', 'FileDelete',
                                 'DirCreate', 'DirDelete', 'DirList', 'DirSubdirs'):
                    dir_elem.set(opt_name, '1')

                tree.write(config_path, xml_declaration=True, encoding='utf-8')
            except Exception as e:
                return CommandResult(success=False, error=f"XML config error: {e}")

        return self.reload()

    def remove_user(self, username):
        # Remove from userlist
        try:
            ul = self._userlist_path()
            if os.path.exists(ul):
                with open(ul, 'r') as f:
                    lines = f.readlines()
                with open(ul, 'w') as f:
                    f.writelines(l for l in lines if l.strip() != username)
        except Exception:
            pass

        # Remove from FileZilla XML config
        config_path = self._config_path()
        if os.path.exists(config_path):
            try:
                tree = ET.parse(config_path)
                users = tree.getroot().find('Users')
                if users is not None:
                    for user_elem in users.findall('User'):
                        if user_elem.get('Name') == username:
                            users.remove(user_elem)
                    tree.write(config_path, xml_declaration=True, encoding='utf-8')
            except Exception as e:
                return CommandResult(success=False, error=f"XML config error: {e}")

        return self.reload()

    def change_password(self, username, password):
        config_path = self._config_path()
        if not os.path.exists(config_path):
            return CommandResult(success=False, error="FileZilla config not found")
        try:
            tree = ET.parse(config_path)
            users = tree.getroot().find('Users')
            if users is not None:
                for user_elem in users.findall('User'):
                    if user_elem.get('Name') == username:
                        pass_elem = user_elem.find("Option[@Name='Pass']")
                        if pass_elem is not None:
                            pass_elem.text = password
                        tree.write(config_path, xml_declaration=True, encoding='utf-8')
                        return self.reload()
            return CommandResult(success=False, error=f"User {username} not found")
        except Exception as e:
            return CommandResult(success=False, error=str(e))

    def reload(self):
        _run(['sc', 'stop', 'FileZilla Server'])
        import time
        time.sleep(1)
        return _run(['sc', 'start', 'FileZilla Server'])
