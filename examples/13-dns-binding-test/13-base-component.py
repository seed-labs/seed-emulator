#!/usr/bin/env python
# encoding: utf-8
# __author__ = 'Demon'
from seedsim.layers import Base, Routing, Ebgp, PeerRelationship, Ibgp, Ospf
from seedsim.compiler import Docker
from seedsim.services import DomainNameCachingService
from seedsim.core import Simulator, Binding, Filter, Node
from typing import List

sim = Simulator()

base = Base()
routing = Routing()
ebgp = Ebgp()
ibgp = Ibgp()
ospf = Ospf()
ldns = DomainNameCachingService()


def setup_resolve_conf(hosts: List[ Node ], ldns_ip: str):
    #Setup local dns IP for hosts
    for h in hosts:
        h.appendStartCommand(': > /etc/resolv.conf')
        h.appendStartCommand('echo "nameserver {}" >> /etc/resolv.conf'.format(ldns_ip))

def make_stub_as(asn: int, exchange: str):
    stub_as = base.createAutonomousSystem(asn)
    host = stub_as.createHost('host0')
    host1 = stub_as.createHost('host1')
    host2 = stub_as.createHost('host2')
    host3 = stub_as.createHost('host3')
    host4 = stub_as.createHost('host4')
    host5 = stub_as.createHost('host5')
    ldns_host = stub_as.createHost('ldns') #used for local dns service
    ldns_ip = "10.{}.0.77".format(asn)
    setup_resolve_conf([host,host1,host2,host3,host4,host5,ldns_host], ldns_ip)# Setup resolve.conf for hosts.

    router = stub_as.createRouter('router0')
    net = stub_as.createNetwork('net0')

    routing.addDirect(asn, 'net0')
    router.joinNetwork('net0')
    host.joinNetwork('net0')
    host1.joinNetwork('net0')
    host2.joinNetwork('net0')
    host3.joinNetwork('net0')
    host4.joinNetwork('net0')
    host5.joinNetwork('net0')
    ldns_host.joinNetwork('net0')

    router.joinNetwork(exchange)

##############Install local DNS###############################################
ldns.install('local-dns-150')
ldns.install('local-dns-151')
ldns.install('local-dns-152')
ldns.install('local-dns-153')
ldns.install('local-dns-154')
ldns.install('local-dns-160')
ldns.install('local-dns-161')

#Add bindings for local dns:
sim.addBinding(Binding('local-dns-150', filter = Filter(asn=150, nodeName="ldns")))
sim.addBinding(Binding('local-dns-151', filter = Filter(asn=151, nodeName="ldns")))
sim.addBinding(Binding('local-dns-152', filter = Filter(asn=152, nodeName="ldns")))
sim.addBinding(Binding('local-dns-153', filter = Filter(asn=153, nodeName="ldns")))
sim.addBinding(Binding('local-dns-154', filter = Filter(asn=154, nodeName="ldns")))
sim.addBinding(Binding('local-dns-160', filter = Filter(asn=160, nodeName="ldns")))
sim.addBinding(Binding('local-dns-161', filter = Filter(asn=161, nodeName="ldns")))

##############################################################################
base.createInternetExchange(100)
base.createInternetExchange(101)
base.createInternetExchange(102)

make_stub_as(150, 'ix100')
make_stub_as(151, 'ix100')

make_stub_as(152, 'ix101')
make_stub_as(153, 'ix101')
make_stub_as(154, 'ix101')

make_stub_as(160, 'ix102')
make_stub_as(161, 'ix102')

###############################################################################

as2 = base.createAutonomousSystem(2)

as2_100 = as2.createRouter('r0')
as2_101 = as2.createRouter('r1')
as2_102 = as2.createRouter('r2')

as2_100.joinNetwork('ix100')
as2_101.joinNetwork('ix101')
as2_102.joinNetwork('ix102')

as2_net_100_101 = as2.createNetwork('n01')
as2_net_101_102 = as2.createNetwork('n12')
as2_net_102_100 = as2.createNetwork('n20')

routing.addDirect(2, 'n01')
routing.addDirect(2, 'n12')
routing.addDirect(2, 'n20')

as2_100.joinNetwork('n01')
as2_101.joinNetwork('n01')

as2_101.joinNetwork('n12')
as2_102.joinNetwork('n12')

as2_102.joinNetwork('n20')
as2_100.joinNetwork('n20')

###############################################################################

as3 = base.createAutonomousSystem(3)

as3_101 = as3.createRouter('r1')
as3_102 = as3.createRouter('r2')

as3_101.joinNetwork('ix101')
as3_102.joinNetwork('ix102')

as3_net_101_102 = as3.createNetwork('n12')

routing.addDirect(2, 'n12')

as3_101.joinNetwork('n12')
as3_102.joinNetwork('n12')

###############################################################################

ebgp.addPrivatePeering(100, 2, 150, PeerRelationship.Provider)
ebgp.addPrivatePeering(100, 150, 151, PeerRelationship.Provider)

ebgp.addPrivatePeering(101, 2, 3, PeerRelationship.Provider)
ebgp.addPrivatePeering(101, 2, 152, PeerRelationship.Provider)
ebgp.addPrivatePeering(101, 3, 152, PeerRelationship.Provider)
ebgp.addPrivatePeering(101, 2, 153, PeerRelationship.Provider)
ebgp.addPrivatePeering(101, 3, 153, PeerRelationship.Provider)
ebgp.addPrivatePeering(101, 2, 154, PeerRelationship.Provider)
ebgp.addPrivatePeering(101, 3, 154, PeerRelationship.Provider)


ebgp.addPrivatePeering(102, 2, 160, PeerRelationship.Provider)
ebgp.addPrivatePeering(102, 3, 160, PeerRelationship.Provider)
ebgp.addPrivatePeering(102, 3, 161, PeerRelationship.Provider)

###############################################################################


sim.addLayer(base)
sim.addLayer(routing)
sim.addLayer(ebgp)
sim.addLayer(ibgp)
sim.addLayer(ospf)
sim.addLayer(ldns)

sim.dump('base-component.bin')