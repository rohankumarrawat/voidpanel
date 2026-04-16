"""Linux SSL management via certbot."""
import os
import subprocess
from ..base import SSLManager, CommandResult
from ..config import LinuxPaths as paths


def _run(cmd, **kwargs):
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=120, **kwargs)
        return CommandResult(success=r.returncode == 0, output=r.stdout.strip(),
                             error=r.stderr.strip(), return_code=r.returncode)
    except Exception as e:
        return CommandResult(success=False, error=str(e), return_code=-1)


class LinuxSSLManager(SSLManager):
    def provision(self, domain, webroot='', email=''):
        cmd = ['sudo', 'certbot', '--nginx', '-d', domain,
               '--non-interactive', '--agree-tos']
        if email:
            cmd += ['-m', email]
        else:
            cmd += ['--register-unsafely-without-email']
        return _run(cmd)

    def revoke(self, domain):
        return _run(['sudo', 'certbot', 'revoke',
                      '--cert-path', self.get_cert_path(domain),
                      '--non-interactive'])

    def get_cert_path(self, domain):
        return os.path.join(paths.LETSENCRYPT_LIVE, domain, 'fullchain.pem')

    def get_key_path(self, domain):
        return os.path.join(paths.LETSENCRYPT_LIVE, domain, 'privkey.pem')

    def generate_self_signed(self, domain, cert_path, key_path):
        return _run(['openssl', 'req', '-x509', '-nodes', '-days', '365',
                      '-newkey', 'rsa:2048', '-keyout', key_path,
                      '-out', cert_path, '-subj', f'/CN={domain}'])
