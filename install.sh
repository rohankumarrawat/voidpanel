#!/bin/bash
# =============================================================================
#  VoidPanel Universal Installer
#  Auto-detects the operating environment and routes to the correct path:
#
#    Ubuntu 22.04+ Linux       → full hosting control panel installation
#    AlmaLinux / Rocky / RHEL  → full installation (dnf-based)
#    WSL2 (Windows+Ubuntu)     → full installation + Windows port forwarding setup
#    macOS / Windows-shell     → informative error with correct instructions
#
#  Usage:
#    Linux  :  sudo bash install.sh
#    WSL2   :  sudo bash install.sh (inside Ubuntu-22.04 terminal)
#    Windows:  double-click install.bat (uses this script internally)
# =============================================================================

set -euo pipefail

# ── Colour helpers ─────────────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
RESET='\033[0m'

step() { echo -e "${CYAN}[+] $*${RESET}"; }
ok()   { echo -e "${GREEN}[✔] $*${RESET}"; }
warn() { echo -e "${YELLOW}[!] $*${RESET}"; }
die()  { echo -e "${RED}[✘] $*${RESET}" >&2; exit 1; }
sep()  { echo "--------------------------------------------------------------------------"; }

# ── Banner ─────────────────────────────────────────────────────────────────────
print_banner() {
    clear 2>/dev/null || true
    echo -e "${CYAN}"
    echo "=========================================================================="
    echo "  __      __   _     _   _____                _     _   ______   _      "
    echo "  \\ \\    / /  | |   | | |  __ \\              | |   | | |  ____| | |     "
    echo "   \\ \\  / /__ | | __| | | |__) |__ _  _ __   | |__ | | | |__    | |     "
    echo "    \\ \\/ // _ \\| |/ _\` | |  ___// _\` || '_ \\  | '_ \\| | |  __|   | |     "
    echo "     \\  /| (_) | | (_| | | |   | (_| || | | | | |_) | | | |____  | |____ "
    echo "      \\/  \\___/|_|\\__,_| |_|    \\__,_||_| |_| |_.__/|_| |______| |______|"
    echo "=========================================================================="
    echo -e "${RESET}"
    echo -e "${YELLOW}           The Next-Generation Hybrid Web Control Panel${RESET}"
    echo "=========================================================================="
    echo ""
}

# ── Environment detection ──────────────────────────────────────────────────────
# Returns one of: linux | wsl2 | macos | windows_native | unknown
detect_env() {
    # Git Bash / MSYS2 / Cygwin running natively on Windows set OS=Windows_NT
    # but /proc/version either doesn't exist or lacks 'microsoft'.
    if [[ "${OS:-}" == "Windows_NT" ]]; then
        if ! grep -qiE 'microsoft|WSL' /proc/version 2>/dev/null; then
            echo "windows_native"
            return
        fi
    fi

    # WSL1 / WSL2: /proc/version contains 'microsoft' or 'WSL'
    if [[ -f /proc/version ]] && grep -qiE 'microsoft|WSL' /proc/version 2>/dev/null; then
        echo "wsl2"
        return
    fi

    local UNAME
    UNAME=$(uname -s 2>/dev/null || echo "unknown")
    case "$UNAME" in
        Linux)  echo "linux"   ;;
        Darwin) echo "macos"   ;;
        *)      echo "unknown" ;;
    esac
}

# ── Root check ─────────────────────────────────────────────────────────────────
require_root() {
    if [[ $EUID -ne 0 ]]; then
        die "Must be run as root.  Try: sudo su - && bash install.sh"
    fi
    ok "Running as root"
}

# ── Ubuntu 22.04 check ────────────────────────────────────────────────────────
require_ubuntu_22() {
    if ! command -v lsb_release &>/dev/null; then
        die "OS not supported right now, we will update it soon"
    fi
    local NAME VER
    NAME=$(lsb_release -is 2>/dev/null || echo "unknown")
    VER=$(lsb_release -rs  2>/dev/null || echo "0")
    if [[ "$NAME" != "Ubuntu" || "$VER" != "22.04" ]]; then
        die "OS not supported right now, we will update it soon"
    fi
    ok "OS: Ubuntu $VER"
}

# ── Linux distro detection ─────────────────────────────────────────────────────
# Returns: ubuntu | rhel
detect_distro() {
    local ID=""
    local VERSION_ID=""
    if [[ -f /etc/os-release ]]; then
        ID=$(. /etc/os-release && echo "${ID:-}")
        VERSION_ID=$(. /etc/os-release && echo "${VERSION_ID:-}")
    fi

    # Normalize to lowercase
    ID=$(echo "$ID" | tr '[:upper:]' '[:lower:]')

    if [[ "$ID" == "ubuntu" ]]; then
        if [[ "$VERSION_ID" != "22.04" && "$VERSION_ID" != "24.04" ]]; then
            warn "Recommended Ubuntu version is 22.04 or 24.04. Proceeding anyway."
        fi
        echo "ubuntu"
        return
    elif [[ "$ID" == "almalinux" || "$ID" == "rocky" || "$ID" == "rhel" ]]; then
        echo "rhel"
        return
    else
        die "OS '$ID' is not supported right now."
    fi
}

# ── RAM / disk sanity ──────────────────────────────────────────────────────────
check_resources() {
    local RAM
    RAM=$(free -m 2>/dev/null | awk '/^Mem:/{print $2}' || echo "0")
    if [[ "$RAM" -lt 2048 ]]; then
        warn "Low RAM: ${RAM}MB  (2 GB minimum recommended, 4 GB ideal for WSL2)"
    else
        ok "RAM: ${RAM}MB"
    fi
}

# ── WSL2: ensure systemd is active ────────────────────────────────────────────
# ubuntu.sh uses `systemctl` for every service. Without systemd=true in
# /etc/wsl.conf the entire service layer is non-functional inside WSL2.
ensure_wsl2_systemd() {
    if [[ "$(cat /proc/1/comm 2>/dev/null)" == "systemd" ]] || \
       [[ -d /run/systemd/private ]]; then
        ok "systemd is running in WSL2"
        return 0
    fi

    warn "systemd is NOT active in this WSL2 instance. Enabling it now..."
    cat > /etc/wsl.conf << 'WSLCONF'
[boot]
systemd=true

[user]
default=root
WSLCONF

    echo ""
    echo -e "${BOLD}${YELLOW}================================================================${RESET}"
    echo -e "${YELLOW}  systemd has been enabled in /etc/wsl.conf${RESET}"
    echo -e "${YELLOW}  WSL2 must restart before the installation can continue.${RESET}"
    echo ""
    echo -e "${CYAN}  On your Windows host (PowerShell or CMD):${RESET}"
    echo -e "${CYAN}    wsl --terminate Ubuntu-22.04${RESET}"
    echo ""
    echo -e "${CYAN}  Then re-open WSL2 and run install.sh again.${RESET}"
    echo -e "${BOLD}${YELLOW}================================================================${RESET}"
    echo ""
    exit 0
}

# ── Core VoidPanel Linux installation ─────────────────────────────────────────
run_linux_install() {
    local DISTRO_FAMILY="${1:-ubuntu}"

    step "Initialising installation tracker..."
    local PUBLIC_IP
    PUBLIC_IP=$(curl -4 -s --max-time 8 ifconfig.me 2>/dev/null || \
                curl -4 -s --max-time 8 api.ipify.org 2>/dev/null || \
                echo "unknown")
    curl -s --max-time 8 -X POST \
        -H "Content-Type: application/json" \
        -d "{\"ip\":\"$PUBLIC_IP\"}" \
        "https://voidpanel.com/api/increment/" > /dev/null 2>&1 || true

    local SCRIPT_NAME
    local SCRIPT_URL
    if [[ "$DISTRO_FAMILY" == "rhel" ]]; then
        SCRIPT_NAME="almalinux.sh"
        SCRIPT_URL="https://voidpanel.com/static/almalinux.sh"
    else
        SCRIPT_NAME="ubuntu.sh"
        SCRIPT_URL="https://voidpanel.com/static/ubuntu.sh"
    fi

    step "Downloading VoidPanel installation payload ($SCRIPT_NAME)..."
    local TEMP
    TEMP=$(mktemp /tmp/voidpanel_XXXXXX.sh)
    if ! curl -fsSL --max-time 120 -o "$TEMP" "$SCRIPT_URL"; then
        rm -f "$TEMP"
        die "Download failed. Check your internet connection and try again."
    fi
    chmod +x "$TEMP"
    ok "Download complete. Launching installation engine..."
    sep

    bash "$TEMP"
    rm -f "$TEMP"

    # ── Post-install: Roundcube SSO plugin setup ───────────────────────────────
    step "Configuring Roundcube SSO auto-login plugin..."
    local SCRIPT_DIR
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-install.sh}")" 2>/dev/null && pwd || echo "")"
    local SSO_SETUP="$SCRIPT_DIR/scripts/setup_roundcube_sso.py"

    if [[ -f "$SSO_SETUP" ]]; then
        python3 "$SSO_SETUP" && ok "Roundcube SSO configured" || warn "Roundcube SSO setup returned warnings (non-fatal)"
    else
        # If running via curl pipe (no local repo), download and run the setup
        warn "scripts/setup_roundcube_sso.py not found locally — attempting download..."
        local SSO_TMP
        SSO_TMP=$(mktemp /tmp/vp_sso_XXXXXX.py)
        if curl -fsSL --max-time 30 \
            -o "$SSO_TMP" \
            "https://voidpanel.com/static/setup_roundcube_sso.py" 2>/dev/null; then
            python3 "$SSO_TMP" && ok "Roundcube SSO configured" || warn "Roundcube SSO setup returned warnings (non-fatal)"
            rm -f "$SSO_TMP"
        else
            warn "Could not download Roundcube SSO setup script. Run manually after install:"
            warn "  sudo python3 scripts/setup_roundcube_sso.py"
        fi
    fi
}

# ── WSL2: generate windows-startup.ps1 if not found locally ──────────────────
# When install.sh is piped from curl (no local repo), windows-startup.ps1 may
# not be present. We generate a fresh copy from template so WSL2 setup always works.
ensure_startup_script() {
    local DEST="$1"   # directory path (WSL path)

    # Prefer script from the voidpanel repo directory if present
    local SCRIPT_DIR
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-install.sh}")" 2>/dev/null && pwd || echo "")"

    if [[ -n "$SCRIPT_DIR" && -f "$SCRIPT_DIR/windows-startup.ps1" ]]; then
        cp "$SCRIPT_DIR/windows-startup.ps1" "$DEST/"
        ok "Startup script copied from repo"
        return
    fi

    # Try to download from voidpanel.com
    if curl -fsSL --max-time 30 \
        -o "$DEST/windows-startup.ps1" \
        "https://voidpanel.com/static/windows-startup.ps1" 2>/dev/null; then
        ok "Startup script downloaded"
        return
    fi

    # Last resort: generate a minimal working version inline
    warn "windows-startup.ps1 not found locally or remotely. Generating inline..."
    cat > "$DEST/windows-startup.ps1" << 'PEOF'
param([string]$Distribution = "Ubuntu-22.04")
$ErrorActionPreference = 'Continue'
$LogDir  = "$env:ProgramData\VoidPanel"
$LogFile = "$LogDir\startup.log"
if (-not (Test-Path $LogDir)) { New-Item -ItemType Directory -Path $LogDir | Out-Null }
function Write-Log { param($m); "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')  $m" | Tee-Object -FilePath $LogFile -Append | Write-Host }
$PORTS = @(21,22,25,53,80,110,143,443,465,587,953,993,995,3306,8080,8082,8090,8092,9000,9002)
Write-Log "=== VoidPanel Port Forward Refresh ==="
wsl -d $Distribution -- echo "WSL2 online" 2>&1 | Out-Null
Start-Sleep -Seconds 8
$wslIP = ((wsl -d $Distribution -- hostname -I 2>&1) -split '\s+' | Where-Object { $_ -match '^\d{1,3}(\.\d{1,3}){3}$' } | Select-Object -First 1)
if (-not $wslIP) { Write-Log "ERROR: Cannot resolve WSL2 IP"; exit 1 }
Write-Log "WSL2 IP: $wslIP"
foreach ($port in $PORTS) {
    netsh interface portproxy delete v4tov4 listenport=$port listenaddress=0.0.0.0 2>&1 | Out-Null
    netsh interface portproxy add v4tov4 listenport=$port listenaddress=0.0.0.0 connectport=$port connectaddress=$wslIP | Out-Null
}
Write-Log "Done. Panel: http://localhost:8080"
PEOF
    ok "Startup script generated inline"
}

# ── WSL2: configure Windows host automatically ────────────────────────────────
# This runs AFTER ubuntu.sh completes. It reaches out to the Windows host
# via /mnt/c/Windows/System32/...powershell.exe to set up:
#   • netsh portproxy rules   (TCP port forwarding Windows → WSL2)
#   • Windows Firewall        (allow inbound on panel ports)
#   • Task Scheduler job      (refresh portproxy on every Windows boot)
#   • Desktop credentials file
setup_wsl2_windows() {
    local POWERSHELL="/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe"
    local WIN_DATA_WSL="/mnt/c/ProgramData/VoidPanel"
    local WIN_DATA_WIN='C:\ProgramData\VoidPanel'

    echo ""
    echo -e "${BOLD}${CYAN}============================================================${RESET}"
    echo -e "${CYAN}   Configuring Windows Host (port forwarding + firewall)${RESET}"
    echo -e "${BOLD}${CYAN}============================================================${RESET}"

    # Get current WSL2 IP
    local WSL_IP
    WSL_IP=$(hostname -I 2>/dev/null | awk '{print $1}' || echo "")
    if [[ -z "$WSL_IP" ]]; then
        warn "Could not determine WSL2 IP — skipping automatic Windows setup"
        warn "Run windows-startup.ps1 manually on your Windows host as Administrator"
        return
    fi
    ok "WSL2 IP: $WSL_IP"

    # Create C:\ProgramData\VoidPanel\ and deploy startup script
    mkdir -p "$WIN_DATA_WSL" 2>/dev/null || {
        warn "Cannot write to $WIN_DATA_WIN — Windows drive may not be mounted"
        warn "Run windows-startup.ps1 manually as Administrator on your Windows host"
        return
    }

    ensure_startup_script "$WIN_DATA_WSL"

    # Write the one-time Windows setup script
    # IMPORTANT: unquoted heredoc (EOF) → bash expands $WSL_IP $PORTS_LIST etc.
    # PowerShell variables use \$ to survive bash expansion and appear as $ in the .ps1
    local PORTS_CSV="21,22,25,53,80,110,143,443,465,587,953,993,995,3306,8080,8082,8090,8092,9000,9002"
    local PS_SETUP_WSL="/mnt/c/Windows/Temp/voidpanel_windows_setup.ps1"
    local PS_SETUP_WIN='C:\Windows\Temp\voidpanel_windows_setup.ps1'

    cat > "$PS_SETUP_WSL" << EOF
# VoidPanel — Windows One-Time Setup
# Auto-generated by install.sh on $(date)
\$ErrorActionPreference = 'SilentlyContinue'
\$wslIP   = "$WSL_IP"
\$ports   = @($PORTS_CSV)
\$dataDir = "C:\ProgramData\VoidPanel"

Write-Host ""
Write-Host "======================================================" -ForegroundColor Cyan
Write-Host " VoidPanel Windows Host Configuration" -ForegroundColor Cyan
Write-Host "======================================================" -ForegroundColor Cyan

# ── 1. Port forwarding ──────────────────────────────────────────────────────
Write-Host "[+] Setting up TCP port forwarding -> \$wslIP" -ForegroundColor Cyan
foreach (\$port in \$ports) {
    netsh interface portproxy delete v4tov4 listenport=\$port listenaddress=0.0.0.0 2>\$null | Out-Null
    netsh interface portproxy add    v4tov4 listenport=\$port listenaddress=0.0.0.0 connectport=\$port connectaddress=\$wslIP | Out-Null
}
Write-Host "[v] $PORTS_CSV ports forwarded" -ForegroundColor Green

# ── 2. Firewall rule ─────────────────────────────────────────────────────────
Write-Host "[+] Configuring Windows Firewall..." -ForegroundColor Cyan
netsh advfirewall firewall delete rule name='VoidPanel-WSL2-Inbound' 2>\$null | Out-Null
netsh advfirewall firewall add rule name='VoidPanel-WSL2-Inbound' dir=in action=allow protocol=tcp localport=(\$ports -join ',') | Out-Null
Write-Host "[v] Firewall rule created" -ForegroundColor Green

# ── 3. Startup task (refresh portproxy after reboot — WSL2 IP changes) ───────
if (Test-Path "\$dataDir\windows-startup.ps1") {
    Write-Host "[+] Registering startup task..." -ForegroundColor Cyan
    \$act  = New-ScheduledTaskAction -Execute "PowerShell.exe" -Argument "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File \`"\$dataDir\windows-startup.ps1\`""
    \$tri  = New-ScheduledTaskTrigger -AtStartup
    \$prin = New-ScheduledTaskPrincipal -UserId "SYSTEM" -RunLevel Highest
    \$set  = New-ScheduledTaskSettingsSet -ExecutionTimeLimit (New-TimeSpan -Minutes 5) -StartWhenAvailable -MultipleInstances IgnoreNew
    Register-ScheduledTask -TaskName "VoidPanel WSL2 Port Forward" -Action \$act -Trigger \$tri -Principal \$prin -Settings \$set -Force | Out-Null
    Write-Host "[v] Startup task registered: 'VoidPanel WSL2 Port Forward'" -ForegroundColor Green
} else {
    Write-Host "[!] windows-startup.ps1 not found in \$dataDir — startup task skipped" -ForegroundColor Yellow
}

# ── 4. Summary ───────────────────────────────────────────────────────────────
Write-Host ""
Write-Host "======================================================"  -ForegroundColor Green
Write-Host "  VoidPanel is now accessible from Windows:"           -ForegroundColor Green
Write-Host "  Admin Panel  : http://localhost:8080"                -ForegroundColor Cyan
Write-Host "  Admin Panel  : https://localhost:8082"               -ForegroundColor Cyan
Write-Host "  phpMyAdmin   : http://localhost:8090"                -ForegroundColor Cyan
Write-Host "  Roundcube    : http://localhost:9000"                 -ForegroundColor Cyan
Write-Host "  WSL2 IP      : \$wslIP"                              -ForegroundColor White
Write-Host "  NOTE: DNS UDP (port 53) and FTP passive ports"       -ForegroundColor Yellow
Write-Host "        need direct WSL2 IP access (TCP-only proxy)"   -ForegroundColor Yellow
Write-Host "======================================================"  -ForegroundColor Green
EOF

    # ── Run the setup script via PowerShell (requires Admin terminal) ──────────
    step "Running Windows port forwarding setup via PowerShell..."

    if [[ ! -f "$POWERSHELL" ]]; then
        warn "PowerShell not found at expected path: $POWERSHELL"
        _save_manual_script "$WSL_IP" "$PS_SETUP_WIN"
        return
    fi

    local EXIT_CODE=0
    "$POWERSHELL" -NoProfile -ExecutionPolicy Bypass -File "$PS_SETUP_WIN" 2>/dev/null \
        || EXIT_CODE=$?

    if [[ $EXIT_CODE -eq 0 ]]; then
        ok "Windows port forwarding configured successfully"
        ok "Startup task registered (auto-refresh on reboot)"
        _save_windows_credentials "$WSL_IP"
        rm -f "$PS_SETUP_WSL" 2>/dev/null || true
    else
        warn "PowerShell exited with code $EXIT_CODE"
        warn "This usually means the WSL2 terminal was not opened as Administrator."
        _save_manual_script "$WSL_IP" "$PS_SETUP_WIN"
    fi
}

# Save the setup .ps1 to Public Desktop + show manual instructions
_save_manual_script() {
    local WSL_IP="$1"
    local PS_WIN_PATH="$2"

    # Copy to Public Desktop so it's easy to find
    local PUB_DESK_WSL="/mnt/c/Users/Public/Desktop"
    if [[ -d "$PUB_DESK_WSL" ]]; then
        cp "/mnt/c/Windows/Temp/voidpanel_windows_setup.ps1" \
           "$PUB_DESK_WSL/VoidPanel_Windows_Setup.ps1" 2>/dev/null || true
        PS_WIN_PATH='C:\Users\Public\Desktop\VoidPanel_Windows_Setup.ps1'
    fi

    echo ""
    echo -e "${BOLD}${YELLOW}================================================================${RESET}"
    echo -e "${YELLOW}  ACTION REQUIRED — Windows port forwarding not yet configured${RESET}"
    echo -e "${YELLOW}================================================================${RESET}"
    echo ""
    echo -e "  VoidPanel installed successfully inside WSL2."
    echo -e "  To access it from Windows, you need to run a ONE-TIME"
    echo -e "  command in an ${BOLD}Administrator PowerShell${RESET} window:"
    echo ""
    echo -e "  ${CYAN}powershell -ExecutionPolicy Bypass -File \"$PS_WIN_PATH\"${RESET}"
    echo ""
    echo -e "  This will:"
    echo -e "  • Forward all panel ports from Windows to WSL2 ($WSL_IP)"
    echo -e "  • Open the required ports in Windows Firewall"
    echo -e "  • Register a startup task so forwarding persists after reboot"
    echo ""
    echo -e "  After running it, open: ${CYAN}http://localhost:8080${RESET}"
    echo -e "${BOLD}${YELLOW}================================================================${RESET}"
    echo ""
}

# Write access credentials to the Windows Desktop
_save_windows_credentials() {
    local WSL_IP="$1"
    local POWERSHELL="/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe"

    local DESKTOP_WIN
    DESKTOP_WIN=$("$POWERSHELL" -NoProfile -Command \
        "[Environment]::GetFolderPath('Desktop')" 2>/dev/null | tr -d '\r\n' || echo "")

    [[ -z "$DESKTOP_WIN" ]] && return

    local DESKTOP_WSL
    DESKTOP_WSL=$(wslpath "$DESKTOP_WIN" 2>/dev/null || echo "")
    [[ -z "$DESKTOP_WSL" || ! -d "$DESKTOP_WSL" ]] && return

    local CREDS
    CREDS=$(cat /root/voidpanel_access.txt 2>/dev/null || echo "(see /root/voidpanel_access.txt inside WSL2)")

    local HOST_IP
    HOST_IP=$("$POWERSHELL" -NoProfile -Command \
        "(Get-NetIPAddress -AddressFamily IPv4 | Where-Object { \$_.IPAddress -notmatch '^(127|169)\.' } | Sort-Object PrefixLength | Select-Object -First 1).IPAddress" \
        2>/dev/null | tr -d '\r\n' || echo "YOUR_WINDOWS_IP")

    cat > "$DESKTOP_WSL/VoidPanel-Access.txt" << CRED
VoidPanel — Windows (WSL2) Access Details
==========================================
Admin Panel (HTTP)  : http://localhost:8080  |  http://${HOST_IP}:8080
Admin Panel (HTTPS) : https://localhost:8082 |  https://${HOST_IP}:8082
phpMyAdmin          : http://localhost:8090  |  http://${HOST_IP}:8090
Roundcube           : http://localhost:9000  |  http://${HOST_IP}:9000

WSL2 IP (current)   : $WSL_IP
WSL2 Shell          : wsl -d Ubuntu-22.04

--- Admin Credentials ---
$CREDS

--- Port Forwarding Notes ---
• DNS UDP port 53 and FTP passive (40000–50000) require direct WSL2 IP
  access — netsh portproxy only forwards TCP.
• After each Windows reboot, the Task Scheduler job 'VoidPanel WSL2 Port
  Forward' automatically refreshes port forwarding to the new WSL2 IP.
• Startup log  : C:\ProgramData\VoidPanel\startup.log
• Manual refresh: powershell -ExecutionPolicy Bypass -File "C:\ProgramData\VoidPanel\windows-startup.ps1"

Generated: $(date)
CRED

    ok "Credentials saved to your Windows Desktop: VoidPanel-Access.txt"
}

# ── MAIN ───────────────────────────────────────────────────────────────────────
main() {
    print_banner

    local ENV
    ENV=$(detect_env)

    echo -e "${CYAN}[i] Detected environment: ${BOLD}${ENV}${RESET}"
    echo ""

    case "$ENV" in

        # ── Windows-native shell (Git Bash, MSYS2, Cygwin) ───────────────────
        windows_native)
            echo -e "${RED}[✘] Cannot run directly in a Windows shell.${RESET}"
            echo ""
            echo -e "  Please use ${BOLD}install.bat${RESET} instead:"
            echo -e "  • Double-click ${BOLD}install.bat${RESET} in the voidpanel folder"
            echo -e "  • It sets up WSL2 + Ubuntu 22.04 and runs this script inside Ubuntu"
            echo ""
            exit 1
            ;;

        # ── macOS: not valid as a server target ───────────────────────────────
        macos)
            echo -e "${RED}[✘] macOS is not supported for VoidPanel server installation.${RESET}"
            echo ""
            echo -e "  VoidPanel is a Linux web hosting control panel."
            echo -e "  Deploy it on an Ubuntu 22.04+ VPS, or on Windows via WSL2."
            echo ""
            exit 1
            ;;

        # ── Unknown / unsupported OS ──────────────────────────────────────────
        unknown)
            die "Unsupported operating system."
            ;;

        # ── Native Linux server (Ubuntu / AlmaLinux / Rocky / RHEL) ────────
        linux)
            require_root
            echo -e "${CYAN}[+] Running pre-flight checks...${RESET}"

            local DISTRO_FAMILY
            DISTRO_FAMILY=$(detect_distro)
            ok "Distro family: $DISTRO_FAMILY"
            check_resources
            run_linux_install "$DISTRO_FAMILY"

            echo ""
            echo -e "${GREEN}==========================================================================${RESET}"
            echo -e "${GREEN}   VoidPanel installation complete! All services are coming online.${RESET}"
            echo -e "${GREEN}   Access the panel: http://YOUR_SERVER_IP:8080${RESET}"
            echo -e "${GREEN}   Credentials saved: /root/voidpanel_access.txt${RESET}"
            echo -e "${GREEN}==========================================================================${RESET}"
            ;;

        # ── WSL2: Ubuntu running inside Windows ───────────────────────────────
        wsl2)
            require_root

            echo -e "${GREEN}[i] Running inside WSL2 — Windows Subsystem for Linux${RESET}"
            echo -e "${GREEN}[i] All services (nginx, postfix, dovecot, bind9, vsftpd, mysql, etc.)${RESET}"
            echo -e "${GREEN}[i] run natively in Ubuntu. Windows port forwarding auto-configured.${RESET}"
            echo ""

            echo -e "${CYAN}[+] Running pre-flight checks...${RESET}"
            ensure_wsl2_systemd   # exits with restart instructions if systemd not active
            require_ubuntu_22
            check_resources

            # ── Linux-side installation (identical to native Linux path) ──────
            run_linux_install "ubuntu"

            # ── Windows-side setup (portproxy, firewall, task scheduler) ──────
            setup_wsl2_windows

            echo ""
            echo -e "${GREEN}==========================================================================${RESET}"
            echo -e "${GREEN}   VoidPanel installation complete!${RESET}"
            echo -e "${GREEN}   Admin Panel  : http://localhost:8080   (HTTP)${RESET}"
            echo -e "${GREEN}   Admin Panel  : https://localhost:8082  (HTTPS)${RESET}"
            echo -e "${GREEN}   phpMyAdmin   : http://localhost:8090${RESET}"
            echo -e "${GREEN}   Roundcube    : http://localhost:9000${RESET}"
            echo -e "${GREEN}   Credentials  : /root/voidpanel_access.txt  (inside WSL2)${RESET}"
            echo -e "${GREEN}   WSL2 shell   : wsl -d Ubuntu-22.04${RESET}"
            echo -e "${GREEN}==========================================================================${RESET}"
            ;;
    esac
}

main "$@"
