#!/usr/bin/env python
# encoding: utf-8
# __author__ = 'Demon'

from seedsim.services import DomainNameService, DomainNameCachingService
from seedsim.core import Simulator


sim = Simulator()

dns = DomainNameService()
ldns = DomainNameCachingService()

#Install UK TLD server
dns.install('a-uk-server').addZone('uk.')

#Install UK sub zones
dns.install('a-com-uk-server').addZone('com.uk.')
dns.install('a-net-uk-server').addZone('net.uk.')

#Add some default record
com_uk = dns.getZone('company.com.uk.')
net_uk = dns.getZone('example.net.uk.')

com_uk.addRecord('@ A 1.1.1.1')
com_uk.addRecord('www A 1.1.1.1')

net_uk.addRecord('@ A 1.1.1.1')
net_uk.addRecord('www A 7.7.7.7')

#CONFLICT TEST
# twitter_com = dns.getZone('www.twitter.com.')
# twitter_com.addRecord('abc A 11.11.11.11')


#Host com_uk and net_uk on godaddy server
dns.install('godaddy').addZone('company.com.uk.')
dns.install('godaddy').addZone('example.net.uk.')
#dns.install('godaddy').addZone(twitter_com)


sim.addLayer(dns)

sim.dump('dns-component-1.bin')



