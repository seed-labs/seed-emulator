#!/usr/bin/env python3
# encoding: utf-8

from seedemu.core import Emulator
from seedemu.services import DomainNameService, DomainNameCachingService

emu = Emulator()

###########################################################
# Create a DNS layer
dns = DomainNameService()

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

# Customize the display names (for visualization purpose)
emu.getVirtualNode('a-root-server').setDisplayName('Root-A')
emu.getVirtualNode('b-root-server').setDisplayName('Root-B')
emu.getVirtualNode('a-com-server').setDisplayName('COM-A')
emu.getVirtualNode('b-com-server').setDisplayName('COM-B')
emu.getVirtualNode('a-net-server').setDisplayName('NET')
emu.getVirtualNode('a-edu-server').setDisplayName('EDU')
emu.getVirtualNode('a-cn-server').setDisplayName('CN-A')
emu.getVirtualNode('b-cn-server').setDisplayName('CN-B')
emu.getVirtualNode('ns-twitter-com').setDisplayName('twitter.com')
emu.getVirtualNode('ns-google-com').setDisplayName('google.com')
emu.getVirtualNode('ns-example-net').setDisplayName('example.net')
emu.getVirtualNode('ns-syr-edu').setDisplayName('syr.edu')
emu.getVirtualNode('ns-weibo-cn').setDisplayName('weibo.cn')


###########################################################
emu.addLayer(dns)
emu.dump('dns-component.bin')
