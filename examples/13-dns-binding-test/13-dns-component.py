#!/usr/bin/env python
# encoding: utf-8
# __author__ = 'Demon'

from seedsim.layers import Base, Routing, Ebgp, Dnssec
from seedsim.services import DomainNameService, DomainNameCachingService, WebService
from seedsim.core import Simulator, Binding, Filter
from seedsim.compiler import Docker


sim = Simulator()

dns = DomainNameService()
ldns = DomainNameCachingService()


#Install root servers
dns.install('a-root-server').addZone(dns.getZone('.'))
dns.install('b-root-server').addZone(dns.getZone('.'))
dns.install('c-root-server').addZone(dns.getZone('.'))
dns.install('d-root-server').addZone(dns.getZone('.'))

#Install COM TLD servers
dns.install('a-gtld-servers.net').addZone(dns.getZone('com.'))
dns.install('b-gtld-servers.net').addZone(dns.getZone('com.'))
dns.install('c-gtld-servers.net').addZone(dns.getZone('com.'))

#Install NET TLD servers
dns.install('d-gtld-servers.net').addZone(dns.getZone('net.'))
dns.install('e-gtld-servers.net').addZone(dns.getZone('net.'))
dns.install('f-gtld-servers.net').addZone(dns.getZone('net.'))

#Install EDU TLD servers
dns.install('a-edu-servers.net').addZone(dns.getZone('edu.'))
dns.install('b-edu-servers.net').addZone(dns.getZone('edu.'))
dns.install('c-edu-servers.net').addZone(dns.getZone('edu.'))

#Install CN TLD servers
dns.install('a-dns.cn').addZone(dns.getZone('cn.'))
dns.install('b-dns.cn').addZone(dns.getZone('cn.'))
dns.install('c-dns.cn').addZone(dns.getZone('cn.'))

#Install DNSPOD servers
dns.install('ns1-dnspod.com').addZone(dns.getZone('example.com.'))
dns.install('ns2-dnspod.com').addZone(dns.getZone('tencent.com.'))
dns.install('ns3-dnspod.com').addZone(dns.getZone('facebook.com.'))

#Install local DNS
ldns.install('local-dns-1')
ldns.install('local-dns-2')
ldns.install('local-dns-3')

sim.addLayer(dns)
sim.addLayer(ldns)

sim.dump('dns-component.bin')