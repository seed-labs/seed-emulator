from seedemu import *

emu = Emulator()

# DNS
###########################################################
# Create a DNS layer
dns = DomainNameService()

# Create two nameservers for the root zone
dns.install('a-root-server').addZone('.').setRealRootNS()  # Master server
#dns.install('b-root-server').addZone('.')               # Slave server

# Create nameservers for TLD and ccTLD zones
#dns.install('a-com-server').addZone('com.')#.setMaster()  
#dns.install('b-com-server').addZone('com.')  
#dns.install('a-edu-server').addZone('edu.')

# Create nameservers for second-level zones
#dns.install('ns-twitter-com').addZone('twitter.com.')
#dns.install('ns-example-net').addZone('example.net.')

# Add records to zones 
#dns.getZone('twitter.com.').addRecord('@ A 1.1.1.1')  
#dns.getZone('example.net.').addRecord('@ A 2.2.2.2') 
#dns.getZone('.').resolveToVnode('ns1.twitter.com.', 'ns-twitter-com').addRecord('twitter.com. NS ns1.twitter.com.')
#dns.getZone('edu.').addRecord('ns1.syr.edu. A 128.230.12.8').addRecord('syr.edu. NS ns1.syr.edu.') 
#dns.getZone('edu.').addRecord('its-ndd-nc-extns-01.syr.edu. A 128.230.100.38').addRecord('syracuse.edu. NS its-ndd-nc-extns-01.syr.edu.') 
#dns.getZone('com.').addRecord('ns1.google.com. A 216.239.32.10').addRecord('google.com. NS ns1.google.com.')

# Customize the display names (for visualization purpose)
emu.getVirtualNode('a-root-server').setDisplayName('Root-A')
#emu.getVirtualNode('b-root-server').setDisplayName('Root-B')
#emu.getVirtualNode('a-com-server').setDisplayName('COM-A')
#emu.getVirtualNode('b-com-server').setDisplayName('COM-B')
#emu.getVirtualNode('a-edu-server').setDisplayName('EDU')
#emu.getVirtualNode('ns-twitter-com').setDisplayName('twitter.com')

###########################################################
emu.addLayer(dns)
emu.dump('hybrid-dns-component.bin')