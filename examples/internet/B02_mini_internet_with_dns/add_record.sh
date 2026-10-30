#!/bin/bash

# This shell script shows how to use the nsupdate command
# to add records to a nameserver. The nameserver in our emulator
# is configured to allow remote update.

if [ -z "$1" ]; then
   echo "Error: Missing required argumetns."
   echo "Usage: $0 <ip address>"
   exit 1
fi

# This is the nameserver of example.net
dns_server=10.163.0.71

new_ip=$1

update_command=$(cat <<EOF
server $dns_server
zone example.net.
update delete www.example.net A
update add www.example.net 1 A $new_ip
show
send
EOF
)

printf "$update_command" | nsupdate
