
import subprocess
import socket
import os
import sys
import mimetypes
import stat
import random
import re
import shlex
import requests
try:
    import mysql.connector
    from mysql.connector import Error
except ImportError:
    try:
        import pymysql as mysql
        Error = Exception
    except ImportError:
        mysql = None
        Error = Exception
from voidplatform import get_platform
from voidplatform.config import paths


def _validate_sql_identifier(name):
    """Validate a SQL identifier (database name, username) to prevent injection."""
    if not name or not re.match(r'^[a-zA-Z0-9_.-]+$', name):
        raise ValueError(f'Invalid SQL identifier: {name!r}')
    return name


def _validate_domain(domain):
    """Validate a domain name to prevent command injection via shell calls.

    Accepts standard domain names (e.g. example.com, sub.example.co.uk).
    Raises ValueError for anything containing shell metacharacters.
    """
    if not domain or not re.match(r'^[a-zA-Z0-9]([a-zA-Z0-9-]*[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9-]*[a-zA-Z0-9])?)*$', domain):
        raise ValueError(f'Invalid domain name: {domain!r}')
    if len(domain) > 253:
        raise ValueError(f'Domain name too long: {domain!r}')
    return domain


def _validate_path(path):
    """Validate a filesystem path to prevent command injection.

    Only allows alphanumerics, slashes, dots, hyphens, underscores.
    """
    if not path or not re.match(r'^[a-zA-Z0-9/._ -]+$', path):
        raise ValueError(f'Invalid path: {path!r}')
    if '..' in path:
        raise ValueError(f'Path traversal not allowed: {path!r}')
    return path


_ALLOWED_MYSQL_PRIVILEGES = frozenset({
    'ALL PRIVILEGES', 'SELECT', 'INSERT', 'UPDATE', 'DELETE',
    'CREATE', 'DROP', 'ALTER', 'INDEX', 'REFERENCES', 'EXECUTE',
    'CREATE TEMPORARY TABLES', 'LOCK TABLES', 'TRIGGER',
})

def is_website_live(url):
    """
    Check if a website is live. Tries HTTPS first, falls back to HTTP.
    Accepts any non-server-error response as 'live'.
    SSL cert verification is intentionally skipped — we only care if the
    site responds, not whether its certificate chain is trusted.
    """
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    domain = url.replace('http://', '').replace('https://', '').rstrip('/')
    attempts = [
        f"https://{domain}",
        f"http://{domain}",
        f"https://www.{domain}",
        f"http://www.{domain}",
    ]
    for attempt_url in attempts:
        try:
            resp = requests.get(
                attempt_url,
                timeout=8,
                allow_redirects=True,
                verify=False,                         # skip SSL cert verification
                stream=True,                          # avoid downloading full body
                headers={'User-Agent': 'VoidPanel/1.0 SiteCheck'},
            )
            resp.close()
            if resp.status_code < 600:                # any real response = live
                return True
        except Exception:
            continue
    return False
def get_random_port(excluded_ports=None):
    # Define the range of ports
    min_port = 1024
    max_port = 49151
    
    # Set default excluded_ports if not provided
    if excluded_ports is None:
        excluded_ports = set()
    
    # Create a list of all ports in the specified range
    all_ports = list(range(min_port, max_port + 1))
    
    # Filter out the excluded ports
    available_ports = [port for port in all_ports if port not in excluded_ports]
    
    # Check if there are available ports
    if not available_ports:
        raise ValueError("No available ports left after exclusion.")
    
    # Select a random port from the available ports
    return random.choice(available_ports)

def get_server_ip():
    """Get the server's IP address."""
    try:
        response = requests.get('https://api.ipify.org', timeout=1.5)
        public_ip = response.text
        return public_ip
    except Exception as e:
        print(f"Error getting server IP address: {e}")
        return None
    

def run_command(command, check=True):
    """Run a shell command and optionally check for errors.

    SECURITY: Only pass *trusted* commands — never embed unsanitised user input.
    For user-supplied arguments, use run_command_safe() or shlex.quote().
    """
    result = subprocess.run(command, shell=True, check=check, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return result


def run_command_safe(args, check=True):
    """Run a command as a list (no shell) to avoid injection."""
    result = subprocess.run(args, check=check, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return result

import subprocess
import sys

def change_hostname(new_hostname):
    try:
        # Validate hostname: only allow safe characters
        import re
        if not re.match(r'^[a-zA-Z0-9._-]{1,253}$', new_hostname):
            print(f'Invalid hostname: {new_hostname!r}. Only alphanumeric, dots, underscores and hyphens allowed.')
            return

        # Change the hostname (platform-aware)
        if sys.platform == 'win32':
            subprocess.run(['powershell', '-Command', f'Rename-Computer -NewName "{new_hostname}" -Force'], check=True)
        else:
            subprocess.run(['sudo', 'hostnamectl', 'set-hostname', new_hostname], check=True)

        # Update hosts file
        hosts_file = paths.HOSTS_FILE
        with open(hosts_file, 'r') as file:
            lines = file.readlines()

        settings_path = os.path.join(paths.PANEL_ROOT, 'panel', 'settings.py')
        with open(settings_path, 'a+') as file:
            file.write('\n')
            file.write(f'CSRF_TRUSTED_ORIGINS.extend(["http://{new_hostname}", "http://{new_hostname}:8080", "https://{new_hostname}", "https://{new_hostname}:8082"])')

        with open(hosts_file, 'w') as file:
            for line in lines:
                if '127.0.1.1' in line:
                    file.write(f'127.0.1.1\t{new_hostname}\n')
                else:
                    file.write(line)

        print(f'Successfully changed hostname to: {new_hostname}')
    except subprocess.CalledProcessError as e:
        print(f'Error changing hostname: {e}')
    except PermissionError:
        print('Permission denied. Please run this script with sudo.')
    except Exception as e:
        print(f'An error occurred: {e}')
   
def hostnamessl(hostname,email,xx):
        plat = get_platform()
        get_platform().ssl.provision(hostname, email=email)
        old_hostname=socket.gethostname()
        sites_dir = paths.NGINX_SITES_AVAILABLE
        for site in ['panel', 'phpmyadmin', 'roundcube']:
            site_path = os.path.join(sites_dir, site)
            if os.path.exists(site_path):
                with open(site_path, 'r') as f:
                    content = f.read()
                content = content.replace(paths.SSL_DUMMY_CERT, f'{paths.LETSENCRYPT_LIVE}/{hostname}/fullchain.pem')
                content = content.replace(paths.SSL_DUMMY_KEY, f'{paths.LETSENCRYPT_LIVE}/{hostname}/privkey.pem')
                
                if old_hostname and old_hostname != hostname:
                    import re
                    suffix = ""
                    if hostname.startswith(old_hostname):
                        suffix = hostname[len(old_hostname):]
                    
                    esc_old = re.escape(old_hostname)
                    esc_suf = re.escape(suffix) if suffix else ""
                    
                    pattern = rf'\b{esc_old}\b'
                    if esc_suf:
                        pattern += rf'(?!{esc_suf})'
                        
                    content = re.sub(pattern, hostname, content)
                    content = content.replace(f'{paths.LETSENCRYPT_LIVE}/{old_hostname}/', f'{paths.LETSENCRYPT_LIVE}/{hostname}/')
                with open(site_path, 'w') as f:
                    f.write(content)
        plat.services.reload('nginx')
        import time
        time.sleep(2)


def get_file_info(directory):
    files = []
    directories = []
    others = []

    try:
        for item in os.listdir(directory):
            item_path = os.path.join(directory, item)

            # Get file type and permissions
            if os.path.isfile(item_path):
                file_size = os.path.getsize(item_path)
                file_type, _ = mimetypes.guess_type(item_path)
                file_permissions = stat.filemode(os.stat(item_path).st_mode)

                files.append({
                    'name': item,
                    'size': file_size//1024,
                    'type': file_type if file_type else 'Unknown',
                    'permissions': file_permissions
                })

            elif os.path.isdir(item_path):
                dir_permissions = stat.filemode(os.stat(item_path).st_mode)
                directories.append({
                     'name': item,
                    'size': '-',
                    'type': 'Directory',
                    'permissions': dir_permissions
                })

            else:
                other_permissions = stat.filemode(os.stat(item_path).st_mode)
                others.append({
                    'name': item,
                    'permissions': other_permissions
                })
        # files=files.sort()
        # directories=directories.sort()
        # others=others.sort()
    
    except PermissionError:
        print(f"Permission denied for directory: {directory}. Attempting sudo fallback...")
        try:
            import json, subprocess
            py_code = """
import sys, os, stat, mimetypes, json
d = sys.argv[1]
try:
    files=[]; dirs=[]; others=[]
    for i in os.listdir(d):
        p = os.path.join(d, i)
        try:
            m = stat.filemode(os.stat(p).st_mode)
            if os.path.isfile(p):
                t = mimetypes.guess_type(p)[0] or 'Unknown'
                files.append({'name': i, 'size': os.path.getsize(p)//1024, 'type': t, 'permissions': m})
            elif os.path.isdir(p):
                dirs.append({'name': i, 'size': '-', 'type': 'Directory', 'permissions': m})
            else:
                others.append({'name': i, 'permissions': m})
        except Exception:
            pass
    print(json.dumps({'files': files, 'directories': dirs, 'others': others}))
except Exception as e:
    print(json.dumps({'error': str(e)}))
"""
            out = subprocess.run(['sudo', 'python3', '-c', py_code, directory], capture_output=True, text=True, check=True)
            data = json.loads(out.stdout)
            if 'error' not in data:
                return data
        except Exception as e:
            print(f"Sudo fallback listdir failed: {e}")
    except OSError as e:
        print(f"Error accessing directory {directory}: {e}")

    return {
        'files': files,
        'directories': directories,
        'others': others
    }


import zipfile

def zip_files_and_folders(zip_filename, paths):
    print("rohan")
    with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for path in paths:
      
            if os.path.isfile(path):
                # Add a single file
                zipf.write(path, arcname=os.path.basename(path))
            elif os.path.isdir(path):
                # Add a directory
                parent_dir = os.path.dirname(path)
                for root, dirs, files in os.walk(path):
                    for file in files:
                        filepath = os.path.join(root, file)
                        # Write the file with relative path inside the zip
                        zipf.write(filepath, arcname=os.path.relpath(filepath, parent_dir))
            else:
                print(f"Skipping {path}, it is neither a file nor a directory.")


def extract_zip_with_error_handling(zip_filename, extract_to_folder):
    
        if not os.path.exists(extract_to_folder):
            os.makedirs(extract_to_folder)

        abs_dest = os.path.realpath(extract_to_folder)
        with zipfile.ZipFile(zip_filename, 'r') as zip_ref:
            for member in zip_ref.infolist():
                member_path = os.path.realpath(os.path.join(extract_to_folder, member.filename))
                if not member_path.startswith(abs_dest + os.sep) and member_path != abs_dest:
                    raise ValueError(f'Zip entry would escape target directory: {member.filename}')
            zip_ref.extractall(extract_to_folder)



def generate_ssl_certificates(domain, ssl_dir, logs):
    import subprocess, tempfile
    cert_path = os.path.join(ssl_dir, f"{domain}.crt")
    key_path = os.path.join(ssl_dir, f"{domain}.key")

    # Ensure SSL directory exists — use sudo since dir may be root-owned
    if sys.platform != 'win32':
        from voidplatform.config import get_web_user
        _wu = get_web_user()
        subprocess.run(['sudo', 'mkdir', '-p', ssl_dir], check=False)
        subprocess.run(['sudo', 'chown', f'{_wu}:{_wu}', ssl_dir], check=False)
        subprocess.run(['sudo', 'mkdir', '-p', logs], check=False)
        subprocess.run(['sudo', 'chown', f'{_wu}:{_wu}', logs], check=False)
    else:
        os.makedirs(ssl_dir, exist_ok=True)

    log_msg = ''
    try:
        get_platform().ssl.generate_self_signed(domain, cert_path, key_path)
        log_msg = f"\nSSL certificate and key generated for {domain} at {ssl_dir}"
        print(log_msg)
    except Exception as e:
        log_msg = f"\nFailed to generate SSL certificate: {e}"
        print(log_msg)
        return None, None
    finally:
        try:
            with open(os.path.join(logs, 'ssl.txt'), 'a') as _f:
                _f.write(log_msg)
        except Exception:
            pass

    return cert_path, key_path


def create_nginx_ssl_conf(file_path, domain, root_dir, cert_path, key_path):
    # Build PHP FastCGI directive based on platform
    if sys.platform == 'win32':
        php_fastcgi = f"fastcgi_pass 127.0.0.1:{paths.PHP_CGI_PORT};"
    else:
        php_fastcgi = f"fastcgi_pass unix:{paths.PHP_FPM_SOCK.format(version='8.3')};"

    nginx_ssl_conf = f"""
server {{
    listen 443 ssl;
    server_name {domain} www.{domain};
    client_max_body_size 1500M;

    ssl_certificate {cert_path};
    ssl_certificate_key {key_path};

    access_log /var/log/nginx/{domain}.access.log;
    error_log  /var/log/nginx/{domain}.error.log;

    # Security Headers
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;

    root {root_dir};
    index index.php index.html index.htm;

    location /vpanel {{
        return 301 https://$host:8082;
    }}

    location /control/ {{
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }}

    # Route all requests through index.php (required for WordPress, Laravel, etc.)
    location / {{
        try_files $uri $uri/ /index.php?$args;
    }}

    location ~ \\.php$ {{
        include snippets/fastcgi-php.conf;
        {php_fastcgi}
        fastcgi_param SCRIPT_FILENAME $document_root$fastcgi_script_name;
        include fastcgi_params;
        fastcgi_read_timeout 300;
        fastcgi_connect_timeout 300;
        fastcgi_send_timeout 300;
    }}

    location ~ /\\.ht {{
        deny all;
    }}
}}


server {{
    listen 80;
    server_name {domain};
    return 301 https://$host$request_uri;
}}
"""

    try:
        import tempfile, subprocess
        with tempfile.NamedTemporaryFile('w', delete=False) as f:
            f.write(nginx_ssl_conf)
            tmp = f.name
        subprocess.run(['sudo', 'cp', tmp, file_path], check=False)
        os.unlink(tmp)
        get_platform().services.reload('nginx')
        print(f"Nginx SSL configuration file created at: {file_path}")
    except OSError as e:
        print(f"Error creating Nginx configuration file: {e}")
           

# def generate_dkim_keys(domain, key_dir):
#     """Generate DKIM keys for a domain and save them to the specified directory."""
#     os.makedirs(key_dir, exist_ok=True)
    
#     # Generate DKIM keys
#     private_key_path = os.path.join(key_dir, 'default.private')
#     public_key_path = os.path.join(key_dir, 'default.txt')

#     subprocess.run([
#         'opendkim-genkey', '-t', '-s', 'default', '-d', domain, '-b', '2048', '-r', '-v'
#     ], check=True)
    
#     # Move generated keys to the specified directory
#     os.rename('default.private', private_key_path)
#     os.rename('default.txt', public_key_path)

#     print(f"DKIM keys generated for {domain}.")
#     return private_key_path, public_key_path
def generate_dkim_keys(domain, key_dir):
    """Generate DKIM keys for a domain and save them to the specified directory."""
    import subprocess
    _validate_domain(domain)
    _validate_path(key_dir)

    subprocess.run(['sudo', 'mkdir', '-p', key_dir], check=False)

    private_key_path = os.path.join(key_dir, 'default.private')
    public_key_path = os.path.join(key_dir, 'default.txt')

    if sys.platform == 'win32':
        # On Windows use openssl to generate DKIM RSA key pair
        subprocess.run([
            'openssl', 'genrsa', '-out', private_key_path, '2048'
        ], check=True)
        subprocess.run([
            'openssl', 'rsa', '-in', private_key_path, '-pubout', '-out', public_key_path
        ], check=True)
    else:
        subprocess.run([
            'sudo', 'opendkim-genkey', '-t', '-s', 'default',
            '-d', domain, '-b', '2048', '-D', key_dir, '-r', '-v'
        ], check=True)
        
        # Determine the web server group dynamically (www-data or nginx)
        web_group = 'www-data'
        try:
            import grp
            grp.getgrnam('www-data')
        except KeyError:
            try:
                grp.getgrnam('nginx')
                web_group = 'nginx'
            except KeyError:
                web_group = 'opendkim'
                
        subprocess.run(['sudo', 'chown', '-R', f'opendkim:{web_group}', key_dir], check=False)
        subprocess.run(['sudo', 'chmod', '750', key_dir], check=False)
        subprocess.run(['sudo', 'chmod', '600', os.path.join(key_dir, 'default.private')], check=False)
        subprocess.run(['sudo', 'chmod', '644', os.path.join(key_dir, 'default.txt')], check=False)
        
        # Self-healing parent directory permission repair
        subprocess.run(['sudo', 'chmod', '750', '/etc/opendkim'], check=False)
        subprocess.run(['sudo', 'chmod', '750', '/etc/opendkim/keys'], check=False)
        subprocess.run(['sudo', 'chown', f'opendkim:{web_group}', '/etc/opendkim'], check=False)
        subprocess.run(['sudo', 'chown', f'opendkim:{web_group}', '/etc/opendkim/keys'], check=False)

    print(f"DKIM keys generated for {domain}.")
    return private_key_path, public_key_path
# def create_bind_records(domain, key_dir, zone_file_path):
#     """Create BIND zone file records including DKIM and other common DNS records."""
#     dkim_record_file = os.path.join(key_dir, 'default.txt')
#     with open(dkim_record_file) as f:
#         dkim_record = f.read().strip()

#     with open(zone_file_path, 'a') as zone_file:
#         # Example BIND records
       
        
#         # Example A record
#         zone_file.write(f"\n; A Record\n")
#         zone_file.write(f"@ IN A 192.0.2.1\n")
        
#         # Example MX record
#         zone_file.write(f"\n; MX Record\n")
#         zone_file.write(f"@  IN MX 10 mail.{domain}.\n")
        
#         # Example CNAME record
#         zone_file.write(f"\n; CNAME Record\n")
#         zone_file.write(f"www IN CNAME {domain}.\n")
        
#         # Example TXT record
#         zone_file.write(f"\n; TXT Record\n")
#         zone_file.write(f"@ IN TXT \"v=spf1 a mx ~all\"\n")

#         zone_file.write(f"\n; DKIM Record for {domain}\n")
#         zone_file.write(f"{dkim_record}\n")

#     print(f"BIND zone file updated at {zone_file_path}.")



def create_bind_records(domain, key_dir, zone_file_path):
    """Create BIND zone file records including DKIM, SOA, NS, A, MX, and other common DNS records."""
    
    # Read the DKIM public key from the generated key file
    dkim_record_file = os.path.join(key_dir, 'default.txt')
    with open(dkim_record_file) as f:
        dkim_record_lines = f.readlines()

    # Extract the DKIM selector and public key
    dkim_selector = "default._domainkey"
    dkim_record = "".join(dkim_record_lines).replace('" "', "").replace("\n", "")
    
    # ── Read admin-configured nameservers from Hostname settings ──
    ns1 = f"ns1.{domain}"
    ns2 = f"ns2.{domain}"
    try:
        from control.models import quick
        q = quick.objects.first()
        if q and q.nameserver1 and q.nameserver2:
            ns1 = q.nameserver1.strip().rstrip('.')
            ns2 = q.nameserver2.strip().rstrip('.')
    except Exception:
        pass  # Fallback to ns1.{domain} if DB not ready

    server_ip = get_server_ip()

    import tempfile, subprocess
    with tempfile.NamedTemporaryFile('w', delete=False) as zone_file:
        # Write TTL and SOA records
        zone_file.write(f"$TTL 86400  ; Default TTL\n")
        zone_file.write(f"@   IN  SOA {ns1}. admin.{domain}. (\n")
        zone_file.write(f"                2024091501  ; Serial\n")
        zone_file.write(f"                3600        ; Refresh\n")
        zone_file.write(f"                1800        ; Retry\n")
        zone_file.write(f"                604800      ; Expire\n")
        zone_file.write(f"                86400 )     ; Negative Cache TTL\n\n")
        
        # Write NS records
        zone_file.write(f"@   IN  NS   {ns1}.\n")
        zone_file.write(f"@   IN  NS   {ns2}.\n\n")
        
        # Write A record
        zone_file.write(f"; A Record\n")
        zone_file.write(f"@   IN  A    {server_ip}\n\n")
        zone_file.write(f"ns1   IN  A    {server_ip}\n\n")
        zone_file.write(f"ns2   IN  A    {server_ip}\n\n")

        
         # Write A record
        zone_file.write(f"; A Record\n")
        zone_file.write(f"mail   IN  A    {server_ip}\n\n")
        zone_file.write(f"ftp   IN  A    {server_ip}\n\n")

        # Write MX record
        zone_file.write(f"; MX Record\n")
        zone_file.write(f"@   IN  MX  10 mail.{domain}.\n\n")
        
        # Write CNAME record
        zone_file.write(f"; CNAME Record\n")
        zone_file.write(f"www IN  CNAME {domain}.\n\n")
        
        # Write TXT SPF record
        zone_file.write(f"; TXT Record\n")
        zone_file.write(f"@   IN  TXT  \"v=spf1 ip4:{server_ip} a mx ~all\"\n\n")

        # Write DKIM Record
        zone_file.write(f"; DKIM Record for {domain}\n")
 
        
        # Split the DKIM public key into chunks for readability
        
        for chunk in dkim_record_lines:
            zone_file.write(chunk)

        # Write DMARC Record
        zone_file.write(f"\n; DMARC Record\n")
        zone_file.write(f"_dmarc  IN  TXT  \"v=DMARC1; p=none; rua=mailto:admin@{domain}\"\n\n")
        tmp_zone = zone_file.name
        
    subprocess.run(['sudo', 'cp', tmp_zone, zone_file_path], check=False)
    subprocess.run(['sudo', 'chmod', '644', zone_file_path], check=False)
    os.unlink(tmp_zone)
     
    # Remove any existing zone entry first to prevent duplicates
    # This is critical: if we just append without checking, BIND will crash
    # with "zone 'domain': already exists" on restart.
    try:
        remove_zone_from_file(paths.BIND_CONF, domain)
    except Exception:
        pass  # File may not exist yet on first run

    with tempfile.NamedTemporaryFile('w', delete=False) as f:
        f.write("\n")
        f.write(f'zone "{domain}" ')
        f.write("{\n")
        f.write("type master; \n")
        zone_db = os.path.join(paths.BIND_ZONE_DIR, f'db.{domain}')
        f.write(f'file "{zone_db}"; \n')
        f.write("};\n")
        tmp_conf = f.name
    # Append zone config safely using sudo tee
    with open(tmp_conf, 'r') as f:
        conf_content = f.read()
    proc = subprocess.run(['sudo', 'tee', '-a', paths.BIND_CONF],
                          input=conf_content, capture_output=True, text=True)
    os.unlink(tmp_conf)
    

    print(f"BIND zone file created and saved to {zone_file_path}.")

def create_bind_recordsforsubdomain(name, zone_file_path):
    """Create BIND zone file records including DKIM, SOA, NS, A, MX, and other common DNS records."""
    
    import tempfile, subprocess
    
    record = f"\n; A Record\n{name}   IN  A    {get_server_ip()}\n\n"
    
    proc = subprocess.run(['sudo', 'tee', '-a', zone_file_path],
                          input=record, capture_output=True, text=True)
    # No temp file needed — piped directly

def configure_opendkim(domain, key_dir):
    """Configure OpenDKIM for a new domain.

    The main opendkim.conf should reference KeyTable, SigningTable, and
    TrustedHosts files for multi-domain support.  This function:
      1. Ensures opendkim.conf has the table-based config (writes it once
         if it doesn't already reference KeyTable).
      2. Appends entries to KeyTable, SigningTable, and TrustedHosts.
    """
    try:
        _validate_domain(domain)
        _validate_path(key_dir)

        if sys.platform == 'win32':
            print(f"Skipping OpenDKIM config on Windows for {domain}.")
            return

        import tempfile, subprocess

        # ── Step 1: Ensure opendkim.conf uses table-based multi-domain config ──
        needs_rewrite = True
        try:
            with open('/etc/opendkim.conf', 'r') as f:
                conf_content = f.read()
            if 'KeyTable' in conf_content and 'SigningTable' in conf_content:
                needs_rewrite = False
        except Exception:
            pass

        if needs_rewrite:
            base_conf = f"""# OpenDKIM Configuration — Multi-domain mode
Syslog          yes
LogWhy          yes
SyslogSuccess   yes

Canonicalization    relaxed/simple
Mode                sv
SubDomains          no

AutoRestart         yes
AutoRestartRate     10/1h

UMask               007
Socket              {paths.OPENDKIM_SOCKET}

PidFile             /run/opendkim/opendkim.pid
OversignHeaders     From

UserID              opendkim

# Multi-domain tables
KeyTable            {paths.OPENDKIM_KEYTABLE}
SigningTable        refile:{paths.OPENDKIM_SIGNINGTABLE}
ExternalIgnoreList  {paths.OPENDKIM_TRUSTEDHOSTS}
InternalHosts       {paths.OPENDKIM_TRUSTEDHOSTS}
"""
            with tempfile.NamedTemporaryFile('w', delete=False) as f:
                f.write(base_conf)
                tmp_conf = f.name
            subprocess.run(['sudo', 'cp', tmp_conf, '/etc/opendkim.conf'], check=False)
            os.unlink(tmp_conf)

        # Helper: append entry to a file if not already present (no shell)
        def _append_if_absent(file_path, search_str, entry):
            """Append entry to file_path if search_str is not already in it."""
            try:
                with open(file_path, 'r') as fh:
                    if search_str in fh.read():
                        return  # Already present
            except FileNotFoundError:
                pass
            subprocess.run(['sudo', 'tee', '-a', file_path],
                           input=entry, capture_output=True, text=True)

        # ── Step 2: Append to KeyTable (if not already present) ──
        key_entry = f"default._domainkey.{domain} {domain}:default:{os.path.join(key_dir, 'default.private')}\n"
        _append_if_absent(paths.OPENDKIM_KEYTABLE,
                          f"default._domainkey.{domain}", key_entry)

        # ── Step 3: Append to SigningTable (if not already present) ──
        sign_entry = f"*@{domain} default._domainkey.{domain}\n"
        _append_if_absent(paths.OPENDKIM_SIGNINGTABLE,
                          f"*@{domain}", sign_entry)

        # ── Step 4: Append to TrustedHosts (if not already present) ──
        trust_entry = f"*.{domain}\n"
        _append_if_absent(paths.OPENDKIM_TRUSTEDHOSTS,
                          f"*.{domain}", trust_entry)

        print(f"OpenDKIM configured for {domain}.")
    except IOError as e:
        print(f"Error configuring OpenDKIM: {e}")
   



BIND_ZONE_PATH = paths.BIND_ZONE_DIR + os.sep
ZONE_FILE = "example.com.zone"  # Replace with your zone file

# import re

# def parse_dns_zone_file(zone_file):
#     """
#     Parse the DNS zone file and extract records.
#     """
#     dns_records = []
    
#     try:
#         with open(zone_file, 'r') as file:
#             current_record = ""
#             finaldk=""
#             for line in file:
#                 line = line.strip()
                
#                 # Skip comments and empty lines
#                 if not line or line.startswith(';'):
#                     continue
#                 # if 'default._domainkey' in line and 'v=DKIM' in line:
#                 #     dkmirecord+=line+" "
#                 #     continue
#                 # elif '"p=' in line:
#                 #     dkmirecord+=line+" "
#                 #     continue
#                 # elif 'DKIM key default' in line:
#                 #     dkmirecord+=line+" "
#                 #     line=dkmirecord
              
#                 if '(' in line and ')' not in line:
#                     current_record += line + " "
#                     continue
#                 elif '; ----- DKIM key' in line:
#                     # print(line)
#                     finaldk = line
                   

              
#                 elif ')' in line:
#                     current_record += line
#                     line = current_record
#                     current_record = ""

#                 else:
#                     line = current_record + line
#                     current_record = ""
           
         

#                 # Regular expression to capture DNS records
#                 # Matches: [name] [optional: TTL] [class] [type] [data...]
#                 match = re.match(r"(\S+)\s*(\d+)?\s*(IN)?\s*(\S+)\s+(.+)", line)
#                 if match:
#                     record_name = match.group(1)
#                     record_ttl = match.group(2) if match.group(2) else "86400"  # Default TTL if not specified
#                     record_class = match.group(3) if match.group(3) else "IN"  # Default class to IN if not specified
#                     record_type = match.group(4)
#                     record_data = match.group(5)

#                     if '"v=DKIM1; h=sha256; k=rsa; t=y; s=email; " "p=' in record_data:
#                               dns_records.append({
#                             'name': record_name,
#                             'ttl': record_ttl,
#                             'class': record_class,
#                             'type': record_type,
#                             'data': record_data+finaldk,
#                         })
#                     else:

#                     # Add the record to the list
#                         dns_records.append({
#                             'name': record_name,
#                             'ttl': record_ttl,
#                             'class': record_class,
#                             'type': record_type,
#                             'data': record_data,
#                         })
#     except FileNotFoundError:
#         print(f"File not found: {zone_file}")
#         dns_records = []

#     return dns_records





# import re

# def parse_dns_zone_file(file_path):
#     records = []

#     with open(file_path, 'r') as file:
#         for line in file:
#             line = line.strip()
#             if not line or line.startswith(';'):
#                 continue  # Skip comments and empty lines
            
#             # Check if it's a TTL line
#             ttl_match = re.match(r'^\$TTL\s+(?P<ttl>\d+)\s+;\s+(?P<data>.*)', line)
#             if ttl_match:
#                 records.append({
#                     'name': '$TTL',
#                     'ttl': ttl_match.group('ttl'),
#                     'class': 'IN',
#                     'type': ';',
#                     'data': ttl_match.group('data')
#                 })
#                 continue
            
#             # Match typical DNS record types
#             general_pattern = re.compile(
#                 r'(?P<name>\S+)\s+IN\s+(?P<type>\S+)\s+(?P<data>.*)'
#             )
#             match = general_pattern.match(line)
#             if match:
#                 record_data = match.groupdict()

#                 # Handle records with multiple fields (e.g., MX records with priority)
#                 if record_data['type'] == 'MX':
#                     mx_match = re.match(r'(?P<priority>\d+)\s+(?P<data>.*)', record_data['data'])
#                     if mx_match:
#                         record_data['data'] = mx_match.group('data')
#                         record_data['priority'] = mx_match.group('priority')

#                 # Handle TXT records with multiple lines
#                 if record_data['type'] == 'TXT' or record_data['type'] == 'DKIM':
#                     record_data['data'] = record_data['data'].replace('"', '').replace('(', '').replace(')', '')

#                 record_data['ttl'] = None  # TTL is not specified for individual records here
#                 record_data['class'] = 'IN'

#                 records.append(record_data)

#     return records





def get_active_zone_file_path(domainname):
    """
    Find the actual zone file path used by BIND for the given domain across Linux distros (Ubuntu/Debian & AlmaLinux/RHEL/CentOS).
    Checks named.conf for exact zone file setting, as well as candidate zone directories.
    """
    domainname = (domainname or '').strip().lower()
    if not domainname:
        return ''

    conf_files = [
        '/etc/bind/named.conf',
        '/etc/bind/named.conf.local',
        '/etc/named.conf',
        '/etc/named.conf.local',
        '/var/named/named.conf',
    ]
    for cf in conf_files:
        if os.path.exists(cf):
            try:
                with open(cf, 'r') as f:
                    content = f.read()
                pattern = rf'zone\s+"{re.escape(domainname)}"\s*\{{[^}}]*file\s+"([^"]+)";'
                match = re.search(pattern, content, re.IGNORECASE | re.DOTALL)
                if match:
                    fp = match.group(1)
                    if os.path.exists(fp):
                        return fp
            except Exception:
                pass

    candidates = [
        os.path.join('/etc/bind/zones', f'{domainname}.zone'),
        os.path.join(paths.BIND_ZONE_DIR, 'zones', f'{domainname}.zone'),
        os.path.join(paths.BIND_ZONE_DIR, f'db.{domainname}'),
        os.path.join('/etc/bind', f'db.{domainname}'),
        os.path.join('/var/named', f'{domainname}.zone'),
        os.path.join('/var/named', f'db.{domainname}'),
    ]
    for c in candidates:
        if os.path.exists(c):
            return c

    return os.path.join(paths.BIND_ZONE_DIR, f'db.{domainname}')

def format_dns_data(record_type, data):
    """
    Ensure TXT record values are properly enclosed in double quotes for BIND zone file syntax.
    """
    data = (data or '').strip()
    if record_type.upper() == 'TXT':
        if not (data.startswith('"') and data.endswith('"')):
            cleaned = data.replace('\\"', '"').replace('"', '\\"')
            data = f'"{cleaned}"'
    return data

def update_soa_serial_in_content(content):
    """
    Increment or set the SOA serial number (YYYYMMDDNN format) in BIND zone file content.
    """
    import datetime
    today = datetime.datetime.now().strftime('%Y%m%d')

    def replace_serial(m):
        old_val = m.group(1)
        if old_val.startswith(today):
            try:
                seq = int(old_val[-2:]) + 1
                new_val = f"{today}{seq:02d}"
            except Exception:
                new_val = f"{today}01"
        else:
            new_val = f"{today}01"
        return m.group(0).replace(old_val, new_val)

    res = re.sub(r'(\d{8,10})\s*;\s*[Ss]erial', replace_serial, content)
    if res == content:
        res = re.sub(r'(\b\d{10}\b)', replace_serial, content, count=1)
    return res

def fix_zone_file_permissions(filepath):
    """
    Fix ownership and permissions on a BIND zone file after writing.
    BIND runs as 'bind' user and needs read access.
    Sets ownership to bind:bind and mode 644.
    """
    import subprocess
    try:
        subprocess.run(['sudo', 'chown', 'bind:bind', filepath], check=False, capture_output=True)
        subprocess.run(['sudo', 'chmod', '644', filepath], check=False, capture_output=True)
    except Exception:
        pass

def parse_dns_zone_file(DNS_FILE):
    records = []
    multiline_record = ""
    inside_multiline = False

    # Zone files are owned by bind:bind (mode 640).
    # www-data can't read them directly, so use 'sudo cat'.
    try:
        import subprocess as _sp
        result = _sp.run(['sudo', 'cat', DNS_FILE], capture_output=True, text=True, timeout=10)
        if result.returncode != 0:
            raise PermissionError(f'Permission denied reading zone file. Check server file permissions.')
        content = result.stdout
    except PermissionError:
        raise
    except Exception as e:
        raise PermissionError(f'Could not read zone file: {e}')

    for line in content.splitlines():
        line = line.strip()

        if not line or line.startswith(';'):
            continue  # Skip comments and empty lines

        # Check if it's a TTL line
        ttl_match = re.match(r'^\$TTL\s+(?P<ttl>\d+)', line)
        if ttl_match:
            records.append({
                'name': '$TTL',
                'ttl': ttl_match.group('ttl'),
                'class': 'IN',
                'type': ';',
                'data': 'Default TTL'
            })
            continue

        # Check if the record is a multiline TXT/DKIM entry (inside parentheses)
        if '(' in line:
            inside_multiline = True
            multiline_record = line
            continue
        elif inside_multiline:
            multiline_record += " " + line
            if ')' in line:
                inside_multiline = False

                # Process multiline record as one line
                multiline_record = multiline_record.replace('(', '').replace(')', '')
                match = re.match(r'(?P<name>\S+)\s+((?P<ttl>\d+)\s+)?IN\s+(?P<type>\S+)\s+(?P<data>.*)', multiline_record)
                if match:
                    record_data = match.groupdict()
                    record_data['ttl'] = record_data.get('ttl') or '86400'
                    record_data['class'] = 'IN'
                    # Merge divided TXT string parts ("part1" "part2" -> "part1part2")
                    if record_data.get('type') == 'TXT' and record_data.get('data'):
                        parts = re.findall(r'"([^"]*)"', record_data['data'])
                        if parts:
                            record_data['data'] = f'"{ "".join(parts) }"'
                    records.append(record_data)
                multiline_record = ""
            continue

        # Match general DNS record lines (with or without IN class keyword)
        general_pattern = re.compile(
            r'(?P<name>\S+)\s+((?P<ttl>\d+)\s+)?(?:IN\s+)?(?P<type>[A-Z]+)\s+(?P<data>.*)'
        )
        match = general_pattern.match(line)
        if match:
            record_data = match.groupdict()
            record_data['ttl'] = record_data.get('ttl') or '86400'
            record_data['class'] = 'IN'
            if record_data.get('type') == 'TXT' and record_data.get('data'):
                parts = re.findall(r'"([^"]*)"', record_data['data'])
                if parts:
                    record_data['data'] = f'"{ "".join(parts) }"'
            records.append(record_data)

    return records





# Function to create a database and a table
def create_database_and_table(db_name,password):
    connection = None
    try:
        _validate_sql_identifier(db_name)
        connection = mysql.connector.connect(
            host="localhost",
            user="root", 
            password=password
        )
        if connection.is_connected():
            cursor = connection.cursor()
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{db_name}`")
            return True
        else:
            return False

    except (Error, ValueError) as e:
        print(f"Error: {e}")
        return False



def create_mysql_user(username,password,passw):
    connection = None
    try:
        _validate_sql_identifier(username)
        connection = mysql.connector.connect(
            host="localhost",
            user="root",
            password=passw
        )

        if connection.is_connected():
            cursor = connection.cursor()
            cursor.execute("CREATE USER %s@'localhost' IDENTIFIED BY %s", (username, password))
            return True

    except (Error, ValueError) as e:
        print(f"Error: {e}")
        return False



import mysql.connector
from mysql.connector import Error

def get_database_names(passw):
    connection = None
    databases = []
    try:
        # Establish a connection to MySQL server
        connection = mysql.connector.connect(
            host="localhost",  
            user="root",  # Replace with your MySQL admin username
            password=passw  # Replace with your MySQL admin password
        )

        if connection.is_connected():
            cursor = connection.cursor()
            # Query to fetch database names
            cursor.execute("SHOW DATABASES;")
            databases = [db[0] for db in cursor.fetchall()]  # Fetch all databases and store in a list

    except Error as e:
        print(f"Error: {e}")
    finally:
        if connection and connection.is_connected():
            cursor.close()
            connection.close()

    return databases

def get_database_users(passw):
    connection = None
    users = []
    try:
        # Establish a connection to MySQL server
        connection = mysql.connector.connect(
            host="localhost",  
            user="root",  # Replace with your MySQL admin username
            password=passw  # Replace with your MySQL admin password
        )

        if connection.is_connected():
            cursor = connection.cursor()
            # Query to fetch user names from the MySQL `mysql.user` table
            cursor.execute("SELECT user FROM mysql.user;")
            users = [user[0] for user in cursor.fetchall()]  # Fetch all users and store in a list

    except Error as e:
        print(f"Error: {e}")
    finally:
        if connection and connection.is_connected():
            cursor.close()
            connection.close()

    return users

def get_database_names_with_filter(passw, filter_string):
    connection = None
    databases = []
    try:
        # Establish a connection to MySQL server
        connection = mysql.connector.connect(
            host="localhost",  
            user="root",  # Replace with your MySQL admin username
            password=passw  # Replace with your MySQL admin password
        )

        if connection.is_connected():
            cursor = connection.cursor()
            # Query to fetch database names
            cursor.execute("SHOW DATABASES;")
            all_databases = cursor.fetchall()

            # Filter databases that start with the specified string
            databases = [db[0] for db in all_databases if db[0].startswith(filter_string)]

    except Error as e:
        print(f"Error: {e}")
    finally:
        if connection and connection.is_connected():
            cursor.close()
            connection.close()

    return databases


def get_database_users_with_filter(passw, filter_string):
    connection = None
    users = []
    try:
        # Establish a connection to MySQL server
        connection = mysql.connector.connect(
            host="localhost",  
            user="root",  # Replace with your MySQL admin username
            password=passw  # Replace with your MySQL admin password
        )

        if connection.is_connected():
            cursor = connection.cursor()
            # Query to fetch user names from the MySQL `mysql.user` table
            cursor.execute("SELECT user FROM mysql.user;")
            all_users = cursor.fetchall()

            # Filter users that start with the specified string
            users = [user[0] for user in all_users if user[0].startswith(filter_string)]

    except Error as e:
        print(f"Error: {e}")
    finally:
        if connection and connection.is_connected():
            cursor.close()
            connection.close()

    return users

def get_database_privileges_with_filter(passw, filter_string):
    connection = None
    mappings = []
    try:
        connection = mysql.connector.connect(
            host="localhost",  
            user="root",
            password=passw
        )
        if connection.is_connected():
            cursor = connection.cursor()
            cursor.execute("SELECT User, Db FROM mysql.db;")
            all_privs = cursor.fetchall()
            
            for user, db in all_privs:
                if user.startswith(filter_string) or db.startswith(filter_string):
                    mappings.append({"user": user, "database": db})

    except Error as e:
        print(f"Error fetched privs: {e}")
    finally:
        if connection and connection.is_connected():
            cursor.close()
            connection.close()

    return mappings

def revoke_mysql_user_privileges(username, database, passw):
    connection = None
    try:
        connection = mysql.connector.connect(
            host="localhost",
            user="root",
            password=passw
        )
        if connection.is_connected():
            cursor = connection.cursor()
            cursor.execute(f"REVOKE ALL PRIVILEGES ON `{database}`.* FROM '{username}'@'localhost'")
            connection.commit()
            return True
        return False
    except Error as e:
        print(f"Error revoking privileges: {e}")
        return False
    finally:
        if connection and connection.is_connected():
            cursor.close()
            connection.close()

import mysql.connector
from mysql.connector import Error

def remove_database(db_name, passw):
    connection = None
    try:
        _validate_sql_identifier(db_name)
        connection = mysql.connector.connect(
            host="localhost",  
            user="root",
            password=passw
        )

        if connection.is_connected():
            cursor = connection.cursor()
            cursor.execute(f"DROP DATABASE IF EXISTS `{db_name}`")
            connection.commit()
            return True

    except (Error, ValueError) as e:
        print(f"Error: {e}")
        return False
    finally:
        if connection and connection.is_connected():
            cursor.close()
            connection.close()

def delete_mysql_user(username, passw):
    connection = None
    try:
        _validate_sql_identifier(username)
        connection = mysql.connector.connect(
            host="localhost",  
            user="root",
            password=passw
        )

        if connection.is_connected():
            cursor = connection.cursor()
            cursor.execute("DROP USER IF EXISTS %s@'localhost'", (username,))
            connection.commit()
            return True

    except (Error, ValueError) as e:
        print(f"Error: {e}")
        return False
    finally:
        if connection and connection.is_connected():
            cursor.close()
            connection.close()

# Usage Example

import mysql.connector
from mysql.connector import Error

def change_mysql_user_password(username, new_password, passw):
    connection = None
    try:
        _validate_sql_identifier(username)
        connection = mysql.connector.connect(
            host="localhost",  
            user="root",
            password=passw
        )

        if connection.is_connected():
            cursor = connection.cursor()
            cursor.execute("ALTER USER %s@'localhost' IDENTIFIED BY %s", (username, new_password))
            connection.commit()
            return True

    except (Error, ValueError) as e:
        print(f"Error: {e}")
        return False
    finally:
        if connection and connection.is_connected():
            cursor.close()
            connection.close()





def grant_mysql_user_privileges(username, database, privileges, admin_password):
    connection = None
    try:
        _validate_sql_identifier(username)
        _validate_sql_identifier(database)
        # Validate each privilege against the allowlist
        for priv in privileges:
            if priv.upper().strip() not in _ALLOWED_MYSQL_PRIVILEGES:
                raise ValueError(f'Invalid MySQL privilege: {priv!r}')
        connection = mysql.connector.connect(
            host="localhost",  
            user="root",
            password=admin_password
        )

        if connection.is_connected():
            cursor = connection.cursor()
            privileges_string = ', '.join(p.upper().strip() for p in privileges)
            grant_privileges_query = f"GRANT {privileges_string} ON `{database}`.* TO %s@'localhost'"
            cursor.execute(grant_privileges_query, (username,))
            connection.commit()
            return True

    except (Error, ValueError) as e:
        print(f"Error: {e}")
        return False
    finally:
        if connection and connection.is_connected():
            cursor.close()
            connection.close()

# Example usage


import os
import zipfile
def zip_multiple_locations_backup(main_directory, locations, zip_filename):
    # Ensure the main directory exists
    if not os.path.exists(main_directory):
        os.makedirs(main_directory)
    # Path to the zip file
    zip_filepath = os.path.join(main_directory, f"{zip_filename}.zip")

    # Create a zip file in write mode
    with zipfile.ZipFile(zip_filepath, 'w') as zipf:
        for location in locations:
            if os.path.exists(location):
                if os.path.isdir(location):
                    # If it's a directory, add all files recursively
                    for root, dirs, files in os.walk(location):
                        for file in files:
                            file_path = os.path.join(root, file)
                            arcname = os.path.relpath(file_path, start=location)
                            zipf.write(file_path, arcname=os.path.join(os.path.basename(location), arcname))
                else:
                    # If it's a file, add it directly
                    zipf.write(location, arcname=os.path.basename(location))

def zip_multiple_locations_backup_user(main_directory, locations, zip_filename, current, progress_file=None):
    import time
    import json

    # Directories that should NEVER be backed up (regenerable, huge, or irrelevant)
    EXCLUDED_DIRS = {
        'node_modules', '__pycache__', '.git', '.svn', '.hg',
        'venv', '.venv', 'env', '.env', '.tox',
        '.npm', '.npm_cache', '.cache', '.next', '.nuxt',
        'dist', 'bower_components', '.trash', '.backups', # .trash = Recycle Bin, .backups = Backup Quota Dir
    }
    # Files to explicitly skip
    EXCLUDED_NAMES = {'.backup_progress', '.DS_Store', 'Thumbs.db', '.backup_done'}

    # Ensure the main directory exists
    if not os.path.exists(main_directory):
        os.makedirs(main_directory)

    zip_filepath = os.path.join(main_directory, f"{zip_filename}.zip")

    # Write PID + start timestamp to progress file for stale detection
    if progress_file:
        try:
            meta = json.dumps({'pct': 5, 'pid': os.getpid(), 'ts': time.time()})
            with open(progress_file, 'w') as pf:
                pf.write(meta)
        except Exception:
            pass

    file_list = []
    for location in locations:
        if not os.path.exists(location):
            continue
        if os.path.isdir(location):
            for root, dirs, files in os.walk(location, topdown=True):
                # Prune excluded directories in-place (prevents os.walk from descending)
                dirs[:] = [d for d in dirs if d not in EXCLUDED_DIRS]
                for file in files:
                    full_path = os.path.join(root, file)
                    fname = os.path.basename(full_path)
                    # Skip backup zips, progress files, and excluded names
                    if fname in EXCLUDED_NAMES:
                        continue
                    if fname.startswith("backup_") and fname.endswith(".zip"):
                        continue
                    arcname = os.path.join(
                        os.path.basename(location),
                        os.path.relpath(full_path, start=location)
                    )
                    file_list.append((full_path, arcname))
        else:
            fname = os.path.basename(location)
            if fname not in EXCLUDED_NAMES:
                file_list.append((location, fname))

    total_files = len(file_list)
    processed = 0
    # Update progress every 1% (min 1 file, max every 50 files) for smooth bar movement
    update_interval = max(1, min(50, total_files // 100))
    last_pct = 5

    with zipfile.ZipFile(zip_filepath, 'w', compression=zipfile.ZIP_DEFLATED, allowZip64=True) as zipf:
        for file_path, arcname in file_list:
            if file_path == zip_filepath:
                continue
            try:
                zipf.write(file_path, arcname=arcname)
            except Exception:
                continue

            processed += 1
            if progress_file and total_files > 0 and processed % update_interval == 0:
                pct = max(5, min(99, int((processed / total_files) * 95) + 5))
                if pct != last_pct:
                    last_pct = pct
                    try:
                        meta = json.dumps({'pct': pct, 'pid': os.getpid(), 'ts': time.time()})
                        with open(progress_file, 'w') as pf:
                            pf.write(meta)
                    except Exception:
                        pass

    if sys.platform != 'win32':
        run_command(f'sudo chown {current}:{current} {zip_filepath}')
    else:
        run_command(f'icacls "{zip_filepath}" /grant {current}:F')

          



import re

def remove_zone_from_file(file_path, domain):
    """Remove ALL occurrences of a zone block for the given domain from the BIND config file.
    
    This handles the case where duplicate zone entries exist (e.g., from a failed
    termination followed by recreation), which would otherwise crash BIND.
    """
    with open(file_path, 'r') as file:
        lines = file.readlines()

    # Identify the zone block to remove — match all occurrences
    zone_start = f'zone "{domain}" {{'
    zone_end = "};" 
    
    in_zone_block = False
    updated_lines = []
    
    for line in lines:
        if zone_start in line:
            in_zone_block = True  # Start of a zone block
            continue  # Skip the zone start line
        if in_zone_block:
            if zone_end in line:
                in_zone_block = False  # End of the zone block
                continue  # Skip the zone end line
            continue  # Skip lines inside the zone block
        updated_lines.append(line)

    # Clean up excessive blank lines that may be left behind
    cleaned_lines = []
    prev_blank = False
    for line in updated_lines:
        is_blank = line.strip() == ''
        if is_blank and prev_blank:
            continue  # Skip consecutive blank lines
        cleaned_lines.append(line)
        prev_blank = is_blank

    import tempfile, subprocess
    with tempfile.NamedTemporaryFile('w', delete=False) as tmp:
        tmp.writelines(cleaned_lines)
        tmp_name = tmp.name

    if sys.platform != 'win32':
        subprocess.run(['sudo', 'cp', tmp_name, file_path], check=False)
        subprocess.run(['rm', '-f', tmp_name], check=False)
    else:
        with open(file_path, 'w') as file:
            file.writelines(cleaned_lines)
        try:
            os.remove(tmp_name)
        except Exception:
            pass


import subprocess
import os

def get_php_versions():
    versions = []
    if sys.platform == 'win32':
        # On Windows, check for PHP versions under C:\VoidPanel\php\
        php_base = getattr(paths, 'PHP_DIR', os.path.join(os.environ.get('VOIDPANEL_BASE', r'C:\VoidPanel'), 'php'))
        if os.path.isdir(php_base):
            for entry in os.listdir(php_base):
                php_exe = os.path.join(php_base, entry, 'php.exe')
                if os.path.exists(php_exe):
                    versions.append(php_exe)
    else:
        for php_bin in ['/usr/bin/php5', '/usr/bin/php7.0', '/usr/bin/php7.1', '/usr/bin/php7.2',
                        '/usr/bin/php7.3', '/usr/bin/php7.4', '/usr/bin/php8.0', '/usr/bin/php8.1',
                        '/usr/bin/php8.2', '/usr/bin/php8.3', '/usr/bin/php8.4']:
            if os.path.exists(php_bin):
                versions.append(php_bin)

    return versions

def get_php_version(php_bin):
    try:
        # Run the command to get PHP version
        result = subprocess.run([php_bin, '-v'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

        # Check if there was an error
        if result.stderr:
            return None

        # Extract the PHP version from the output
        version_line = result.stdout.splitlines()[0]
        version = version_line.split()[1]  # Extract the version number
        return version

    except FileNotFoundError:
        return None

def get_php_extensions(php_bin):
    try:
        # Run the command to get PHP extensions
        result = subprocess.run([php_bin, '-m'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

        # Check if there was an error
        if result.stderr:
            return []

        # Split the output into lines and return as a list
        extensions = result.stdout.splitlines()
        
        # The first line is the "PHP Modules" header; skip it
        return extensions[1:]  # Return all lines after the header

    except FileNotFoundError:
        return []


def get_service_status(service_name):
    try:
        plat = get_platform()
        if plat.services.is_active(service_name):
            return 'active'
        return 'inactive'
    except Exception:
        return False


def restart_service(service_name):
    try:
        result = get_platform().services.restart(service_name)
        return result.success
    except Exception:
        return False

def start_service(service_name):
    try:
        result = get_platform().services.start(service_name)
        return result.success
    except Exception:
        return False

def stop_service(service_name):
    try:
        result = get_platform().services.stop(service_name)
        return result.success
    except Exception:
        return False



def get_directory_size_in_mb(directory='.'):
    total_size = 0
    # Traverse through all files and subdirectories
    for dirpath, dirnames, filenames in os.walk(directory):
        for f in filenames:
            fp = os.path.join(dirpath, f)
            # Skip if it's a symbolic link
            if not os.path.islink(fp):
                total_size += os.path.getsize(fp)
    
    # Convert bytes to MB (1 MB = 1024 * 1024 bytes)
    size_in_mb = total_size / (1024 * 1024)
    return size_in_mb


# ─────────────────────────────────────────────────────────────────────────────
# Site Cloner — cross-platform, handles React/SPA sites
# ─────────────────────────────────────────────────────────────────────────────

def clone_website(target_url, destination_dir):
    """
    Clone an external website (including React/SPA) into destination_dir.
    Works on both Linux and Windows (pure Python, no external binaries).

    Steps:
      1. Fetch the root HTML page.
      2. Parse all <script>, <link>, <img>, <source>, <video>, <audio> tags.
      3. Download every discovered asset and rewrite src/href to relative paths.
      4. Also recursively discovers JS chunk imports for React split-code apps.

    Returns: (True, "Success message") | (False, "Error message")
    """
    try:
        from urllib.parse import urlparse, urljoin
        import re as _re
        import os as _os
        import hashlib
        import json

        task_id = hashlib.md5(destination_dir.encode()).hexdigest()
        status_path = f"/tmp/clone_{task_id}.json"

        # Initialize/clean status file
        if _os.path.exists(status_path):
            try: _os.remove(status_path)
            except: pass

        def _update_status(percentage, current_file, log_msg=None, status="running", error=""):
            try:
                logs = []
                if _os.path.exists(status_path):
                    with open(status_path, 'r') as sf:
                        try:
                            data = json.load(sf)
                            logs = data.get('logs', [])
                        except:
                            pass
                if log_msg:
                    logs.append(log_msg)
                    logs = logs[-50:]
                with open(status_path, 'w') as sf:
                    json.dump({
                        'status': status,
                        'percentage': percentage,
                        'current_file': current_file,
                        'logs': logs,
                        'error': error,
                        'destination': destination_dir
                    }, sf)
            except:
                pass

        _update_status(5, target_url, log_msg=f"Fetching root HTML page from {target_url}...")

        HEADERS = {
            'User-Agent': (
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                'AppleWebKit/537.36 (KHTML, like Gecko) '
                'Chrome/123.0.0.0 Safari/537.36'
            ),
            'Accept-Language': 'en-US,en;q=0.9',
        }

        _os.makedirs(destination_dir, exist_ok=True)
        parsed_root = urlparse(target_url)
        base_url = f"{parsed_root.scheme}://{parsed_root.netloc}"

        downloaded = set()

        def _safe_filename(url_path):
            path = url_path.lstrip('/')
            if not path or path.endswith('/'):
                path = path + 'index.html'
            if '?' in path:
                base_p, qs = path.split('?', 1)
                path = base_p + '_' + hashlib.md5(qs.encode()).hexdigest()[:8]
            return path

        def _download_asset(asset_url):
            if asset_url in downloaded:
                return None
            downloaded.add(asset_url)
            try:
                resp = requests.get(asset_url, headers=HEADERS, timeout=15,
                                    allow_redirects=True, stream=True)
                if resp.status_code != 200:
                    return None
                rel_path = _safe_filename(urlparse(asset_url).path)
                local_path = _os.path.join(destination_dir, rel_path)
                _os.makedirs(_os.path.dirname(local_path), exist_ok=True)
                with open(local_path, 'wb') as f:
                    for chunk in resp.iter_content(chunk_size=8192):
                        f.write(chunk)
                return rel_path
            except Exception:
                return None

        def _discover_js_chunk_imports(js_content):
            chunk_pattern = _re.findall(
                r'["\']([^"\']*?static/[^"\']*?\.(?:js|css|woff2?|ttf|eot|png|jpg|jpeg|svg|gif|webp|ico)[^"\']*)["\']',
                js_content
            )
            return chunk_pattern

        # Fetch root HTML
        root_resp = requests.get(target_url, headers=HEADERS, timeout=20, allow_redirects=True)
        if root_resp.status_code != 200:
            err_msg = f"Failed to fetch {target_url} (HTTP {root_resp.status_code})"
            _update_status(100, "Failed", log_msg=err_msg, status="error", error=err_msg)
            return False, err_msg

        html_content = root_resp.text
        downloaded.add(target_url)
        _update_status(10, "Scanning assets", log_msg="Root HTML page loaded successfully. Scanning for assets...")

        # Discover assets from HTML
        asset_tags = _re.findall(
            r'(?:src|href|data-src|srcset)\s*=\s*["\']([^"\']+)["\']',
            html_content
        )
        css_urls = _re.findall(r'url\(["\']?([^"\')\s]+)["\']?\)', html_content)
        all_refs = asset_tags + css_urls

        assets_to_download = []
        for ref in all_refs:
            if ref.startswith('data:') or ref.startswith('#') or ref.startswith('mailto:'):
                continue
            full_url = urljoin(base_url, ref) if not ref.startswith('http') else ref
            if urlparse(full_url).netloc == parsed_root.netloc or not ref.startswith('http'):
                assets_to_download.append(full_url)

        url_to_local = {}
        js_contents_to_scan = []

        total_assets = len(assets_to_download)
        _update_status(15, "Downloading assets", log_msg=f"Discovered {total_assets} main assets to download. Starting download...")

        for idx, asset_url in enumerate(assets_to_download):
            progress = 15 + int(60 * ((idx + 1) / max(1, total_assets)))
            asset_name = asset_url.split('/')[-1] or asset_url
            _update_status(progress, asset_name, log_msg=f"[{progress}%] Downloading asset {idx+1}/{total_assets}: {asset_name}")
            local_path = _download_asset(asset_url)
            if local_path:
                url_to_local[asset_url] = local_path
                if asset_url.endswith('.js'):
                    try:
                        with open(_os.path.join(destination_dir, local_path), 'r',
                                  encoding='utf-8', errors='ignore') as jf:
                            js_contents_to_scan.append((asset_url, jf.read()))
                    except Exception:
                        pass

        # Scan JS bundles for React chunks
        _update_status(80, "Scanning React Chunks", log_msg="Scanning JavaScript bundles for dynamic React chunk imports...")
        
        js_scanned_count = 0
        for js_url, js_text in js_contents_to_scan:
            js_scanned_count += 1
            js_base = f"{urlparse(js_url).scheme}://{urlparse(js_url).netloc}"
            chunks = list(_discover_js_chunk_imports(js_text))
            total_chunks = len(chunks)
            if total_chunks > 0:
                _update_status(82, f"JS bundle {js_scanned_count}", log_msg=f"Discovered {total_chunks} dynamic chunks in {js_url.split('/')[-1]}")
            for idx, chunk_ref in enumerate(chunks):
                progress = 80 + int(10 * ((idx + 1) / max(1, total_chunks)))
                chunk_name = chunk_ref.split('/')[-1] or chunk_ref
                _update_status(progress, chunk_name, log_msg=f"[{progress}%] Downloading dynamic React chunk: {chunk_name}")
                lp = _download_asset(full_chunk := (urljoin(js_base, chunk_ref) if not chunk_ref.startswith('http') else chunk_ref))
                if lp:
                    url_to_local[full_chunk] = lp

        # Rewrite HTML to use local paths
        _update_status(92, "Rewriting HTML", log_msg="Re-linking discovered assets to local paths in index.html...")
        rewritten_html = html_content
        for orig_url, local_rel in url_to_local.items():
            orig_path = urlparse(orig_url).path
            rewritten_html = rewritten_html.replace(orig_url, local_rel)
            if orig_path and orig_path != '/':
                rewritten_html = rewritten_html.replace(orig_path, local_rel)

        index_path = _os.path.join(destination_dir, 'index.html')
        with open(index_path, 'w', encoding='utf-8') as f:
            f.write(rewritten_html)

        total = len(downloaded)
        success_msg = f"Site cloned successfully! {total} assets downloaded."
        _update_status(100, "Completed", log_msg=success_msg, status="success")
        return True, success_msg

    except Exception as e:
        err_msg = f"Clone failed: {str(e)}"
        _update_status(100, "Failed", log_msg=err_msg, status="error", error=err_msg)
        return False, err_msg


def create_default_index_html(target_dir, domain_name):
    """Create a clean default index.html placeholder page if no index file exists."""
    try:
        os.makedirs(target_dir, exist_ok=True)
        index_file = os.path.join(target_dir, 'index.html')
        if not os.path.exists(index_file) and not os.path.exists(os.path.join(target_dir, 'index.php')):
            html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Welcome to {domain_name}</title>
    <style>
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #0f172a; color: #f8fafc; display: flex; align-items: center; justify-content: center; min-height: 100vh; padding: 20px; }}
        .card {{ background: #1e293b; border: 1px solid #334155; border-radius: 16px; padding: 40px; max-width: 500px; width: 100%; text-align: center; box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.3); }}
        .icon {{ font-size: 48px; margin-bottom: 20px; color: #38bdf8; }}
        h1 {{ font-size: 24px; font-weight: 700; margin-bottom: 12px; color: #ffffff; }}
        p {{ font-size: 15px; color: #94a3b8; line-height: 1.6; margin-bottom: 24px; }}
        .badge {{ display: inline-block; background: rgba(56, 189, 248, 0.1); color: #38bdf8; padding: 6px 16px; border-radius: 20px; font-size: 13px; font-weight: 600; border: 1px solid rgba(56, 189, 248, 0.2); }}
    </style>
</head>
<body>
    <div class="card">
        <div class="icon">🚀</div>
        <h1>{domain_name} is live!</h1>
        <p>Your website has been successfully provisioned. Upload your web files to <code>public_html</code> to publish your site.</p>
        <span class="badge">Powered by VoidPanel</span>
    </div>
</body>
</html>"""
            with open(index_file, 'w', encoding='utf-8') as f:
                f.write(html_content)
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning('Failed to create default index.html for %s: %s', domain_name, e)

