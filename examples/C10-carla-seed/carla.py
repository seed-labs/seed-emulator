#!/usr/bin/env python3
# encoding: utf-8

from seedemu import *


###############################################################################
emu     = Emulator()
base    = Base()
routing = Routing()
ebgp    = Ebgp()
ibgp    = Ibgp()
ospf    = Ospf()
web     = WebService()
ovpn    = OpenVpnRemoteAccessProvider()
etc_hosts = EtcHosts()


###############################################################################

ix100 = base.createInternetExchange(100)

# Customize names (for visualization purpose)
ix100.getPeeringLan().setDisplayName('CARLA-SEED')


as150 = base.createAutonomousSystem(150)
as150.createNetwork('net0')
as150.createRouter('router0').joinNetwork('net0').joinNetwork('ix100')
as150.createHost('websocket').joinNetwork('net0').addHostName('websocket')

as151 = base.createAutonomousSystem(151)
as151.createNetwork('net0')
as151.createRouter('router0').joinNetwork('net0').joinNetwork('ix100')
as151.createHost('controller').joinNetwork('net0').addHostName('controller')

as152 = base.createAutonomousSystem(152)
as152.createNetwork('net0')
as152.createRouter('router0').joinNetwork('net0').joinNetwork('ix100')
as152.createHost('seedcar1').joinNetwork('net0').addHostName('seedcar1')

as153 = base.createAutonomousSystem(153)
as153.createNetwork('net0')
as153.createRouter('router0').joinNetwork('net0').joinNetwork('ix100')
as153.createHost('seedcar2').joinNetwork('net0').addHostName('seedcar2')

as154 = base.createAutonomousSystem(154)
as154.createNetwork('net0')
as154.createRouter('router0').joinNetwork('net0').joinNetwork('ix100')
as154.createHost('seedcar3').joinNetwork('net0').addHostName('seedcar3')

as155 = base.createAutonomousSystem(155)
as155.createNetwork('net0')
as155.createRouter('router0').joinNetwork('net0').joinNetwork('ix100')
as155.createHost('seedcar4').joinNetwork('net0').addHostName('seedcar4')

as156 = base.createAutonomousSystem(156)
as156.createNetwork('net0')
as156.createRouter('router0').joinNetwork('net0').joinNetwork('ix100')
as156.createHost('seedcar5').joinNetwork('net0').addHostName('seedcar5')

as157 = base.createAutonomousSystem(157)
as157.createNetwork('net0')
as157.createRouter('router0').joinNetwork('net0').joinNetwork('ix100')
as157.createHost('seedcar6').joinNetwork('net0').addHostName('seedcar6')

as158 = base.createAutonomousSystem(158)
as158.createNetwork('net0')
as158.createRouter('router0').joinNetwork('net0').joinNetwork('ix100')
as158.createHost('traffic').joinNetwork('net0').addHostName('traffic')

# Create real-world AS.
# AS11872 is the Syracuse University's autonomous system

as11872 = base.createAutonomousSystem(11872)
as11872.createRealWorldRouter('rw-11872-syr').joinNetwork('ix100', '10.100.0.95')


###############################################################################
# Create hybrid AS.
# AS99999 is the emulator's autonomous system that routes the traffics to the real-world internet
as99999 = base.createAutonomousSystem(99999)
as99999.createRealWorldRouter('rw-real-world', prefixes=['0.0.0.0/1', '128.0.0.0/1']).joinNetwork('ix100', '10.100.0.99')
###############################################################################


ebgp.addRsPeer(100, 150)
ebgp.addRsPeer(100, 151)
ebgp.addRsPeer(100, 152)
ebgp.addRsPeer(100, 153)
ebgp.addRsPeer(100, 154)
ebgp.addRsPeer(100, 155)
ebgp.addRsPeer(100, 156)
ebgp.addRsPeer(100, 157)
ebgp.addRsPeer(100, 158)
ebgp.addRsPeer(100, 11872)
ebgp.addRsPeer(100, 99999)

###############################################################################

# Add layers to the emulator
emu.addLayer(base)
emu.addLayer(routing)
emu.addLayer(ebgp)
emu.addLayer(ibgp)
emu.addLayer(ospf)
emu.addLayer(web)
emu.addLayer(etc_hosts)


# Save it to a component file, so it can be used by other emulators
#emu.dump('base-component.bin')

# Uncomment the following if you want to generate the final emulation files
emu.render()
#print(dns.getZone('.').getRecords())
emu.compile(Docker(), './output', override=True)

