#!/usr/bin/env python3
# encoding: utf-8

from seedemu.layers import Base, Routing, Ebgp
from seedemu.services import WebService
from seedemu.compiler import Docker, OpenVSwitch
from seedemu.core import Emulator, Binding, Filter


# Initialize the emulator and layers
emu     = Emulator()
base    = Base()
routing = Routing()
ebgp    = Ebgp()
web     = WebService()

###############################################################################
# Create an Internet Exchange
base.createInternetExchange(100)

###############################################################################
# Create and set up AS-150

# Create an autonomous system 
as0 = base.createAutonomousSystem(10)

as0.createSwitch('sdn0').setHostIpRange(1,100,1)

for i in range(0, 2):
    node = as0.createHost('host{}'.format(i)).joinSwitch('sdn0')
    node.addSoftware('iperf3').addSoftware('netperf')
    node.setLabel('position_x', value=str(100*int(i%5+1)))
    node.setLabel('position_y', value=str(100*int(i//5+1)))
    tc_init = '''#!/bin/bash

tc qdisc add dev eth1 root handle 1:0 htb default 30
'''
    for id in range(1, 3):
        tc_init += '''
tc class add dev eth1 parent 1:0 classid 1:1{id} htb rate 1000000000000
tc filter add dev eth1 protocol ip parent 1:0 prio 1 u32 match ip dst 10.0.0.{id}/32 flowid 1:1{id}
tc qdisc add dev eth1 parent 1:1{id} handle 1{id}: netem delay 0ms loss 0%
'''.format(id=id)
    node.setFile('/tc_init',tc_init)
    node.appendStartCommand('chmod +x /tc_init')

###############################################################################
# Rendering 

emu.addLayer(base)

emu.render()

###############################################################################
# Compilation

emu.compile(Docker(), './output')
emu.compile(OpenVSwitch(), './command')
