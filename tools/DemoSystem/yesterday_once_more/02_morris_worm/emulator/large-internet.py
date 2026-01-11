#!/usr/bin/env python3
# encoding: utf-8

#from seedemu.layers import Base, Routing, Ebgp, Ibgp, Ospf, PeerRelationship
#from seedemu.compiler import Docker, Platform, DockerImage
#from seedemu.mergers import DEFAULT_MERGERS
#from seedemu.core import Emulator
#from seedemu.raps import OpenVpnRemoteAccessProvider
#from seedemu.utilities import Makers
#from seedemu.services import DomainNameCachingService

from seedemu import *
import os, sys, random, re


DOCKER_COMPOSE_ENTRY = """\
    {name}:
        image: handsonsecurity/seedemu-internetmap:2.0
        container_name: {name}
        privileged: true
        volumes:
            - /var/run/docker.sock:/var/run/docker.sock
        ports:
            - 8080:8080/tcp
"""

def setup_dns(emu):
    base: Base = emu.getLayer('Base')
    # Create a DNS layer
    dns = DomainNameService()
    emu.addLayer(dns)

    dns.install('root-server').addZone('.').setMaster()
    dns.install('com-server').addZone('com.').setMaster()

    dns.getZone('com.').addRecord('worm.com.  A  2.0.0.0')

    # Customize the display names (for visualization purpose)
    emu.getVirtualNode('root-server').setDisplayName('Root')
    emu.getVirtualNode('com-server').setDisplayName('COM')

    # Set up root and com servers 
    as150 = base.getAutonomousSystem(150)
    as150.createHost('root-node').joinNetwork('net0', address = '10.150.0.53')
    as160 = base.getAutonomousSystem(160)
    as160.createHost('com-node').joinNetwork('net0', address = '10.160.0.53')
    emu.addBinding(Binding('root-server', filter=Filter(asn=150, nodeName='root-node')))
    emu.addBinding(Binding('com-server', filter=Filter(asn=160, nodeName='com-node')))

    current_dir = os.getcwd()
    com_server = as160.getHost('com-node')
    com_server.importFile(hostpath=f"{current_dir}/scripts/add_dns_record.sh", 
                          containerpath="/tmp/add_dns_record.sh")
    com_server.appendStartCommand("chmod +x /tmp/add_dns_record.sh")



def setup_ldns(emu, stub_ases):
    base: Base = emu.getLayer('Base')

    ldns = DomainNameCachingService()
    emu.addLayer(ldns)

    # Set up Local DNS (DNS Resolvers)
    dns_resolvers = [('dns-resolver-1', 163), ('dns-resolver-2', 170)] 

    resolvers=[]
    for (ldns_name, ldns_as) in dns_resolvers:
        asys = base.getAutonomousSystem(ldns_as)
        asys.createHost(ldns_name).joinNetwork('net0', address = f'10.{ldns_as}.0.53')

        dns_resolver:DomainNameCachingServer = ldns.install(ldns_name)
        emu.addBinding(Binding(ldns_name, filter = Filter(asn=ldns_as, nodeName=ldns_name)))
        resolvers.append(dns_resolver)

    midpoint = len(stub_ases) // 2
    resolvers[0].setNameServerOnNodesByAsns(asns=stub_ases[:midpoint])
    resolvers[1].setNameServerOnAllNodes()


def run(dumpfile=None, hosts_per_as=2): 
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

    emu   = Emulator()
    ebgp  = Ebgp()
    base  = Base()
    ovpn = OpenVpnRemoteAccessProvider()

    
    ###############################################################################
    # Create internet exchanges
    ix100 = base.createInternetExchange(100)
    ix101 = base.createInternetExchange(101)
    ix102 = base.createInternetExchange(102)
    ix103 = base.createInternetExchange(103)
    ix104 = base.createInternetExchange(104)
    ix105 = base.createInternetExchange(105)
    ix106 = base.createInternetExchange(106)
    ix107 = base.createInternetExchange(107)
    ix108 = base.createInternetExchange(108)
    ix109 = base.createInternetExchange(109)
    
    # Customize names (for visualization purpose)
    ix100.getPeeringLan().setDisplayName('Beijing-100')
    ix101.getPeeringLan().setDisplayName('Shanghai-101')
    ix102.getPeeringLan().setDisplayName('Hangzhou-102')
    ix103.getPeeringLan().setDisplayName('Wuhan-103')
    ix104.getPeeringLan().setDisplayName('Guanzhou-104')
    ix105.getPeeringLan().setDisplayName('Chongqing-105')
    ix106.getPeeringLan().setDisplayName('Lanzhou-106')
    ix107.getPeeringLan().setDisplayName('Kunming-107')
    ix108.getPeeringLan().setDisplayName('Nanchang-108')
    ix109.getPeeringLan().setDisplayName('Changchun-109')
    
    
    ###############################################################################
    # Create Transit Autonomous Systems 
    
    ## Tier 1 ASes
    Makers.makeTransitAs(base, 2, [100, 101, 102, 107], 
           [(100, 101), (101, 102), (100, 107), (102, 107)] 
    )
    
    Makers.makeTransitAs(base, 3, [100, 103, 104, 107, 108], 
           [(100, 103), (103, 104), (104, 107), (107, 108)]
    )
    
    Makers.makeTransitAs(base, 4, [100, 102, 104, 106, 108], 
           [(100, 104), (102, 104), (102, 106), (100, 108)]
    )

    
    ## Tier 2 ASes
    Makers.makeTransitAs(base, 11, [102, 105], [(102, 105)])
    Makers.makeTransitAs(base, 12, [101, 104, 109], [(101, 104), (104, 109)])
    Makers.makeTransitAs(base, 13, [103, 106], [(103, 106)])
    
    
    ###############################################################################
    # Create single-homed stub ASes. 
    stub_ases = range(150, 178+1)
    Makers.makeStubAsWithHosts(emu, base, 150, 100, hosts_per_as)
    Makers.makeStubAsWithHosts(emu, base, 151, 100, hosts_per_as)
    Makers.makeStubAsWithHosts(emu, base, 152, 100, hosts_per_as)

    Makers.makeStubAsWithHosts(emu, base, 153, 101, hosts_per_as)
    Makers.makeStubAsWithHosts(emu, base, 154, 101, hosts_per_as)
    Makers.makeStubAsWithHosts(emu, base, 155, 101, hosts_per_as)

    Makers.makeStubAsWithHosts(emu, base, 156, 102, hosts_per_as)
    Makers.makeStubAsWithHosts(emu, base, 157, 102, hosts_per_as)
    Makers.makeStubAsWithHosts(emu, base, 158, 102, hosts_per_as)

    Makers.makeStubAsWithHosts(emu, base, 159, 103, hosts_per_as)
    Makers.makeStubAsWithHosts(emu, base, 160, 103, hosts_per_as)
    Makers.makeStubAsWithHosts(emu, base, 161, 103, hosts_per_as)

    Makers.makeStubAsWithHosts(emu, base, 162, 104, hosts_per_as)
    Makers.makeStubAsWithHosts(emu, base, 163, 104, hosts_per_as)
    Makers.makeStubAsWithHosts(emu, base, 164, 104, hosts_per_as)

    Makers.makeStubAsWithHosts(emu, base, 165, 105, hosts_per_as)
    Makers.makeStubAsWithHosts(emu, base, 166, 105, hosts_per_as)

    Makers.makeStubAsWithHosts(emu, base, 167, 106, hosts_per_as)
    Makers.makeStubAsWithHosts(emu, base, 168, 106, hosts_per_as)
    Makers.makeStubAsWithHosts(emu, base, 169, 106, hosts_per_as)


    Makers.makeStubAsWithHosts(emu, base, 170, 107, hosts_per_as)
    Makers.makeStubAsWithHosts(emu, base, 171, 107, hosts_per_as)
    Makers.makeStubAsWithHosts(emu, base, 172, 107, hosts_per_as)

    Makers.makeStubAsWithHosts(emu, base, 173, 108, hosts_per_as)
    Makers.makeStubAsWithHosts(emu, base, 174, 108, hosts_per_as)
    Makers.makeStubAsWithHosts(emu, base, 175, 108, hosts_per_as)

    Makers.makeStubAsWithHosts(emu, base, 176, 109, hosts_per_as)
    Makers.makeStubAsWithHosts(emu, base, 177, 109, hosts_per_as)
    Makers.makeStubAsWithHosts(emu, base, 178, 109, hosts_per_as)

    # Create a real-world router, attach it to ix-101 and peer with AS-2
    as77777 = base.createAutonomousSystem(77777)
    as77777.createRealWorldRouter(name='real-world', prefixes=['0.0.0.0/1', '128.0.0.0/1'])\
          .joinNetwork('ix102', address = '10.102.0.177')
    ebgp.addPrivatePeerings(102, [2],  [77777], PeerRelationship.Provider)


    # Create a new AS as the BGP attacker, attach it to ix-105 and peer with AS-11
    as199 = base.createAutonomousSystem(199)
    as199.createNetwork('net0')
    as199.createHost('host-0').joinNetwork('net0')
    as199.createRouter('attacker-bgp').joinNetwork('net0').joinNetwork('ix105')
    ebgp.addPrivatePeerings(105, [11],  [199], PeerRelationship.Provider)

    # Enable VPN on AS 174
    as174 = base.getAutonomousSystem(174)
    as174.getNetwork("net0").enableRemoteAccess(ovpn)
    
    ###############################################################################
    # Peering via RS (route server). The default peering mode for RS is PeerRelationship.Peer, 
    # which means each AS will only export its customers and their own prefixes. 
    # We will use this peering relationship to peer all the ASes in an IX.
    # None of them will provide transit service for others. 
    
    ebgp.addRsPeers(100, [2, 3, 4])
    ebgp.addRsPeers(104, [3, 4])
    ebgp.addRsPeers(107, [2, 3])
    ebgp.addRsPeers(108, [3, 4])
    
    # To buy transit services from another autonomous system, 
    # we will use private peering  
    
    ebgp.addPrivatePeerings(100, [2],  [150, 151, 152], PeerRelationship.Provider)
    ebgp.addPrivatePeerings(100, [3],  [150], PeerRelationship.Provider)
    ebgp.addPrivatePeerings(100, [4],  [151, 152], PeerRelationship.Provider)

    ebgp.addPrivatePeerings(101, [2],  [12, 155], PeerRelationship.Provider)
    ebgp.addPrivatePeerings(101, [12], [153, 154], PeerRelationship.Provider)
    
    ebgp.addPrivatePeerings(102, [2],  [11, 156, 157, 158], PeerRelationship.Provider)
    
    ebgp.addPrivatePeerings(103, [3],  [13, 159], PeerRelationship.Provider)
    ebgp.addPrivatePeerings(103, [13],  [160, 161], PeerRelationship.Provider)
    
    ebgp.addPrivatePeerings(104, [3, 4], [12], PeerRelationship.Provider)
    ebgp.addPrivatePeerings(104, [4],  [162], PeerRelationship.Provider)
    ebgp.addPrivatePeerings(104, [12], [163, 164], PeerRelationship.Provider)
    
    ebgp.addPrivatePeerings(105, [11], [165, 166], PeerRelationship.Provider)

    ebgp.addPrivatePeerings(106, [13], [167, 168, 169], PeerRelationship.Provider)
    
    ebgp.addPrivatePeerings(107, [2], [170, 171], PeerRelationship.Provider)
    ebgp.addPrivatePeerings(107, [3], [172], PeerRelationship.Provider)

    ebgp.addPrivatePeerings(108, [3], [173], PeerRelationship.Provider)
    ebgp.addPrivatePeerings(108, [4], [174, 175], PeerRelationship.Provider)


    ebgp.addPrivatePeerings(109, [12], [176, 177, 178], PeerRelationship.Provider)
    


    ###############################################################################
    # Add layers to the emulator

    emu.addLayer(base)
    emu.addLayer(Routing())
    emu.addLayer(ebgp) 
    emu.addLayer(Ibgp())
    emu.addLayer(Ospf())


    ###############################################################################
    # Set up DNS Server and Resolvers
    setup_dns (emu)
    setup_ldns(emu, stub_ases)

    if dumpfile is not None: 
        # Save it to a file, so it can be used by other emulators
        emu.dump(dumpfile)
    else: 
        emu.render()

        docker = Docker(platform=platform, internetMapEnabled=False)

        # Use the new internet-map:2.0
        docker.attachCustomContainer(compose_entry =
             DOCKER_COMPOSE_ENTRY.format(name="seedemu_internetmap"))

        # Use the "morris-worm-base" custom base image
        docker.addImage(DockerImage('morris-worm-base', [], local = True))

        # Change the base for all the host nodes
        for stub_as in stub_ases:
           hosts = base.getAutonomousSystem(stub_as).getHosts()
           for hostname in hosts:
               if re.search(r"dns-", hostname): 
                   continue  # Skip DNS nodes

               host = base.getAutonomousSystem(stub_as).getHost(hostname)
               docker.setImageOverride(host, 'morris-worm-base')
               host.appendStartCommand('rm -f /root/.bashrc && cd /bof && ./server &')
        

        OUTPUT_DIR = './demo_output'
        emu.compile(docker, OUTPUT_DIR, override=True)

        # Copy the base container image to the output folder
        os.system(f'cp -r container_files/morris-worm-base {OUTPUT_DIR}')
        os.system(f'cp -r container_files/z_start.sh  {OUTPUT_DIR}')
        os.system(f'cp -r container_files/z_build.sh  {OUTPUT_DIR}')
        os.system(f'chmod a+x {OUTPUT_DIR}/z_start.sh')
        os.system(f'chmod a+x {OUTPUT_DIR}/z_build.sh')


if __name__ == "__main__":
    run(hosts_per_as=5)
