#!/bin/bash

if [ $# -eq 0 ]; then
    echo "Error: No IP address provided."
    echo "Usage: $0 <vpn server>"
    exit 1
fi

SERVER=$1

sudo openvpn --config ovpn-client.ovpn --remote $SERVER 65000
