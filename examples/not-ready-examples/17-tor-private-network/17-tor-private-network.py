#!/usr/bin/env python
# encoding: utf-8
# __author__ = 'Demon'

from seedemu.core import Emulator, Binding, Filter, Action
from seedemu.compiler import Docker
from seedemu.services import TorService, TorNodeType
from seedemu.services import WebService


sim = Emulator()
tor = TorService()
web = WebService()

sim.load('base-component.bin')

#Create DA node, CLIENT node, RELAY node and EXIT node
tor.install("da").setRole(TorNodeType.DA)
tor.install("da1").setRole(TorNodeType.DA)
tor.install("da2").setRole(TorNodeType.DA)
tor.install("client").setRole(TorNodeType.CLIENT)
tor.install("relay").setRole(TorNodeType.RELAY)
tor.install("relay1").setRole(TorNodeType.RELAY)
tor.install("exit").setRole(TorNodeType.EXIT)

#Create a webserver for verifying tor network
web.install("webserver")

#Create Tor hidden service, the hs node will point to webserver
onion_service = tor.install("hs")
onion_service.setRole(TorNodeType.HS)
onion_service.linkByVnode("webserver", 80)


#Add bindings
sim.addBinding(Binding('da*', filter = Filter(asn = 150)))
sim.addBinding(Binding('client', filter = Filter(asn = 151), action=Action.FIRST))
sim.addBinding(Binding('relay*', filter = Filter(asn = 152)))
sim.addBinding(Binding('exit', filter = Filter(asn = 153)))
sim.addBinding(Binding('hs', filter = Filter(asn = 154)))
sim.addBinding(Binding('webserver', filter = Filter(asn = 160)))

sim.addLayer(tor)
sim.addLayer(web)
sim.render()

sim.compile(Docker(), './tor-private-network')