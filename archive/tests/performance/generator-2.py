#!/usr/bin/env python3

from seedemu import *
from typing import List
import argparse

TEST_SCRIPT = '''\
#!/bin/bash

# wait for b to go online (mostly waiting for routing convergence).
while ! ping -t255 -c10 {remote}; do sleep 1; done

ping -c1000 -i.01 {remote} > /ping.txt
while ! iperf3 -c {remote} -t 60 > /iperf-tx.txt; do sleep 1; done
while ! iperf3 -Rc {remote} -t 60 > /iperf-rx.txt; do sleep 1; done

touch /done
'''

def createEmulation(asCount: int, chainLength: int) -> Emulator:
    assert chainLength < 254, 'chain too long.'
    emu = Emulator()
    emu.addLayer(Routing())
    emu.addLayer(Ibgp())
    emu.addLayer(Ospf())

    base = Base()
    emu.addLayer(base)

    for asnOffset in range(0, asCount):
        asn = 150 + asnOffset

        asObject = base.createAutonomousSystem(asn)

        nets: List[Network] = []
        lastNetName: str = None

        for netId in range(0, chainLength):
            netName = 'net{}'.format(netId)

            net = asObject.createNetwork(netName)
            nets.append(net)
            
            if lastNetName != None:
                thisRouter = asObject.createRouter('router{}'.format(netId))

                thisRouter.joinNetwork(netName)
                thisRouter.joinNetwork(lastNetName)

            lastNetName = netName

        hostA = asObject.createHost('a')
        hostB = asObject.createHost('b')

        netA = nets[0]
        netB = nets[-1]

        addressA = netA.getPrefix()[100]
        addressB = netB.getPrefix()[100]

        hostA.joinNetwork(nets[0].getName(), addressA)
        hostB.joinNetwork(nets[-1].getName(), addressB)

        hostA.addSoftware('iperf3')
        hostB.addSoftware('iperf3')

        hostA.appendStartCommand('sysctl -w net.ipv4.ip_default_ttl=255')
        hostB.appendStartCommand('sysctl -w net.ipv4.ip_default_ttl=255')

        hostB.appendStartCommand('iperf3 -s -D')

        hostA.setFile('/test', TEST_SCRIPT.format(remote = addressB))
        hostA.appendStartCommand('chmod +x /test')
        hostA.appendStartCommand('/test', True)
     
    return emu

    
def main():
    parser = argparse.ArgumentParser(description='Make an emulation with a ASes that has long hops and run ping and iperf across hosts.')
    parser.add_argument('--ases', help = 'Number of ASes to generate.', required = True)
    parser.add_argument('--hops', help = 'Number of hops between two hosts.', required = True)
    parser.add_argument('--outdir', help = 'Output directory.', required = True)

    args = parser.parse_args()

    emu = createEmulation(int(args.ases), int(args.hops))
    
    emu.render()
    emu.compile(Docker(selfManagedNetwork = True), args.outdir)

if __name__ == '__main__':
    main()
