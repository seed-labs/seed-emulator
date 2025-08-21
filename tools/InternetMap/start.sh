#!/bin/sh

if [ "$DEFAULT_ROUTE" ]; then
    ip rou del default 2> /dev/null
    ip route add default via $DEFAULT_ROUTE dev eth0
fi

cd /usr/src/app/backend
while true; do node ./bin/main.js; done
