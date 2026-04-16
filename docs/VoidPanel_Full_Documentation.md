# VoidPanel — Complete Documentation

**VoidPanel** is a modern, open-source web hosting control panel that lets you manage websites, email, databases, DNS, and applications from a single web interface. It supports **Ubuntu**, **AlmaLinux**, **Rocky Linux**, and **Windows Server (WSL2)**.

> **Version**: 1.x  
> **License**: Open Source  
> **Requirements**: 2GB+ RAM, Static IPv4, Fresh OS Install

---

## Table of Contents

1. [Getting Started](#1-getting-started)
2. [Admin Dashboard (Panel)](#2-admin-dashboard)
3. [User Control Panel](#3-user-control-panel)
4. [Website & Domain Management](#4-website--domain-management)
5. [Subdomain Management](#5-subdomain-management)
6. [SSL / HTTPS Certificates](#6-ssl--https-certificates)
7. [Email System](#7-email-system)
8. [DNS Management](#8-dns-management)
9. [File Manager](#9-file-manager)
10. [Database Management](#10-database-management)
11. [PHP Configuration](#11-php-configuration)
12. [FTP Accounts](#12-ftp-accounts)
13. [Python Application Hosting](#13-python-application-hosting)
14. [MERN / Node.js Application Hosting](#14-mern--nodejs-application-hosting)
15. [Cron Jobs (Scheduled Tasks)](#15-cron-jobs)
16. [URL Redirects](#16-url-redirects)
17. [Backup & Restore](#17-backup--restore)
18. [Web Terminal](#18-web-terminal)
19. [Firewall (CSF)](#19-firewall-csf)
20. [Server Status & Monitoring](#20-server-status--monitoring)
21. [User & Package Management](#21-user--package-management)
22. [AI Help Assistant (Chat)](#22-ai-help-assistant)
23. [WHMCS / Billing API](#23-whmcs--billing-api)
24. [Installation Guide](#24-installation-guide)
25. [Access Ports & URLs](#25-access-ports--urls)
26. [Updating VoidPanel](#26-updating-voidpanel)
27. [Troubleshooting](#27-troubleshooting)
28. [Project Structure](#28-project-structure)
29. [FAQ](#29-faq)

---

## 1. Getting Started

### What is VoidPanel?

VoidPanel is a **web hosting control panel** — similar to cPanel or Plesk — but free, open-source, and built with modern technology. It allows server administrators to:

- Host multiple websites on a single server
- Create email accounts with webmail access
- Manage DNS records
- Create and manage MySQL databases
- Host Python and Node.js applications
- Manage SSL certificates automatically
- Control server firewall rules
- Create FTP accounts
- Schedule cron jobs
- Monitor server health in real-time

### Two Interfaces

VoidPanel has **two separate interfaces**:

| Interface | Who Uses It | What It Does |
|-----------|------------|--------------|
| **Admin Dashboard** | Server administrator (superuser) | Full server control, user management, global settings |
| **User Control Panel** | Website owners (regular users) | Domain-specific tools — file manager, email, databases, etc. |

### Quick Overview

After installation, you'll access:
- **Admin Dashboard** — for managing the server, creating users, and global settings
- **User Control Panel** — each user gets their own control panel for their domains

---

## 2. Admin Dashboard

The Admin Dashboard is the central management hub. Only **superusers** (administrators) can access it.

### Dashboard Home

The dashboard shows:
- **Server load** — Real-time CPU, RAM, and disk usage graphs
- **Quick actions** — Add website, manage users, server status
- **Recent activity** — Login history and recent operations
- **System messages** — Alerts and notifications

### What Admins Can Do

| Feature | Description |
|---------|-------------|
| Add Users | Create hosting accounts with domain assignments |
| Manage Packages | Create hosting plans with storage, email, and database limits |
| Server Status | Monitor and restart services (Nginx, Mail, DNS, etc.) |
| Firewall | Manage CSF firewall rules, block/allow IPs |
| PHP Settings | Install PHP versions and extensions globally |
| FTP Server | Configure FTP server settings |
| Email Config | Set email sending limits, spam filters, DKIM/SPF enforcement |
| Analytics | View server-wide analytics and usage reports |
| Terminal | Full root terminal access via web browser |
| Hostname | Configure server hostname and nameservers |
| Updates | Update VoidPanel to the latest version |
| Backups | Create and download domain backups |
| Suspend/Unsuspend | Suspend or reactivate user accounts |
| Terminate | Completely remove a user account and all data |

### First-Time Setup Wizard

On first login, VoidPanel presents a **Quick Setup Wizard**:

1. **Step 1** — Set your server hostname (e.g., `panel.yourdomain.com`)
2. **Step 2** — Configure nameservers (e.g., `ns1.yourdomain.com`, `ns2.yourdomain.com`)
3. **Step 3** — Set admin email address
4. **Step 4** — SSL certificate is automatically provisioned for the panel

---

## 3. User Control Panel

Each user gets their own control panel at `/control/`. After logging in, users see their **domain dashboard** with:

- **Storage usage** — Visual bar showing used vs allocated space
- **Quick links** — File Manager, Email, Databases, DNS, SSL, etc.
- **Domain list** — All domains associated with the account

### What Users Can Do

| Feature | Description |
|---------|-------------|
| File Manager | Upload, edit, move, and manage website files |
| Email | Create email accounts and access webmail |
| Databases | Create MySQL databases and manage users |
| DNS | Edit DNS zone records for their domains |
| SSL | Provision free Let's Encrypt SSL certificates |
| Subdomains | Create and manage subdomains |
| PHP | Switch PHP versions per domain, edit php.ini |
| FTP | Create FTP accounts for file transfer |
| Python Apps | Deploy and manage Python applications |
| MERN Apps | Deploy and manage Node.js / MERN applications |
| Cron Jobs | Schedule automated tasks |
| Redirects | Set up URL redirects |
| Backups | Create and download website backups |
| Terminal | Web-based terminal (if shell access is enabled) |
| Analytics | Domain-specific traffic and usage stats |

---

## 4. Website & Domain Management

### Adding a Website (Admin)

1. Go to **Admin Dashboard → Add Website**
2. Enter:
   - **Domain name** (e.g., `example.com`)
   - **Username** — a Linux system user is created
   - **Email** — admin email for the domain
   - **Password** — account password
   - **Hosting Package** — select a quota package
3. Click **Create**

VoidPanel automatically:
- Creates the system user and home directory
- Sets up Nginx virtual host configuration
- Configures PHP-FPM pool for the domain
- Creates DNS zone with standard records
- Provisions SSL certificate via Let's Encrypt
- Generates DKIM keys for email authentication
- Applies storage quota from the selected package

### Adding an Addon Domain

Existing users can host additional domains:

1. Go to **Admin Dashboard → Add Website**
2. Select an **existing user** instead of creating new
3. Enter the new domain name
4. The domain shares the user's storage quota and system resources

### Website Directory Structure

Each domain gets its own directory:

```
/home/<username>/
├── public_html/          ← Website root (place files here)
├── logs/                 ← Access and error logs
├── ssl/                  ← SSL certificates
├── backups/              ← Backup archives
└── mail/                 ← Email data
```

### Domain Status

Domains can have these statuses:

| Status | Meaning |
|--------|---------|
| **Active** | Website is live and accessible |
| **Suspended** | Website returns a suspension page |
| **SSL Active** | SSL certificate is installed and valid |

### Suspending / Unsuspending

Admins can suspend a user's account which:
- Replaces the website with a "Suspended" page
- Blocks email sending
- Disables FTP access
- Keeps all data intact for later restoration

To unsuspend, click **Unsuspend** — everything is restored to normal.

### Terminating an Account

**Warning**: This permanently deletes:
- All website files
- Email data and accounts
- DNS zone
- DKIM keys
- SSL certificates
- FTP accounts
- Python/MERN app services
- System user account

---

## 5. Subdomain Management

### Creating a Subdomain

1. Navigate to your domain's management page
2. Click **Subdomains**
3. Enter the subdomain prefix (e.g., `blog` for `blog.example.com`)
4. Click **Create**

VoidPanel automatically:
- Creates the subdomain directory
- Adds Nginx configuration
- Creates DNS A record
- Assigns the same PHP version as the parent domain

### Subdomain Features

- **PHP Version** — Each subdomain can have its own PHP version
- **SSL** — Auto SSL works for subdomains too
- **Delete** — Removes the subdomain config and DNS record

### Subdomain Directory

```
/home/<username>/public_html/<subdomain>/
```

For example, `blog.example.com` would serve files from:
```
/home/<username>/public_html/blog.example.com/
```

---

## 6. SSL / HTTPS Certificates

VoidPanel uses **Let's Encrypt** for free, automatic SSL certificates.

### Auto SSL for One Domain

1. Go to your domain → **SSL Management**
2. Click **Run Auto SSL**
3. VoidPanel runs Certbot to obtain and install the certificate
4. Nginx is automatically configured for HTTPS

### Auto SSL for All Domains

Admins can provision SSL for **all hosted domains at once**:
1. Go to **Admin Dashboard → All SSL**
2. Click **Run SSL for All**
3. Each domain is processed sequentially

### SSL Status Indicators

| Indicator | Meaning |
|-----------|---------|
| ✅ Active | SSL certificate is installed and valid |
| ❌ Inactive | No SSL certificate or certificate expired |
| 🔄 Processing | SSL provisioning in progress |

### SSL Renewal

Let's Encrypt certificates auto-renew via a Certbot cron job that VoidPanel installs during setup.

### Self-Signed Certificates

If Let's Encrypt fails (e.g., DNS not pointed), VoidPanel generates a **self-signed certificate** as a fallback so HTTPS still works.

### Requirements for Auto SSL

- Domain's DNS **A record** must point to your server's IP
- Port 80 must be open (Let's Encrypt uses HTTP-01 challenge)
- Domain must be reachable from the internet

---

## 7. Email System

VoidPanel includes a **full email stack**:

| Component | Purpose |
|-----------|---------|
| **Postfix** | Outgoing email server (SMTP) |
| **Dovecot** | Incoming email server (IMAP/POP3/LMTP) |
| **OpenDKIM** | Email authentication (DKIM signing) |
| **Roundcube** | Webmail client (access email in browser) |

### Mail Storage

All email data is stored under the **domain owner's home directory**:

```
/home/<username>/mail/<domain>/<mailbox>/Maildir/
```

For example, if user `john` owns `example.com`, email for `info@example.com` is stored at:
```
/home/john/mail/example.com/info/Maildir/
```

**Delivery architecture:** Postfix hands incoming mail to Dovecot via **LMTP** (Local Mail Transfer Protocol). Dovecot looks up the per-account home path in `/etc/dovecot/users` and delivers mail directly to the correct Maildir. This ensures all mail lives under the user's home directory regardless of the system configuration.

### Creating an Email Account

1. Go to your domain → **Email**
2. Click **Add Email Account**
3. Enter:
   - Email address (e.g., `info@example.com`)
   - Password
4. Click **Create**

### Email Protocols & Ports

| Protocol | Port | Security | Purpose |
|----------|------|----------|---------|
| SMTP | 587 | STARTTLS | Sending email |
| SMTPS | 465 | SSL/TLS | Sending email (implicit TLS) |
| IMAP | 993 | SSL/TLS | Receiving email |
| POP3 | 995 | SSL/TLS | Receiving email |

### Roundcube Webmail

Access webmail directly from VoidPanel:
1. Go to **Email** → click **Webmail** next to any email account
2. VoidPanel automatically logs you into Roundcube via SSO (Single Sign-On)
3. No need to enter credentials — it's seamless

### Email Statistics

The email dashboard shows per-domain statistics:
- **Sent** — Total emails sent
- **Failed** — Delivery failures
- **Queued** — Emails waiting to send
- **Received** — Total emails received

### Email Configuration (Admin)

Admins can configure global email settings:

| Setting | Default | Description |
|---------|---------|-------------|
| Hourly sending limit | 100 | Max emails per hour per domain |
| Daily sending limit | 1,000 | Max emails per day per domain |
| Default mailbox quota | 1,024 MB | Storage per email account |
| Max attachment size | 50 MB | Maximum email attachment |
| Anti-spam (SpamAssassin) | Enabled | Spam filtering |
| Spam score threshold | 5.0 | Messages above this score are rejected |
| DKIM/SPF enforcement | Enabled | Require DKIM and SPF for authentication |
| Max SMTP connections | 20 | Concurrent sending connections |
| Catch-all aliases | Disabled | Forward all unmatched emails |
| Autoresponders | Enabled | Out-of-office auto-replies |

### DKIM / SPF / DMARC

VoidPanel automatically configures:
- **DKIM** — Signs outgoing emails (2048-bit key auto-generated per domain)
- **SPF** — DNS record authorizing your server to send email
- **DMARC** — Policy for handling failed authentication

These DNS records are created automatically when you add a domain.

### Changing Email Password

1. Go to **Email** → find the account
2. Click **Change Password**
3. Enter new password and confirm

### Deleting an Email Account

1. Go to **Email** → find the account
2. Click **Delete**
3. Confirm deletion — this removes the mailbox and all stored emails

---

## 8. DNS Management

VoidPanel runs **BIND9** as an authoritative DNS server, giving you full control over DNS zones.

### Accessing DNS Editor

1. Go to your domain → **DNS Zone Editor**
2. You'll see all existing DNS records

### Record Types Supported

| Type | Example | Purpose |
|------|---------|---------|
| **A** | `example.com → 1.2.3.4` | Points domain to IPv4 address |
| **AAAA** | `example.com → 2001:db8::1` | Points domain to IPv6 address |
| **CNAME** | `www → example.com` | Alias one name to another |
| **MX** | `example.com → mail.example.com` | Mail server for the domain |
| **TXT** | `v=spf1 ip4:1.2.3.4 ~all` | Text records (SPF, DKIM, verification) |
| **NS** | `example.com → ns1.example.com` | Name server delegation |
| **SRV** | `_sip._tcp → 1.2.3.4:5060` | Service location records |
| **CAA** | `example.com → letsencrypt.org` | Certificate authority authorization |

### Adding a DNS Record

1. Click **Add Record**
2. Select the record type
3. Enter the **Name**, **Value**, and **TTL**
4. Click **Save**

### Editing a DNS Record

1. Find the record in the list
2. Click **Edit**
3. Modify the values
4. Click **Save**

### Deleting a DNS Record

1. Find the record
2. Click **Delete**
3. Confirm

### Default Records

When you add a domain, VoidPanel creates these records automatically:

| Record | Value | Purpose |
|--------|-------|---------|
| `A` | Server IP | Points domain to your server |
| `A (www)` | Server IP | Points www subdomain |
| `MX` | mail.domain.com | Email routing |
| `NS` | ns1, ns2 | Nameserver delegation |
| `TXT (SPF)` | SPF record | Email authorization |
| `TXT (DKIM)` | DKIM public key | Email signing verification |

### Custom Nameservers

To use your own nameservers (e.g., `ns1.yourdomain.com`):
1. During setup, enter your custom nameserver hostnames
2. At your domain registrar, create **Glue Records** pointing NS hostnames to your server IP
3. Set the domain's nameservers to your custom NS hostnames

---

## 9. File Manager

The built-in File Manager lets you manage website files directly from the browser — no FTP client needed.

### Features

| Feature | Description |
|---------|-------------|
| **Browse** | Navigate directories with click navigation |
| **Upload** | Drag-and-drop or click to upload files (up to 50 MB) |
| **Download** | Download any file to your computer |
| **Edit** | Built-in code editor with syntax highlighting |
| **Create** | Create new files or folders |
| **Copy / Move** | Copy or move files between directories |
| **Rename** | Rename files and folders |
| **Compress** | Create ZIP archives |
| **Extract** | Extract ZIP files |
| **Permissions** | Change file permissions (chmod) |
| **Delete** | Soft-delete to Recycle Bin |
| **Recycle Bin** | Restore accidentally deleted files |

### Using the Code Editor

1. Click any text file to open it in the editor
2. The editor supports syntax highlighting for:
   - HTML, CSS, JavaScript
   - PHP, Python
   - JSON, XML, YAML
   - SQL, Markdown
   - Configuration files
3. Click **Save** to save changes

### Recycle Bin (Trash)

When you delete a file, it moves to the **Recycle Bin** instead of being permanently deleted.

- **View Trash** — See all deleted files with deletion date and original path
- **Restore** — Move a file back to its original location
- **Empty Trash** — Permanently delete all trashed files

### Storage Quota

Your file manager respects the storage quota assigned by your hosting package. If you exceed it:
- File uploads will be blocked
- A warning message appears showing usage vs limit

---

## 10. Database Management

VoidPanel supports **MySQL / MariaDB** databases.

### Creating a Database

1. Go to your domain → **Databases**
2. Click **Create Database**
3. Enter a database name
4. The database is created with the naming format: `username_dbname`

### Creating a Database User

1. In the Database section, click **Create User**
2. Enter a username and password
3. The user is created with format: `username_dbuser`

### Granting Permissions

1. Select a database and user
2. Choose permissions to grant:

| Permission | Description |
|-----------|-------------|
| SELECT | Read data from tables |
| INSERT | Add new rows |
| UPDATE | Modify existing rows |
| DELETE | Remove rows |
| CREATE | Create new tables |
| DROP | Delete tables |
| ALTER | Modify table structure |
| INDEX | Create/remove indexes |
| CREATE TEMPORARY TABLES | Create temp tables |
| LOCK TABLES | Lock tables for exclusive access |
| EXECUTE | Run stored procedures |
| CREATE VIEW | Create database views |
| SHOW VIEW | View the definition of views |
| CREATE ROUTINE | Create stored procedures |
| ALTER ROUTINE | Modify stored procedures |
| EVENT | Create scheduled events |
| TRIGGER | Create triggers |
| REFERENCES | Create foreign key references |
| ALL PRIVILEGES | Grant all permissions |

### phpMyAdmin

VoidPanel includes **phpMyAdmin** for visual database management:

1. Go to **Databases** → click **phpMyAdmin**
2. VoidPanel logs you in automatically via SSO
3. Full phpMyAdmin interface is available for:
   - Running SQL queries
   - Importing/exporting databases
   - Managing tables, views, and stored procedures
   - Visualizing table structures

### Changing Database User Password

1. Go to **Databases**
2. Find the user → click **Change Password**
3. Enter new password

### Deleting a Database

1. Go to **Databases**
2. Find the database → click **Delete**
3. Confirm — this permanently deletes the database and all its data

---

## 11. PHP Configuration

VoidPanel supports multiple PHP versions simultaneously, with per-domain version selection.

### Supported PHP Versions

- PHP 5.6
- PHP 7.0, 7.1, 7.2, 7.3, 7.4
- PHP 8.0, 8.1, 8.2, 8.3, 8.4

### Changing PHP Version

1. Go to your domain settings
2. Click **Change PHP Version**
3. Select the desired version from the dropdown
4. Click **Apply**

VoidPanel switches the PHP-FPM pool for that domain without affecting other domains.

### Editing php.ini

1. Go to your domain → **PHP INI Editor**
2. Edit the configuration directly
3. Click **Save**

Common settings you might change:

| Setting | Default | Description |
|---------|---------|-------------|
| `upload_max_filesize` | 50M | Maximum file upload size |
| `post_max_size` | 50M | Maximum POST data size |
| `max_execution_time` | 300 | Script timeout in seconds |
| `memory_limit` | 256M | Maximum memory per script |
| `display_errors` | Off | Show PHP errors (enable for debugging) |
| `max_input_vars` | 3000 | Maximum form input variables |

### Installing PHP Extensions (Admin)

Admins can install additional PHP extensions globally:

1. Go to **Admin → PHP Settings**
2. Select a PHP version
3. Choose extensions to install (e.g., `gd`, `mbstring`, `curl`, `xml`, `zip`)
4. Click **Install**

### Installing New PHP Versions (Admin)

1. Go to **Admin → PHP Settings**
2. Click **Install PHP Version**
3. Select the version to install
4. VoidPanel installs it from the official PHP PPA/Remi repository

---

## 12. FTP Accounts

VoidPanel uses **VSFTPD** for FTP file transfer.

### Creating an FTP Account

1. Go to your domain → **FTP Accounts**
2. Click **Add FTP Account**
3. Enter:
   - **Username** — FTP login name
   - **Password** — FTP password
   - **Storage Quota** — Maximum storage for this account
4. Click **Create**

### FTP Connection Details

| Setting | Value |
|---------|-------|
| **Host** | Your server IP or hostname |
| **Port** | 21 |
| **Protocol** | FTP with Explicit TLS (FTPES) |
| **Username** | As created |
| **Password** | As created |

### Changing FTP Password

1. Go to **FTP Accounts**
2. Find the account → **Change Password**
3. Enter new password

### Changing FTP Storage Quota

1. Go to **FTP Accounts**
2. Find the account → **Change Storage**
3. Enter new quota in MB

### Deleting FTP Account

1. Find the account → **Delete**
2. Confirm deletion

### FTP Server Settings (Admin)

Admins can configure:
- Enable/disable FTP server
- TLS certificate configuration
- Passive port range
- Maximum connections

---

## 13. Python Application Hosting

VoidPanel can host Python web applications (Flask, Django, FastAPI, etc.) with production-grade deployment.

### Creating a Python App

1. Go to your domain → **Python Apps**
2. Click **Create Python Application**
3. Enter:
   - **App Name** — identifier for the application
4. Click **Create**

VoidPanel automatically:
- Creates a Python virtual environment
- Sets up a Gunicorn-based systemd service
- Configures Nginx reverse proxy
- Assigns the app to the domain

### Managing Python Apps

| Action | Description |
|--------|-------------|
| **Start** | Start the application service |
| **Stop** | Stop the application service |
| **Restart** | Restart with new code changes |
| **Delete** | Remove the app, service, and configuration |

### Python App Directory Structure

```
/home/<username>/<app_name>/
├── venv/              ← Python virtual environment
├── app.py             ← Your application code
├── requirements.txt   ← Python dependencies
└── ...
```

### Deploying Your Code

1. Upload your Python files via **File Manager** or **FTP**
2. Install dependencies: use the **Terminal** to run `pip install -r requirements.txt`
3. Click **Restart** to apply changes

---

## 14. MERN / Node.js Application Hosting

VoidPanel supports Node.js applications with automatic port assignment and process management.

### Creating a MERN/Node App

1. Go to your domain → **MERN Apps**
2. Click **Create MERN Application**
3. Enter:
   - **App Name** — identifier for the application
4. Click **Create**

VoidPanel automatically:
- Assigns a unique port number
- Creates a systemd service for the Node.js process
- Configures Nginx reverse proxy to the assigned port

### Managing Node.js Apps

| Action | Description |
|--------|-------------|
| **Start** | Start the Node.js service |
| **Stop** | Stop the service |
| **Restart** | Restart with new code changes |
| **Delete** | Remove the app, service, and configuration |

### MERN App Directory Structure

```
/home/<username>/<app_name>/
├── package.json       ← Node.js dependencies
├── index.js           ← Entry point
├── node_modules/      ← Installed packages
└── ...
```

### Deploying Your Code

1. Upload your Node.js files via **File Manager** or **FTP**
2. Use **Terminal** to run `npm install`
3. Click **Restart** to apply changes

### Port Assignment

Each MERN app gets a unique port. VoidPanel manages this automatically — Nginx proxies requests from port 80/443 to the assigned port.

---

## 15. Cron Jobs

Schedule automated tasks to run at specific intervals.

### Creating a Cron Job

1. Go to your domain → **Cron Jobs**
2. Enter:
   - **Schedule** — Choose from presets or enter custom cron syntax
   - **Command** — The command to run
3. Click **Add**

### Cron Schedule Syntax

```
┌───────────── minute (0 - 59)
│ ┌───────────── hour (0 - 23)
│ │ ┌───────────── day of month (1 - 31)
│ │ │ ┌───────────── month (1 - 12)
│ │ │ │ ┌───────────── day of week (0 - 7, Sun=0 or 7)
│ │ │ │ │
* * * * *
```

### Common Schedules

| Schedule | Cron Expression | Description |
|----------|----------------|-------------|
| Every minute | `* * * * *` | Runs every 60 seconds |
| Every 5 minutes | `*/5 * * * *` | Runs every 5 minutes |
| Hourly | `0 * * * *` | Runs at the start of every hour |
| Daily at midnight | `0 0 * * *` | Runs once a day at 00:00 |
| Weekly (Sunday) | `0 0 * * 0` | Runs once a week |
| Monthly | `0 0 1 * *` | Runs on the 1st of every month |

### Examples

```bash
# Run a PHP script every hour
0 * * * * /usr/bin/php /home/user/public_html/cron.php

# Run a Python script daily
0 0 * * * /home/user/venv/bin/python /home/user/script.py

# Clear temp files weekly
0 0 * * 0 find /home/user/tmp -type f -mtime +7 -delete
```

### Server-Level Cron (Admin)

Admins can manage server-level cron jobs that run as root for system maintenance tasks.

### Deleting a Cron Job

Click the **Delete** button next to the cron job to remove it.

---

## 16. URL Redirects

Set up URL redirects to forward traffic from one path to another.

### Adding a Redirect

1. Go to your domain → **Redirects**
2. Enter:
   - **Source path** — The URL path to redirect from
   - **Destination** — Where to redirect to
3. Click **Add Redirect**

### How Redirects Work

VoidPanel creates **301 (permanent) redirects** in the Nginx configuration. For example:

| Source | Destination | Result |
|--------|------------|--------|
| `/old-page` | `/new-page` | `example.com/old-page → example.com/new-page` |
| `/blog` | `https://blog.example.com` | `example.com/blog → blog.example.com` |

### Protected Paths

Some paths cannot be redirected as they're used by VoidPanel services:
- `/phpmyadmin` — phpMyAdmin access
- `/static` — Static files
- `/roundcube` — Webmail

### Deleting a Redirect

Click **Delete** next to the redirect rule to remove it.

---

## 17. Backup & Restore

### Creating a Backup

1. Go to your domain → **Backups**
2. Click **Create Backup**
3. VoidPanel creates a ZIP archive containing:
   - All website files (`public_html/`)
   - Email data
   - DKIM keys
   - SSL certificates
   - Nginx configuration

### Downloading a Backup

1. Go to **Backups**
2. Click **Download** next to the backup file
3. The ZIP file downloads to your computer

### Backup Processing

Backups are created in the background — large websites may take several minutes. You'll see the progress indicator, and the backup appears once complete.

### Best Practices

- Create regular backups before making major changes
- Download backups to your local computer or external storage
- Test restoring from backups periodically

---

## 18. Web Terminal

VoidPanel includes a **browser-based terminal** for command-line access.

### Admin Terminal

- Full root access to the server
- Available from **Admin Dashboard → Terminal**
- Can execute any server command

### User Terminal

- Available from **User Control Panel → Terminal**
- Shell access must be enabled by the admin for the user
- Runs in the context of the user's home directory
- Limited to user-level permissions

### Terminal Features

- Full interactive terminal with tab completion
- Supports window resizing
- Color output support
- Works with vim, nano, and other terminal programs

---

## 19. Firewall (CSF)

VoidPanel integrates **ConfigServer Firewall (CSF)** for server protection.

### IP Management (Admin)

| Action | Description |
|--------|-------------|
| **Allow IP** | Whitelist an IP address in csf.allow |
| **Deny IP** | Permanently block an IP in csf.deny |
| **Block IP** | Temporarily block an IP |
| **Unblock IP** | Remove a temporary block |
| **Ignore IP** | Exclude IP from brute-force detection |

### Brute-Force Protection

VoidPanel monitors failed login attempts and automatically:
- Blocks IPs after consecutive failed logins
- Logs all login activity (IP address, time, success/failed)
- Provides brute-force configuration controls

### Default Open Ports

VoidPanel configures these ports during installation:

| Port | Service |
|------|---------|
| 22 | SSH |
| 53 | DNS (TCP/UDP) |
| 80 | HTTP |
| 443 | HTTPS |
| 587 | SMTP (mail sending) |
| 465 | SMTPS |
| 993 | IMAPS |
| 995 | POP3S |
| 8080 | phpMyAdmin |
| 8082 | VoidPanel Admin |
| 8092 | VoidPanel User |
| 9002 | Roundcube Webmail |

---

## 20. Server Status & Monitoring

### Real-Time Monitoring

The Server Status page shows:

| Metric | Description |
|--------|-------------|
| **CPU Usage** | Current CPU load percentage |
| **RAM Usage** | Memory used vs available |
| **Disk Usage** | Storage used vs total |
| **Uptime** | How long the server has been running |

Data updates in real-time via AJAX polling.

### Service Management (Admin)

Admins can manage core services directly:

| Service | Actions Available |
|---------|------------------|
| **Nginx** | Start, Stop, Restart |
| **Named (BIND9)** | Start, Stop, Restart |
| **Postfix** | Start, Stop, Restart |
| **Dovecot** | Start, Stop, Restart |
| **VSFTPD** | Start, Stop, Restart |
| **OpenDKIM** | Start, Stop, Restart |

### Server Power (Admin)

| Action | Description |
|--------|-------------|
| **Reboot** | Restart the entire server |
| **Shutdown** | Power off the server |

**Use with caution** — these affect all hosted websites.

---

## 21. User & Package Management

### Hosting Packages

Packages define resource limits for user accounts.

#### Creating a Package (Admin)

1. Go to **Admin → Packages**
2. Fill in:

| Field | Description |
|-------|-------------|
| **Name** | Package name (e.g., "Starter", "Business") |
| **Storage** | Disk quota in GB |
| **FTP Accounts** | Maximum FTP accounts allowed |
| **Subdomains** | Maximum subdomains allowed |
| **Bandwidth** | Monthly bandwidth in GB |
| **Email Accounts** | Maximum email accounts |
| **Databases** | Maximum databases allowed |

3. Click **Create Package**

### User Management

#### Creating a User (Admin)

1. Go to **Admin → Add User**
2. Enter user details:
   - Username (becomes Linux system user)
   - Email address
   - Domain name
   - Password
   - Hosting package
3. Click **Create**

#### Changing User Password

1. Go to **Admin → Users**
2. Find the user → **Change Password**

#### Changing User Package

1. Go to **Admin → Users**
2. Find the user → **Change Package**
3. Select new package — quotas update immediately

#### Shell Access

Admins can enable or disable terminal/shell access per user. When disabled, the user won't see the Terminal option in their control panel.

---

## 22. AI Help Assistant

VoidPanel includes a built-in **AI Help Assistant** that answers questions about using the panel.

### How to Access

1. Click the **AI Chat** icon from any page, or navigate to `/ai/`
2. Type your question in natural language
3. Get instant help with step-by-step instructions

### What It Can Help With

The assistant has a knowledge base covering **all VoidPanel features**:

- Installation and setup
- Domain and website management
- SSL certificates
- Email configuration
- DNS record management
- File manager usage
- Database creation and management
- PHP version switching
- FTP account setup
- Python and Node.js app deployment
- Cron job scheduling
- URL redirects
- Backup and restore
- Terminal usage
- Firewall configuration
- Package and user management
- Hostname setup
- Troubleshooting common issues

### Example Questions

> "How do I add an SSL certificate to my domain?"

> "How to create a MySQL database?"

> "Why am I getting a 502 Bad Gateway error?"

> "How do I change PHP version for my website?"

> "How to set up email for my domain?"

### Chat Sessions

- Conversations are saved and you can revisit previous chats
- Each chat has a session name for easy reference
- You can provide feedback (positive/negative) to help improve responses

---

## 23. WHMCS / Billing API

VoidPanel includes a **REST API** for integration with billing systems like WHMCS.

### Available API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/auth/` | POST | Authenticate and get session token |
| `/api/create-account/` | POST | Create a new hosting account |
| `/api/list-packages/` | POST | List available hosting packages |
| `/api/suspend-account/` | POST | Suspend a hosting account |
| `/api/unsuspend-account/` | POST | Unsuspend a hosting account |
| `/api/terminate-account/` | POST | Permanently delete an account |

### Authentication

All API requests require authentication:

1. Send credentials to `/api/auth/`
2. Receive a session token
3. Include the token in subsequent requests

### Create Account Example

**Request:**
```json
{
  "username": "johndoe",
  "domain": "example.com",
  "email": "john@example.com",
  "password": "securepassword",
  "package": "Starter"
}
```

**Response:**
```json
{
  "status": "success",
  "message": "Account created successfully"
}
```

### Integration with WHMCS

VoidPanel can be used as a hosting backend for WHMCS:
1. Install the VoidPanel WHMCS module
2. Configure API credentials in WHMCS
3. WHMCS automatically provisions/suspends/terminates accounts

---

## 24. Installation Guide

### Supported Operating Systems

| OS | Version | Status |
|----|---------|--------|
| Ubuntu | 22.04 LTS, 24.04 LTS | ✅ Fully Supported |
| AlmaLinux | 8.x, 9.x | ✅ Fully Supported |
| Rocky Linux | 8.x, 9.x | ✅ Fully Supported |
| RHEL | 8.x, 9.x | ✅ Fully Supported |
| CentOS | 8.x, 9.x | ✅ Fully Supported |
| Windows Server | 2019, 2022 (via WSL2) | ✅ Supported |

### System Requirements

| Resource | Minimum | Recommended |
|----------|---------|-------------|
| RAM | 2 GB | 4 GB+ |
| CPU | 1 core | 2+ cores |
| Storage | 20 GB | 50 GB+ |
| IP | Static IPv4 | Static IPv4 |
| OS | Fresh installation | Fresh installation |

### Installation Steps

#### Linux (Ubuntu / AlmaLinux / Rocky / RHEL / CentOS)

1. **Start with a fresh OS installation** (no existing web server)

2. **Run the installer**:
   ```bash
   wget -O install.sh https://voidpanel.com/install.sh && sudo bash install.sh
   ```

3. **Wait for installation** — this installs all components:
   - Nginx (web server)
   - PHP (multiple versions)
   - MySQL / MariaDB (database)
   - Postfix & Dovecot (email)
   - BIND9 / Named (DNS)
   - Certbot (SSL)
   - VSFTPD (FTP)
   - CSF (firewall)
   - OpenDKIM (email authentication)
   - phpMyAdmin (database GUI)
   - Roundcube (webmail)
   - VoidPanel application

4. **Access VoidPanel** — after installation completes, you'll see:
   - Admin panel URL
   - Login credentials
   - Important port information

#### Windows Server (WSL2)

1. Open PowerShell as Administrator
2. Run the Windows installer script
3. This sets up WSL2 with Ubuntu and installs VoidPanel inside it
4. Access VoidPanel at `https://your-server-ip:8082`

### What the Installer Does

The installer automatically:

1. Updates the system packages
2. Installs all required software
3. Configures Nginx with multiple virtual hosts
4. Sets up PHP-FPM with multiple versions
5. Installs and secures MySQL/MariaDB
6. Configures Postfix and Dovecot for email
7. Sets up BIND9 for DNS
8. Installs and configures CSF firewall
9. Sets up Let's Encrypt (Certbot)
10. Installs phpMyAdmin and Roundcube
11. Deploys the VoidPanel Django application
12. Creates the admin superuser account
13. Configures systemd services for auto-start
14. Opens necessary firewall ports

### Auto-Detection

The installer automatically detects your Linux distribution:
- **Ubuntu** → Uses `apt` package manager, PPA repositories
- **AlmaLinux/Rocky/RHEL/CentOS** → Uses `dnf` package manager, EPEL + Remi repositories

---

## 25. Access Ports & URLs

After installation, VoidPanel services are available at:

| Service | URL | Port |
|---------|-----|------|
| **Admin Dashboard** | `https://your-ip:8082` | 8082 |
| **User Control Panel** | `https://your-ip:8092` | 8092 |
| **phpMyAdmin** | `https://your-ip:8080` | 8080 |
| **Roundcube Webmail** | `https://your-ip:9002` | 9002 |

### Hosted Websites

Websites hosted on VoidPanel are accessible via:
- `http://domain.com` (port 80)
- `https://domain.com` (port 443, after SSL is provisioned)

---

## 26. Updating VoidPanel

### From the Admin Dashboard

1. Go to **Admin Dashboard → Update**
2. Click **Update Panel**
3. VoidPanel downloads and applies the latest version
4. Services are automatically restarted

### Important Notes

- Always **create a backup** before updating
- Updates preserve your data and configuration
- The update process takes a few minutes
- Your websites stay online during the update

---

## 27. Troubleshooting

### Common Issues and Solutions

#### Website shows "502 Bad Gateway"

**Cause**: PHP-FPM pool for the domain is not running.

**Solution**:
1. Go to **Server Status**
2. Restart the PHP-FPM service
3. If the issue persists, check PHP error logs in the domain's `logs/` directory

#### SSL Certificate Not Working

**Cause**: DNS not pointing to your server, or port 80 is blocked.

**Solution**:
1. Verify your domain's A record points to your server IP
2. Check that port 80 is open in the firewall
3. Try running Auto SSL again
4. Check Certbot logs for specific errors

#### Email Not Sending

**Cause**: Various possible causes.

**Solution**:
1. Verify Postfix is running (Server Status page)
2. Check that port 587/465 is open
3. Verify SPF and DKIM DNS records exist
4. Check if your IP is blacklisted (use mxtoolbox.com)
5. Review mail queue for stuck messages

#### Email Not Receiving

**Cause**: MX record misconfiguration.

**Solution**:
1. Verify your domain's MX record points to `mail.<yourdomain>`
2. Ensure Dovecot is running
3. Check that ports 993/995 are open
4. Verify the email account exists in VoidPanel

#### Database Connection Refused

**Cause**: MySQL/MariaDB service is down or credentials are wrong.

**Solution**:
1. Verify MySQL is running (Server Status page)
2. Double-check database name, username, and password
3. Ensure the database user has proper permissions granted

#### Cannot Access VoidPanel Dashboard

**Cause**: uWSGI/Daphne service is not running.

**Solution**:
1. SSH into the server
2. Check if the panel service is running:
   ```bash
   systemctl status uwsgi
   ```
3. Restart if needed:
   ```bash
   systemctl restart uwsgi
   ```

#### FTP Connection Failed

**Cause**: VSFTPD not running or firewall blocking.

**Solution**:
1. Verify VSFTPD is running
2. Check that port 21 is open
3. Ensure passive ports are open (if using passive mode)
4. Use "FTP with Explicit TLS" mode in your FTP client

#### Python/MERN App Not Working

**Cause**: Application service not running.

**Solution**:
1. Go to the app management page
2. Click **Restart**
3. Check application logs for errors
4. Ensure all dependencies are installed

#### Panel Shows "Server Error (500)"

**Cause**: Application error in VoidPanel itself.

**Solution**:
1. Check the panel error log
2. Ensure all VoidPanel dependencies are installed
3. Verify database connectivity
4. Try restarting the panel service

---

## 28. Project Structure

VoidPanel follows a **Django project structure** with clear separation of concerns:

```
voidpanel/
│
├── panel/                    ← Core Django project settings
│   ├── settings.py           ← Server configuration
│   ├── urls.py               ← URL routing (120+ routes)
│   ├── views.py              ← Admin dashboard views
│   ├── celery.py             ← Background task configuration
│   └── asgi.py / wsgi.py     ← Server gateway interfaces
│
├── control/                  ← User control panel app
│   ├── views.py              ← User portal views
│   ├── models.py             ← Database models (users, domains, email, etc.)
│   ├── tasks.py              ← Celery background tasks (provisioning, SSL, etc.)
│   ├── consumers.py          ← WebSocket terminal consumer
│   ├── urls.py               ← User route definitions
│   └── migrations/           ← Database schema migrations
│
├── chatting/                 ← AI Help Assistant app
│   ├── views.py              ← Chat interface views
│   ├── models.py             ← Chat message storage
│   ├── knowledge.py          ← Help knowledge base (30+ topics)
│   └── urls.py               ← Chat route definitions
│
├── voidplatform/             ← Cross-platform abstraction layer
│   ├── base.py               ← Abstract interfaces for all services
│   ├── config.py             ← Platform-specific file paths
│   ├── detector.py           ← OS detection (Linux/Windows/WSL2/macOS)
│   ├── linux/                ← Linux implementations
│   │   ├── services.py       ← systemctl service management
│   │   ├── users.py          ← Linux user management
│   │   ├── web.py            ← Nginx configuration
│   │   ├── dns.py            ← BIND9 zone management
│   │   ├── mail.py           ← Postfix/Dovecot setup
│   │   ├── ftp.py            ← VSFTPD management
│   │   ├── firewall.py       ← CSF firewall
│   │   ├── ssl.py            ← Certbot/OpenSSL
│   │   ├── php.py            ← PHP version management
│   │   ├── terminal.py       ← PTY terminal spawning
│   │   └── cron.py           ← Crontab management
│   └── windows/              ← Windows implementations
│       ├── services.py       ← Windows service management
│       ├── users.py          ← Net user management
│       ├── web.py            ← IIS/Nginx configuration
│       ├── dns.py            ← Windows DNS
│       ├── mail.py           ← hMailServer
│       ├── ftp.py            ← FileZilla Server
│       ├── firewall.py       ← Windows Firewall
│       ├── ssl.py            ← Certificate management
│       ├── php.py            ← PHP CGI setup
│       ├── terminal.py       ← CMD/PowerShell
│       └── cron.py           ← Task Scheduler
│
├── templates/                ← HTML templates
│   ├── panel/                ← Admin dashboard templates (48 files)
│   ├── control/              ← User panel templates (25 files)
│   ├── chatting/             ← Chat interface templates (4 files)
│   └── login/                ← Login page templates
│
├── static/                   ← Static assets
│   ├── assets/               ← JavaScript, CSS bundles
│   │   ├── css/              ← Stylesheets
│   │   ├── vendor/           ← Third-party libraries
│   │   └── bundles/          ← Compiled JS/CSS bundles
│   ├── icons/                ← Feature icons (50+ images)
│   └── login/                ← Login page assets
│
├── function.py               ← Shared utility functions
├── manage.py                 ← Django management entry point
├── requirements.txt          ← Python dependencies
├── install.sh                ← Main installer (auto-detects OS)
├── ubuntu.sh                 ← Ubuntu-specific installer
├── almalinux.sh              ← AlmaLinux/RHEL installer
└── db.sqlite3                ← SQLite database (default)
```

### Technology Stack

| Layer | Technology |
|-------|-----------|
| **Backend Framework** | Django 5.x (Python) |
| **Task Queue** | Celery with Redis |
| **WebSockets** | Django Channels + Daphne (ASGI) |
| **Database** | SQLite (default) / MySQL (production) |
| **Web Server** | Nginx |
| **App Server** | uWSGI / Daphne |
| **Frontend** | HTML/CSS/JS, Font Awesome 6, AJAX |
| **Design** | Glassmorphism UI |

### Background Task Processing

VoidPanel uses **Celery** for long-running operations:
- Account provisioning (user creation, nginx config, SSL, DKIM)
- Account termination (cleanup all resources)
- Addon domain creation
- Hostname updates with SSL
- Domain conversion

These tasks run asynchronously so the web interface stays responsive.

### WebSocket Terminal

The web terminal uses **Django Channels** with a WebSocket consumer that:
- Spawns a pseudo-terminal (PTY) for the user
- Provides real-time bidirectional communication
- Supports terminal resize events
- Enforces permission checks (admin vs regular user)

---

## 29. FAQ

### General

**Q: Is VoidPanel free?**  
A: Yes, VoidPanel is open-source and free to use.

**Q: Can I use VoidPanel for commercial hosting?**  
A: Yes, VoidPanel is suitable for shared hosting businesses and supports WHMCS integration for automated billing.

**Q: What makes VoidPanel different from cPanel?**  
A: VoidPanel is free, supports Python/Node.js app hosting natively, has a modern glassmorphism UI, and works on both Linux and Windows Server.

### Technical

**Q: Can I host multiple domains on one server?**  
A: Yes, VoidPanel supports unlimited domains per server. Each domain gets its own isolated directory, PHP version, and resource allocation.

**Q: Does VoidPanel support IPv6?**  
A: Yes, you can create AAAA DNS records and Nginx supports IPv6 connections.

**Q: Can users have different PHP versions?**  
A: Yes, each domain (and subdomain) can run a different PHP version independently.

**Q: Is email hosting included?**  
A: Yes, full email stack is included — SMTP, IMAP, POP3, webmail, DKIM/SPF, and spam filtering.

**Q: How do I migrate from cPanel?**  
A: Create the domain and user in VoidPanel, then transfer files via FTP/SCP, import databases via phpMyAdmin, and recreate email accounts.

### Security

**Q: Is HTTPS enabled by default?**  
A: VoidPanel provisions Let's Encrypt SSL certificates automatically. The panel itself uses HTTPS.

**Q: How are passwords stored?**  
A: User passwords are hashed using Django's PBKDF2 algorithm. Email and FTP passwords are stored securely for authentication.

**Q: Is there brute-force protection?**  
A: Yes, CSF firewall monitors and blocks IPs after repeated failed login attempts.

### Maintenance

**Q: How do I back up the entire server?**  
A: Use the domain backup feature for individual websites. For full server backup, use your hosting provider's snapshot feature.

**Q: How often should I update VoidPanel?**  
A: Check for updates regularly from the Admin Dashboard. Always back up before updating.

**Q: Can I customize the panel's appearance?**  
A: The templates are in the `templates/` directory and can be customized. CSS is in `static/assets/css/`.

---

## Support

For help and support:
- Use the built-in **AI Help Assistant** — type your question in the chat
- Check the [Troubleshooting](#27-troubleshooting) section
- Review the [FAQ](#29-faq)

---

*VoidPanel Documentation — Complete Reference Guide*
