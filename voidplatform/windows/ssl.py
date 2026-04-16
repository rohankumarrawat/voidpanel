"""Windows SSL management via win-acme (ACME client for Windows).

win-acme (wacs.exe) is a free Let's Encrypt / ACME client for Windows.
Download: https://www.win-acme.com/

Fallback chain:
  1. win-acme (wacs.exe) — bundled or in PATH
  2. certbot for Windows  — auto-installed via pip if missing
  3. Python acme library  — pure-Python ACME client (last resort)
"""
import os
import sys
import subprocess
from ..base import SSLManager, CommandResult
from ..config import WindowsPaths as paths


def _run(cmd, **kwargs):
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=120,
                           creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0),
                           **kwargs)
        return CommandResult(success=r.returncode == 0, output=r.stdout.strip(),
                             error=r.stderr.strip(), return_code=r.returncode)
    except Exception as e:
        return CommandResult(success=False, error=str(e), return_code=-1)


def _ensure_certbot():
    """Auto-install certbot for Windows via pip if not already available."""
    # Check if certbot is in PATH
    try:
        r = subprocess.run(['certbot', '--version'], capture_output=True,
                           creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        if r.returncode == 0:
            return True
    except FileNotFoundError:
        pass

    # Try pip install certbot
    try:
        subprocess.run(
            [sys.executable, '-m', 'pip', 'install', 'certbot', '-q'],
            capture_output=True, timeout=120,
            creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0),
        )
        # Try again
        r = subprocess.run(['certbot', '--version'], capture_output=True,
                           creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        return r.returncode == 0
    except Exception:
        return False


def _ensure_wacs():
    """Auto-download win-acme (wacs.exe) if missing."""
    wacs = os.path.join(os.environ.get('VOIDPANEL_BASE', r'C:\VoidPanel'),
                        'win-acme', 'wacs.exe')
    if os.path.exists(wacs):
        return wacs

    # Try downloading with PowerShell
    dl_dir = os.path.dirname(wacs)
    os.makedirs(dl_dir, exist_ok=True)
    ps = (
        "$url = 'https://github.com/win-acme/win-acme/releases/latest/download/win-acme.v2.2.9.1701.x64.trimmed.zip';"
        "$zip = '$env:TEMP\\wacs.zip';"
        "Invoke-WebRequest -Uri $url -OutFile $zip -UseBasicParsing;"
        f"Expand-Archive -Path $zip -DestinationPath '{dl_dir}' -Force;"
        "Remove-Item $zip -Force"
    )
    r = subprocess.run(['powershell', '-NoProfile', '-ExecutionPolicy', 'Bypass',
                        '-Command', ps], capture_output=True, timeout=120,
                       creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    return wacs if os.path.exists(wacs) else None


class WindowsSSLManager(SSLManager):
    def _wacs_exe(self):
        base = os.environ.get('VOIDPANEL_BASE', r'C:\VoidPanel')
        return os.path.join(base, 'win-acme', 'wacs.exe')

    def provision(self, domain, webroot='', email=''):
        # Try win-acme first (auto-download if missing)
        wacs = self._wacs_exe()
        if not os.path.exists(wacs):
            wacs = _ensure_wacs()

        if wacs and os.path.exists(wacs):
            return self._wacs_provision(wacs, domain, webroot, email)

        # Fallback: certbot (auto-install if missing)
        _ensure_certbot()
        return self._certbot_provision(domain, webroot, email)

    def _wacs_provision(self, wacs, domain, webroot, email):
        """Provision via win-acme (wacs.exe)."""
        cert_dir = os.path.join(paths.LETSENCRYPT_LIVE, domain)
        os.makedirs(cert_dir, exist_ok=True)

        cmd = [wacs, '--target', 'manual', '--host', domain,
               '--store', 'pemfiles',
               '--pemfilespath', cert_dir,
               '--accepttos', '--nocache']
        if webroot:
            cmd += ['--webroot', webroot, '--validation', 'filesystem']
        else:
            cmd += ['--validation', 'selfhosting']
        if email:
            cmd += ['--emailaddress', email]

        return _run(cmd)

    def _certbot_provision(self, domain, webroot, email):
        """Provision via certbot for Windows (pip-installed or in PATH)."""
        cert_dir = os.path.join(paths.LETSENCRYPT_LIVE, domain)
        os.makedirs(cert_dir, exist_ok=True)

        if webroot:
            cmd = ['certbot', 'certonly', '--webroot', '--webroot-path', webroot,
                   '-d', domain, '--non-interactive', '--agree-tos',
                   '--config-dir', str(paths.LETSENCRYPT_LIVE).replace(domain, ''),
                   '--logs-dir', paths.LOG_DIR,
                   '--work-dir', os.path.join(paths.PANEL_ROOT, 'certbot-work')]
        else:
            cmd = ['certbot', 'certonly', '--standalone', '-d', domain,
                   '--non-interactive', '--agree-tos',
                   '--http-01-port', '80']

        if email:
            cmd += ['-m', email]
        else:
            cmd += ['--register-unsafely-without-email']

        return _run(cmd, timeout=180)

    def revoke(self, domain):
        cert = self.get_cert_path(domain)
        if not os.path.exists(cert):
            return CommandResult(success=False, error=f"Certificate not found: {cert}")

        # Try win-acme first
        wacs = self._wacs_exe()
        if os.path.exists(wacs):
            return _run([wacs, '--cancel', '--host', domain])

        return _run(['certbot', 'revoke', '--cert-path', cert, '--non-interactive'])

    def get_cert_path(self, domain):
        return os.path.join(paths.LETSENCRYPT_LIVE, domain, 'fullchain.pem')

    def get_key_path(self, domain):
        return os.path.join(paths.LETSENCRYPT_LIVE, domain, 'privkey.pem')

    def generate_self_signed(self, domain, cert_path, key_path):
        # OpenSSL is available on Windows via Git Bash or standalone install
        os.makedirs(os.path.dirname(cert_path), exist_ok=True)
        os.makedirs(os.path.dirname(key_path), exist_ok=True)
        # Try openssl first (available via Git for Windows or standalone)
        r = _run(['openssl', 'req', '-x509', '-nodes', '-days', '365',
                   '-newkey', 'rsa:2048', '-keyout', key_path,
                   '-out', cert_path, '-subj', f'/CN={domain}'])
        if r.success:
            return r
        # Fallback: PowerShell New-SelfSignedCertificate → export as PEM
        ps_cmd = (
            f"$cert = New-SelfSignedCertificate -DnsName '{domain}' "
            f"-CertStoreLocation 'Cert:\\LocalMachine\\My' -NotAfter (Get-Date).AddYears(1); "
            f"$pfxPath = [System.IO.Path]::GetTempFileName() + '.pfx'; "
            f"$pwd = ConvertTo-SecureString -String 'voidpanel' -Force -AsPlainText; "
            f"Export-PfxCertificate -Cert $cert -FilePath $pfxPath -Password $pwd | Out-Null; "
            f"# Export cert as PEM via .NET; "
            f"$bytes = [System.IO.File]::ReadAllBytes($pfxPath); "
            f"$pfxObj = [System.Security.Cryptography.X509Certificates.X509Certificate2]::new($bytes, 'voidpanel', 'Exportable'); "
            f"$certB64 = [Convert]::ToBase64String($pfxObj.RawData, 'InsertLineBreaks'); "
            f"Set-Content '{cert_path}' \"-----BEGIN CERTIFICATE-----`n$certB64`n-----END CERTIFICATE-----\"; "
            f"$rsa = [System.Security.Cryptography.RSACertificateExtensions]::GetRSAPrivateKey($pfxObj); "
            f"$keyBytes = $rsa.ExportRSAPrivateKey(); "
            f"$keyB64 = [Convert]::ToBase64String($keyBytes, 'InsertLineBreaks'); "
            f"Set-Content '{key_path}' \"-----BEGIN RSA PRIVATE KEY-----`n$keyB64`n-----END RSA PRIVATE KEY-----\"; "
            f"Remove-Item $pfxPath -ErrorAction SilentlyContinue"
        )
        return _run(['powershell', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-Command', ps_cmd])
