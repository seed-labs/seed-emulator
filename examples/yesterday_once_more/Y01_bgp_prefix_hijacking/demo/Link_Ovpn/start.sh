#!/bin/bash

# Check if parameters are provided
if [ $# -ge 2 ]; then
    # Get command line parameters
    REMOTE_IP=$1
    REMOTE_PORT=$2
    if ! command -v openvpn &> /dev/null; then
        echo "OpenVPN is not installed, attempting to install..."
        if command -v apt &> /dev/null; then
            sudo apt update && sudo apt install -y openvpn
        fi
    fi

    DEFAULT_IFACE=$(ip route | grep default | awk '{print $5}' | head -n 1)
    if [ -z "$DEFAULT_IFACE" ]; then
        echo "Unable to detect default network interface, please set manually."
        exit 1
    fi
    echo "Detected default network interface: $DEFAULT_IFACE"
    # Start OpenVPN
    echo "Connecting... wait a moment"
    sudo openvpn --config ovpn-client.ovpn --remote $REMOTE_IP $REMOTE_PORT &
    sleep 5

    # Check if tap0 interface exists
    if ip link show tap0 > /dev/null 2>&1; then
        echo "tap0 interface exists."
        sudo ip route add 10.0.0.0/8 via 10.154.0.254
    else
        echo "tap0 interface does not exist."
    fi
else
    echo "Usage: $0 <remote_ip> <remote_port>"
    echo "No remote IP and port provided. Skipping OpenVPN connection."
fi

# Define kill_openvpn function
kill_openvpn() {
    # Use killall command to kill all processes named openvpn
    sudo killall openvpn
    sleep 2
    if [ $? -eq 0 ]; then
        echo "Successfully killed all OpenVPN processes."
    else
        echo "Failed to kill OpenVPN processes, possibly because no OpenVPN processes are running."
    fi
}

# Call kill_openvpn function
# kill_openvpn
