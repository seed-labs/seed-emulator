#!/bin/bash
ip rou del default 2> /dev/null
ip route add default via 10.152.0.254 dev eth0

tail -f /dev/null

