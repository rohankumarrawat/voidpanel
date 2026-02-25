#!/bin/bash

# Check for root privileges
if [[ $EUID -ne 0 ]]; then
    echo "This script must be run as root." 1>&2
    echo "Try Running Command after This" 1>&2
    print_colored_ascii_box "sudo su" 1>&2
    exit 1
fi

# Check Ubuntu version
REQUIRED_VERSION=22
OS_NAME=$(lsb_release -is)
OS_VERSION=$(lsb_release -rs | cut -d. -f1)

if [[ "$OS_NAME" != "Ubuntu" || "$OS_VERSION" -lt "$REQUIRED_VERSION" ]]; then
    print_colored_ascii_box "This script requires Ubuntu 22.04 or higher."
    exit 1
fi

# ANSI color codes
RED='\033[0;31m'
YELLOW='\033[1;33m'
RESET='\033[0m'  # No color

URL="https://voidpanel.com/api/increment/"  # Replace with your actual API URL

# Define the IP address to send in the request
IP=$(curl -s ifconfig.me)

# Send the POST request using curl
RESPONSE=$(curl -s -X POST -H "Content-Type: application/json" -d '{"ip": "'"$IP"'"}' $URL)

# Function to print the welcome message inside a big ASCII box with colors
print_colored_ascii_box() {
    MESSAGE=$1  # Your message
    MESSAGE_LENGTH=${#MESSAGE}        # Length of the message
    BOX_WIDTH=$((MESSAGE_LENGTH + 8)) # Adding extra padding for the box

    # Print the top border of the box in red
    echo -en "${RED}"
    for (( i=1; i<=BOX_WIDTH; i++ )); do
        echo -n "*"
    done
    echo

    # Print an empty line with side borders
    echo -e "*$(printf ' %.0s' $(seq 1 $((BOX_WIDTH - 2))))*"

    # Print the message with padding in yellow
    echo -e "*    ${YELLOW}$MESSAGE${RESET}${RED}    *"

    # Print an empty line with side borders
    echo -e "*$(printf ' %.0s' $(seq 1 $((BOX_WIDTH - 2))))*"

    # Print the bottom border of the box in red
    for (( i=1; i<=BOX_WIDTH; i++ )); do
        echo -n "*"
    done
    echo -e "${RESET}"  # Reset colors to default
}

# Call the function to print the box
print_colored_ascii_box "Welcome To VoidPanel!"
curl -fsSL https://voidpanel.com/op/ubuntu.sh | bash
