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
    
    base = emu.getLayer("Base")

    etc_hosts = EtcHosts()

    traffic_service = TrafficService()
    traffic_service.install("iperf-receiver-1", TrafficServiceType.IPERF_RECEIVER, log_file="/root/iperf3_receiver.log")
    traffic_service.install("iperf-receiver-2", TrafficServiceType.IPERF_RECEIVER, log_file="/root/iperf3_receiver.log")
    traffic_service.install(
        "iperf-generator",
        TrafficServiceType.IPERF_GENERATOR,
        log_file="/root/iperf3_generator.log",
        protocol="TCP",
        duration=600,
        rate=0,
        extra_options="--debug",
    ).addReceivers(hosts=["iperf-receiver-1", "iperf-receiver-2"])


    # Add hosts to AS-150
    as150 = base.getAutonomousSystem(150)
    as150.createHost("iperf-generator").joinNetwork("net0")

    # Add hosts to AS-162
    as162 = base.getAutonomousSystem(162)
    as162.createHost("iperf-receiver-1").joinNetwork("net0")

    # Add hosts to AS-171
    as171 = base.getAutonomousSystem(171)
    as171.createHost("iperf-receiver-2").joinNetwork("net0")

    # Binding virtual nodes to physical nodes
    emu.addBinding(
        Binding("iperf-generator", filter=Filter(asn=150, nodeName="iperf-generator"))
    )
    emu.addBinding(
        Binding("iperf-receiver-1", filter=Filter(asn=162, nodeName="iperf-receiver-1"))
    )
    emu.addBinding(
        Binding("iperf-receiver-2", filter=Filter(asn=171, nodeName="iperf-receiver-2"))
    )

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
