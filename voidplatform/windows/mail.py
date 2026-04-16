"""Windows mail management via hMailServer COM automation.

hMailServer is a free, open-source Windows-native mail server supporting
SMTP, IMAP, POP3, SSL/TLS, DKIM, virtual domains, and virtual accounts.
It exposes a COM API for full automation from Python.

Requires: pip install pywin32
Install: https://www.hmailserver.com/download
"""
import os
from ..base import MailManager, CommandResult
from ..config import WindowsPaths as paths

# hMailServer COM API — loaded lazily so the module doesn't crash on Linux
_hmail_app = None


def _get_hmail():
    """Connect to the hMailServer COM object (singleton)."""
    global _hmail_app
    if _hmail_app is not None:
        return _hmail_app
    try:
        import win32com.client
        _hmail_app = win32com.client.Dispatch("hMailServer.Application")
        # Read the admin password
        pw_file = paths.MYSQL_PASSWORD_FILE
        password = 'Administrator'
        if os.path.exists(pw_file):
            with open(pw_file, 'r') as f:
                password = f.read().strip()
        _hmail_app.Authenticate("Administrator", password)
        return _hmail_app
    except Exception as e:
        raise RuntimeError(
            f"Cannot connect to hMailServer COM API: {e}\n"
            f"Ensure hMailServer is installed and running as a Windows service."
        )


def _find_domain(hmail, domain_name):
    """Find a domain in hMailServer by name. Returns (domain_obj, index) or (None, -1)."""
    domains = hmail.Domains
    for i in range(domains.Count):
        d = domains.Item(i)
        if d.Name.lower() == domain_name.lower():
            return d, i
    return None, -1


class WindowsMailManager(MailManager):
    def create_domain(self, domain, username=''):
        try:
            hmail = _get_hmail()
            d, _ = _find_domain(hmail, domain)
            if d:
                return CommandResult(success=True, output=f"Domain {domain} already exists")
            new_domain = hmail.Domains.Add()
            new_domain.Name = domain
            new_domain.Active = True
            new_domain.Save()
            # Create mail directory under user's home
            if username:
                vhost = os.path.join(paths.HOME_BASE, username, 'mail', domain)
            else:
                vhost = os.path.join(paths.HOME_BASE, 'vmail', 'mail', domain)
            os.makedirs(vhost, exist_ok=True)
            return CommandResult(success=True, output=f"Domain {domain} created")
        except Exception as e:
            return CommandResult(success=False, error=str(e))

    def delete_domain(self, domain):
        try:
            hmail = _get_hmail()
            _, idx = _find_domain(hmail, domain)
            if idx < 0:
                return CommandResult(success=False, error=f"Domain {domain} not found")
            hmail.Domains.DeleteByDBID(hmail.Domains.Item(idx).ID)
            return CommandResult(success=True, output=f"Domain {domain} deleted")
        except Exception as e:
            return CommandResult(success=False, error=str(e))

    def create_account(self, email, password, username=''):
        try:
            user, domain = email.split('@')
            hmail = _get_hmail()
            d, _ = _find_domain(hmail, domain)
            if not d:
                # Auto-create the domain
                self.create_domain(domain, username=username)
                d, _ = _find_domain(hmail, domain)
            account = d.Accounts.Add()
            account.Address = email
            account.Password = password
            account.Active = True
            account.MaxSize = 1024  # 1 GB default
            account.Save()
            return CommandResult(success=True, output=f"Account {email} created")
        except Exception as e:
            return CommandResult(success=False, error=str(e))

    def delete_account(self, email):
        try:
            user, domain = email.split('@')
            hmail = _get_hmail()
            d, _ = _find_domain(hmail, domain)
            if not d:
                return CommandResult(success=False, error=f"Domain {domain} not found")
            accounts = d.Accounts
            for i in range(accounts.Count):
                a = accounts.Item(i)
                if a.Address.lower() == email.lower():
                    accounts.DeleteByDBID(a.ID)
                    return CommandResult(success=True, output=f"Account {email} deleted")
            return CommandResult(success=False, error=f"Account {email} not found")
        except Exception as e:
            return CommandResult(success=False, error=str(e))

    def change_account_password(self, email, password):
        try:
            user, domain = email.split('@')
            hmail = _get_hmail()
            d, _ = _find_domain(hmail, domain)
            if not d:
                return CommandResult(success=False, error=f"Domain {domain} not found")
            accounts = d.Accounts
            for i in range(accounts.Count):
                a = accounts.Item(i)
                if a.Address.lower() == email.lower():
                    a.Password = password
                    a.Save()
                    return CommandResult(success=True, output=f"Password changed for {email}")
            return CommandResult(success=False, error=f"Account {email} not found")
        except Exception as e:
            return CommandResult(success=False, error=str(e))

    def reload(self):
        # hMailServer picks up changes immediately via COM — no reload needed
        return CommandResult(success=True, output="hMailServer applies changes immediately")
