"""Linux Postfix/Dovecot mail management."""
import os
import subprocess
from ..base import MailManager, CommandResult
from ..config import LinuxPaths as paths


def _run(cmd, **kwargs):
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=30, **kwargs)
        return CommandResult(success=r.returncode == 0, output=r.stdout.strip(),
                             error=r.stderr.strip(), return_code=r.returncode)
    except Exception as e:
        return CommandResult(success=False, error=str(e), return_code=-1)


class LinuxMailManager(MailManager):
    def create_domain(self, domain, username=''):
        try:
            with open(paths.POSTFIX_VIRTUAL_DOMAINS, 'a') as f:
                f.write(f'{domain}\n')
            _run(['sudo', 'postmap', paths.POSTFIX_VIRTUAL_DOMAINS])
            if username:
                vhost = os.path.join(paths.HOME_BASE, username, 'mail', domain)
            else:
                vhost = os.path.join(paths.HOME_BASE, 'vmail', 'mail', domain)
            os.makedirs(vhost, exist_ok=True)
            _run(['sudo', 'chown', '-R', 'vmail:vmail', vhost])
            return self.reload()
        except Exception as e:
            return CommandResult(success=False, error=str(e))

    def delete_domain(self, domain):
        try:
            with open(paths.POSTFIX_VIRTUAL_DOMAINS, 'r') as f:
                lines = f.readlines()
            with open(paths.POSTFIX_VIRTUAL_DOMAINS, 'w') as f:
                f.writelines(l for l in lines if l.strip() != domain)
            _run(['sudo', 'postmap', paths.POSTFIX_VIRTUAL_DOMAINS])
            return self.reload()
        except Exception as e:
            return CommandResult(success=False, error=str(e))

    def create_account(self, email, password, username=''):
        user, domain = email.split('@')
        r = _run(['doveadm', 'pw', '-s', 'SHA512-CRYPT', '-p', password])
        if not r.success:
            return r
        pw_hash = r.output.strip()
        try:
            owner = username or 'vmail'
            basedir = os.path.join(paths.HOME_BASE, owner, 'mail', domain, user)
            with open(paths.DOVECOT_USERS, 'a') as f:
                f.write(f'{email}:{pw_hash}:5000:5000::{basedir}\n')
            with open(paths.POSTFIX_VIRTUAL_MAILBOX, 'a') as f:
                f.write(f'{email} {domain}/{user}/\n')
            _run(['sudo', 'postmap', paths.POSTFIX_VIRTUAL_MAILBOX])
            os.makedirs(basedir, exist_ok=True)
            mail_root = os.path.join(paths.HOME_BASE, owner, 'mail')
            _run(['sudo', 'chown', '-R', 'vmail:vmail', mail_root])
            return self.reload()
        except Exception as e:
            return CommandResult(success=False, error=str(e))

    def delete_account(self, email):
        try:
            with open(paths.DOVECOT_USERS, 'r') as f:
                lines = f.readlines()
            with open(paths.DOVECOT_USERS, 'w') as f:
                f.writelines(l for l in lines if not l.startswith(f'{email}:'))
            with open(paths.POSTFIX_VIRTUAL_MAILBOX, 'r') as f:
                lines = f.readlines()
            with open(paths.POSTFIX_VIRTUAL_MAILBOX, 'w') as f:
                f.writelines(l for l in lines if not l.startswith(f'{email} '))
            _run(['sudo', 'postmap', paths.POSTFIX_VIRTUAL_MAILBOX])
            return self.reload()
        except Exception as e:
            return CommandResult(success=False, error=str(e))

    def change_account_password(self, email, password):
        r = _run(['doveadm', 'pw', '-s', 'SHA512-CRYPT', '-p', password])
        if not r.success:
            return r
        pw_hash = r.output.strip()
        try:
            with open(paths.DOVECOT_USERS, 'r') as f:
                lines = f.readlines()
            with open(paths.DOVECOT_USERS, 'w') as f:
                for line in lines:
                    if line.startswith(f'{email}:'):
                        f.write(f'{email}:{pw_hash}\n')
                    else:
                        f.write(line)
            return self.reload()
        except Exception as e:
            return CommandResult(success=False, error=str(e))

    def reload(self):
        _run(['sudo', 'systemctl', 'reload', 'postfix'])
        return _run(['sudo', 'systemctl', 'reload', 'dovecot'])

def apply_global_email_config(config):
    """Applies global email configurations from the database to Postfix and SpamAssassin."""
    try:
        # Convert MB to bytes for Postfix message_size_limit
        max_bytes = int(config.max_attachment_size_mb) * 1024 * 1024
        _run(['sudo', 'postconf', '-e', f'message_size_limit = {max_bytes}'])

        # Concurrent connections limit per client
        conn_limit = int(config.max_concurrent_connections)
        _run(['sudo', 'postconf', '-e', f'smtpd_client_connection_count_limit = {conn_limit}'])

        # Native hourly limit capability using anvil_rate_time_unit and message_rate_limit
        hourly = int(config.hourly_limit)
        _run(['sudo', 'postconf', '-e', 'anvil_rate_time_unit = 3600s'])
        _run(['sudo', 'postconf', '-e', f'smtpd_client_message_rate_limit = {hourly}'])

        # Antispam adjustments if SpamAssassin is installed
        if config.enable_antispam:
            sa_cmd = (
                "if [ -f /etc/spamassassin/local.cf ]; then "
                "sed -i -E 's/^[#\s]*required_score\s+.*/required_score " + str(config.spam_score_threshold) + "/g' /etc/spamassassin/local.cf; "
                "systemctl reload spamassassin || true; "
                "fi"
            )
            _run(['sudo', 'bash', '-c', sa_cmd])

        # Reload settings across the cluster
        _run(['sudo', 'systemctl', 'reload', 'postfix'])
        return True
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Failed to apply global email config: {str(e)}")
        return False

