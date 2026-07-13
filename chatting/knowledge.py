"""
VoidPanel Help Bot — knowledge base.

Each entry has:
  - keywords: list of words/phrases that trigger this topic
  - title: short heading shown to the user
  - answer: the help text (may contain HTML)
"""

KNOWLEDGE_BASE = [
    # ── Installation ───────────────────────────────────────────────
    {
        "keywords": ["install", "installation", "setup", "curl", "one-line", "deploy", "fresh install"],
        "title": "Installation",
        "answer": (
            "<b>One-Line Installation</b><br>"
            "<code>curl -fsSL https://voidpanel.com/op/install.sh | bash</code><br><br>"
            "<b>Supported OS:</b> Ubuntu 22.04/24.04 LTS, AlmaLinux 8/9, Rocky Linux 8/9<br>"
            "<b>Requirements:</b> Fresh server, 2 GB RAM (4 GB+ recommended), static public IPv4.<br><br>"
            "The installer automatically detects your distro and runs the correct setup script. "
            "After completion, your admin credentials are saved to <code>/root/voidpanel_access.txt</code>."
        ),
    },
    {
        "keywords": ["windows", "wsl", "wsl2", "windows install"],
        "title": "Windows Installation (WSL2)",
        "answer": (
            "VoidPanel supports Windows Server via <b>WSL2</b>.<br><br>"
            "<b>Steps:</b><br>"
            "1. Run <code>install-windows.ps1</code> in an elevated PowerShell.<br>"
            "2. It enables WSL2, installs Ubuntu, and runs the Linux installer inside WSL.<br>"
            "3. Use <code>windows-startup.ps1</code> to forward ports (8082, 9002, etc.) from Windows to WSL on boot.<br><br>"
            "<b>Note:</b> The web terminal is not available on Windows."
        ),
    },
    # ── Domains & Websites ─────────────────────────────────────────
    {
        "keywords": ["domain", "add domain", "website", "add website", "create website", "new domain", "list website"],
        "title": "Domain / Website Management",
        "answer": (
            "Go to <b>Admin Panel → List Websites</b> to see all hosted domains.<br><br>"
            "<b>Adding a domain:</b><br>"
            "1. Click <b>'Add Website'</b> and enter the domain name, user, and package.<br>"
            "2. VoidPanel automatically creates the home directory, nginx config, self-signed SSL, and DNS zone.<br><br>"
            "<b>Document root:</b> <code>/home/&lt;user&gt;/public_html/</code><br>"
            "<b>Logs:</b> <code>/home/&lt;user&gt;/logs/</code>"
        ),
    },
    {
        "keywords": ["subdomain", "sub domain", "add subdomain", "create subdomain", "delete subdomain"],
        "title": "Subdomain Management",
        "answer": (
            "Navigate to <b>Subdomains</b> from the domain's management page.<br><br>"
            "<b>Add:</b> Enter the subdomain prefix → VoidPanel creates the directory under "
            "<code>public_html/&lt;name&gt;/</code>, generates an nginx config, and provisions a self-signed SSL.<br>"
            "<b>Delete:</b> Click the delete icon. The directory and nginx config are removed automatically.<br><br>"
            "Subdomain limits are enforced per hosting package."
        ),
    },
    # ── SSL ─────────────────────────────────────────────────────────
    {
        "keywords": ["ssl", "https", "certificate", "certbot", "let's encrypt", "letsencrypt", "auto ssl"],
        "title": "SSL / HTTPS Certificates",
        "answer": (
            "<b>Auto SSL (Let's Encrypt):</b><br>"
            "1. Go to <b>SSL</b> on the domain page → click <b>'Run Auto SSL'</b>.<br>"
            "2. Certbot provisions a free certificate and updates nginx automatically.<br><br>"
            "<b>Run SSL for All:</b> On the admin panel, use 'Auto SSL for All' to batch-provision.<br><br>"
            "<b>Troubleshooting:</b><br>"
            "• Ensure DNS A-record points to your server IP.<br>"
            "• Port 80 must be open (CSF firewall).<br>"
            "• Check logs at <code>/home/&lt;user&gt;/logs/ssl.txt</code>."
        ),
    },
    # ── Email ──────────────────────────────────────────────────────
    {
        "keywords": ["email", "mail", "postfix", "dovecot", "roundcube", "webmail", "smtp", "imap", "add email", "email account"],
        "title": "Email System",
        "answer": (
            "VoidPanel provides a full mail stack: <b>Postfix</b> (SMTP), <b>Dovecot</b> (IMAP/POP3), "
            "and <b>Roundcube</b> webmail.<br><br>"
            "<b>Add an email account:</b><br>"
            "1. Go to the domain → <b>Email Accounts</b> → enter username and password.<br>"
            "2. The mailbox is created under <code>/home/&lt;username&gt;/mail/&lt;domain&gt;/</code>.<br><br>"
            "<b>Webmail (Roundcube):</b> Access via <code>https://&lt;hostname&gt;:9002</code><br>"
            "<b>Change password:</b> Use the 'Change Password' button next to the email account.<br><br>"
            "<b>Limits:</b> Email account quotas are enforced per hosting package."
        ),
    },
    # ── DNS ─────────────────────────────────────────────────────────
    {
        "keywords": ["dns", "bind", "bind9", "nameserver", "zone", "a record", "mx record", "cname", "txt record", "dkim", "spf"],
        "title": "DNS Management",
        "answer": (
            "VoidPanel uses <b>BIND9</b> for authoritative DNS.<br><br>"
            "<b>Edit DNS records:</b> Go to Domain → <b>DNS Zone Editor</b>.<br>"
            "Supported record types: A, AAAA, MX, CNAME, TXT, NS, SRV.<br><br>"
            "<b>DKIM:</b> Auto-generated when a domain is added (OpenDKIM).<br>"
            "<b>Custom nameservers:</b> Point your domain registrar to your server's NS records.<br><br>"
            "<b>Tip:</b> After editing records, BIND reloads automatically. Allow 5-60 min for DNS propagation."
        ),
    },
    # ── File Manager ───────────────────────────────────────────────
    {
        "keywords": ["file manager", "files", "upload", "download", "edit file", "extract", "compress", "zip", "permissions"],
        "title": "File Manager",
        "answer": (
            "Access via <b>Domain → File Manager</b>.<br><br>"
            "<b>Features:</b><br>"
            "• Upload files (drag & drop or button)<br>"
            "• Create / rename / delete files and folders<br>"
            "• Edit files in-browser with syntax highlighting<br>"
            "• Compress / extract .zip archives<br>"
            "• Copy and move files between directories<br><br>"
            "<b>Storage quotas</b> are enforced per hosting package. "
            "Max upload size: 50 MB per file."
        ),
    },
    # ── Database ───────────────────────────────────────────────────
    {
        "keywords": ["database", "mysql", "mariadb", "phpmyadmin", "pma", "create database", "add database", "db user"],
        "title": "Database Management",
        "answer": (
            "<b>Create a database:</b> Domain → <b>Databases</b> → enter name → Create.<br>"
            "<b>Create a DB user:</b> Enter username + password → Create User.<br>"
            "<b>Grant privileges:</b> Select the user, database, and privilege set → Apply.<br><br>"
            "<b>phpMyAdmin:</b> Click 'Open phpMyAdmin' — you're auto-logged in via SSO.<br>"
            "Access URL: <code>https://&lt;domain&gt;/phpmyadmin</code><br><br>"
            "<b>Database limits</b> are enforced per hosting package."
        ),
    },
    # ── PHP ─────────────────────────────────────────────────────────
    {
        "keywords": ["php", "php version", "php.ini", "php extension", "php-fpm", "change php", "install php"],
        "title": "PHP Configuration",
        "answer": (
            "<b>Change PHP version per domain:</b><br>"
            "Domain → Settings → select PHP version (5.6 – 8.4).<br><br>"
            "<b>Install a new PHP version (Admin):</b><br>"
            "Server Settings → PHP → select version → Install.<br><br>"
            "<b>Edit php.ini:</b> Server Settings → PHP → click the version → edit directly.<br>"
            "<b>Manage extensions:</b> Toggle extensions on/off per PHP version.<br><br>"
            "Changes take effect after PHP-FPM is restarted (automatic)."
        ),
    },
    # ── FTP ─────────────────────────────────────────────────────────
    {
        "keywords": ["ftp", "vsftpd", "ftp account", "ftp user", "add ftp"],
        "title": "FTP Accounts",
        "answer": (
            "<b>Create an FTP account:</b> Domain → <b>FTP Accounts</b> → enter username, password, storage quota.<br><br>"
            "<b>Connection details:</b><br>"
            "• Host: your server IP<br>"
            "• Port: 21<br>"
            "• Protocol: FTP (explicit TLS)<br>"
            "• Username: the full FTP username<br><br>"
            "<b>Change password / storage:</b> Use the edit buttons next to the FTP account."
        ),
    },
    # ── Python / MERN Apps ─────────────────────────────────────────
    {
        "keywords": ["python app", "django", "flask", "gunicorn", "python hosting", "venv", "virtual environment", "mern", "node", "nodejs", "npm", "react"],
        "title": "Python & MERN (Node.js) App Hosting",
        "answer": (
            "<b>Python Apps:</b><br>"
            "1. Domain → <b>Python Apps</b> → enter app name.<br>"
            "2. VoidPanel creates a virtualenv, systemd service, and nginx reverse proxy.<br>"
            "3. Use the built-in terminal to <code>pip install</code> packages.<br>"
            "4. Start / Stop / Restart from the UI.<br><br>"
            "<b>MERN / Node.js Apps:</b><br>"
            "1. Domain → <b>Node.js Apps</b> → enter app name.<br>"
            "2. A port is auto-assigned and nginx is configured as a reverse proxy.<br>"
            "3. Use the terminal to run <code>npm install</code> and <code>npm start</code>."
        ),
    },
    # ── Terminal ───────────────────────────────────────────────────
    {
        "keywords": ["terminal", "shell", "command line", "cli", "ssh", "bash", "web terminal"],
        "title": "Web Terminal",
        "answer": (
            "VoidPanel includes a built-in <b>web terminal</b> for each domain.<br><br>"
            "Access: Domain → <b>Terminal</b>.<br>"
            "• Commands run as the domain's Linux user (not root).<br>"
            "• Supports pip, python, npm, node, and general bash commands.<br>"
            "• Use <code>cd &lt;dir&gt;</code> to navigate within the user's home.<br><br>"
            "<b>Admin Terminal:</b> Available via <b>Server Settings → Active Terminal</b> (ShellInABox).<br><br>"
            "<b>Note:</b> Web terminal is not available on Windows installations."
        ),
    },
    # ── Firewall ───────────────────────────────────────────────────
    {
        "keywords": ["firewall", "csf", "block ip", "whitelist", "blacklist", "brute force", "security"],
        "title": "Firewall (CSF)",
        "answer": (
            "VoidPanel uses <b>CSF (ConfigServer Firewall)</b>.<br><br>"
            "<b>Manage:</b> Admin Panel → <b>Firewall</b>.<br>"
            "• View / add / remove blocked IPs<br>"
            "• Brute-force protection: tracks failed login attempts and auto-blocks IPs<br><br>"
            "<b>Default open ports:</b> 21, 22, 25, 53, 80, 110, 143, 443, 465, 587, 993, 995, "
            "8080, 8082, 9002, 8092."
        ),
    },
    # ── Packages & Users ───────────────────────────────────────────
    {
        "keywords": ["package", "hosting package", "plan", "quota", "storage", "bandwidth", "user", "add user", "create user", "client"],
        "title": "Hosting Packages & Users",
        "answer": (
            "<b>Create a hosting package:</b> Admin → <b>Packages</b> → set storage, email, FTP, "
            "subdomain, and database limits. Use '0' or 'unlimited' for no limit.<br><br>"
            "<b>Create a user (client):</b><br>"
            "When adding a website, a Linux user is auto-created with the specified package.<br><br>"
            "<b>Change package:</b> Admin → Users → select user → Change Package.<br>"
            "<b>Change password:</b> Admin → Users → select user → Change Password."
        ),
    },
    # ── Backups ────────────────────────────────────────────────────
    {
        "keywords": ["backup", "restore", "download backup", "zip backup"],
        "title": "Backups",
        "answer": (
            "<b>Create a backup:</b> Domain → <b>Backup</b> → click 'Create Backup'.<br>"
            "This zips the domain's files, mail, DKIM keys, and SSL certificates.<br><br>"
            "<b>Download:</b> After creation, click the download link.<br>"
            "Backups are stored in the user's home directory.<br><br>"
            "<b>Note:</b> Database backups should be exported separately via phpMyAdmin."
        ),
    },
    # ── Cron Jobs ──────────────────────────────────────────────────
    {
        "keywords": ["cron", "cron job", "scheduled task", "cronjob", "crontab"],
        "title": "Cron Jobs",
        "answer": (
            "<b>Manage cron jobs:</b> Admin → <b>Cron Jobs</b>.<br><br>"
            "Enter the <b>schedule</b> (minute, hour, day, month, weekday) and the <b>command</b>.<br>"
            "Example: <code>0 2 * * * /usr/bin/php /home/user/script.php</code><br><br>"
            "Cron jobs run under the system crontab. Only admins can manage server-level crons."
        ),
    },
    # ── Redirects ──────────────────────────────────────────────────
    {
        "keywords": ["redirect", "301", "url redirect", "rewrite"],
        "title": "URL Redirects",
        "answer": (
            "<b>Add a redirect:</b> Domain → <b>Redirects</b> → enter source path and destination path.<br>"
            "This creates a <code>301</code> redirect rule in the nginx config.<br><br>"
            "<b>Delete:</b> Click the remove button next to the redirect entry.<br><br>"
            "<b>Note:</b> <code>/phpmyadmin</code> and <code>/static</code> paths cannot be redirected."
        ),
    },
    # ── Server Status / Services ───────────────────────────────────
    {
        "keywords": ["service", "restart", "start", "stop", "nginx", "mysql restart", "server status", "status", "reboot"],
        "title": "Server Status & Services",
        "answer": (
            "<b>View:</b> Admin → <b>Server Status</b>.<br>"
            "Shows domain count, email count, database count, and status of all services.<br><br>"
            "<b>Manage services:</b> Start / Stop / Restart individual services "
            "(nginx, MySQL, Postfix, Dovecot, BIND9, CSF, uWSGI).<br><br>"
            "<b>Restart All:</b> Restarts all core services at once.<br>"
            "<b>Reboot / Shutdown:</b> Available from Server Status (admin only)."
        ),
    },
    # ── Hostname ───────────────────────────────────────────────────
    {
        "keywords": ["hostname", "change hostname", "server name", "panel url"],
        "title": "Hostname Configuration",
        "answer": (
            "<b>Change hostname:</b> Admin → <b>Hostname</b> → enter the new FQDN.<br>"
            "VoidPanel updates <code>/etc/hostname</code>, <code>/etc/hosts</code>, "
            "nginx configs, and Django's <code>CSRF_TRUSTED_ORIGINS</code>.<br><br>"
            "<b>Hostname SSL:</b> Click 'SSL for Hostname' to provision a Let's Encrypt cert "
            "for the panel itself (ports 8082/9002)."
        ),
    },
    # ── Credentials / Access ───────────────────────────────────────
    {
        "keywords": ["credentials", "password", "login", "access", "admin url", "panel url", "port 8082", "forgot password"],
        "title": "Access & Credentials",
        "answer": (
            "<b>Admin panel:</b> <code>https://&lt;server-ip&gt;:8082</code><br>"
            "<b>User panel:</b> <code>https://&lt;server-ip&gt;:8080</code> (or 80)<br>"
            "<b>Roundcube:</b> <code>https://&lt;server-ip&gt;:9002</code><br>"
            "<b>phpMyAdmin:</b> <code>https://&lt;server-ip&gt;:8092</code><br><br>"
            "<b>Initial credentials:</b> Saved in <code>/root/voidpanel_access.txt</code> after install.<br>"
            "<b>MySQL password:</b> Stored in <code>/etc/dontdelete.txt</code>."
        ),
    },
    # ── Update ─────────────────────────────────────────────────────
    {
        "keywords": ["update", "upgrade", "update panel", "new version"],
        "title": "Updating VoidPanel",
        "answer": (
            "<b>Update:</b> Admin → <b>Server Status</b> → click <b>'Update Panel'</b>.<br>"
            "This downloads the latest version from voidpanel.com and applies it.<br><br>"
            "<b>Manual update:</b><br>"
            "<code>curl -fsSL https://voidpanel.com/updatepanel.sh | bash</code>"
        ),
    },
    # ── Troubleshooting ────────────────────────────────────────────
    {
        "keywords": ["error", "not working", "problem", "issue", "troubleshoot", "debug", "log", "500", "502", "404", "help"],
        "title": "Troubleshooting",
        "answer": (
            "<b>Common issues:</b><br><br>"
            "<b>502 Bad Gateway:</b> PHP-FPM or uWSGI is not running → "
            "Admin → Server Status → restart the service.<br><br>"
            "<b>SSL not working:</b> Check that DNS points to your server and port 80 is open. "
            "See logs: <code>/home/&lt;user&gt;/logs/ssl.txt</code>.<br><br>"
            "<b>Email not sending:</b> Verify Postfix is running, port 25 is open, "
            "and SPF/DKIM records are set in DNS.<br><br>"
            "<b>Panel not loading:</b> Restart uWSGI: <code>sudo systemctl restart uwsgi</code><br><br>"
            "<b>Install logs:</b> <code>/var/log/voidpanel_install.log</code><br>"
            "<b>Panel logs:</b> <code>/var/www/panel/panel.log</code>"
        ),
    },
]


def search_knowledge(query):
    """
    Search the knowledge base for entries matching the user's query.
    Returns a list of matching entries sorted by relevance (keyword hit count).
    """
    query_lower = query.lower()
    query_words = set(query_lower.split())

    scored = []
    for entry in KNOWLEDGE_BASE:
        score = 0
        for kw in entry["keywords"]:
            kw_lower = kw.lower()
            # Exact phrase match in query — strongest signal
            if kw_lower in query_lower:
                score += 3
            # Individual word overlap
            elif any(w in query_words for w in kw_lower.split()):
                score += 1
        if score > 0:
            scored.append((score, entry))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [entry for _, entry in scored]
