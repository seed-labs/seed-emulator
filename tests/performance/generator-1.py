#!/usr/bin/env python3

from seedemu import *
from typing import List, Dict, Set
from ipaddress import IPv4Network
from math import ceil
from random import choice

import argparse

def createEmulation(asCount: int, asEachIx: int, routerEachAs: int, hostEachNet: int, hostService: Service, hostCommands: List[str], hostFiles: List[File], yes: bool) -> Emulator:
    asNetworkPool = IPv4Network('16.0.0.0/4').subnets(new_prefix = 16)
    linkNetworkPool = IPv4Network('32.0.0.0/4').subnets(new_prefix = 24)
    ixNetworkPool = IPv4Network('100.0.0.0/13').subnets(new_prefix = 24)
    ixCount = ceil(asCount / asEachIx)

    rtrCount = asCount * routerEachAs
    hostCount = asCount * routerEachAs * hostEachNet + ixCount
    netCount = asCount * (routerEachAs + routerEachAs - 1) + ixCount

    print('Total nodes: {} ({} routers, {} hosts)'.format(rtrCount + hostCount, rtrCount, hostCount))
    print('Total nets: {}'.format(netCount))

    if not yes:
        input('Press [Enter] to continue, or ^C to exit ')

    aac = AddressAssignmentConstraint(hostStart = 2, hostEnd = 255, hostStep = 1, routerStart = 1, routerEnd = 2, routerStep = 0)

    assert asCount <= 4096, 'too many ASes.'
    assert ixCount <= 2048, 'too many IXs.'
    assert hostEachNet <= 253, 'too many hosts.'
    assert routerEachAs <= 256, 'too many routers.'

    emu = Emulator()
    emu.addLayer(Routing())
    emu.addLayer(Ibgp())
    emu.addLayer(Ospf())

    if hostService != None:
        emu.addLayer(hostService)

    base = Base()
    ebgp = Ebgp()

    ases: Dict[int, AutonomousSystem] = {}
    asRouters: Dict[int, List[Router]] = {}
    hosts: List[Node] = []
    routerAddresses: List[str] = []

    # create ASes
    for i in range(0, asCount):
        asn = 5000 + i
        asObject = base.createAutonomousSystem(asn)
        
        ases[asn] = asObject
        asRouters[asn] = []

        localNetPool = next(asNetworkPool).subnets(new_prefix = 24)

        # create host networks
        for j in range(0, routerEachAs):
            prefix = next(localNetPool)
            netname = 'net{}'.format(j)
            asObject.createNetwork(netname, str(prefix), aac = aac)

            router = asObject.createRouter('router{}'.format(j))
            router.joinNetwork(netname)
            routerAddresses.append(str(next(prefix.hosts())))

            asRouters[asn].append(router)

            # create hosts
            for k in range(0, hostEachNet):
                hostname = 'host{}_{}'.format(j, k)
                host = asObject.createHost(hostname)
                host.joinNetwork(netname)

                if hostService != None:
                    vnode = 'as{}_{}'.format(asn, hostname)
                    hostService.install(vnode)
                    emu.addBinding(Binding(vnode, action = Action.FIRST, filter = Filter(asn = asn, nodeName = hostname)))

                hosts.append(host)

                for file in hostFiles:
                    path, body = file.get()
                    host.setFile(path, body)
        
        routers = asRouters[asn]

        # link routers        
        for i in range (1, len(routers)):
            linkname = 'link_{}_{}'.format(i - 1, i)
            asObject.createNetwork(linkname, str(next(linkNetworkPool)))
            routers[i - 1].joinNetwork(linkname)
            routers[i].joinNetwork(linkname)

    lastRouter = None
    asnPtr = 5000

    ixMembers: Dict[int, Set[int]] = {}

    # create and join exchanges
    for ix in range(1, ixCount + 1):
        ixPrefix = next(ixNetworkPool)
        ixHosts = ixPrefix.hosts()
        ixNetName = base.createInternetExchange(ix, str(ixPrefix), rsAddress = str(next(ixHosts))).getPeeringLan().getName()
        ixMembers[ix] = set()

        if lastRouter != None:
            ixMembers[ix].add(lastRouter.getAsn())
            lastRouter.joinNetwork(ixNetName, str(next(ixHosts)))

        for i in range(1 if lastRouter != None else 0, asEachIx):
            router = asRouters[asnPtr][0]
            ixMembers[ix].add(router.getAsn())
            router.joinNetwork(ixNetName, str(next(ixHosts)))

            asnPtr += 1
            lastRouter = router

    # peerings
    for ix, members in ixMembers.items():
        for a in members:
            for b in members:
                peers = ebgp.getPrivatePeerings().keys()
                if a!= b and (ix, a, b) not in peers and (ix, b, a) not in peers:
                    ebgp.addPrivatePeering(ix, a, b, PeerRelationship.Unfiltered)

    # host commands
    for host in hosts:
        for cmd in hostCommands:
            host.appendStartCommand(cmd.format(
                randomRouterIp = choice(routerAddresses)
            ), True)

    emu.addLayer(base)
    emu.addLayer(ebgp)

    return emu

def main():
    parser = argparse.ArgumentParser(description='Make an emulation with lots of networks.')
    parser.add_argument('--ases', help = 'Number of ASes to generate.', required = True)
    parser.add_argument('--ixs', help = 'Number of ASes in each IX.', required = True)
    parser.add_argument('--routers', help = 'Number of routers in each AS.', required = True)
    parser.add_argument('--hosts', help = 'Number of hosts in each AS.', required = True)
    parser.add_argument('--web', help = 'Install web server on all hosts.', action = 'store_true')
    parser.add_argument('--ping', help = 'Have all hosts randomly ping some router.', action = 'store_true')
    parser.add_argument('--outdir', help = 'Output directory.', required = True)
    parser.add_argument('--yes', help = 'Do not prompt for confirmation.', action = 'store_true')

    args = parser.parse_args()

    emu = createEmulation(int(args.ases), int(args.ixs), int(args.routers), int(args.hosts), WebService() if args.web else None, ['{{ while true; do ping {randomRouterIp}; done }}'] if args.ping else [], [], args.yes)
    
    emu.render()
    emu.compile(Docker(selfManagedNetwork = True), args.outdir)

if __name__ == '__main__':
    main()
