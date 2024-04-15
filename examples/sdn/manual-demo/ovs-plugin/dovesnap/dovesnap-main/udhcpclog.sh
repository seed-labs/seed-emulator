#!/bin/bash

if [[ "$1" == "bound" || "$1" == "renew" ]] ; then
	touch /var/run/udhcpc.updated
	echo $ip > /var/run/${CONTAINER_ID}-ipv4.txt
fi
exec /etc/udhcpc/default.script $*
