#!/bin/bash
ip rou del default 2> /dev/null
ip route add default via 10.151.0.254 dev eth0

tail -f /dev/null

