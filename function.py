
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
import mysql.connector
from mysql.connector import Error
from voidplatform import get_platform
from voidplatform.config import paths


def _validate_sql_identifier(name):
    """Validate a SQL identifier (database name, username) to prevent injection."""
    if not name or not re.match(r'^[a-zA-Z0-9_.-]+$', name):
        raise ValueError(f'Invalid SQL identifier: {name!r}')
    return name


_ALLOWED_MYSQL_PRIVILEGES = frozenset({
    'ALL PRIVILEGES', 'SELECT', 'INSERT', 'UPDATE', 'DELETE',
    'CREATE', 'DROP', 'ALTER', 'INDEX', 'REFERENCES', 'EXECUTE',
    'CREATE TEMPORARY TABLES', 'LOCK TABLES', 'TRIGGER',
})

def is_website_live(url):
    try:
        response = requests.get(url, timeout=5)
        # Check if the status code is 200 (OK)
        if response.status_code == 200:
            return True
        else:
            return False
    except requests.ConnectionError:
        # Website is unreachable
        return False
    except requests.Timeout:
        # Website timed out
        return False
    except requests.RequestException as e:
        # Any other exceptions like invalid URL
        print(f"An error occurred: {e}")
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
            file.write(f'CSRF_TRUSTED_ORIGINS.append("https://{new_hostname}:8082")')

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
                content = content.replace(old_hostname, hostname)
                content = content.replace(paths.SSL_DUMMY_CERT, f'{paths.LETSENCRYPT_LIVE}/{hostname}/fullchain.pem')
                content = content.replace(paths.SSL_DUMMY_KEY, f'{paths.LETSENCRYPT_LIVE}/{hostname}/privkey.pem')
                if old_hostname:
                    content = content.replace(f'{paths.LETSENCRYPT_LIVE}/{old_hostname}/fullchain.pem', f'{paths.LETSENCRYPT_LIVE}/{hostname}/fullchain.pem')
                    content = content.replace(f'{paths.LETSENCRYPT_LIVE}/{old_hostname}/privkey.pem', f'{paths.LETSENCRYPT_LIVE}/{hostname}/privkey.pem')
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
                for root, dirs, files in os.walk(path):
                    for file in files:
                        filepath = os.path.join(root, file)
                        # Write the file with relative path inside the zip
                        zipf.write(filepath, arcname=os.path.relpath(filepath, path))
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
        subprocess.run(['sudo', 'mkdir', '-p', ssl_dir], check=False)
        subprocess.run(['sudo', 'chown', 'www-data:www-data', ssl_dir], check=False)
        subprocess.run(['sudo', 'mkdir', '-p', logs], check=False)
        subprocess.run(['sudo', 'chown', 'www-data:www-data', logs], check=False)
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
   location ~ \\.php$ {{
        include snippets/fastcgi-php.conf;
        {php_fastcgi}
        fastcgi_param SCRIPT_FILENAME $document_root$fastcgi_script_name;
        include fastcgi_params;
         fastcgi_read_timeout 300;
        fastcgi_connect_timeout 300;
        fastcgi_send_timeout 300;
    }}

    location /phpmyadmin {{
    alias /usr/share/phpmyadmin;  # This should point to your phpMyAdmin installation
    index index.php;

    location ~ ^/phpmyadmin/(.+\\.php)$ {{
        {php_fastcgi}
        fastcgi_index index.php;
        include fastcgi_params;
        fastcgi_param SCRIPT_FILENAME /usr/share/phpmyadmin/$1;  # Ensure this is correct
    }}

    location ~ ^/phpmyadmin/(.+\\.(gif|jpe?g|png|ico|css|js))$ {{
        alias /usr/share/phpmyadmin/$1;  # This serves static assets
    }}
}}

     location ~ /\\.ht {{
        deny all;
    }}
     proxy_read_timeout 300;
    proxy_connect_timeout 300;
    proxy_send_timeout 300;


}}


server {{
    listen 80;
    server_name {domain};

    # Redirect all HTTP traffic to HTTPS
    return 301 https://$host$request_uri;



}}
"""

    try:
        import tempfile, subprocess
        with tempfile.NamedTemporaryFile('w', delete=False) as f:
            f.write(nginx_ssl_conf)
            tmp = f.name
        subprocess.run(f"sudo cp {tmp} {file_path}", shell=True, check=False)
        subprocess.run(f"rm {tmp}", shell=True, check=False)
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
    subprocess.run(f"sudo mkdir -p {key_dir}", shell=True)

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
        subprocess.run(f"sudo opendkim-genkey -t -s default -d {domain} -b 2048 -D {key_dir} -r -v", shell=True, check=True)
        subprocess.run(f"sudo chown www-data:www-data {key_dir}/default.*", shell=True, check=False)

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
    
    import tempfile, subprocess
    with tempfile.NamedTemporaryFile('w', delete=False) as zone_file:
        # Write TTL and SOA records
        zone_file.write(f"$TTL 86400  ; Default TTL\n")
        zone_file.write(f"@   IN  SOA ns1.{domain}. admin.{domain}. (\n")
        zone_file.write(f"                2024091501  ; Serial\n")
        zone_file.write(f"                3600        ; Refresh\n")
        zone_file.write(f"                1800        ; Retry\n")
        zone_file.write(f"                604800      ; Expire\n")
        zone_file.write(f"                86400 )     ; Negative Cache TTL\n\n")
        
        # Write NS records
        zone_file.write(f"@   IN  NS   ns1.{domain}.\n")
        zone_file.write(f"@   IN  NS   ns2.{domain}.\n\n")
        
        # Write A record
        zone_file.write(f"; A Record\n")
        zone_file.write(f"@   IN  A    {get_server_ip()}\n\n")
        zone_file.write(f"ns1   IN  A    {get_server_ip()}\n\n")
        zone_file.write(f"ns2   IN  A    {get_server_ip()}\n\n")

        
         # Write A record
        zone_file.write(f"; A Record\n")
        zone_file.write(f"mail   IN  A    {get_server_ip()}\n\n")
        zone_file.write(f"ftp   IN  A    {get_server_ip()}\n\n")

        # Write MX record
        zone_file.write(f"; MX Record\n")
        zone_file.write(f"@   IN  MX  10 mail.{domain}.\n\n")
        
        # Write CNAME record
        zone_file.write(f"; CNAME Record\n")
        zone_file.write(f"www IN  CNAME {domain}.\n\n")
        
        # Write TXT SPF record
        zone_file.write(f"; TXT Record\n")
        zone_file.write(f"@   IN  TXT  \"v=spf1 a mx ~all\"\n\n")

        # Write DKIM Record
        zone_file.write(f"; DKIM Record for {domain}\n")
 
        
        # Split the DKIM public key into chunks for readability
        
        for chunk in dkim_record_lines:
            zone_file.write(chunk)
        tmp_zone = zone_file.name
        
    subprocess.run(f"sudo cp {tmp_zone} {zone_file_path}", shell=True)
    subprocess.run(f"sudo chmod 644 {zone_file_path}", shell=True)
    subprocess.run(f"rm {tmp_zone}", shell=True)
     
    with tempfile.NamedTemporaryFile('w', delete=False) as f:
        f.write("\n")
        f.write(f'zone "{domain}" ')
        f.write("{\n")
        f.write("type master; \n")
        zone_db = os.path.join(paths.BIND_ZONE_DIR, f'db.{domain}')
        f.write(f'file "{zone_db}"; \n')
        f.write("};\n")
        tmp_conf = f.name
    subprocess.run(f"cat {tmp_conf} | sudo tee -a {paths.BIND_CONF}", shell=True)
    subprocess.run(f"rm {tmp_conf}", shell=True)
    

    print(f"BIND zone file created and saved to {zone_file_path}.")

def create_bind_recordsforsubdomain(name, zone_file_path):
    """Create BIND zone file records including DKIM, SOA, NS, A, MX, and other common DNS records."""
    
    import tempfile, subprocess
    
    record = f"\n; A Record\n{name}   IN  A    {get_server_ip()}\n\n"
    
    with tempfile.NamedTemporaryFile('w', delete=False, suffix='.zone') as tmp:
        tmp.write(record)
        tmp_path = tmp.name
    
    subprocess.run(f"cat {tmp_path} | sudo tee -a {zone_file_path}", shell=True, check=False)
    subprocess.run(f"rm {tmp_path}", shell=True, check=False)

def configure_opendkim(domain, key_dir):
    """Configure OpenDKIM for the domain."""
    try:
        if sys.platform == 'win32':
            # On Windows, DKIM is handled by hMailServer — no opendkim config
            print(f"Skipping OpenDKIM config on Windows (handled by mail server) for {domain}.")
            return

        # Update OpenDKIM configuration
        import tempfile, subprocess
        with tempfile.NamedTemporaryFile('w', delete=False) as f:
            f.write(f"\nDomain          {domain}\n")
            f.write(f"KeyFile          {os.path.join(key_dir, 'default.private')}\n")
            f.write(f"Selector         default\n")
            f.write(f"AutoRestart      yes\n")
            f.write(f"AutoRestartRate  10/1h\n")
            f.write(f"Umask            002\n")
            f.write(f"Mode             sv\n")
            f.write(f"Syslog           yes\n")
            f.write(f"LogWhy           yes\n")
            f.write(f"Canonicalization    relaxed/simple\n")
            tmp1 = f.name
        subprocess.run(f"cat {tmp1} | sudo tee -a /etc/opendkim.conf", shell=True)

        # Update KeyTable
        with tempfile.NamedTemporaryFile('w', delete=False) as f:
            f.write(f"default._domainkey.{domain} {domain}:default:{os.path.join(key_dir, 'default.private')}\n")
            tmp2 = f.name
        subprocess.run(f"cat {tmp2} | sudo tee -a {paths.OPENDKIM_KEYTABLE}", shell=True)

        # Update SigningTable
        with tempfile.NamedTemporaryFile('w', delete=False) as f:
            f.write(f"*@{domain} default._domainkey.{domain}\n")
            tmp3 = f.name
        subprocess.run(f"cat {tmp3} | sudo tee -a {paths.OPENDKIM_SIGNINGTABLE}", shell=True)

        # Update TrustedHosts
        with tempfile.NamedTemporaryFile('w', delete=False) as f:
            f.write(f"127.0.0.1\n")
            f.write(f"localhost\n")
            f.write(f"*.{domain}\n")
            tmp4 = f.name
        subprocess.run(f"cat {tmp4} | sudo tee -a {paths.OPENDKIM_TRUSTEDHOSTS}", shell=True)
        subprocess.run(f"rm {tmp1} {tmp2} {tmp3} {tmp4}", shell=True)

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





import re

def parse_dns_zone_file(DNS_FILE):
    records = []
    multiline_record = ""
    inside_multiline = False

    with open(DNS_FILE, 'r') as file:
        for line in file:
            line = line.strip()

            if not line or line.startswith(';'):
                continue  # Skip comments and empty lines

            # Check if it's a TTL line
            ttl_match = re.match(r'^\$TTL\s+(?P<ttl>\d+)\s+;\s+(?P<data>.*)', line)
            if ttl_match:
                records.append({
                    'name': '$TTL',
                    'ttl': ttl_match.group('ttl'),
                    'class': 'IN',
                    'type': ';',
                    'data': ttl_match.group('data')
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
                        record_data['ttl'] = record_data.get('ttl', None)
                        records.append(record_data)
                    multiline_record = ""
                continue

            # Match general DNS record lines
            general_pattern = re.compile(
                r'(?P<name>\S+)\s+((?P<ttl>\d+)\s+)?IN\s+(?P<type>\S+)\s+(?P<data>.*)'
            )
            match = general_pattern.match(line)
            if match:
                record_data = match.groupdict()
                record_data['ttl'] = record_data.get('ttl', None)
                records.append(record_data)

    return records





# Function to create a database and a table
def create_database_and_table(db_name,password):
    connection = None
    try:
        _validate_sql_identifier(db_name)
        connection = mysql.connector.connect(
            host="localhost",
            user="newuser", 
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
            user="newuser",
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
            user="newuser",  # Replace with your MySQL admin username
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
            user="newuser",  # Replace with your MySQL admin username
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
            user="newuser",  # Replace with your MySQL admin username
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
            user="newuser",  # Replace with your MySQL admin username
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
            user="newuser",
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
            user="newuser",
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
            user="newuser",
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
            user="newuser",
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
    # Ensure the main directory exists
    if not os.path.exists(main_directory):
        os.makedirs(main_directory)
    # Path to the zip file
    zip_filepath = os.path.join(main_directory, f"{zip_filename}.zip")

    file_list = []
    # Pre-calculate files for percentage indexing
    for location in locations:
        if os.path.exists(location):
            if os.path.isdir(location):
                for root, dirs, files in os.walk(location):
                    for file in files:
                        file_list.append(
                            (os.path.join(root, file), os.path.join(os.path.basename(location), os.path.relpath(os.path.join(root, file), start=location)))
                        )
            else:
                file_list.append((location, os.path.basename(location)))

    total_files = len(file_list)
    processed = 0

    # Create a zip file in write mode
    with zipfile.ZipFile(zip_filepath, 'w') as zipf:
        for file_path, arcname in file_list:
            # Skip the currently forming zip file if it overlaps
            if file_path == zip_filepath:
                continue
            
            # Skip old backup zips or the progress file
            fname = os.path.basename(file_path)
            if fname.startswith("backup_") and fname.endswith(".zip"):
                continue
            if fname == ".backup_progress":
                continue

            try:
                zipf.write(file_path, arcname=arcname)
            except Exception:
                continue
            
            processed += 1
            # Update progress file safely every few ticks to save IO mapping
            if progress_file and total_files > 0 and processed % max(1, total_files // 100) == 0:
                pct = int((processed / total_files) * 100)
                try:
                    with open(progress_file, 'w') as pf:
                        pf.write(str(pct))
                except Exception:
                    pass
    if sys.platform != 'win32':
        run_command(f'sudo chown {current}:{current} {zip_filepath}')
    else:
        run_command(f'icacls "{zip_filepath}" /grant {current}:F')
                



import re

def remove_zone_from_file(file_path, domain):
    with open(file_path, 'r') as file:
        lines = file.readlines()

    # Identify the zone block to remove
    zone_start = f'zone "{domain}" {{'
    zone_end = "};\n"
    
    in_zone_block = False
    updated_lines = []
    
    for line in lines:
        if zone_start in line:
            in_zone_block = True  # Start of the zone block
        if in_zone_block and zone_end in line:
            in_zone_block = False  # End of the zone block
            continue  # Skip adding the zone block to updated_lines
        if not in_zone_block:
            updated_lines.append(line)

    # Write the updated content back to the file
    with open(file_path, 'w') as file:
        file.writelines(updated_lines)


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
            # Match React code-split chunk paths inside JS bundles
            chunk_pattern = _re.findall(
                r'["\']([^"\']*?static/[^"\']*?\.(?:js|css|woff2?|ttf|eot|png|jpg|jpeg|svg|gif|webp|ico)[^"\']*)["\']',
                js_content
            )
            return chunk_pattern

        # Fetch root HTML
        root_resp = requests.get(target_url, headers=HEADERS, timeout=20, allow_redirects=True)
        if root_resp.status_code != 200:
            return False, f"Failed to fetch {target_url} (HTTP {root_resp.status_code})"

        html_content = root_resp.text
        downloaded.add(target_url)

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

        for asset_url in assets_to_download:
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
        for js_url, js_text in js_contents_to_scan:
            js_base = f"{urlparse(js_url).scheme}://{urlparse(js_url).netloc}"
            for chunk_ref in _discover_js_chunk_imports(js_text):
                full_chunk = urljoin(js_base, chunk_ref) if not chunk_ref.startswith('http') else chunk_ref
                lp = _download_asset(full_chunk)
                if lp:
                    url_to_local[full_chunk] = lp

        # Rewrite HTML to use local paths
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
        return True, f"Site cloned successfully! {total} assets downloaded to {destination_dir}"

    except Exception as e:
        return False, f"Clone failed: {str(e)}"
