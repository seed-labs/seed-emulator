#!/usr/bin/env python
# encoding: utf-8
# __author__ = 'Demon'

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

merged = simA.merge(simB, DEFAULT_MERGERS)
merged = merged.merge(simC, DEFAULT_MERGERS)

#Add binding for First Component
merged.addBinding(Binding('.*-root-server', filter = Filter(asn = 150)))
merged.addBinding(Binding('.*-com-server', filter = Filter(asn = 151)))
merged.addBinding(Binding('a-net-server', filter = Filter(asn = 150)))
merged.addBinding(Binding('a-gov-server', filter = Filter(asn = 153), action=Action.LAST))
merged.addBinding(Binding('a-edu-server', filter = Filter(prefix = "10.160.0.0/24")))
merged.addBinding(Binding('a-cn-server', filter = Filter()))
merged.addBinding(Binding('ns[1-3]-dnspod.com', filter = Filter(custom = lambda vnode_name, node: node.getAsn() == 154 )))
merged.addBinding(Binding('local-dns-\w', filter = Filter(asn=152, nodeName="host0")))

#Add binding for Second Component
merged.addBinding(Binding('a-uk-server', filter = Filter()))
merged.addBinding(Binding('a-com-uk-server', filter = Filter()))
merged.addBinding(Binding('a-net-uk-server', filter = Filter()))
merged.addBinding(Binding('godaddy', filter = Filter()))

#binding for resolveToVnode
merged.addBinding(Binding('www-twitter-com-web', filter = Filter(asn=152, nodeName="host0")))
merged.addBinding(Binding('www-google-com-web', filter = Filter(asn=150, nodeName="host0")))
merged.addBinding(Binding('www-facebook-com-web', filter = Filter(asn=152, nodeName="host1")))
merged.addBinding(Binding('www-syr-edu-web', filter = Filter(asn=152, nodeName="host2")))

merged.addHook(ResolvConfHook(['10.152.0.71']))

merged.render()

###############################################################################

merged.compile(Docker(), './dns-binding')