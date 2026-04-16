"""Windows BIND9 DNS zone management (ISC BIND for Windows)."""
import os
import re
import subprocess
import time
from ..base import DNSManager, CommandResult
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


class WindowsDNSManager(DNSManager):
    def _zone_file(self, domain):
        os.makedirs(paths.BIND_ZONE_DIR, exist_ok=True)
        return os.path.join(paths.BIND_ZONE_DIR, f'db.{domain}')

    def create_zone(self, domain, ip, ns1='', ns2=''):
        ns1 = ns1 or f'ns1.{domain}'
        ns2 = ns2 or f'ns2.{domain}'
        serial = int(time.strftime('%Y%m%d')) * 100 + 1
        zone = (f"$TTL 86400\n"
                f"@   IN  SOA {ns1}. admin.{domain}. (\n"
                f"        {serial}  ; Serial\n"
                f"        3600      ; Refresh\n"
                f"        1800      ; Retry\n"
                f"        604800    ; Expire\n"
                f"        86400 )   ; Minimum TTL\n\n"
                f"@   IN  NS  {ns1}.\n@   IN  NS  {ns2}.\n"
                f"@   IN  A   {ip}\nwww IN  A   {ip}\n")
        zf = self._zone_file(domain)
        try:
            with open(zf, 'w') as f:
                f.write(zone)
            # Use forward slashes in BIND config paths
            zf_bind = zf.replace('\\', '/')
            conf_dir = os.path.dirname(paths.BIND_CONF_LOCAL)
            os.makedirs(conf_dir, exist_ok=True)
            with open(paths.BIND_CONF_LOCAL, 'a') as f:
                f.write(f'\nzone "{domain}" {{\n    type master;\n    file "{zf_bind}";\n}};\n')
            return self.reload()
        except Exception as e:
            return CommandResult(success=False, error=str(e))

    def delete_zone(self, domain):
        zf = self._zone_file(domain)
        try:
            if os.path.exists(zf):
                os.remove(zf)
            if os.path.exists(paths.BIND_CONF_LOCAL):
                with open(paths.BIND_CONF_LOCAL, 'r') as f:
                    content = f.read()
                content = re.sub(
                    rf'\s*zone\s+"{re.escape(domain)}"\s*\{{[^}}]*\}};?\s*',
                    '\n', content)
                with open(paths.BIND_CONF_LOCAL, 'w') as f:
                    f.write(content)
            return self.reload()
        except Exception as e:
            return CommandResult(success=False, error=str(e))

    def add_record(self, domain, record_type, name, value, ttl=3600):
        try:
            with open(self._zone_file(domain), 'a') as f:
                f.write(f'{name} {ttl} IN {record_type} {value}\n')
            return self.reload()
        except Exception as e:
            return CommandResult(success=False, error=str(e))

    def delete_record(self, domain, record_type, name):
        zf = self._zone_file(domain)
        try:
            with open(zf, 'r') as f:
                lines = f.readlines()
            with open(zf, 'w') as f:
                for l in lines:
                    parts = l.split()
                    if len(parts) >= 4 and parts[0] == name and record_type in parts:
                        continue
                    f.write(l)
            return self.reload()
        except Exception as e:
            return CommandResult(success=False, error=str(e))

    def check_zone(self, domain):
        # named-checkzone is available in BIND9 for Windows
        return _run(['named-checkzone', domain, self._zone_file(domain)])

    def reload(self):
        # rndc is available in BIND9 for Windows
        return _run(['rndc', 'reload'])
