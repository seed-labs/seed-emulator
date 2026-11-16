#!/usr/bin/env python3
# encoding: utf-8

from Lib.RansomwareService import RansomwareClientService, RansomwareService, RansomwareServerFileTemplates
from Lib.TorService import *

from seedemu.core.Emulator import *
from seedemu.services.DomainNameService import *
from seedemu.services.DomainNameCachingService import *
from seedemu.core.Binding import Action, Filter, Binding
from seedemu.layers.Base import Base
from seedemu.core.Node import *
from seedemu.compiler.Docker import *
import random
import os


emu = Emulator()

# Load the base layer from the mini Internet example
emu.load('./base-component.bin')
base: Base = emu.getLayer("Base")

# Create a Ransomware Service
ransomware = RansomwareService()
ransomware.install('ransom-attacker').supportBotnet(False).supportTor(False)
emu.getVirtualNode('ransom-attacker').setDisplayName('Ransom-Attacker')
base.getAutonomousSystem(170).createHost('ransom-attacker').joinNetwork('net0', address='10.170.0.99')
emu.addBinding(Binding("ransom-attacker", filter=Filter(asn=170, nodeName='ransom-attacker')))

victim = RansomwareClientService()

for i in range(1, 17):
   victim_name =  'victim-{}'.format(i)
   display_name = 'Ransom-Victim-{}'.format(i)
   victim.install(victim_name).supportBotnet(False)
   emu.getVirtualNode(victim_name).setDisplayName(display_name)
   emu.addBinding(Binding(victim_name, filter=Filter(nodeName="host"), action=Action.RANDOM))

#################################################################
# Create a Tor component

# Create the Tor service layer
tor = TorService()

# Different types of Tor nodes (virtual nodes)
vnodes = {
   "da-1":     TorNodeType.DA,
   "da-2":     TorNodeType.DA,
   "da-3":     TorNodeType.DA,
   "da-4":     TorNodeType.DA,
   "da-5":     TorNodeType.DA,
   "client-1": TorNodeType.CLIENT,
   "client-2": TorNodeType.CLIENT,
   "relay-1":  TorNodeType.RELAY,
   "relay-2":  TorNodeType.RELAY,
   "relay-3":  TorNodeType.RELAY,
   "relay-4":  TorNodeType.RELAY,
   "exit-1":   TorNodeType.EXIT,
   "exit-2":   TorNodeType.EXIT,
   "hidden-service": TorNodeType.HS
}

# Create the virtual nodes
for i, (name, nodeType) in enumerate(vnodes.items()):
   if nodeType == TorNodeType.HS: 
      # Create 3 hidden services as bot-controller opens 4 ports (445, 446, 447, 448)
      tor.install(name).setRole(nodeType).linkByVnode("ransom-attacker", [445, 446, 447, 448])
   else:
      tor.install(name).setRole(nodeType)

   # Customize the display names.
   emu.getVirtualNode(name).setDisplayName("Tor-{}".format(name))

# Bind virtual nodes to physical nodes
as_list = [150, 151, 152, 153, 154, 160, 161, 162, 163, 164, 170, 171]
for i, (name, nodeType) in enumerate(vnodes.items()):
    # Pick an autonomous system randomly from the list,
    # and create a new host for each Tor node
    asn = random.choice(as_list)
    emu.addBinding(Binding(name, filter=Filter(asn=asn, nodeName=name), action=Action.NEW))


#################################################################
# Create a DNS layer
dns = DomainNameService()

# Create one nameserver for the root zone
dns.install('root-server').addZone('.')

# Create nameservers for TLD and ccTLD zones
dns.install('com-server').addZone('com.')
dns.install('edu-server').addZone('edu.')

# Create nameservers for second-level zones
dns.install('ns-syr-edu').addZone('syr.edu.')
dns.install('killswitch').addZone('iuqerfsodp9ifjaposdfjhgosurijfaewrwergwea.com.')

# Add records to zones
dns.getZone('syr.edu.').addRecord('@ A 128.230.18.63')
#dns.getZone('iuqerfsodp9ifjaposdfjhgosurijfaewrwergwea.com.').addRecord('@ A 5.5.5.5').addRecord('www A 5.5.5.5')

# Customize the display name (for visualization purpose)
emu.getVirtualNode('root-server').setDisplayName('Root')
emu.getVirtualNode('com-server').setDisplayName('COM')
emu.getVirtualNode('edu-server').setDisplayName('EDU')
emu.getVirtualNode('ns-syr-edu').setDisplayName('syr.edu')
emu.getVirtualNode('killswitch').setDisplayName('killswitch')

# Bind the virtual nodes in the DNS infrastructure layer to physical nodes.
emu.addBinding(Binding('root-server', filter=Filter(asn=171), action=Action.NEW))
emu.addBinding(Binding('com-server', filter=Filter(asn=150), action=Action.NEW))
emu.addBinding(Binding('edu-server', filter=Filter(asn=152), action=Action.NEW))
emu.addBinding(Binding('ns-syr-edu', filter=Filter(asn=154), action=Action.NEW))
emu.addBinding(Binding('killswitch', filter=Filter(asn=161), action=Action.NEW))

# Create one local DNS server (virtual nodes).
ldns = DomainNameCachingService()
ldns.install('global-dns')

# Customize the display name (for visualization purpose)
emu.getVirtualNode('global-dns').setDisplayName('Global DNS')

# Create new host in AS-153, use them to host the local DNS server.
as153 = base.getAutonomousSystem(153)
as153.createHost('local-dns').joinNetwork('net0', address = '10.153.0.53')

# Bind the Local DNS virtual node to physical node
emu.addBinding(Binding('global-dns', filter=Filter(asn=153, nodeName='local-dns')))

# Add 10.153.0.53 as the local DNS server for all the other nodes
base.setNameServers(['10.153.0.53'])


emu.addLayer(ldns)
emu.addLayer(dns)
emu.addLayer(tor)
emu.addLayer(ransomware)
emu.addLayer(victim)
emu.render()

# Use the "morris-worm-base" custom base image
docker = Docker()

docker.addImage(DockerImage('morris-worm-base', [], local = True))
docker.addImage(DockerImage('handsonsecurity/seed-ubuntu:large', [], local=False))

victim_nodes = base.getNodesByName('host')
for victim in victim_nodes:
   docker.setImageOverride(victim, 'morris-worm-base')

attacker_node = base.getNodesByName('ransom-attacker')
docker.setImageOverride(attacker_node[0], 'handsonsecurity/seed-ubuntu:large')

emu.compile(docker, './output', override=True)

os.system('cp -r container_files/morris-worm-base ./output')
os.system('cp -r container_files/z_start.sh ./output')
os.system('chmod a+x ./output/z_start.sh')
