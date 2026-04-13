# 🚀 Void Panel - India's First Web Hosting Control Panel

> **India's first Web Hosting control panel developed from scratch** with AI integration, advanced security, and a futuristic user interface.

---

## 📋 About Void Panel

Void Panel is a **next-generation AI-based web hosting control panel** designed for seamless and efficient management of websites and servers. Built with a focus on UI/UX excellence and futuristic design, it simplifies complex hosting tasks and is **completely free for all users**.

### Why Void Panel?

✨ **AI Enhanced** - Intelligent recommendations and automation
🎨 **Simple & Attractive UI** - Intuitive interface for all skill levels
⚡ **Faster Response Time** - Optimized performance
📦 **Multiple Application Support** - Deploy various applications easily
🔒 **Advanced Security** - Enterprise-grade security features
🇮🇳 **Made in India** - India's first web hosting control panel developed from scratch

---

## 🌟 Key Features

### 🎯 Core Management
- **Domain Management** - Easy domain registration and management
- **Website Management** - Create, edit, and manage multiple websites
- **Database Setup** - Simple database creation and configuration
- **File Manager** - Secure file management with intuitive interface
- **Email Management** - Full email account management

### 🔐 Security Features
- **Automated SSL Integration** - Free SSL certificate management
- **Multi-Factor Authentication** - Enhanced account security
- **Advanced Firewall** - Built-in firewall settings
- **File Encryption** - Secure file storage protocols
- **Security Analytics** - Real-time security monitoring

### 🤖 AI-Powered Features
- **VoidPanel Assistant** - AI chatbot for instant support
- **Intelligent Recommendations** - AI-driven optimization suggestions
- **Predictive Analytics** - Forecast server performance
- **Automated Optimization** - AI-based system tuning
- **Smart Resource Management** - Dynamic resource allocation

### 🚀 Performance
- **Server Optimization** - Automatic performance tuning
- **Backup Scheduling** - Automated backup system
- **Cron Job Management** - Schedule automated tasks
- **Real-time Analytics** - Monitor website performance
- **Load Balancing** - Distribute traffic efficiently

### 📱 Developer Friendly
- **Multiple Language Support** - Python, Node.js, PHP, and more
- **Git Integration** - Deploy from Git repositories
- **API Access** - RESTful API for automation
- **CLI Tools** - Command-line interface support
- **Extensible Architecture** - Plugin support for custom functionality

---

## 📥 Installation

VoidPanel runs on **Linux (Ubuntu 22.04+)** and **Windows 10/11 (via WSL2)**.
Choose the guide for your operating system below.

---

### 🐧 Linux Installation (Ubuntu 22.04+)

#### Prerequisites
- **Operating System:** Ubuntu 22.04 or higher
- **Internet Connection:** Required for package downloads
- **Disk Space:** Minimum 10GB free space
- **RAM:** Minimum 2GB (4GB recommended)
- **User Permissions:** Root / sudo access required

#### Quick Installation

##### Method 1: One-line installer
```bash
curl -fsSL https://voidpanel.com/op/install.sh | bash
```

##### Method 2: With sudo
```bash
sudo su
curl -fsSL https://voidpanel.com/op/install.sh | bash
```

##### Method 3: Manual
```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y curl wget gnupg2 git python3 python3-pip
git clone https://github.com/rohankumarrawat/voidpanel.git
cd voidpanel
pip3 install -r requirements.txt
bash install.sh
```

---

### 🪟 Windows Installation (WSL2 — Windows 10/11)

VoidPanel on Windows runs inside **WSL2 (Windows Subsystem for Linux)** with
Ubuntu 22.04. All services — nginx, postfix, dovecot, bind9, vsftpd, php-fpm,
mysql — run inside the Linux subsystem, giving you **100% feature parity** with
a native Linux installation. No services are emulated or missing.

#### Windows Prerequisites
| Requirement | Minimum |
|-------------|---------|
| Windows version | Windows 10 **Build 19041** (May 2020 Update) or Windows 11 |
| Virtualization | Hyper-V / SVM enabled in BIOS (check: Task Manager → Performance → CPU → Virtualization: Enabled) |
| RAM | 4 GB (2 GB minimum, 4 GB strongly recommended for WSL2) |
| Disk space | 15 GB free |
| Internet | Required (downloads ~2 GB) |

#### Windows Quick Installation

1. **Clone or download** this repository to your Windows machine.
2. **Double-click `install.bat`** — it automatically requests Administrator rights.
3. The installer will:
   - Enable WSL2 and the Virtual Machine Platform Windows feature
   - Install Ubuntu 22.04 inside WSL2 with systemd enabled
   - Run the full VoidPanel Linux installation inside Ubuntu (~15–30 min)
   - Set up Windows port forwarding for all panel ports
   - Register a startup task to keep port forwarding correct after reboots
4. If a **reboot is required** after enabling WSL2 (Step 3), reboot your PC and
   run `install.bat` again — it resumes safely from where it left off.
5. Find your credentials in **`VoidPanel-Access.txt`** on your Desktop.
6. Open your browser and go to **`http://localhost:8080`**.

#### How It Works (Architecture)

```
  Windows Host
  ┌──────────────────────────────────────────────────────────┐
  │  Browser → localhost:8080                                │
  │       ↓                                                  │
  │  netsh portproxy  (TCP port forwarding)                  │
  │       ↓                                                  │
  │  WSL2 Virtual Network Adapter  (172.x.x.x, new each boot)│
  │       ↓                                                  │
  │  ┌───────────────────────────────────────────────────┐   │
  │  │  Ubuntu 22.04  (systemd enabled)                  │   │
  │  │  ┌──────────┐ ┌──────────┐ ┌───────────────────┐ │   │
  │  │  │  nginx   │ │  mysql   │ │  postfix/dovecot  │ │   │
  │  │  │  uWSGI   │ │  redis   │ │  bind9 / vsftpd   │ │   │
  │  │  │  php-fpm │ │  celery  │ │  opendkim / csf   │ │   │
  │  │  └──────────┘ └──────────┘ └───────────────────┘ │   │
  │  └───────────────────────────────────────────────────┘   │
  └──────────────────────────────────────────────────────────┘
```

- **Port forwarding** is maintained automatically. A Task Scheduler job
  (`VoidPanel WSL2 Port Forward`) runs at every Windows startup to refresh the
  `netsh portproxy` rules because WSL2's internal IP changes on each reboot.
- **Systemd** is enabled in WSL2 so all services start automatically when WSL2
  wakes up — no manual `service start` commands needed.

#### Opening a Shell in Your VoidPanel Environment
```powershell
wsl -d Ubuntu-22.04
```
This gives you a root shell inside the Ubuntu instance where VoidPanel runs —
identical to SSHing into a Linux server.

#### Manual Port Forwarding Refresh
If the panel becomes unreachable after a reboot, open **Administrator PowerShell** and run:
```powershell
powershell -ExecutionPolicy Bypass -File "C:\ProgramData\VoidPanel\windows-startup.ps1"
```
Port forwarding log: `C:\ProgramData\VoidPanel\startup.log`

#### Windows Limitations

| Feature | Status | Notes |
|---------|--------|-------|
| Web panel (8080 / 8082) | ✅ Full support | |
| phpMyAdmin (8090 / 8092) | ✅ Full support | |
| Roundcube webmail (9000 / 9002) | ✅ Full support | |
| Email SMTP / IMAP / POP3 | ✅ Full support | TCP portproxy |
| DNS TCP (port 53) | ✅ Full support | TCP portproxy |
| Web terminal (SSH-in-browser) | ✅ Full support | Requires WSL2 |
| FTP active mode (port 21/22) | ✅ Full support | |
| SSL / Let's Encrypt | ✅ Full support | Needs public IP + domain |
| **DNS UDP (port 53)** | ⚠️ Use WSL2 IP | `netsh portproxy` is TCP-only |
| **FTP passive (40000–50000)** | ⚠️ Use WSL2 IP | Too many ports for portproxy |

For DNS UDP and FTP passive, point clients directly at the WSL2 IP (shown in
`VoidPanel-Access.txt` — it also changes on reboot, so use a DNS hostname).

#### Developer Note (Native Windows, No WSL2)

If you are contributing to VoidPanel UI code on a Windows machine without WSL2,
you can run just the Django frontend using Daphne (no `uWSGI` required):

```bash
pip install django channels daphne djangorestframework psutil pexpect requests
python manage.py migrate
daphne -b 0.0.0.0 -p 8080 panel.asgi:application
```

Service management features (nginx config, email, DNS, etc.) will return errors
without a Linux environment — this mode is for UI-only development only.

---

## 🔧 Getting Started

### First Login
1. Open your browser and navigate to your server's IP address or domain
2. Default credentials are provided in the installation output
3. Change your password immediately (Documentations → Change Password)

### First Steps
1. **Change Password** - Update your admin password
2. **Add Website** - Create your first website
3. **Configure SSL** - Enable HTTPS with free SSL
4. **Setup Email** - Create email accounts
5. **Database Setup** - Create and manage databases

### Documentation Links
- **Overview** - https://voidpanel.com/overview
- **Change Password** - https://voidpanel.com/chpass
- **Add Website** - https://voidpanel.com/addweb
- **Add SSL Certificate** - https://voidpanel.com/addssl
- **Database Management** - https://voidpanel.com/db
- **Add Email Accounts** - https://voidpanel.com/addemail

---

## 📚 Full Documentation

Complete documentation is available at https://voidpanel.com/docs

### Topics Covered
- Installation and setup
- Server configuration
- Website management
- Email setup
- Database administration
- SSL certificates
- Backup and restore
- Security best practices
- Troubleshooting guide

---

## 🛠️ Technology Stack

### Backend
- **Framework:** Django (Python)
- **Language:** Python 3.8+
- **Database:** SQLite / MySQL / PostgreSQL
- **Web Server:** Nginx / Apache

### Frontend
- **Framework:** React / Vue.js
- **CSS:** Tailwind CSS
- **UI Components:** Modern, responsive design

### Additional Technologies
- **AI Integration:** Google Gemini API
- **Task Queue:** Celery
- **Real-time Updates:** WebSockets
- **API:** RESTful API

---

## 📖 Project Structure

```
voidpanel/
├── panel/                  # Django project settings
├── control/                # Control panel app
├── chatting/               # AI chat application
├── templates/              # HTML templates
├── static/                 # CSS, JS, images
├── manage.py               # Django management script
├── db.sqlite3              # Database (SQLite)
├── install.sh              # Linux installation script
├── install.bat             # Windows installer launcher (double-click)
├── install-windows.ps1     # Windows/WSL2 full installer (PowerShell)
├── windows-startup.ps1     # WSL2 port-forwarding refresh (runs at boot)
├── ubuntu.sh               # Linux service provisioning script
└── README.md               # This file
```

---

## 🚀 Deployment

### Single Server Setup
Perfect for small to medium websites

### Multi-Server Setup
Available for enterprise deployments with:
- Load balancer
- Multiple application servers
- Separate database server
- Dedicated storage

### Cloud Deployment
- AWS EC2 - AWS-optimized setup
- DigitalOcean Droplets - One-click deployment
- Linode - Pre-configured images
- Azure - Enterprise deployment
- Google Cloud - High-performance setup

---

## 🔐 Security

Void Panel implements enterprise-grade security:

- SSL/TLS Encryption - All traffic encrypted
- Database Security - Prepared statements prevent SQL injection
- File Permissions - Strict access control
- Input Validation - All user inputs validated
- CSRF Protection - Cross-Site Request Forgery prevention
- XSS Prevention - Cross-Site Scripting protection
- Rate Limiting - DDoS attack mitigation
- Regular Updates - Security patches released regularly

---

## 🤝 Contributing

We welcome contributions from the community!

### How to Contribute
1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Open a Pull Request

---

## 🐛 Bug Reports & Support

### Get Support
- Documentation - https://voidpanel.com/docs
- Blog Articles - https://voidpanel.com/blogs
- AI Assistant - https://voidpanel.com/ai/

---

## 📝 Changelog

### Version 1.0.0 (Current)
- Initial release
- Core hosting panel features
- AI integration
- Advanced security features
- Real-time analytics
- High-performance infrastructure

---

## 📄 License

Void Panel is completely free and open-source for everyone.

---

## 👨‍💻 Developer

**Rohan Kumar Rawat**

- GitHub: https://github.com/rohankumarrawat
- Website: https://voidpanel.com
- LinkedIn: https://www.linkedin.com/in/rohankumarrawat/
- YouTube: https://www.youtube.com/@voidpanel
- Twitter: https://x.com/rohankumarrawat/

---

## 🌐 Links

- Official Website - https://voidpanel.com
- Documentation - https://voidpanel.com/docs
- GitHub Repository - https://github.com/rohankumarrawat/voidpanel
- Blog - https://voidpanel.com/blogs
- AI Assistant - https://voidpanel.com/ai/

---

## ⭐ Show Your Support

If you find Void Panel helpful, please:
- Star this repository
- Share with your friends
- Leave feedback and suggestions
- Report bugs to help us improve

---

Made with ❤️ in India

© 2024 Void Panel. All rights reserved.

India's First Web Hosting Control Panel Developed From Scratch
