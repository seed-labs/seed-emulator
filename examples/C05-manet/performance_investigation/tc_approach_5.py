#!/usr/bin/env python3
# encoding: utf-8

from dockercontroller import * 
import time
import os

container_interface = get_interface_by_ip("10.0.0.1")
tc_init = '''
sudo bash -c 'tc qdisc add dev {ifname} root handle 1:0 htb default 30; tc class add dev {ifname} parent 1:0 classid 1:12 htb rate 1000000000000; tc filter add dev {ifname} protocol ip parent 1:0 prio 1 u32 match ip dst 10.0.0.2/32 flowid 1:12; tc qdisc add dev {ifname} parent 1:12 handle 12: netem delay 0ms loss 0%;'
'''

# os.system(tc_init.format(ifname=container_interface))
elasped_time = 0
for test in range(100):
    start = time.time()

    os.system("sudo tc -b tc_batch_container_if")
    end = time.time()
    elasped_time += (end-start)

print("avg: ", elasped_time/100)
