#!/bin/bash
set -euo pipefail

# ANSI color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
RESET='\033[0m'

# Clear screen for impact
clear

# Function to print the welcome banner
print_banner() {
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

# Check for root privileges
if [[ $EUID -ne 0 ]]; then
    echo -e "${RED}[!] Critical Error: This script must be run as root.${RESET}"
    echo -e "${YELLOW}Attempt elevation with:${RESET} sudo su -"
    exit 1
fi

# Pre-flight environment checks
REQUIRED_RAM=2048 # in MB (2GB minimum)
REQUIRED_DISK=10 # in GB

TOTAL_RAM=$(free -m | awk '/^Mem:/{print $2}')
TOTAL_DISK=$(df / --output=avail -h | tail -1 | tr -d ' ' | sed 's/G//')

print_banner

echo -e "${CYAN}[+] Running Pre-flight Environment Checks...${RESET}"

# Check Ubuntu version
OS_NAME=$(lsb_release -is)
OS_VERSION=$(lsb_release -rs | cut -d. -f1)
if [[ "$OS_NAME" != "Ubuntu" || "$OS_VERSION" -lt 22 ]]; then
    echo -e "${RED}[!] Error: VoidPanel requires Ubuntu 22.04 or higher.${RESET}"
    exit 1
fi

if [[ "$TOTAL_RAM" -lt "$REQUIRED_RAM" ]]; then
    echo -e "${RED}[!] Error: Insufficient RAM. At least 2GB is required (Detected: ${TOTAL_RAM}MB).${RESET}"
    # exit 1 (Optional, can just warn, but set to 1 for stability)
fi

echo -e "${GREEN}[✔] OS: Ubuntu $OS_VERSION${RESET}"
echo -e "${GREEN}[✔] RAM: ${TOTAL_RAM}MB${RESET}"

# Tracking Installation
URL="https://voidpanel.com/api/increment/"
IP=$(curl -s ifconfig.me || echo "unknown")
echo -e "${CYAN}[+] Initializing installation tracker...${RESET}"
curl -s -X POST -H "Content-Type: application/json" -d '{"ip": "'"$IP"'"}' "$URL" > /dev/null || true

echo -e "${YELLOW}[+] Downloading the master VoidPanel payload...${RESET}"
TEMP_FILE=$(mktemp)
if ! curl -fsSL -o "$TEMP_FILE" "https://voidpanel.com/op/ubuntu.sh"; then
    echo -e "${RED}[!] Critical Error: Failed to download the VoidPanel payload due to network errors.${RESET}"
    rm -f "$TEMP_FILE"
    exit 1
fi
chmod +x "$TEMP_FILE"

echo -e "${GREEN}[✔] Download complete. Starting installation engine...${RESET}"
echo "--------------------------------------------------------------------------"
bash "$TEMP_FILE"

# Clean up
rm -f "$TEMP_FILE"
echo ""
echo -e "${GREEN}==========================================================================${RESET}"
echo -e "${GREEN}      VoidPanel Bootstrapping Concluded. Services are coming online!      ${RESET}"
echo -e "${GREEN}==========================================================================${RESET}"
