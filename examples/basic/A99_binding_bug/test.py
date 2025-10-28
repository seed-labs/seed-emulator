#!/usr/bin/env python3
# encoding: utf-8

from seedemu import *
import sys, os
import math, json
from examples.basic.A99_binding_bug import MyMakers

###############################################################################
# Set the platform information
script_name = os.path.basename(__file__)

platform = Platform.AMD64  # Default platform is AMD64


total_number_of_v_nodes = 100

asns = [150, 151, 152, 153, 154, 160, 161, 162, 163, 164]
total_stub_as  = len(asns)
hosts_per_as   = 20
vnodes_per_as  = 15

emu = MyMakers.makeEmulatorBaseWith10StubASAndHosts(hosts_per_stub_as=hosts_per_as)

web   = WebService()

###################################################
vid = 0
for asn in asns:
  for i in range(vnodes_per_as):
      vnode_name = f"vnod_{vid}"
      node_name  = f"host_{i}"
      web.install(vnode_name)
      emu.addBinding(Binding(vnode_name, filter=Filter(asn=asn, nodeName=node_name))) 
      print(f"{vnode_name} - {node_name} - {asn}")
      vid +=1
###################################################

emu.addLayer(web)
emu.render()

docker = Docker(internetMapEnabled=True, etherViewEnabled=True, platform=platform)
emu.compile(docker, './output', override=True)
