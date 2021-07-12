#!/usr/bin/env python3
# encoding: utf-8

from seedemu.core import Emulator
from seedemu.services import DomainNameService, DomainNameCachingService

emu = Emulator()
dns = DomainNameService()

###########################################################
# Create two root servers
dns.install('a-root-server').addZone('.').setMaster()   # Master server
dns.install('b-root-server').addZone('.')               # Slave server

# Create generic TLD servers
dns.install('a-com-server').addZone('com.').setMaster()  
dns.install('b-com-server').addZone('com.')  

dns.install('a-net-server').addZone('net.')
dns.install('a-edu-server').addZone('edu.')

# Create country-code TLD servers (ccTLD)
dns.install('a-cn-server').addZone('cn.').setMaster() 
dns.install('b-cn-server').addZone('cn.') 

# Create domain nameservers
dns.getZone('twitter.com.').addRecord('@ A 1.1.1.1')  \
         .resolveToVnode("www", "www-twitter-com-web")

dns.getZone('google.com.').addRecord('@ A 2.2.2.2') \
         .resolveToVnode('www','www-google-com-web')

dns.getZone('facebook.com.').addRecord('@ A 3.3.3.3') \
         .resolveToVnode('www', 'www-facebook-com-web')

dns.getZone('syr.edu.').addRecord('@ A 128.230.18.63') \
         .resolveToVnode('www', 'www-syr-edu-web')

dns.getZone('weibo.cn.').addRecord('@ A 4.4.4.4').addRecord('www A 4.4.4.4')



emu.addLayer(dns)
emu.dump('dns-component.bin')
