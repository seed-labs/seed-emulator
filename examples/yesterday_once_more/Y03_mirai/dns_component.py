#!/usr/bin/env python3
# encoding: utf-8

from seedemu.core import Emulator
from seedemu.services import DomainNameService, DomainNameCachingService


def run(dumpfile = None):
    emu = Emulator()

    ###########################################################
    # Create a DNS layer
    dns = DomainNameService()
    dns.install('a-root-server').addZone('.').setMaster()  
    dns.install('a-com-server').addZone('com.').setMaster()  

    # Customize the display names (for visualization purpose)
    emu.getVirtualNode('a-root-server').setDisplayName('Root-A')
    emu.getVirtualNode('a-com-server').setDisplayName('COM-A')

    ###########################################################
    emu.addLayer(dns)
    
    if dumpfile is not None:
        emu.dump(dumpfile)
    else:
        emu.dump('dns_component.bin')
        
if __name__ == "__main__":
    run()
