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


#Install root server
dns.install('a-root-server').addZone(dns.getZone('.'))
dns.install('b-root-server').addZone(dns.getZone('.'))

#Install COM TLD server
dns.install('a-com-server').addZone(dns.getZone('com.'))

#Install NET TLD server
dns.install('a-net-server').addZone(dns.getZone('net.'))

#Install EDU TLD server
dns.install('a-edu-server').addZone(dns.getZone('edu.'))

#Install CN TLD server
dns.install('a-cn-server').addZone(dns.getZone('cn.'))

#Install GOV TLD server
dns.install('a-gov-server').addZone(dns.getZone('gov.'))


#Add some default record
twitter_com = dns.getZone('twitter.com.')
google_com = dns.getZone('google.com.')
facebook_com = dns.getZone('facebook.com.')
syr_edu = dns.getZone('syr.edu.')
weibo_cn = dns.getZone('weibo.cn.')
php_net = dns.getZone('php.net.')
us_gov = dns.getZone('us.gov.')

twitter_com.addRecord('@ A 1.1.1.1')
twitter_com.addRecord('www A 1.1.1.1')
google_com.addRecord('@ A 2.2.2.2')
google_com.addRecord('www A 2.2.2.2')
facebook_com.addRecord('@ A 3.3.3.3')
facebook_com.addRecord('www A 3.3.3.3')
syr_edu.addRecord('@ A 128.230.18.63')
syr_edu.addRecord('www A 128.230.18.63')
weibo_cn.addRecord('@ A 4.4.4.4')
weibo_cn.addRecord('www A 4.4.4.4')
php_net.addRecord('@ A 5.5.5.5')
php_net.addRecord('www A 5.5.5.5')
us_gov.addRecord('@ A 6.6.6.6')
us_gov.addRecord('www A 6.6.6.6')


#Install DNSPOD servers
dns.install('ns1-dnspod.com').addZone(twitter_com)
dns.install('ns1-dnspod.com').addZone(google_com)
dns.install('ns1-dnspod.com').addZone(facebook_com)

dns.install('ns2-dnspod.com').addZone(syr_edu)
dns.install('ns2-dnspod.com').addZone(us_gov)

dns.install('ns2-dnspod.com').addZone(weibo_cn)
dns.install('ns3-dnspod.com').addZone(php_net)

#Install local DNS
ldns.install('local-dns-1')

sim.addLayer(dns)
sim.addLayer(ldns)

sim.dump('dns-component.bin')