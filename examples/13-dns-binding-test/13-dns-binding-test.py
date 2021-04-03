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
merged.addBinding(Binding('.*-root-server', filter = Filter(asn = 150), action=Action.FIRST))
merged.addBinding(Binding('.*-com-server', filter = Filter(asn = 151), action=Action.FIRST))
merged.addBinding(Binding('a-net-server', filter = Filter(asn = 152), action=Action.FIRST))
merged.addBinding(Binding('a-gov-server', filter = Filter(asn = 153), action=Action.FIRST))
merged.addBinding(Binding('a-edu-server', filter = Filter(asn=161, nodeName="host3")))
merged.addBinding(Binding('a-cn-server', filter = Filter(asn=161, nodeName="host1")))
merged.addBinding(Binding('ns[1-3]-dnspod.com', filter = Filter(custom = lambda vnode_name, node: node.getAsn() == 154 )))


#Add bindings for local dns:
merged.addBinding(Binding('local-dns-150', filter = Filter(asn=150, nodeName="ldns")))
merged.addBinding(Binding('local-dns-151', filter = Filter(asn=151, nodeName="ldns")))
merged.addBinding(Binding('local-dns-152', filter = Filter(asn=152, nodeName="ldns")))
merged.addBinding(Binding('local-dns-153', filter = Filter(asn=153, nodeName="ldns")))
merged.addBinding(Binding('local-dns-154', filter = Filter(asn=154, nodeName="ldns")))
merged.addBinding(Binding('local-dns-160', filter = Filter(asn=160, nodeName="ldns")))
merged.addBinding(Binding('local-dns-161', filter = Filter(asn=161, nodeName="ldns")))

#Add binding for Second Component
merged.addBinding(Binding('a-uk-server', filter = Filter(asn=160), action=Action.FIRST))
merged.addBinding(Binding('a-com-uk-server', filter = Filter(asn=160, nodeName="host1")))
merged.addBinding(Binding('a-net-uk-server', filter = Filter(asn=160, nodeName="host2")))
merged.addBinding(Binding('godaddy', filter = Filter(asn=160, nodeName="host3")))

#binding for resolveToVnode
merged.addBinding(Binding('www-twitter-com-web', filter = Filter(asn=152, nodeName="host0")))
merged.addBinding(Binding('www-google-com-web', filter = Filter(asn=150, nodeName="host0")))
merged.addBinding(Binding('www-facebook-com-web', filter = Filter(asn=152, nodeName="host1")))
merged.addBinding(Binding('www-syr-edu-web', filter = Filter(asn=152, nodeName="host2")))


merged.addHook(ResolvConfHook(['10.150.0.77','10.151.0.77','10.152.0.77',
                            '10.153.0.77','10.154.0.77','10.160.0.77','10.161.0.77']))
merged.render()

###############################################################################

merged.compile(Docker(), './dns-binding')