#!/usr/bin/env python3
# encoding: utf-8

"""
Email System Implementation for SEED Emulator
============================================

This example demonstrates how to build a basic email system using docker-mailserver
in the SEED emulator environment. The implementation creates multiple autonomous 
systems with email servers and clients to simulate a realistic email infrastructure.

Features:
- Multiple email servers with different domains
- DNS infrastructure for email routing  
- SMTP/IMAP/POP3 services
- Support for ARM64 and AMD64 platforms

Author: SEED Lab
"""

from seedemu.layers import Base, Routing, Ebgp, Ibgp, Ospf, PeerRelationship
from seedemu.services import DomainNameService, DomainNameCachingService
from seedemu.compiler import Docker, Platform
from seedemu.core import Emulator, Binding, Filter, Action
from seedemu.utilities import Makers
import os, sys

# Docker compose entry for mailserver containers
MAILSERVER_COMPOSE_ENTRY = """\
    {name}:
        image: mailserver/docker-mailserver:edge
        platform: linux/arm64  # Will be adjusted based on detected platform
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
            - ENABLE_MANAGESIEVE=1
            - SSL_TYPE=self-signed
        volumes:
            - ./{name}/mail-data/:/var/mail/
            - ./{name}/mail-state/:/var/mail-state/
            - ./{name}/mail-logs/:/var/log/mail/
            - ./{name}/config/:/tmp/docker-mailserver/
            - /etc/localtime:/etc/localtime:ro
        ports:
            - "{smtp_port}:25"
            - "{submission_port}:587"
            - "{imap_port}:143"
            - "{imaps_port}:993"
        cap_add:
            - NET_ADMIN
        networks:
            - {network_name}
"""

def create_base_network(emu):
    """Create the base network topology for email system"""
    base = Base()
    
    # Create Internet Exchanges
    ix100 = base.createInternetExchange(100)
    ix101 = base.createInternetExchange(101)
    ix102 = base.createInternetExchange(102)
    
    # Set display names for visualization
    ix100.getPeeringLan().setDisplayName('Email-IX-100')
    ix101.getPeeringLan().setDisplayName('Corporate-IX-101') 
    ix102.getPeeringLan().setDisplayName('ISP-IX-102')
    
    # Create Transit AS (Internet Service Provider)
    Makers.makeTransitAs(base, 2, [100, 101, 102], 
                        [(100, 101), (101, 102), (100, 102)])
    
    # Create Stub ASes for email providers
    # AS 150: Public Email Provider (like Gmail)
    Makers.makeStubAsWithHosts(emu, base, 150, 100, 2)
    
    # AS 151: Corporate Email Provider  
    Makers.makeStubAsWithHosts(emu, base, 151, 101, 2)
    
    # AS 152: Small Business Email Provider
    Makers.makeStubAsWithHosts(emu, base, 152, 102, 2)
    
    # AS 160: Client networks
    Makers.makeStubAsWithHosts(emu, base, 160, 100, 3)
    Makers.makeStubAsWithHosts(emu, base, 161, 101, 3)
    
    return base

def configure_dns_system(emu, base):
    """Configure DNS system for email domains"""
    dns = DomainNameService()
    dns_cache = DomainNameCachingService()
    
    # Install DNS servers
    dns.install('dns-150').addZone('seedemail.net')
    dns.install('dns-151').addZone('corporate.local') 
    dns.install('dns-152').addZone('smallbiz.org')
    
    # Install DNS cache servers
    dns_cache.install('dns-cache-160')
    dns_cache.install('dns-cache-161')
    
    # Create DNS server hosts
    as150 = base.getAutonomousSystem(150)
    as150.createHost('dns').joinNetwork('net0').addHostName('dns.seedemail.net')
    
    as151 = base.getAutonomousSystem(151) 
    as151.createHost('dns').joinNetwork('net0').addHostName('dns.corporate.local')
    
    as152 = base.getAutonomousSystem(152)
    as152.createHost('dns').joinNetwork('net0').addHostName('dns.smallbiz.org')
    
    # Create cache servers in client networks
    as160 = base.getAutonomousSystem(160)
    as160.createHost('dns-cache').joinNetwork('net0')
    
    as161 = base.getAutonomousSystem(161)
    as161.createHost('dns-cache').joinNetwork('net0')
    
    # Add DNS records for email servers
    dns.getZone('seedemail.net').addRecord('@ MX 10 mail.seedemail.net.')
    dns.getZone('seedemail.net').addRecord('mail A 10.150.0.10')
    
    dns.getZone('corporate.local').addRecord('@ MX 10 mail.corporate.local.')
    dns.getZone('corporate.local').addRecord('mail A 10.151.0.10')
    
    dns.getZone('smallbiz.org').addRecord('@ MX 10 mail.smallbiz.org.')
    dns.getZone('smallbiz.org').addRecord('mail A 10.152.0.10')
    
    # Bind DNS services to hosts
    emu.addBinding(Binding('dns-150', filter=Filter(nodeName='dns', asn=150)))
    emu.addBinding(Binding('dns-151', filter=Filter(nodeName='dns', asn=151)))
    emu.addBinding(Binding('dns-152', filter=Filter(nodeName='dns', asn=152)))
    emu.addBinding(Binding('dns-cache-160', filter=Filter(nodeName='dns-cache', asn=160)))
    emu.addBinding(Binding('dns-cache-161', filter=Filter(nodeName='dns-cache', asn=161)))
    
    return dns, dns_cache

def create_email_servers(base, platform):
    """Create email server hosts and configure mailserver containers"""
    
    # Create email server hosts
    as150 = base.getAutonomousSystem(150)
    as150.createHost('mail').joinNetwork('net0', address='10.150.0.10') \
                           .addHostName('mail.seedemail.net')
    
    as151 = base.getAutonomousSystem(151)
    as151.createHost('mail').joinNetwork('net0', address='10.151.0.10') \
                           .addHostName('mail.corporate.local')
    
    as152 = base.getAutonomousSystem(152)
    as152.createHost('mail').joinNetwork('net0', address='10.152.0.10') \
                           .addHostName('mail.smallbiz.org')
    
    # Return mailserver configuration information
    mailservers = [
        {
            'name': 'mailserver-150',
            'hostname': 'mail',
            'domain': 'seedemail.net',
            'asn': 150,
            'network': 'net0',
            'ip': '10.150.0.10',
            'smtp_port': '25150',
            'submission_port': '587150', 
            'imap_port': '143150',
            'imaps_port': '993150'
        },
        {
            'name': 'mailserver-151',
            'hostname': 'mail', 
            'domain': 'corporate.local',
            'asn': 151,
            'network': 'net0',
            'ip': '10.151.0.10',
            'smtp_port': '25151',
            'submission_port': '587151',
            'imap_port': '143151', 
            'imaps_port': '993151'
        },
        {
            'name': 'mailserver-152',
            'hostname': 'mail',
            'domain': 'smallbiz.org', 
            'asn': 152,
            'network': 'net0',
            'ip': '10.152.0.10',
            'smtp_port': '25152',
            'submission_port': '587152',
            'imap_port': '143152',
            'imaps_port': '993152'
        }
    ]
    
    return mailservers

def setup_peering(ebgp):
    """Configure BGP peering relationships"""
    
    # Provider relationships
    ebgp.addPrivatePeerings(100, [2], [150, 160], PeerRelationship.Provider)
    ebgp.addPrivatePeerings(101, [2], [151, 161], PeerRelationship.Provider)
    ebgp.addPrivatePeerings(102, [2], [152], PeerRelationship.Provider)

def run(dumpfile=None):
    """Main function to build the email system emulation"""
    
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
                print(f"Usage: {script_name} amd|arm")
                sys.exit(1)
        else:
            print(f"Usage: {script_name} amd|arm")
            sys.exit(1)
    else:
        platform = Platform.AMD64  # Default for dump mode
    
    ###############################################################################
    # Initialize emulator and layers
    emu = Emulator()
    ebgp = Ebgp()
    
    # Create base network
    base = create_base_network(emu)
    
    # Configure DNS
    dns, dns_cache = configure_dns_system(emu, base)
    
    # Create email servers
    mailservers = create_email_servers(base, platform)
    
    # Setup peering relationships
    setup_peering(ebgp)
    
    ###############################################################################
    # Add layers to emulator
    emu.addLayer(base)
    emu.addLayer(Routing())
    emu.addLayer(ebgp)
    emu.addLayer(Ibgp()) 
    emu.addLayer(Ospf())
    emu.addLayer(dns)
    emu.addLayer(dns_cache)
    
    ###############################################################################
    # Render and compile
    if dumpfile is not None:
        emu.dump(dumpfile)
    else:
        emu.render()
        
        docker = Docker(platform=platform)
        
        # Attach mailserver containers
        for mailserver in mailservers:
            # Adjust platform string in compose entry
            platform_str = "linux/arm64" if platform == Platform.ARM64 else "linux/amd64"
            compose_entry = MAILSERVER_COMPOSE_ENTRY.format(
                name=mailserver['name'],
                hostname=mailserver['hostname'],
                domain=mailserver['domain'],
                smtp_port=mailserver['smtp_port'],
                submission_port=mailserver['submission_port'],
                imap_port=mailserver['imap_port'],
                imaps_port=mailserver['imaps_port'],
                network_name=f"as{mailserver['asn']}net0"
            ).replace("linux/arm64", platform_str)
            
            docker.attachCustomContainer(
                compose_entry=compose_entry,
                asn=mailserver['asn'],
                net=mailserver['network'],
                ip_address=mailserver['ip'],
                node_name=mailserver['name'],
                show_on_map=True
            )
        
        # Compile the emulation
        emu.compile(docker, './output', override=True)
        
        print("\n" + "="*60)
        print("Email System Emulation Created Successfully!")
        print("="*60)
        print("\nMailserver Information:")
        for mailserver in mailservers:
            print(f"\nDomain: {mailserver['domain']}")
            print(f"  Hostname: {mailserver['hostname']}.{mailserver['domain']}")
            print(f"  SMTP Port: {mailserver['smtp_port']}")
            print(f"  IMAP Port: {mailserver['imap_port']}")
            print(f"  Network: AS{mailserver['asn']}")
        
        print(f"\nTo run the emulation:")
        print(f"  cd output/")
        print(f"  docker-compose up -d")
        print(f"\nTo view the network map:")
        print(f"  Open http://localhost:8080/map.html in your browser")

if __name__ == "__main__":
    run()
