<#
.SYNOPSIS
    VoidPanel WSL2 Port Forwarding Refresh Script

.DESCRIPTION
    Registered by install-windows.ps1 as a Task Scheduler job.
    Runs at every Windows startup (as SYSTEM) to:
      1. Wake WSL2 (which triggers systemd to start all enabled services).
      2. Resolve the new WSL2 internal IP (changes on every reboot).
      3. Refresh all netsh portproxy rules so that Windows forwards the panel
         ports to the correct WSL2 address.

    WSL2 assigns a new 172.x.x.x IP to the virtual network adapter on each
    boot, so static portproxy rules become stale. This script corrects them.

.PARAMETER Distribution
    The WSL2 distribution name. Defaults to "Ubuntu-22.04".

.NOTES
    Logs are written to C:\ProgramData\VoidPanel\startup.log
    To run manually (Administrator PowerShell):
        powershell -ExecutionPolicy Bypass -File "C:\ProgramData\VoidPanel\windows-startup.ps1"
#>
param(
    [string]$Distribution = "Ubuntu-22.04"
)

$ErrorActionPreference = 'Continue'
$LogDir  = "$env:ProgramData\VoidPanel"
$LogFile = "$LogDir\startup.log"

if (-not (Test-Path $LogDir)) {
    New-Item -ItemType Directory -Path $LogDir | Out-Null
}

function Write-Log {
    param([string]$Message)
    $ts = Get-Date -Format 'yyyy-MM-dd HH:mm:ss'
    $line = "$ts  $Message"
    $line | Tee-Object -FilePath $LogFile -Append | Write-Host
}

# All TCP ports that VoidPanel uses
$PORTS = @(
    21,   # FTP
    22,   # SSH
    25,   # SMTP
    53,   # DNS (TCP)
    80,   # HTTP
    110,  # POP3
    143,  # IMAP
    443,  # HTTPS
    465,  # SMTPS
    587,  # SMTP submission
    953,  # RNDC (BIND9 control)
    993,  # IMAPS
    995,  # POP3S
    3306, # MySQL
    8080, # VoidPanel admin (HTTP)
    8082, # VoidPanel admin (HTTPS)
    8090, # phpMyAdmin (HTTP)
    8092, # phpMyAdmin (HTTPS)
    9000, # Roundcube (HTTP)
    9002  # Roundcube (HTTPS)
)

Write-Log "=== VoidPanel WSL2 Port Forward Refresh ==="

# ── Step 1: Wake WSL2 (triggers systemd → services auto-start) ───────────────
Write-Log "Starting WSL2 distribution: $Distribution"
$wakeResult = wsl -d $Distribution -- echo "WSL2 online" 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Log "WARNING: WSL2 start returned exit code $LASTEXITCODE — $wakeResult"
    Write-Log "If this is the first boot after install, WSL2 may need initialization."
    Write-Log "Try running: wsl --install -d Ubuntu-22.04"
}

# Give systemd time to bring all services online
Write-Log "Waiting 8 seconds for systemd services to initialize..."
Start-Sleep -Seconds 8

# ── Step 2: Get the new WSL2 IP ──────────────────────────────────────────────
$rawIP = wsl -d $Distribution -- hostname -I 2>&1
$wslIP = ($rawIP -split '\s+' `
    | Where-Object { $_ -match '^\d{1,3}(\.\d{1,3}){3}$' } `
    | Select-Object -First 1)

if (-not $wslIP) {
    Write-Log "ERROR: Cannot determine WSL2 IP from output: '$rawIP'"
    Write-Log "Port forwarding NOT updated. Panel may be unreachable."
    exit 1
}
Write-Log "WSL2 IP resolved: $wslIP"

# ── Step 3: Remove old portproxy rules ───────────────────────────────────────
Write-Log "Removing stale portproxy rules..."
foreach ($port in $PORTS) {
    netsh interface portproxy delete v4tov4 `
        listenport=$port listenaddress=0.0.0.0 2>&1 | Out-Null
}

# ── Step 4: Add fresh portproxy rules to the new WSL2 IP ─────────────────────
Write-Log "Adding fresh portproxy rules -> $wslIP ..."
$failed = @()
foreach ($port in $PORTS) {
    $result = netsh interface portproxy add v4tov4 `
        listenport=$port   listenaddress=0.0.0.0 `
        connectport=$port  connectaddress=$wslIP 2>&1
    if ($LASTEXITCODE -ne 0) {
        $failed += $port
        Write-Log "  WARNING: Port $port — $result"
    }
}

if ($failed.Count -gt 0) {
    Write-Log "WARNING: Failed to set portproxy for ports: $($failed -join ', ')"
    Write-Log "This usually means another process is already listening on those ports."
} else {
    Write-Log "All $($PORTS.Count) portproxy rules applied successfully."
}

# ── Step 5: Summary ──────────────────────────────────────────────────────────
Write-Log ""
Write-Log "VoidPanel is now accessible:"
Write-Log "  Admin Panel  : http://localhost:8080  (HTTP)"
Write-Log "  Admin Panel  : https://localhost:8082 (HTTPS)"
Write-Log "  phpMyAdmin   : http://localhost:8090"
Write-Log "  Roundcube    : http://localhost:9000"
Write-Log "  WSL2 Shell   : wsl -d $Distribution"
Write-Log ""
Write-Log "NOTE: DNS UDP (port 53) and FTP passive ports (40000-50000) require"
Write-Log "      direct access to the WSL2 IP ($wslIP) as netsh portproxy is TCP-only."
Write-Log "=== Done ==="
