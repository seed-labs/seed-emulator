#!/usr/bin/env python3
# encoding: utf-8

from seedemu.core import Emulator, Binding, Filter, Action
from seedemu.mergers import DEFAULT_MERGERS
from seedemu.compiler import Docker, Platform, DockerImage
from seedemu.services import DomainNameCachingService
from seedemu.services.DomainNameCachingService import DomainNameCachingServer
from seedemu.layers import Base
from examples.yesterday_once_more.Y03_mirai import mini_internet_for_mirai
from examples.yesterday_once_more.Y03_mirai import dns_component
import os, sys

def run(dumpfile=None):
	###############################################################################
    # Set the platform information
    if dumpfile is None:
        script_name = os.path.basename(__file__)

        if len(sys.argv) == 1:
            platform = Platform.AMD64
        elif len(sys.argv) == 2:
            if sys.argv[1].lower() == 'amd':
                platform = Platform.AMD64
            elif sys.argv[1].lower() == 'arm':
                platform = Platform.ARM64
            else:
                print(f"Usage:  {script_name} amd|arm")
                sys.exit(1)
        else:
            print(f"Usage:  {script_name} amd|arm")
            sys.exit(1)

    emuA = Emulator()
    emuB = Emulator()

    # Run the pre-built components
    mini_internet_for_mirai.run(dumpfile='./base_internet.bin')
    dns_component.run(dumpfile='./dns_component.bin')
    
    # Load and merge the pre-built components 
    emuA.load('./base_internet.bin')
    emuB.load('./dns_component.bin')
    emu = emuA.merge(emuB, DEFAULT_MERGERS)
    
    
    #####################################################################################
    # Bind the virtual nodes in the DNS infrastructure layer to physical nodes.
    # Action.FIRST will look for the first acceptable node that satisfies the filter rule.
    # There are several other filters types that are not shown in this example.
    
    base: Base = emu.getLayer('Base')
    as150 = base.getAutonomousSystem(150)
    as150.createHost('root-a').joinNetwork('net0', address = '10.150.0.53')
    as151 = base.getAutonomousSystem(151)
    COMA = as151.createHost('com-a').joinNetwork('net0', address = '10.151.0.53')
    emu.addBinding(Binding('a-root-server', filter=Filter(asn=150, nodeName='root-a')))
    emu.addBinding(Binding('a-com-server', filter=Filter(asn=151, nodeName='com-a')))

    current_dir = os.getcwd()
    COMA.importFile(hostpath="{}/scripts/add_dns_record.sh".format(current_dir),
                      containerpath="/tmp/add_dns_record.sh")
    COMA.appendStartCommand("cd /tmp && chmod +x ./add_dns_record.sh")
    
    #####################################################################################
    # Create two local DNS servers (virtual nodes).
    ldns = DomainNameCachingService()
    global_dns_1:DomainNameCachingServer = ldns.install('global-dns-1')
    global_dns_2:DomainNameCachingServer = ldns.install('global-dns-2')
    
    # Customize the display name (for visualization purpose)
    emu.getVirtualNode('global-dns-1').setDisplayName('Global DNS-1')
    emu.getVirtualNode('global-dns-2').setDisplayName('Global DNS-2')
    
    as152 = base.getAutonomousSystem(152)
    as152.createHost('local-dns-1').joinNetwork('net0', address = '10.152.0.53')
    as153 = base.getAutonomousSystem(153)
    as153.createHost('local-dns-2').joinNetwork('net0', address = '10.153.0.53')
    
    # Bind the Local DNS virtual nodes to physical nodes
    emu.addBinding(Binding('global-dns-1', filter = Filter(asn=152, nodeName="local-dns-1")))
    emu.addBinding(Binding('global-dns-2', filter = Filter(asn=153, nodeName="local-dns-2")))
    
    # Add 10.152.0.53 as the local DNS server for AS-160 and AS-170
    # Add 10.153.0.53 as the local DNS server for all the other nodes
    global_dns_1.setNameServerOnNodesByAsns(asns=[160, 170])
    global_dns_2.setNameServerOnAllNodes()
    
    # Add the ldns layer
    emu.addLayer(ldns)
    
    if dumpfile is not None:
       # Save it to a file, so it can be used by other emulators
       emu.dump(dumpfile)
    else:
       # Rendering compilation 
       emu.render()
       # change base
       docker = Docker(internetMapEnabled=True)
       docker.addImage(DockerImage('mirai-base', [], local = True))
       for stub_as in [150, 151, 152, 153, 154, 160, 161, 162, 163, 164, 170, 171]:
        hosts = base.getAutonomousSystem(stub_as).getHosts()
        for hostname in hosts:
            host = base.getAutonomousSystem(stub_as).getHost(hostname)
            docker.setImageOverride(host, 'mirai-base')
       
       emu.compile(docker, './output', override=True)
       os.system('cp -r container_files/mirai-base ./output')

if __name__ == "__main__":
    run()

