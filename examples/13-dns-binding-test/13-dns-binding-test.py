#!/usr/bin/env python
# encoding: utf-8
# __author__ = 'Demon'


from seedsim.layers import Base, Routing, Ebgp, Dnssec
from seedsim.services import DomainNameService, DomainNameCachingService, WebService
from seedsim.core import Simulator, Binding, Filter
from seedsim.compiler import Docker


simA = Simulator()
simB = Simulator()

simA.load('dns-component.bin')
simB.load('base-component.bin')

dns: DomainNameService = simA.getLayer('DomainNameService')
ldns: DomainNameCachingService = simA.getLayer('DomainNameCachingService')

root_zones = dns.getZoneServerNames('.')

asn = 150
for zone in root_zones:
    simB.addBinding(Binding(zone, filter = Filter(asn = asn)))
    asn += 1

simB.addBinding(Binding('[a-c].gtld-servers.net', filter = Filter(asn = 161)))
simB.addBinding(Binding('[d-f].gtld-servers.net', filter = Filter(asn = 153)))
simB.addBinding(Binding('.*edu-servers.net', filter = Filter(prefix = "10.160.0.0/24")))
simB.addBinding(Binding('.*dns.cn', filter = Filter()))
simB.addBinding(Binding('ns[1-3]-dnspod.com', filter = Filter(custom = lambda vnode_name, node: node.getAsn() == 154 )))
simB.addBinding(Binding('local-dns-\w', filter = Filter(notServices=['DomainNameService'])))

simB.addLayer(dns)
simB.addLayer(ldns)

simB.render()

###############################################################################

simB.compile(Docker(), './dns-binding')