@echo off
:: ============================================================
::  VoidPanel Windows Installer Launcher
::  Double-click this file to install VoidPanel on Windows.
::  Automatically requests Administrator privileges.
:: ============================================================

:: Check if already running as Administrator
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo [!] Requesting Administrator privileges...
    powershell -Command "Start-Process -FilePath '%~f0' -Verb RunAs"
    exit /b
)

:: Run the PowerShell installer from the same directory as this .bat
echo [+] Starting VoidPanel Windows Installer...
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0install-windows.ps1"

echo.
echo [+] Installer finished. Press any key to close.
pause >nul
