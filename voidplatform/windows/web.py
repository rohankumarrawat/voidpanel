"""Windows nginx management (nginx for Windows)."""
import os
import subprocess
import shutil
from ..base import WebServerManager, CommandResult
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


class WindowsWebServerManager(WebServerManager):
    def _nginx_exe(self):
        return os.path.join(paths.NGINX_DIR, 'nginx.exe')

    def create_site(self, domain, root_dir, php_version='', ssl=False):
        conf = self.get_site_config_path(domain)
        os.makedirs(os.path.dirname(conf), exist_ok=True)

        # Convert backslashes to forward slashes for nginx config
        nginx_root = root_dir.replace('\\', '/')

        block = f"server {{\n    listen 80;\n    server_name {domain} www.{domain};\n"
        block += f"    root {nginx_root};\n    index index.html index.php;\n\n"
        block += "    location / {\n        try_files $uri $uri/ =404;\n    }\n"
        if php_version:
            # Windows uses php-cgi via FastCGI over TCP instead of Unix socket
            block += f"\n    location ~ \\.php$ {{\n"
            block += f"        fastcgi_pass 127.0.0.1:{paths.PHP_CGI_PORT};\n"
            block += f"        fastcgi_index index.php;\n"
            block += f"        fastcgi_param SCRIPT_FILENAME $document_root$fastcgi_script_name;\n"
            block += f"        include fastcgi_params;\n    }}\n"
        block += "}\n"
        try:
            with open(conf, 'w') as f:
                f.write(block)
            return self.enable_site(domain)
        except Exception as e:
            return CommandResult(success=False, error=str(e))

    def delete_site(self, domain):
        self.disable_site(domain)
        try:
            conf = self.get_site_config_path(domain)
            if os.path.exists(conf):
                os.remove(conf)
            return self.reload()
        except Exception as e:
            return CommandResult(success=False, error=str(e))

    def enable_site(self, domain):
        avail = self.get_site_config_path(domain)
        enabled = os.path.join(paths.NGINX_SITES_ENABLED, f'{domain}.conf')
        os.makedirs(paths.NGINX_SITES_ENABLED, exist_ok=True)
        try:
            # Windows doesn't support symlinks without admin; copy instead
            shutil.copy2(avail, enabled)
            return CommandResult(success=True)
        except Exception as e:
            return CommandResult(success=False, error=str(e))

    def disable_site(self, domain):
        enabled = os.path.join(paths.NGINX_SITES_ENABLED, f'{domain}.conf')
        try:
            if os.path.exists(enabled):
                os.remove(enabled)
            return CommandResult(success=True)
        except Exception as e:
            return CommandResult(success=False, error=str(e))

    def test_config(self):
        return _run([self._nginx_exe(), '-t'])

    def reload(self):
        test = self.test_config()
        if not test.success:
            return test
        return _run([self._nginx_exe(), '-s', 'reload'])

    def get_site_config_path(self, domain):
        os.makedirs(paths.NGINX_SITES_AVAILABLE, exist_ok=True)
        return os.path.join(paths.NGINX_SITES_AVAILABLE, f'{domain}.conf')
