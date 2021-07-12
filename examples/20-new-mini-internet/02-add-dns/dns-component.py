#!/usr/bin/env python3
# encoding: utf-8

from seedemu.core import Emulator
from seedemu.services import DomainNameService, DomainNameCachingService

emu = Emulator()
dns = DomainNameService()

###########################################################
# Create two nameservers for the root zone
dns.install('a-root-server').addZone('.').setMaster()   # Master server
dns.install('b-root-server').addZone('.')               # Slave server

# Create nameservers for TLD and ccTLD zones
dns.install('a-com-server').addZone('com.').setMaster()  
dns.install('b-com-server').addZone('com.')  
dns.install('a-net-server').addZone('net.')
dns.install('a-edu-server').addZone('edu.')
dns.install('a-cn-server').addZone('cn.').setMaster() 
dns.install('b-cn-server').addZone('cn.') 

# Create nameservers for second-level zones
dns.install('ns-twitter-com').addZone('twitter.com.')
dns.install('ns-google-com').addZone('google.com.')
dns.install('ns-example-net').addZone('example.net.')
dns.install('ns-syr-edu').addZone('syr.edu.')
dns.install('ns-weibo-cn').addZone('weibo.cn.')

# Add records to zones 
dns.getZone('twitter.com.').addRecord('@ A 1.1.1.1')  
dns.getZone('google.com.').addRecord('@ A 2.2.2.2') 
dns.getZone('example.net.').addRecord('@ A 3.3.3.3') 
dns.getZone('syr.edu.').addRecord('@ A 128.230.18.63') 
dns.getZone('weibo.cn.').addRecord('@ A 5.5.5.5').addRecord('www A 5.5.5.6')

###########################################################
emu.addLayer(dns)
emu.dump('dns-component.bin')
