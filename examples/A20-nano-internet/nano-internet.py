#!/usr/bin/env python3
# encoding: utf-8

from seedemu import *
import os


# Create the Emulator 
emu = Emulator()

# Create the base layer
base = Base()

###############################################################################
# Create Internet exchanges 

ix100 = base.createInternetExchange(100)
ix101 = base.createInternetExchange(101)
ix100.getPeeringLan().setDisplayName('New York-100')
ix101.getPeeringLan().setDisplayName('Chicago-101')


###############################################################################
# Create and set up a transit AS (AS-3)

as3 = base.createAutonomousSystem(3)

# Create 3 internal networks
as3.createNetwork('net0')
as3.createNetwork('net1')
as3.createNetwork('net2')

# Create four routers and link them in a linear structure:
# ix100 <--> r1 <--> r2 <--> r3 <--> r4 <--> ix101
# r1 and r2 are BGP routers because they are connected to internet exchanges
as3.createRouter('r1').joinNetwork('net0').joinNetwork('ix100')
as3.createRouter('r2').joinNetwork('net0').joinNetwork('net1')
as3.createRouter('r3').joinNetwork('net1').joinNetwork('net2')
as3.createRouter('r4').joinNetwork('net2').joinNetwork('ix101')


###############################################################################
# Create and set up the stub AS (AS-151)

as151 = base.createAutonomousSystem(151)

# Create an internal network and a router
as151.createNetwork('net0')
as151.createRouter('router0').joinNetwork('net0').joinNetwork('ix100')

# Create two host nodes 
as151.createHost('host0').joinNetwork('net0')
as151.createHost('host1').joinNetwork('net0', address = '10.151.0.80')

# Install additional software on a host
host0 = as151.getHost('host0')
host0.addSoftware('telnetd').addSoftware('telnet')

# Run an additional command inside the container 
# The command creates a new account inside the host (also sets its password)
host0.addBuildCommand('useradd -m -s /bin/bash seed && echo "seed:dees" | chpasswd')

###############################################################################
# Create and set up the stub AS (AS-152)


as152 = base.createAutonomousSystem(152)
as152.createNetwork('net0')
as152.createRouter('router0').joinNetwork('net0').joinNetwork('ix101')
as152.createHost('host0').joinNetwork('net0')
as152.createHost('host1').joinNetwork('net0')
as152.createHost('host2').joinNetwork('net0')

# Install additional software on a host
as152.getHost('host0').addSoftware('telnet')

###############################################################################
# Create and set up the stub AS (AS-153)

# Use the utility function to create the AS
Makers.makeStubAs(emu, base, 153, 101, [None, None])

# Further customization
as153 = base.getAutonomousSystem(153)
as153.getHost('host_1').addSoftware('telnet')


###############################################################################
# BGP peering

# Create the Ebgp layer
ebgp = Ebgp()

# Make AS-3 the internet service provider for all the stub ASes
ebgp.addPrivatePeering (100, 3,   151, abRelationship = PeerRelationship.Provider)
ebgp.addPrivatePeerings(101, [3], [152, 153], abRelationship = PeerRelationship.Provider)

# Peer AS-152 and AS-153 directly as peers
ebgp.addPrivatePeering(101, 152, 153, abRelationship = PeerRelationship.Peer)


###############################################################################
# Web Service Layer 

# Create the WebService layer
web = WebService()

# Create web service nodes (virtual nodes)
# add Class label to the Conatiner (please refer README.md for further information.)
web01 = web.install('web01').appendClassName("SEEDWeb")
web02 = web.install('web02').appendClassName("SyrWeb")

# Bind the virtual nodes to physical nodes
emu.addBinding(Binding('web01', filter = Filter(nodeName = 'host0', asn = 151)))
emu.addBinding(Binding('web02', filter = Filter(nodeName = 'host0', asn = 152)))

###############################################################################

emu.addLayer(base)
emu.addLayer(ebgp)
emu.addLayer(web)

emu.addLayer(Routing())
emu.addLayer(Ibgp())
emu.addLayer(Ospf())

###############################################################################
# Save it to a component file, so it can be used by other emulators

# This is optional
emu.dump('base-component.bin')


###############################################################################
# Rendering: This is where the actual binding happens

emu.render()

# Change the display name for the nodes hosting the web services
emu.getBindingFor('web01').setDisplayName('Web-1')
emu.getBindingFor('web02').setDisplayName('Web-2')


###############################################################################
# Compilation

docker = Docker()

# Use the "handsonsecurity/seed-ubuntu:small" custom image from dockerhub
docker.addImage(DockerImage('handsonsecurity/seed-ubuntu:small', [], local = False), priority=-1)
docker.setImageOverride(as152.getHost('host1'), 'handsonsecurity/seed-ubuntu:small')

# Use the "seed-ubuntu-large" custom image from local
docker.addImage(DockerImage('seed-ubuntu-large', [], local = True), priority=-1)
docker.setImageOverride(as152.getHost('host2'), 'seed-ubuntu-large')

# Generate the Docker files
emu.compile(docker, './output')

# Copy the base container image to the output folder
# the base container image should be located under the ouput folder to add it as custom image.
os.system('cp -r seed-ubuntu-large ./output')

# Generate other type of outputs
#emu.compile(Graphviz(), './others/graphs')
#emu.compile(DistributedDocker(), './others/distributed-docker')
#emu.compile(GcpDistributedDocker(), './others/gcp-distributed-docker')


