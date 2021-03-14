#!/usr/bin/env python
# encoding: utf-8
# __author__ = 'Demon'


from seedsim.layers import Base, Routing, Ebgp, Dnssec
from seedsim.services import DomainNameService, DomainNameCachingService, WebService
from seedsim.core import Simulator, Binding, Filter, Action
from seedsim.hooks import ResolvConfHook
from seedsim.compiler import Docker


simA = Simulator()
simB = Simulator()

simA.load('dns-component.bin')
simB.load('base-component.bin')

dns: DomainNameService = simA.getLayer('DomainNameService')
ldns: DomainNameCachingService = simA.getLayer('DomainNameCachingService')

root_zones = dns.getZoneServerNames('.')

simB.addBinding(Binding('a-root-server', filter = Filter(asn = 150)))
simB.addBinding(Binding('a-com-server', filter = Filter(asn = 151)))
simB.addBinding(Binding('a-net-server', filter = Filter(asn = 153)))
simB.addBinding(Binding('a-gov-server', filter = Filter(asn = 152), action=Action.LAST))
simB.addBinding(Binding('a-edu-server', filter = Filter(prefix = "10.160.0.0/24")))
simB.addBinding(Binding('a-cn-server', filter = Filter()))
simB.addBinding(Binding('ns[1-3]-dnspod.com', filter = Filter(custom = lambda vnode_name, node: node.getAsn() == 154 )))
simB.addBinding(Binding('local-dns-\w', filter = Filter(asn=152), action=Action.FIRST))

simB.addLayer(dns)
simB.addLayer(ldns)

simB.addHook(ResolvConfHook(['10.152.0.71']))

simB.render()

###############################################################################

simB.compile(Docker(), './dns-binding')