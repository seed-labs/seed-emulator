#!/usr/bin/env python3
# encoding: utf-8

"""
Simple Email System Implementation for SEED Emulator (MVP Version)
================================================================

This is a simplified version that focuses on getting the basic email system
working without complex DNS configuration. It demonstrates:

- Basic network topology with email server containers
- Docker-mailserver integration 
- Multiple email domains
- Platform support (ARM64/AMD64)

This serves as an MVP that can be extended with DNS, security features, etc.

Author: SEED Lab
"""

from seedemu.layers import Base, Routing, Ebgp, Ibgp, Ospf, PeerRelationship
from seedemu.compiler import Docker, Platform
from seedemu.core import Emulator, Binding, Filter, Action
from seedemu.utilities import Makers
import os, sys

# Simplified mailserver container configuration
MAILSERVER_COMPOSE_TEMPLATE = """\
    {name}:
        image: mailserver/docker-mailserver:edge
        platform: {platform}
        container_name: {name}
        hostname: {hostname}
        domainname: {domain}
        restart: unless-stopped
        privileged: true
        environment:
            - OVERRIDE_HOSTNAME={hostname}.{domain}
            - PERMIT_DOCKER=connected-networks
            - ONE_DIR=1
            - ENABLE_CLAMAV=0
            - ENABLE_FAIL2BAN=0
            - ENABLE_POSTGREY=0
            - DMS_DEBUG=1
        volumes:
            - ./{name}-data/mail-data/:/var/mail/
            - ./{name}-data/mail-state/:/var/mail-state/
            - ./{name}-data/mail-logs/:/var/log/mail/
            - ./{name}-data/config/:/tmp/docker-mailserver/
            - /etc/localtime:/etc/localtime:ro
        ports:
            - "{smtp_port}:25"
            - "{submission_port}:587"
            - "{imap_port}:143"
            - "{imaps_port}:993"
        cap_add:
            - NET_ADMIN
            - SYS_PTRACE
        command: >
            sh -c "
            echo 'Starting mailserver setup...' &&
            sleep 10 &&
            supervisord -c /etc/supervisor/supervisord.conf
            "
"""

def run(dumpfile=None):
    """Main function to build the simplified email system"""
    
    ###############################################################################
    # Platform detection
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
                print(f"Usage: {script_name} amd|arm")
                sys.exit(1)
        else:
            print(f"Usage: {script_name} amd|arm")
            sys.exit(1)
    else:
        platform = Platform.AMD64
    
    platform_str = "linux/arm64" if platform == Platform.ARM64 else "linux/amd64"
    
    ###############################################################################
    # Initialize emulator and layers
    emu = Emulator()
    base = Base()
    routing = Routing()
    ebgp = Ebgp()
    ibgp = Ibgp()
    ospf = Ospf()
    
    ###############################################################################
    # Create basic network topology
    
    # Create Internet Exchange
    ix100 = base.createInternetExchange(100)
    ix100.getPeeringLan().setDisplayName('Email-Central-IX')
    
    # Create Transit AS (ISP)
    Makers.makeTransitAs(base, 2, [100], [])
    
    # Create Email Provider ASes
    Makers.makeStubAsWithHosts(emu, base, 150, 100, 1)  # Public email provider
    Makers.makeStubAsWithHosts(emu, base, 151, 100, 1)  # Corporate email provider
    Makers.makeStubAsWithHosts(emu, base, 152, 100, 1)  # Small business email
    
    # Create Client ASes  
    Makers.makeStubAsWithHosts(emu, base, 160, 100, 2)  # Client network 1
    Makers.makeStubAsWithHosts(emu, base, 161, 100, 2)  # Client network 2
    
    ###############################################################################
    # Create email server hosts with specific IPs and hostnames
    
    # AS 150 - Public Email Provider (seedemail.net)
    as150 = base.getAutonomousSystem(150)
    as150.createHost('mailserver').joinNetwork('net0', address='10.150.0.20')
    
    # AS 151 - Corporate Email Provider (corporate.local)  
    as151 = base.getAutonomousSystem(151)
    as151.createHost('mailserver').joinNetwork('net0', address='10.151.0.20')
    
    # AS 152 - Small Business Email (smallbiz.org)
    as152 = base.getAutonomousSystem(152)
    as152.createHost('mailserver').joinNetwork('net0', address='10.152.0.20')
    
    ###############################################################################
    # Configure BGP peering
    
    # All email providers peer with ISP
    ebgp.addPrivatePeering(100, 2, 150, PeerRelationship.Provider)
    ebgp.addPrivatePeering(100, 2, 151, PeerRelationship.Provider)
    ebgp.addPrivatePeering(100, 2, 152, PeerRelationship.Provider)
    ebgp.addPrivatePeering(100, 2, 160, PeerRelationship.Provider)
    ebgp.addPrivatePeering(100, 2, 161, PeerRelationship.Provider)
    
    ###############################################################################
    # Add layers to emulator
    emu.addLayer(base)
    emu.addLayer(routing)
    emu.addLayer(ebgp)
    emu.addLayer(ibgp)
    emu.addLayer(ospf)
    
    ###############################################################################
    # Render and compile
    if dumpfile is not None:
        emu.dump(dumpfile)
    else:
        emu.render()
        
        docker = Docker(platform=platform)
        
        # Email server configurations
        mailservers = [
            {
                'name': 'mail-150-seedemail',
                'hostname': 'mail',
                'domain': 'seedemail.net',
                'asn': 150,
                'network': 'net0',
                'ip': '10.150.0.10',
                'ports': {'smtp': '2525', 'submission': '5870', 'imap': '1430', 'imaps': '9930'}
            },
            {
                'name': 'mail-151-corporate', 
                'hostname': 'mail',
                'domain': 'corporate.local',
                'asn': 151,
                'network': 'net0', 
                'ip': '10.151.0.10',
                'ports': {'smtp': '2526', 'submission': '5871', 'imap': '1431', 'imaps': '9931'}
            },
            {
                'name': 'mail-152-smallbiz',
                'hostname': 'mail',
                'domain': 'smallbiz.org',
                'asn': 152,
                'network': 'net0',
                'ip': '10.152.0.10', 
                'ports': {'smtp': '2527', 'submission': '5872', 'imap': '1432', 'imaps': '9932'}
            }
        ]
        
        # Attach mailserver containers
        for mail in mailservers:
            compose_entry = MAILSERVER_COMPOSE_TEMPLATE.format(
                name=mail['name'],
                platform=platform_str,
                hostname=mail['hostname'],
                domain=mail['domain'],
                smtp_port=mail['ports']['smtp'],
                submission_port=mail['ports']['submission'],
                imap_port=mail['ports']['imap'],
                imaps_port=mail['ports']['imaps']
            )
            
            docker.attachCustomContainer(
                compose_entry=compose_entry,
                asn=mail['asn'],
                net=mail['network'],
                ip_address=mail['ip'],
                node_name=mail['name'],
                show_on_map=True
            )
        
        # Add Internet Map for visualization
        docker.attachInternetMap(
            asn=160, 
            net='net0', 
            ip_address='10.160.0.100',
            port_forwarding='8080:8080/tcp'
        )
        
        # Compile the emulation
        emu.compile(docker, './output', override=True)
        
        # Print setup information
        print("\n" + "="*70)
        print("SEED Email System - Simple Version Created Successfully!")
        print("="*70)
        print("\nEmail Servers Configured:")
        print("-" * 40)
        
        for mail in mailservers:
            print(f"\n📧 {mail['domain']} (AS{mail['asn']})")
            print(f"   Container: {mail['name']}")
            print(f"   Internal IP: {mail['ip']}")
            print(f"   SMTP Port: localhost:{mail['ports']['smtp']}")
            print(f"   IMAP Port: localhost:{mail['ports']['imap']}")
            print(f"   Webmail: http://{mail['ip']}:80 (internal)")
        
        print(f"\n🌐 Network Visualization:")
        print(f"   Internet Map: http://localhost:8080/map.html")
        
        print(f"\n🚀 To Start the Email System:")
        print(f"   cd output/")
        print(f"   docker-compose up -d")
        
        print(f"\n📋 To Create Email Accounts:")
        print(f"   docker exec -it mail-150-seedemail setup email add user@seedemail.net")
        print(f"   docker exec -it mail-151-corporate setup email add admin@corporate.local")
        print(f"   docker exec -it mail-152-smallbiz setup email add info@smallbiz.org")
        
        print(f"\n📧 Email Client Configuration:")
        print(f"   seedemail.net  - SMTP: localhost:2525, IMAP: localhost:1430")
        print(f"   corporate.local - SMTP: localhost:2526, IMAP: localhost:1431") 
        print(f"   smallbiz.org   - SMTP: localhost:2527, IMAP: localhost:1432")
        
        print(f"\n🔍 To Check Status:")
        print(f"   docker-compose ps")
        print(f"   docker logs mail-150-seedemail")
        
        print("\n" + "="*70)

if __name__ == "__main__":
    run()
