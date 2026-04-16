#Requires -RunAsAdministrator
<#
.SYNOPSIS
    VoidPanel Windows Installer (WSL2-based)

.DESCRIPTION
    Installs VoidPanel on Windows 10/11 using WSL2 (Windows Subsystem for Linux).
    All hosting services (nginx, postfix, dovecot, bind9, vsftpd, mysql, php-fpm,
    etc.) run inside an Ubuntu 22.04 WSL2 environment — giving you 100% feature
    parity with a native Linux installation.

    What this installer does:
      1. Checks Windows version (Build 19041+ required for WSL2)
      2. Enables WSL2 Windows features (may require a reboot)
      3. Installs Ubuntu 22.04 inside WSL2
      4. Enables systemd inside WSL2 (required for service management)
      5. Runs the VoidPanel Linux installer (install.sh) inside Ubuntu
      6. Configures Windows port forwarding (netsh portproxy) for panel ports
      7. Opens the required ports in Windows Firewall
      8. Registers windows-startup.ps1 as a Task Scheduler job (runs at boot)
         so port forwarding stays correct even after WSL2 IP changes
      9. Saves admin credentials to your Desktop

.NOTES
    Run this script ONCE on a fresh machine.
    It is safe to re-run — all steps are idempotent.

    If a reboot is needed after enabling WSL2 features, the script will prompt
    you. Simply reboot and run install.bat again to continue.

    Tested on: Windows 10 21H1 (Build 19043), Windows 11 22H2, Windows 11 23H2
#>

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# ── Configuration ─────────────────────────────────────────────────────────────
$DISTRO        = "Ubuntu-22.04"
$TASK_NAME     = "VoidPanel WSL2 Port Forward"
$FIREWALL_RULE = "VoidPanel-WSL2-Inbound"
$DATA_DIR      = "$env:ProgramData\VoidPanel"
$LOG_FILE      = "$DATA_DIR\install.log"

# All TCP ports that VoidPanel uses (UDP port 53 is excluded — netsh portproxy
# is TCP-only; DNS UDP requires direct WSL2 IP access or a separate UDP relay)
$PORTS = @(
    21, 22, 25, 53, 80, 110, 143, 443, 465, 587,
    953, 993, 995, 3306, 8080, 8082, 8090, 8092, 9000, 9002
)

# ── Helpers ───────────────────────────────────────────────────────────────────
function Write-Status  { param($m) Write-Host "`n[+] $m" -ForegroundColor Cyan   }
function Write-Success { param($m) Write-Host "[v] $m"  -ForegroundColor Green  }
function Write-Warn    { param($m) Write-Host "[!] $m"  -ForegroundColor Yellow }
function Write-Err     { param($m) Write-Host "[X] $m"  -ForegroundColor Red    }

function Write-Log {
    param([string]$Message)
    $ts = Get-Date -Format 'yyyy-MM-dd HH:mm:ss'
    "$ts  $Message" | Out-File -FilePath $LOG_FILE -Append -Encoding UTF8
    Write-Host "$ts  $Message"
}

# Ensure log directory
if (-not (Test-Path $DATA_DIR)) {
    New-Item -ItemType Directory -Path $DATA_DIR | Out-Null
}

# ── Banner ────────────────────────────────────────────────────────────────────
Clear-Host
Write-Host @"
==========================================================================
  __      __   _     _   _____                _     _   ______   _
  \ \    / /  | |   | | |  __ \              | |   | | |  ____| | |
   \ \  / /__ | | __| | | |__) |__ _  _ __   | |__ | | | |__    | |
    \ \/ // _ \| |/ _' | |  ___// _' || '_ \  | '_ \| | |  __|   | |
     \  /| (_) | | (_| | | |   | (_| || | | | | |_) | | | |____  | |____
      \/  \___/|_|\__,_| |_|    \__,_||_| |_| |_.__/|_| |______| |______|
==========================================================================
             Windows Installer — Powered by WSL2 + Ubuntu 22.04
==========================================================================
"@ -ForegroundColor Cyan

Write-Log "VoidPanel Windows Installer started"

# ── Step 1: Windows Version Check ────────────────────────────────────────────
Write-Status "Checking Windows version..."
$build = [System.Environment]::OSVersion.Version.Build
Write-Log "Windows build: $build"
if ($build -lt 19041) {
    Write-Err "VoidPanel requires Windows 10 Build 19041 (May 2020 Update) or Windows 11."
    Write-Err "Your current build: $build"
    Write-Err "Please update Windows and try again."
    exit 1
}
Write-Success "Windows Build $build — OK"

# ── Step 2: RAM Check ────────────────────────────────────────────────────────
Write-Status "Checking system resources..."
$ramMB = [math]::Round((Get-CimInstance Win32_PhysicalMemory | Measure-Object -Property Capacity -Sum).Sum / 1MB)
if ($ramMB -lt 3500) {
    Write-Warn "Low RAM detected: ${ramMB}MB. VoidPanel recommends 4GB+ for WSL2."
    Write-Warn "Installation will continue but performance may be degraded."
} else {
    Write-Success "RAM: ${ramMB}MB — OK"
}

# ── Step 3: Enable WSL2 Windows Features ─────────────────────────────────────
Write-Status "Enabling WSL2 Windows features (this may take a few minutes)..."
$needReboot = $false
$features = @('Microsoft-Windows-Subsystem-Linux', 'VirtualMachinePlatform')
foreach ($feature in $features) {
    $state = (Get-WindowsOptionalFeature -Online -FeatureName $feature).State
    Write-Log "Feature $feature : $state"
    if ($state -ne 'Enabled') {
        Write-Log "Enabling $feature ..."
        $result = Enable-WindowsOptionalFeature -Online -FeatureName $feature -NoRestart -WarningAction SilentlyContinue
        if ($result.RestartNeeded) { $needReboot = $true }
        Write-Success "Enabled: $feature"
    } else {
        Write-Success "Already enabled: $feature"
    }
}

if ($needReboot) {
    Write-Warn ""
    Write-Warn "A REBOOT IS REQUIRED to activate WSL2 kernel features."
    Write-Warn "After rebooting, run install.bat again to continue the installation."
    Write-Warn "All steps are idempotent — it is safe to re-run."
    $choice = Read-Host "`nReboot now? (y/n)"
    if ($choice -eq 'y') {
        Restart-Computer -Force
    } else {
        Write-Warn "Please reboot manually and then re-run install.bat."
        exit 0
    }
}

# Update WSL kernel to latest version
Write-Status "Updating WSL2 kernel..."
try {
    wsl --update 2>&1 | Out-Null
    Write-Success "WSL2 kernel updated"
} catch {
    Write-Warn "WSL kernel update skipped (may require internet access)"
}

# Set WSL2 as default
wsl --set-default-version 2 2>&1 | Out-Null

# ── Step 4: Install Ubuntu 22.04 ─────────────────────────────────────────────
Write-Status "Checking for Ubuntu 22.04 WSL2 distribution..."
$installedDistros = wsl --list --quiet 2>&1
$alreadyInstalled = $installedDistros -match 'Ubuntu-22\.04'

if (-not $alreadyInstalled) {
    Write-Status "Installing Ubuntu 22.04 (downloading ~500MB — please wait)..."
    Write-Log "Installing $DISTRO via wsl --install"
    wsl --install -d $DISTRO --no-launch
    Write-Success "Ubuntu 22.04 installed"

    # First-run initialization: set up root user non-interactively
    Write-Status "Initializing Ubuntu 22.04 (first-run setup)..."
    $initResult = wsl -d $DISTRO --user root -- bash -c "echo 'Ubuntu initialized'" 2>&1
    Write-Log "Init result: $initResult"
} else {
    Write-Success "Ubuntu 22.04 already installed"
}

# Ensure WSL2 mode (not WSL1)
wsl --set-version $DISTRO 2 2>&1 | Out-Null
Write-Success "WSL2 mode confirmed for $DISTRO"

# ── Step 5: Enable systemd in WSL2 ───────────────────────────────────────────
# Without systemd=true, `systemctl` commands inside ubuntu.sh fail.
# This is the single most important configuration change for WSL2 compatibility.
Write-Status "Enabling systemd inside WSL2 (required for service management)..."
$wslConf = @"
[boot]
systemd=true

[user]
default=root
"@
# Write /etc/wsl.conf inside the WSL2 instance
$wslConfEscaped = $wslConf -replace "'", "''"
wsl -d $DISTRO --user root -- bash -c "cat > /etc/wsl.conf << 'WSLEOF'
[boot]
systemd=true

[user]
default=root
WSLEOF"

Write-Log "Written /etc/wsl.conf with systemd=true"
Write-Success "systemd enabled in WSL2"

# Restart the distribution to apply /etc/wsl.conf
Write-Status "Restarting WSL2 distribution to apply systemd config..."
wsl --terminate $DISTRO 2>&1 | Out-Null
Start-Sleep -Seconds 4
Write-Success "WSL2 distribution restarted"

# ── Step 6: Install VoidPanel Inside WSL2 ────────────────────────────────────
# Check if already installed (idempotency guard)
$alreadyProvisioned = $false
$skipInstall = $false
$reinstall = 'n'
try {
    $checkResult = wsl -d $DISTRO --user root -- bash -c "test -f /var/www/panel/manage.py && echo YES || echo NO" 2>&1
    $alreadyProvisioned = ($checkResult -match 'YES')
} catch { }

if ($alreadyProvisioned) {
    Write-Warn "VoidPanel appears to already be installed in WSL2 ($DISTRO)."
    $reinstall = Read-Host "Re-install? This will overwrite existing panel data. (y/n)"
    if ($reinstall -ne 'y') {
        Write-Status "Skipping VoidPanel installation. Updating port forwarding only..."
        # Jump straight to port forwarding (label simulation via flag)
        $skipInstall = $true
    }
}

if (-not $alreadyProvisioned -or ($reinstall -eq 'y')) {
    Write-Status "Installing VoidPanel inside WSL2 Ubuntu 22.04..."
    Write-Warn "This takes 15-30 minutes depending on your internet speed."
    Write-Warn "Do NOT close this window during installation."
    Write-Log "Starting VoidPanel installation inside WSL2"

    # Run the VoidPanel installer inside WSL2
    # The installer downloads ubuntu.sh from voidpanel.com and executes it.
    # Inside WSL2, lsb_release returns "Ubuntu 22.04" so all checks pass normally.
    $installCmd = @'
set -euo pipefail
export DEBIAN_FRONTEND=noninteractive
apt-get update -y -qq
apt-get install -y -qq curl wget lsb-release
curl -fsSL https://voidpanel.com/op/install.sh | bash
'@

    wsl -d $DISTRO --user root -- bash -c $installCmd
    if ($LASTEXITCODE -ne 0) {
        Write-Err "VoidPanel installation failed inside WSL2 (exit code $LASTEXITCODE)."
        Write-Err "Check the WSL2 terminal for error details."
        Write-Err "You can open it with: wsl -d $DISTRO"
        exit 1
    }
    Write-Success "VoidPanel installation completed inside WSL2"
}

# ── Step 7: Resolve WSL2 IP ───────────────────────────────────────────────────
Write-Status "Resolving WSL2 internal IP address..."
$rawIP = wsl -d $DISTRO --user root -- hostname -I 2>&1
$wslIP = ($rawIP -split '\s+' `
    | Where-Object { $_ -match '^\d{1,3}(\.\d{1,3}){3}$' } `
    | Select-Object -First 1)

if (-not $wslIP) {
    Write-Err "Cannot determine WSL2 IP address. Output: '$rawIP'"
    exit 1
}
Write-Success "WSL2 IP: $wslIP"
Write-Log "WSL2 IP: $wslIP"

# ── Step 8: Configure Windows Port Forwarding ────────────────────────────────
Write-Status "Configuring Windows port forwarding (netsh portproxy)..."
Write-Log "Setting up $($PORTS.Count) portproxy rules -> $wslIP"

# Remove any stale rules first
foreach ($port in $PORTS) {
    netsh interface portproxy delete v4tov4 listenport=$port listenaddress=0.0.0.0 2>&1 | Out-Null
}

# Add fresh rules
$failedPorts = @()
foreach ($port in $PORTS) {
    $r = netsh interface portproxy add v4tov4 `
        listenport=$port   listenaddress=0.0.0.0 `
        connectport=$port  connectaddress=$wslIP 2>&1
    if ($LASTEXITCODE -ne 0) {
        $failedPorts += $port
    }
}

if ($failedPorts.Count -gt 0) {
    Write-Warn "Could not set portproxy for ports: $($failedPorts -join ', ')"
    Write-Warn "These ports may already be in use by another Windows service."
} else {
    Write-Success "Port forwarding configured for all $($PORTS.Count) ports"
}

Write-Warn "NOTE: DNS UDP (port 53) and FTP passive (40000-50000) require direct"
Write-Warn "      WSL2 IP access ($wslIP) as netsh portproxy is TCP-only."

# ── Step 9: Windows Firewall Rules ───────────────────────────────────────────
Write-Status "Configuring Windows Firewall..."
netsh advfirewall firewall delete rule name="$FIREWALL_RULE" 2>&1 | Out-Null
$portList = ($PORTS -join ',')
netsh advfirewall firewall add rule `
    name="$FIREWALL_RULE" `
    dir=in `
    action=allow `
    protocol=tcp `
    localport=$portList | Out-Null
Write-Success "Firewall rule created: $FIREWALL_RULE"
Write-Log "Firewall: allowing TCP ports $portList"

# ── Step 10: Register startup task for persistent port forwarding ─────────────
# WSL2 gets a NEW IP every time Windows reboots. The windows-startup.ps1 script
# re-applies portproxy rules at each startup to keep the panel reachable.
Write-Status "Registering startup task for persistent port forwarding..."

# Copy windows-startup.ps1 to ProgramData so it persists across user sessions
$startupScript = "$DATA_DIR\windows-startup.ps1"
$sourceScript  = Join-Path $PSScriptRoot "windows-startup.ps1"

if (Test-Path $sourceScript) {
    Copy-Item $sourceScript $startupScript -Force
    Write-Log "Copied windows-startup.ps1 to $startupScript"
} else {
    Write-Warn "windows-startup.ps1 not found next to install-windows.ps1."
    Write-Warn "Port forwarding will NOT be refreshed automatically after reboots."
    Write-Warn "Copy windows-startup.ps1 to $startupScript manually."
}

if (Test-Path $startupScript) {
    $action = New-ScheduledTaskAction `
        -Execute "PowerShell.exe" `
        -Argument "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$startupScript`" -Distribution `"$DISTRO`""

    $trigger    = New-ScheduledTaskTrigger -AtStartup
    $principal  = New-ScheduledTaskPrincipal -UserId "SYSTEM" -RunLevel Highest
    $settings   = New-ScheduledTaskSettingsSet `
        -ExecutionTimeLimit (New-TimeSpan -Minutes 5) `
        -StartWhenAvailable `
        -MultipleInstances IgnoreNew

    Register-ScheduledTask `
        -TaskName   $TASK_NAME `
        -Action     $action `
        -Trigger    $trigger `
        -Principal  $principal `
        -Settings   $settings `
        -Force | Out-Null

    Write-Success "Startup task registered: '$TASK_NAME'"
    Write-Log "Task Scheduler: '$TASK_NAME' registered"
}

# ── Step 11: Save Credentials to Desktop ─────────────────────────────────────
Write-Status "Saving access credentials..."

# Read credentials from VoidPanel's credential file inside WSL2
$wslCreds = wsl -d $DISTRO --user root -- bash -c "cat /root/voidpanel_access.txt 2>/dev/null || echo '(credentials not yet generated)'" 2>&1

# Get the Windows machine's LAN IP for external access instructions
$hostIP = try {
    (Get-NetIPAddress -AddressFamily IPv4 `
        | Where-Object { $_.IPAddress -notmatch '^(127\.|169\.254\.|172\.)' } `
        | Sort-Object -Property PrefixLength `
        | Select-Object -First 1).IPAddress
} catch { "YOUR_WINDOWS_IP" }

$desktop    = [Environment]::GetFolderPath('Desktop')
$credFile   = Join-Path $desktop 'VoidPanel-Access.txt'

@"
VoidPanel Windows Installation — Access Details
================================================
Installation type : WSL2 (Ubuntu 22.04 inside Windows)
Windows host IP   : $hostIP
WSL2 IP           : $wslIP  (changes on reboot — portproxy handles this)

--- Panel Access URLs ---
Admin Panel (HTTP)  : http://localhost:8080   or  http://${hostIP}:8080
Admin Panel (HTTPS) : https://localhost:8082  or  https://${hostIP}:8082
phpMyAdmin          : http://localhost:8090   or  http://${hostIP}:8090
Roundcube Webmail   : http://localhost:9000   or  http://${hostIP}:9000

--- Admin Credentials ---
$wslCreds

--- WSL2 Shell Access ---
Open Ubuntu 22.04 shell (as root):
    wsl -d Ubuntu-22.04

--- Maintenance ---
Port forwarding log    : $DATA_DIR\startup.log
Startup refresh task   : Task Scheduler -> '$TASK_NAME'
Manual refresh (Admin) : powershell -ExecutionPolicy Bypass -File "$startupScript"

--- Limitations on Windows (WSL2) ---
- DNS UDP (port 53)          : Use WSL2 IP ($wslIP) directly for UDP DNS
- FTP passive (40000-50000)  : Use WSL2 IP directly or active FTP mode
- Everything else            : Full feature parity with native Linux

================================================
Generated: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')
"@ | Out-File $credFile -Encoding UTF8

Write-Success "Credentials saved to Desktop: VoidPanel-Access.txt"

# ── Done! ──────────────────────────────────────────────────────────────────────
Write-Log "Installation complete"
Write-Host ""
Write-Host "==========================================================================" -ForegroundColor Green
Write-Host "  VoidPanel installation on Windows (WSL2) is COMPLETE!" -ForegroundColor Green
Write-Host "==========================================================================" -ForegroundColor Green
Write-Host ""
Write-Host "  Admin Panel  : http://localhost:8080" -ForegroundColor Cyan
Write-Host "  Admin Panel  : https://localhost:8082" -ForegroundColor Cyan
Write-Host "  phpMyAdmin   : http://localhost:8090" -ForegroundColor Cyan
Write-Host "  Roundcube    : http://localhost:9000" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Credentials saved to: VoidPanel-Access.txt  (on your Desktop)" -ForegroundColor Yellow
Write-Host "  WSL2 shell  : wsl -d Ubuntu-22.04" -ForegroundColor Yellow
Write-Host ""
Write-Host "  Port forwarding is automatically refreshed after each Windows reboot" -ForegroundColor White
Write-Host "  via the '$TASK_NAME' Task Scheduler job." -ForegroundColor White
Write-Host ""
Write-Host "  Install log : $LOG_FILE" -ForegroundColor DarkGray
Write-Host "==========================================================================" -ForegroundColor Green
