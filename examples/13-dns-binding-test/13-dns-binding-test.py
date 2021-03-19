#!/usr/bin/env python
# encoding: utf-8
# __author__ = 'Demon'


from seedsim.layers import Base, Routing, Ebgp, Dnssec
from seedsim.services import DomainNameService, DomainNameCachingService, WebService
from seedsim.core import Simulator, Binding, Filter, Action
from seedsim.mergers import DEFAULT_MERGERS
from seedsim.hooks import ResolvConfHook
from seedsim.compiler import Docker


simA = Simulator()
simB = Simulator()
simC = Simulator()

simA.load('dns-component.bin')
simB.load('base-component.bin')
simC.load('dns-component-1.bin')

merged = simA.merge(simB, DEFAULT_MERGERS)#.merge(simC, DEFAULT_MERGERS)

merged = merged.merge(simC, DEFAULT_MERGERS)

#dns: DomainNameService = simA.getLayer('DomainNameService')
#ldns: DomainNameCachingService = simA.getLayer('DomainNameCachingService')

#Add binding for First Component
merged.addBinding(Binding('a-root-server', filter = Filter(asn = 150)))
merged.addBinding(Binding('b-root-server', filter = Filter(asn = 150)))
merged.addBinding(Binding('a-com-server', filter = Filter(asn = 151)))
merged.addBinding(Binding('a-net-server', filter = Filter(asn = 153)))
merged.addBinding(Binding('a-gov-server', filter = Filter(asn = 152), action=Action.LAST))
merged.addBinding(Binding('a-edu-server', filter = Filter(prefix = "10.160.0.0/24")))
merged.addBinding(Binding('a-cn-server', filter = Filter()))
merged.addBinding(Binding('ns[1-3]-dnspod.com', filter = Filter(custom = lambda vnode_name, node: node.getAsn() == 154 )))
merged.addBinding(Binding('local-dns-\w', filter = Filter(asn=152), action=Action.FIRST))

#Add binding for Second Component
merged.addBinding(Binding('a-uk-server', filter = Filter()))
merged.addBinding(Binding('a-com-uk-server', filter = Filter()))
merged.addBinding(Binding('a-net-uk-server', filter = Filter()))
merged.addBinding(Binding('godaddy', filter = Filter()))


merged.addHook(ResolvConfHook(['10.152.0.71']))
# merged.addLayer(dns)
# merged.addLayer(ldns)


merged.render()

###############################################################################

merged.compile(Docker(), './dns-binding')