#!/usr/bin/env python3
# encoding: utf-8
import os
from seedemu.layers import Base, Routing, Babel
from seedemu.compiler import Docker, DockerInfo
from seedemu.core import Emulator
import shutil

def get_ipv6_addr(ipv4):
    ipv4a = ipv4.split('.')
    ipv6  =  "fe80::42:aff:fe" 
    ipv6 += "{:02x}:{:02x}{:02x}".format(int(ipv4a[1]), int(ipv4a[2]), int(ipv4a[3]))

    return ipv6

def get_mac_addr(ipv4):
    ipv4a = ipv4.split('.')
    mac  =  "02:42:0a:" 
    mac += "{:02x}:{:02x}:{:02x}".format(int(ipv4a[1]), int(ipv4a[2]), int(ipv4a[3]))

    return mac

def get_tc_init_batch(total):
    tc_cmd = ''
    for i in range(total):
        tc_init_cmd = '''
class add dev ifb0 parent 1:0 classid 1:1{id} htb rate 1000000000000
filter add dev ifb0 protocol ipv6 parent 1:0 prio 1 u32 match ip6 src {ipv6} flowid 1:1{id}
qdisc add dev ifb0 parent 1:1{id} handle 1{id}: netem delay 0ms loss 0%
        '''
        tc_cmd += tc_init_cmd.format(id=i, ipv6=get_ipv6_addr('10.9.0.{}'.format(100 + i))) 
    return tc_cmd

def get_tc_init_on_mac_batch(total):
    tc_cmd = ''
    for i in range(total):
        tc_init_cmd = '''
class add dev ifb0 parent 1:0 classid 1:1{id} htb rate 1000000000000
filter add dev ifb0 protocol all parent 1:0 prio 1 u32 match ether src {mac} flowid 1:1{id}
qdisc add dev ifb0 parent 1:1{id} handle 1{id}: netem delay 0ms loss 0%
        '''
        tc_cmd += tc_init_cmd.format(id=i, mac=get_mac_addr('10.9.0.{}'.format(100 + i))) 
    return tc_cmd

# Initialize the emulator and layers
emu     = Emulator()
base    = Base()
routing = Routing()

# Create an autonomous system 
as_ = base.createAutonomousSystem(9)

as_.createNetwork('net-wireless')

total = 5


node = [None] * total  
for i in range(total):
    # Create a router for the network 
    node[i] = as_.createRouter('router_{}'.format(i))         

    # Join the emulated `wireless` network
    node[i].joinNetwork('net-wireless', address='10.9.0.{}'.format(100 + i)) \
           .appendClassName('Wireless') 
    
    # Customize the routers
    node[i].addSoftware('iperf3').addSoftware('netperf') \
           .addSoftware('iptables').addSoftware('net-tools')  \
           .addSoftware('traceroute') \
           .setDisplayName('Router_{}'.format(i))        

    # Disable ICMP redirect (sending and receiving)
    node[i].appendStartCommand('sysctl -w net.ipv4.conf.all.send_redirects=0')       \
           .appendStartCommand('sysctl -w net.ipv4.conf.default.send_redirects=0')   \
           .appendStartCommand('sysctl -w net.ipv4.conf.all.accept_redirects=0')     \
           .appendStartCommand('sysctl -w net.ipv4.conf.default.accept_redirects=0') 

    # Babel requires IPv6 (IPv6 is disabled by default) 
    node[i].appendStartCommand('sysctl -w net.ipv6.conf.all.disable_ipv6=0')

    # Create ifb0 interface that mirrors traffic from net-wireless
    # This interface used to filter src ip in tc
    node[i].appendStartCommand('ip link add ifb0 type ifb')
    node[i].appendStartCommand('ip link set ifb0 up')

    # Set up TC qdisc
    node[i].appendStartCommand('tc qdisc add dev net-wireless handle ffff: ingress')
    node[i].appendStartCommand('tc filter replace dev net-wireless parent ffff: protocol all u32 match u32 0 0 action mirred egress redirect dev ifb0')
    node[i].appendStartCommand('tc qdisc add dev ifb0 root handle 1:0 htb default 30')

    node[i].setFile(path = '/tc_init_batch', content=get_tc_init_on_mac_batch(total=total))
    node[i].appendStartCommand('tc -b /tc_init_batch')
###############################################################################
# Rendering 

emu.addLayer(base)
emu.addLayer(Routing())
emu.addLayer(Babel(network_type = 'wireless'))  # the default is "wired"
emu.render()

###############################################################################
# Compilation

emu.compile(Docker(internetMapEnabled=False), './output', override = True)

shutil.rmtree("/tmp/node_info")
os.mkdir("/tmp/node_info")
