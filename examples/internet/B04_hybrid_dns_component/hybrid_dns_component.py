#!/usr/bin/env python3
# encoding: utf-8

from seedemu import *

def run(dumpfile = None):
    emu = Emulator()

    # DNS
    ###########################################################
    # Create a DNS layer
    dns = DomainNameService()

    # Create a nameserver for the root zone. 
    # Make it shadow the real root zone. 
    dns.install('a-root-server').addZone('.').setRealRootNS()

    # Create nameservers for second-level zones
    dns.install('ns-twitter-com').addZone('twitter.com.')
    dns.install('ns-google-com').addZone('google.com.')

    # Add records to zones 
    dns.getZone('twitter.com.').addRecord('@ A 1.1.1.1')  
    dns.getZone('google.com.').addRecord('@ A 2.2.2.2') 

    # Customize the display names (for visualization purpose)
    emu.getVirtualNode('a-root-server').setDisplayName('Root-A')
    emu.getVirtualNode('ns-twitter-com').setDisplayName('twitter.com')
    emu.getVirtualNode('ns-google-com').setDisplayName('google.com')

    ###########################################################
    emu.addLayer(dns)
    if dumpfile is not None:
        emu.dump(dumpfile)
    else:
        emu.dump('hybrid_dns_component.bin')
        
if __name__ == "__main__":
    run()
