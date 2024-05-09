#!/usr/bin/env python3
# encoding: utf-8

from seedemu.compiler import Docker
from seedemu.core import Emulator, Binding, Filter
from seedemu.services import TrafficService, TrafficServiceType
from seedemu.layers import EtcHosts
from examples.internet.B00_mini_internet import mini_internet

def run(dumpfile=None):

    emu = Emulator()

    # Run the pre-built components
    mini_internet.run(dumpfile='./base-internet.bin')
    
    # Load and merge the pre-built components 
    emu.load('./base-internet.bin')
    
    base = emu.getLayer('Base')

    etc_hosts = EtcHosts()

    traffic_service = TrafficService()
    traffic_service.install('hybrid-receiver', TrafficServiceType.HYBRID_RECEIVER)
    traffic_service.install('hybrid-generator', TrafficServiceType.HYBRID_GENERATOR).addReceivers(hosts=["hybrid-receiver"])

    # Add hosts to AS-150
    as150 = base.getAutonomousSystem(150)
    as150.createHost('hybrid-generator').joinNetwork('net0')


    # Add hosts to AS-162 
    as162 = base.getAutonomousSystem(162)
    as162.createHost('hybrid-receiver').joinNetwork('net0')

    # Binding virtual nodes to physical nodes
    emu.addBinding(Binding('hybrid-generator', filter = Filter(asn = 150, nodeName='hybrid-generator')))
    emu.addBinding(Binding('hybrid-receiver', filter = Filter(asn = 162, nodeName='hybrid-receiver')))

    # Add the layers
    emu.addLayer(traffic_service)
    emu.addLayer(etc_hosts)
    
    if dumpfile is not None:
       # Save it to a file, so it can be used by other emulators
       emu.dump(dumpfile)
    else:
       # Rendering compilation 
       emu.render()
       emu.compile(Docker(), './output', override=True)

if __name__ == "__main__":
    run()