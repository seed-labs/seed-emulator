#!/usr/bin/env python3
# encoding: utf-8

from seedemu import *
import os, sys, random

# just list 5 groups
MIRAI_CREDS = [
    ("root", "vizxv"),    ("root", "xc3511"),   ("root", "admin"),
    ("admin", "admin"),   ("root", "888888")
]

def makeVictim(emu: Emulator, base: Base, victim_asn: int):
    # set victim to 10.170.0.99
    # set monitor to 10.170.0.100
    victim_as = base.getAutonomousSystem(victim_asn)
    victim_server = victim_as.createHost('host_victim').joinNetwork('net0',address='10.170.0.99')
    
    # import index.html
    victim_server.appendStartCommand('mkdir -p /var/www/html', fork=True)
    current_path = os.getcwd()
    victim_server.importFile(hostpath="{}/misc/index.html".format(current_path), containerpath="/var/www/html/index.html")
    victim_server.importFile(hostpath="{}/misc/large_image.png".format(current_path), containerpath="/var/www/html/large_image.png")
    # start web server
    
    victim_server.appendStartCommand('python3 -m http.server 80 --directory /var/www/html', fork=True)
    victim_server.addPortForwarding(445,80)
    print(f"Victim server created in AS {victim_asn} and serving a website.")


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
    
    ###############################################################################
    # Create internet exchanges
    ix100 = base.createInternetExchange(100)
    ix101 = base.createInternetExchange(101)
    ix102 = base.createInternetExchange(102)
    ix103 = base.createInternetExchange(103)
    ix104 = base.createInternetExchange(104)
    ix105 = base.createInternetExchange(105)
    
    # Customize names (for visualization purpose)
    ix100.getPeeringLan().setDisplayName('NYC-100')
    ix101.getPeeringLan().setDisplayName('San Jose-101')
    ix102.getPeeringLan().setDisplayName('Chicago-102')
    ix103.getPeeringLan().setDisplayName('Miami-103')
    ix104.getPeeringLan().setDisplayName('Boston-104')
    ix105.getPeeringLan().setDisplayName('Huston-105')
    
    
    ###############################################################################
    # Create Transit Autonomous Systems 
    
    ## Tier 1 ASes
    Makers.makeTransitAs(base, 2, [100, 101, 102, 105], 
           [(100, 101), (101, 102), (100, 105)] 
    )
    
    Makers.makeTransitAs(base, 3, [100, 103, 104, 105], 
           [(100, 103), (100, 105), (103, 105), (103, 104)]
    )
    
    Makers.makeTransitAs(base, 4, [100, 102, 104], 
           [(100, 104), (102, 104)]
    )
    
    ## Tier 2 ASes
    Makers.makeTransitAs(base, 11, [102, 105], [(102, 105)])
    Makers.makeTransitAs(base, 12, [101, 104], [(101, 104)])
    
    
    ###############################################################################
    # Create single-homed stub ASes. 
    Makers.makeStubAsWithHosts(emu, base, 150, 100, hosts_per_as)
    Makers.makeStubAsWithHosts(emu, base, 151, 100, hosts_per_as)
    Makers.makeStubAsWithHosts(emu, base, 152, 101, hosts_per_as)
    Makers.makeStubAsWithHosts(emu, base, 153, 101, hosts_per_as)
    Makers.makeStubAsWithHosts(emu, base, 154, 102, hosts_per_as)
    Makers.makeStubAsWithHosts(emu, base, 160, 103, hosts_per_as)
    Makers.makeStubAsWithHosts(emu, base, 161, 103, hosts_per_as)
    Makers.makeStubAsWithHosts(emu, base, 162, 103, hosts_per_as)
    Makers.makeStubAsWithHosts(emu, base, 163, 104, hosts_per_as)
    Makers.makeStubAsWithHosts(emu, base, 164, 104, hosts_per_as)
    Makers.makeStubAsWithHosts(emu, base, 170, 105, hosts_per_as)
    Makers.makeStubAsWithHosts(emu, base, 171, 105, hosts_per_as)
    
    makeVictim(emu, base, victim_asn=170)

    ###############################################################################
    # Peering via RS (route server). The default peering mode for RS is PeerRelationship.Peer, 
    # which means each AS will only export its customers and their own prefixes. 
    # We will use this peering relationship to peer all the ASes in an IX.
    # None of them will provide transit service for others. 
    
    ebgp.addRsPeers(100, [2, 3, 4])
    ebgp.addRsPeers(102, [2, 4])
    ebgp.addRsPeers(104, [3, 4])
    ebgp.addRsPeers(105, [2, 3])
    
    # To buy transit services from another autonomous system, 
    # we will use private peering  
    
    ebgp.addPrivatePeerings(100, [2],  [150, 151], PeerRelationship.Provider)
    ebgp.addPrivatePeerings(100, [3],  [150], PeerRelationship.Provider)

    ebgp.addPrivatePeerings(101, [2],  [12], PeerRelationship.Provider)
    ebgp.addPrivatePeerings(101, [12], [152, 153], PeerRelationship.Provider)
    
    ebgp.addPrivatePeerings(102, [2, 4],  [11, 154], PeerRelationship.Provider)
    ebgp.addPrivatePeerings(102, [11], [154], PeerRelationship.Provider)
    
    ebgp.addPrivatePeerings(103, [3],  [160, 161, 162], PeerRelationship.Provider)
    
    ebgp.addPrivatePeerings(104, [3, 4], [12], PeerRelationship.Provider)
    ebgp.addPrivatePeerings(104, [4],  [163], PeerRelationship.Provider)
    ebgp.addPrivatePeerings(104, [12], [164], PeerRelationship.Provider)
    
    ebgp.addPrivatePeerings(105, [3],  [11, 170], PeerRelationship.Provider)
    ebgp.addPrivatePeerings(105, [11], [171], PeerRelationship.Provider)
    
    
    ###############################################################################
    # Add layers to the emulator

    emu.addLayer(base)
    emu.addLayer(Routing())
    emu.addLayer(ebgp) 
    emu.addLayer(Ibgp())
    emu.addLayer(Ospf())

    ###############################################################################
    # Mirai settings
    # Change the base for all the host nodes 
    for stub_as in [150, 151, 152, 153, 154, 160, 161, 162, 163, 164, 170, 171]:
        hosts = base.getAutonomousSystem(stub_as).getHosts()
        for hostname in hosts:
            host = base.getAutonomousSystem(stub_as).getHost(hostname)
            host.addSoftware('telnetd')
            host.addSoftware('telnet')
            host.appendStartCommand('rm -f /root/.bashrc ', fork=True)
            host.appendStartCommand('echo "pts/0" >> /etc/securetty && echo "pts/1" >> /etc/securetty ', fork=True)
            host.appendStartCommand('echo -e "telnet stream tcp nowait root /usr/sbin/tcpd /usr/sbin/in.telnetd -L /bin/login" > /etc/inetd.conf', fork=True)
            # randomly select mirai credits
            user, pwd = random.choice(MIRAI_CREDS)

            if user == "root":
                host.appendStartCommand(
                    f'echo -e "{pwd}\\n{pwd}" | passwd root', fork=True)
            else:
                host.appendStartCommand(
                    f'useradd -m -s /bin/bash {user} && '
                    f'echo -e "{pwd}\\n{pwd}" | passwd {user}', fork=True)
            host.appendStartCommand('/usr/sbin/inetd -d ', fork=True)

    
    # set C2 server to 10.170.0.101
    # use BotnetService to setup C2
    C2 = base.getAutonomousSystem(170).createHost('c2_server').joinNetwork('net0', address= '10.170.0.101')
    botcontroller = BotnetService()
    botcontroller.install('bot-controller')
    emu.getVirtualNode('bot-controller').setDisplayName('C2_server')
    emu.addBinding(Binding('bot-controller', filter = Filter(ip='10.170.0.101'), action=Action.FIRST))
    emu.addLayer(botcontroller)
    
    C2.appendStartCommand('mkdir -p /var/www/html && cd /var/www/html', fork=True)
    current_dir = os.getcwd()
    C2.importFile(hostpath="{}/mirai.py".format(current_dir),
                    containerpath="/var/www/html/mirai.py")
    C2.appendStartCommand('chmod +x mirai.py',fork=True)
    C2.appendStartCommand('python3 -m http.server 80 --directory /var/www/html', fork=True)  # start C2 server
    C2.addSoftware('telnetd')
    C2.addSoftware('telnet')
    
    if dumpfile is not None: 
        # Save it to a file, so it can be used by other emulators
        emu.dump(dumpfile)
    else: 
        emu.render()
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
