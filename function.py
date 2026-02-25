
import subprocess
import socket
import os
import mimetypes
import stat
import random
import requests
import mysql.connector
from mysql.connector import Error

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
        response = requests.get('https://api.ipify.org')
        public_ip = response.text
        return public_ip
    except Exception as e:
        print(f"Error getting server IP address: {e}")
        return None
    

def run_command(command, check=True):
    """Run a shell command and optionally check for errors."""
    print(f"Running command: {command}")
    result = subprocess.run(command, shell=True, check=check, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return result

import subprocess
import sys

def change_hostname(new_hostname):
    try:
        # Change the hostname
        subprocess.run(['sudo', 'hostnamectl', 'set-hostname', new_hostname], check=True)

        # Update /etc/hosts file
        with open('/etc/hosts', 'r') as file:
            lines = file.readlines()

        with open('/var/www/panel/panel/settings.py', 'a+') as file:
            file.write('\n')
            file.write(f'CSRF_TRUSTED_ORIGINS.append("https://{new_hostname}:8082")')


        with open('/etc/hosts', 'w') as file:
            for line in lines:
                # Replace the old hostname with the new one
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
        run_command(f"certbot --nginx --non-interactive --agree-tos --email {email} -d {hostname} ")  
        old_hostname=socket.gethostname()
        sed_command = f"sed -i 's/{old_hostname}/{hostname}/g' /etc/nginx/sites-available/panel"
        run_command(sed_command)
        sed_command = f"sed -i 's/{old_hostname}/{hostname}/g' /etc/nginx/sites-available/phpmyadmin"
        run_command(sed_command)
        sed_command = f"sed -i 's/{old_hostname}/{hostname}/g' /etc/nginx/sites-available/roundcube"
        run_command(sed_command) 
        if xx==0:
            sed_command = f"sed -i 's|/etc/nginx/dummy.crt|/etc/letsencrypt/live/{hostname}/fullchain.pem|g' /etc/nginx/sites-available/panel"
            run_command(sed_command)
            sed_command = f"sed -i 's|/etc/nginx/dummy.key|/etc/letsencrypt/live/{hostname}/privkey.pem|g' /etc/nginx/sites-available/panel"
            run_command(sed_command)

            sed_command = f"sed -i 's|/etc/nginx/dummy.crt|/etc/letsencrypt/live/{hostname}/fullchain.pem|g' /etc/nginx/sites-available/phpmyadmin"
            run_command(sed_command)
            sed_command = f"sed -i 's|/etc/nginx/dummy.key|/etc/letsencrypt/live/{hostname}/privkey.pem|g' /etc/nginx/sites-available/phpmyadmin"
            run_command(sed_command)

            sed_command = f"sed -i 's|/etc/nginx/dummy.crt|/etc/letsencrypt/live/{hostname}/fullchain.pem|g' /etc/nginx/sites-available/roundcube"
            run_command(sed_command)
            sed_command = f"sed -i 's|/etc/nginx/dummy.key|/etc/letsencrypt/live/{hostname}/privkey.pem|g' /etc/nginx/sites-available/roundcube"
            run_command(sed_command)
        else:
            sed_command = f"sed -i 's|/etc/letsencrypt/live/{old_hostname}/fullchain.pem|/etc/letsencrypt/live/{hostname}/fullchain.pem|g' /etc/nginx/sites-available/panel"
            run_command(sed_command)
            sed_command = f"sed -i 's|/etc/letsencrypt/live/{old_hostname}/privkey.pem|/etc/letsencrypt/live/{hostname}/privkey.pem|g' /etc/nginx/sites-available/panel"
            run_command(sed_command)

            sed_command = f"sed -i 's|/etc/letsencrypt/live/{old_hostname}/fullchain.pem|/etc/letsencrypt/live/{hostname}/fullchain.pem|g' /etc/nginx/sites-available/phpmyadmin"
            run_command(sed_command)
            sed_command = f"sed -i 's|/etc/letsencrypt/live/{old_hostname}/privkey.pem|/etc/letsencrypt/live/{hostname}/privkey.pem|g' /etc/nginx/sites-available/phpmyadmin"
            run_command(sed_command)

            sed_command = f"sed -i 's|/etc/letsencrypt/live/{old_hostname}/fullchain.pem|/etc/letsencrypt/live/{hostname}/fullchain.pem|g' /etc/nginx/sites-available/roundcube"
            run_command(sed_command)
            sed_command = f"sed -i 's|/etc/letsencrypt/live/{old_hostname}/privkey.pem|/etc/letsencrypt/live/{hostname}/privkey.pem|g' /etc/nginx/sites-available/roundcube"
            run_command(sed_command)
        run_command("sudo systemctl reload nginx")
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
        print(f"Permission denied for directory: {directory}")
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

        with zipfile.ZipFile(zip_filename, 'r') as zip_ref:
            zip_ref.extractall(extract_to_folder)



def generate_ssl_certificates(domain, ssl_dir,logs):
    # Paths for SSL certificate and key
    cert_path = os.path.join(ssl_dir, f"{domain}.crt")
    key_path = os.path.join(ssl_dir, f"{domain}.key")

    # Ensure SSL directory exists
    os.makedirs(ssl_dir, exist_ok=True)

    # OpenSSL command to generate a self-signed SSL certificate
    openssl_command = [
        "openssl", "req", "-x509", "-nodes", "-days", "365", "-newkey", "rsa:2048",
        "-keyout", key_path, "-out", cert_path, "-subj", f"/CN={domain}"
    ]
    f=open(f'{logs}/ssl.txt','a')

    try:
        # Run OpenSSL command to generate the certificates
        subprocess.run(openssl_command, check=True)
        
        f.write("\n")
        f.write(f"SSL certificate and key generated for {domain} at {ssl_dir}")
        print(f"SSL certificate and key generated for {domain} at {ssl_dir}")
    except subprocess.CalledProcessError as e:
        f.write("\n")
        f.write(f"Failed to generate SSL certificate: {e}")
        f.write(f"Cannot Write Nginx File")
    
        return None, None
    f.close()

    return cert_path, key_path


def create_nginx_ssl_conf(file_path, domain, root_dir, cert_path, key_path):
    # Nginx configuration content with SSL support
    nginx_ssl_conf = f"""
server {{
    listen 443 ssl;
    server_name {domain} www.{domain};
    client_max_body_size 1500M;

    ssl_certificate {cert_path};
    ssl_certificate_key {key_path};

    # Security Headers
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;

    root {root_dir};
    index index.php index.html index.htm;
   location ~ \.php$ {{
        include snippets/fastcgi-php.conf;
        fastcgi_pass unix:/var/run/php/php8.3-fpm.sock;
        fastcgi_param SCRIPT_FILENAME $document_root$fastcgi_script_name;
        include fastcgi_params;
         fastcgi_read_timeout 300;
        fastcgi_connect_timeout 300;
        fastcgi_send_timeout 300;
    }}

    location /phpmyadmin {{
    alias /usr/share/phpmyadmin;  # This should point to your phpMyAdmin installation
    index index.php;

    location ~ ^/phpmyadmin/(.+\.php)$ {{
        fastcgi_pass unix:/var/run/php/php8.3-fpm.sock;
        fastcgi_index index.php;
        include fastcgi_params;
        fastcgi_param SCRIPT_FILENAME /usr/share/phpmyadmin/$1;  # Ensure this is correct
    }}

    location ~ ^/phpmyadmin/(.+\.(gif|jpe?g|png|ico|css|js))$ {{
        alias /usr/share/phpmyadmin/$1;  # This serves static assets
    }}
}}

     location ~ /\.ht {{
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
        # Write the configuration to the specified file path
        with open(file_path, 'w') as f:
            f.write(nginx_ssl_conf)
            run_command('sudo systemctl restart nginx')
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
    os.makedirs(key_dir, exist_ok=True)
    
    # Paths for the private and public DKIM keys
    private_key_path = os.path.join(key_dir, 'default.private')
    public_key_path = os.path.join(key_dir, 'default.txt')

    # Generate DKIM keys using opendkim-genkey command
    subprocess.run([
        'opendkim-genkey', '-t', '-s', 'default', '-d', domain, '-b', '2048', '-r', '-v'
    ], check=True)
    
    # Move generated keys to the specified directory
    os.rename('default.private', private_key_path)
    os.rename('default.txt', public_key_path)

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
    
    with open(zone_file_path, 'w') as zone_file:
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
     
    with open('/etc/bind/named.conf','a') as f:
        f.write("\n")
        f.write(f'zone "{domain}" ')
        f.write("{\n")
        f.write("type master; \n")
        f.write(f'file "/etc/bind/db.{domain}"; \n')
        f.write("};\n")
    

    print(f"BIND zone file created and saved to {zone_file_path}.")

def create_bind_recordsforsubdomain(name, zone_file_path):
    """Create BIND zone file records including DKIM, SOA, NS, A, MX, and other common DNS records."""
    
   

    
    with open(zone_file_path, 'a') as zone_file:
       



        
         # Write A record\zone_file.write(f"; A Record\n")
         zone_file.write(f"\n")
         zone_file.write(f"; A Record\n")
         zone_file.write(f"{name}   IN  A    {get_server_ip()}\n\n")
        

       

def configure_opendkim(domain, key_dir):
    """Configure OpenDKIM for the domain."""
    try:
        # Update OpenDKIM configuration
        with open('/etc/opendkim.conf', 'a') as f:
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

        # Update KeyTable
        with open('/etc/opendkim/KeyTable', 'a') as f:
            f.write(f"default._domainkey.{domain} {domain}:default:{os.path.join(key_dir, 'default.private')}\n")
        
        # Update SigningTable
        with open('/etc/opendkim/SigningTable', 'a') as f:
            f.write(f"*@{domain} default._domainkey.{domain}\n")

        # Update TrustedHosts
        with open('/etc/opendkim/TrustedHosts', 'a') as f:
            f.write(f"127.0.0.1\n")
            f.write(f"localhost\n")
            f.write(f"*.{domain}\n")

        print(f"OpenDKIM configured for {domain}.")
    except IOError as e:
        print(f"Error configuring OpenDKIM: {e}")
   



BIND_ZONE_PATH = "/etc/bind/zones/"
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
        # Establish a connection to MySQL server
        connection = mysql.connector.connect(
            host="localhost",  # Replace with your host
            user="newuser", 
             password=password # Replace with your MySQL username
        # Replace with your MySQL password
        )
        print(connection)
        if connection.is_connected():
            cursor = connection.cursor()
            

            # Create a new database
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS {db_name}")
            # Return True for successful creation
            return True
        else:
            return False


    except Error as e:
        return False



def create_mysql_user(username,password,passw):
    connection = None
    try:
        # Establish a connection to MySQL server
        connection = mysql.connector.connect(
            host="localhost",  # Replace with your host
            user="newuser",  # Replace with your MySQL admin username
            password=passw # Replace with your MySQL admin password
        )

        if connection.is_connected():
            cursor = connection.cursor()


            create_user_query = f"CREATE USER '{username}'@'localhost' IDENTIFIED BY '{password}';"
            cursor.execute(create_user_query)


            return True

    except Error as e:
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


import mysql.connector
from mysql.connector import Error

def remove_database(db_name, passw):
    connection = None
    try:
        # Establish a connection to MySQL server
        connection = mysql.connector.connect(
            host="localhost",  
            user="newuser",  # Replace with your MySQL admin username
            password=passw  # Replace with your MySQL admin password
        )

        if connection.is_connected():
            cursor = connection.cursor()
            # Drop the database
            cursor.execute(f"DROP DATABASE IF EXISTS {db_name};")
            connection.commit()  # Commit the change
            print(f"Database '{db_name}' has been removed.")
            return True

    except Error as e:
        print(f"Error: {e}")
        return False
    finally:
        if connection and connection.is_connected():
            cursor.close()
            connection.close()

def delete_mysql_user(username, passw):
    connection = None
    try:
        # Establish a connection to MySQL server
        connection = mysql.connector.connect(
            host="localhost",  
            user="newuser",  # Replace with your MySQL admin username
            password=passw  # Replace with your MySQL admin password
        )

        if connection.is_connected():
            cursor = connection.cursor()
            # Drop the user
            delete_user_query = f"DROP USER IF EXISTS '{username}'@'localhost';"
            cursor.execute(delete_user_query)
            connection.commit()  # Commit the change
            print(f"User '{username}' has been removed.")
            return True

    except Error as e:
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
        # Establish a connection to MySQL server
        connection = mysql.connector.connect(
            host="localhost",  
            user="newuser",  # Replace with your MySQL admin username
            password=passw  # Replace with your MySQL admin password
        )

        if connection.is_connected():
            cursor = connection.cursor()
            # Change the user's password
            change_password_query = f"ALTER USER '{username}'@'localhost' IDENTIFIED BY '{new_password}';"
            cursor.execute(change_password_query)
            connection.commit()  # Commit the change
            print(f"Password for user '{username}' has been changed.")
            return True

    except Error as e:
        print(f"Error: {e}")
        return False
    finally:
        if connection and connection.is_connected():
            cursor.close()
            connection.close()





def grant_mysql_user_privileges(username, database, privileges, admin_password):
    connection = None
    try:
        # Establish a connection to the MySQL server
        connection = mysql.connector.connect(
            host="localhost",  
            user="newuser",  # Replace with your MySQL admin username
            password=admin_password  # Replace with your MySQL admin password
        )

        if connection.is_connected():
            cursor = connection.cursor()
            # Construct the GRANT statement for the specified database
            privileges_string = ', '.join(privileges)
            grant_privileges_query = f"GRANT {privileges_string} ON `{database}`.* TO '{username}'@'localhost';"
            cursor.execute(grant_privileges_query)
            connection.commit()  # Commit the change
           
            return True

    except Error as e:
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
         
def zip_multiple_locations_backup_user(main_directory, locations, zip_filename,current):
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
    run_command(f'sudo chown {current}:{current} {zip_filepath}')
                



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
    
    # Check common installation paths for PHP versions
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
        # Fetch the service status using systemctl
        status = subprocess.check_output([ 'sudo' ,'systemctl', 'is-active', service_name], stderr=subprocess.STDOUT).decode('utf-8').strip()
        return status
    except :
        return False

    


def restart_service(service_name):
    try:
        # Restart the service using systemctl
        subprocess.run(['sudo', 'systemctl', 'restart', service_name], check=True)
        return True
    except :
        return False
def start_service(service_name):
    try:
        # Restart the service using systemctl
        subprocess.run(['sudo', 'systemctl', 'start', service_name], check=True)
        return True
    except :
        return False
    
def stop_service(service_name):
    try:
        # Restart the service using systemctl
        subprocess.run(['sudo', 'systemctl', 'stop', service_name], check=True)
        return True
    except :
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



