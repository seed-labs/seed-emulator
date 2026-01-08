#!/bin/bash

TARGET='./target_networks_hosts'
ROUTER='10.174.0.254'   # The default router used by the VPN server
NETWORKS=("10.0.0.0/8") # Initialize with the emulator's network prefixes
DNS_ENTRIES=''

# Check if the file exists
if [ ! -f "$TARGET" ]; then
    echo "Error: File '$TARGET' not found."
    exit 1
fi


while IFS= read -r line || [ -n "$line" ]; do

    [[ "$line" == \#* ]] && continue
    [[ -z "$line" ]]     && continue

    elements=($line)
    if [ ${#elements[@]} -ge 3 ]; then
	NETWORKS+=("${elements[0]}")  # Append prefix to the list
        IP="${elements[1]}"
        HOST="${elements[2]}"
        DNS_ENTRY="$IP"$' '"$HOST"
	DNS_ENTRIES="$DNS_ENTRIES""$DNS_ENTRY"$'\\n'
    fi
done < "$TARGET"

DNS_ENTRIES=${DNS_ENTRIES%\\n}

# Add the mapping to the /etc/hosts file
sudo sed -i '/# BEGIN CUSTOM/,/# END CUSTOM/{//!d;}' /etc/hosts && sudo sed -i "/# BEGIN CUSTOM/a $DNS_ENTRIES" /etc/hosts

# Add the routing information
for network in "${NETWORKS[@]}"; do
   echo "RUN: sudo ip route add $network via $ROUTER"
   sudo ip route add "$network" via "$ROUTER"
done

