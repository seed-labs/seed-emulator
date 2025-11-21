#!/usr/bin/env python3
# encoding: utf-8

from seedemu.layers import Base, Routing, Ebgp
from seedemu.services import (
    EmailComprehensiveService,
    WebmailService,
    DomainNameService,
    DomainNameCachingService,
)
from seedemu.compiler import Docker, Platform
from seedemu.core import Emulator, Binding, Filter
import sys, os


def run():
    # -------------------------------------------------------------------------
    # Platform detection: amd|arm|auto
    script_name = os.path.basename(__file__)
    if len(sys.argv) == 1:
        plat = 'auto'
    elif len(sys.argv) == 2:
        plat = sys.argv[1].lower()
    else:
        print(f"Usage: {script_name} [auto|amd|arm]")
        sys.exit(1)

    if plat in ('amd', 'amd64', 'x86_64'):
        platform = Platform.AMD64
    elif plat in ('arm', 'arm64', 'aarch64'):
        platform = Platform.ARM64
    else:
        arch = os.uname().machine if hasattr(os, 'uname') else ''
        platform = Platform.ARM64 if arch in ('aarch64', 'arm64') else Platform.AMD64

    # -------------------------------------------------------------------------
    # Build emulator and layers
    emu = Emulator()
    base = Base()
    routing = Routing()
    ebgp = Ebgp()

    dns_auth = DomainNameService()
    dns_ldns = DomainNameCachingService(autoRoot=True)

    email = EmailComprehensiveService()
    webmail = WebmailService()

    # -------------------------------------------------------------------------
    # Internet Exchange
    base.createInternetExchange(100)

    # -------------------------------------------------------------------------
    # AS-200: qq.com
    as200 = base.createAutonomousSystem(200)
    as200.createNetwork('net0')
    as200.createRouter('router0').joinNetwork('net0').joinNetwork('ix100')
    as200.createHost('mail').joinNetwork('net0')
    as200.createHost('webmail').joinNetwork('net0').addPort(18080, 80)
    as200.createHost('ns').joinNetwork('net0')
    as200.createHost('dns').joinNetwork('net0')

    # Email server for qq.com
    email.install('mail-qq') \
         .setDomain('qq.com') \
         .enableAutoPublishMx(True) \
         .addAccount('user', 'password123')

    # Webmail for qq.com, target to its mail vnode
    webmail.install('webmail-qq') \
           .setImapTarget('mail-qq') \
           .setSmtpTarget('mail-qq') \
           .setSmtpPort(25)

    # DNS authoritative for qq.com.
    dns_auth.install('ns-qq').addZone('qq.com.').setMaster()

    # Local DNS (LDNS) for AS200, forward its own zone and peer
    dns_ldns.install('dns-qq').setConfigureResolvconf(True) \
            .addForwardZone('qq.com.', 'ns-qq') \
            .addForwardZone('gmail.com.', 'ns-gmail')

    # Bindings for AS200
    emu.addBinding(Binding('mail-qq', filter=Filter(nodeName='mail', asn=200)))
    emu.addBinding(Binding('webmail-qq', filter=Filter(nodeName='webmail', asn=200)))
    emu.addBinding(Binding('ns-qq', filter=Filter(nodeName='ns', asn=200)))
    emu.addBinding(Binding('dns-qq', filter=Filter(nodeName='dns', asn=200)))

    # -------------------------------------------------------------------------
    # AS-201: gmail.com
    as201 = base.createAutonomousSystem(201)
    as201.createNetwork('net0')
    as201.createRouter('router0').joinNetwork('net0').joinNetwork('ix100')
    as201.createHost('mail').joinNetwork('net0')
    as201.createHost('webmail').joinNetwork('net0').addPort(18081, 80)
    as201.createHost('ns').joinNetwork('net0')
    as201.createHost('dns').joinNetwork('net0')

    # Email server for gmail.com
    email.install('mail-gmail') \
         .setDomain('gmail.com') \
         .enableAutoPublishMx(True) \
         .addAccount('user', 'password123')

    # Webmail for gmail.com
    webmail.install('webmail-gmail') \
           .setImapTarget('mail-gmail') \
           .setSmtpTarget('mail-gmail') \
           .setSmtpPort(25)

    # DNS authoritative for gmail.com.
    dns_auth.install('ns-gmail').addZone('gmail.com.').setMaster()

    # Local DNS (LDNS) for AS201
    dns_ldns.install('dns-gmail').setConfigureResolvconf(True) \
            .addForwardZone('qq.com.', 'ns-qq') \
            .addForwardZone('gmail.com.', 'ns-gmail')

    # Bindings for AS201
    emu.addBinding(Binding('mail-gmail', filter=Filter(nodeName='mail', asn=201)))
    emu.addBinding(Binding('webmail-gmail', filter=Filter(nodeName='webmail', asn=201)))
    emu.addBinding(Binding('ns-gmail', filter=Filter(nodeName='ns', asn=201)))
    emu.addBinding(Binding('dns-gmail', filter=Filter(nodeName='dns', asn=201)))

    # -------------------------------------------------------------------------
    # Peering at IX-100
    ebgp.addRsPeer(100, 200)
    ebgp.addRsPeer(100, 201)

    # -------------------------------------------------------------------------
    # Render & compile
    emu.addLayer(base)
    emu.addLayer(routing)
    emu.addLayer(ebgp)
    emu.addLayer(dns_auth)
    emu.addLayer(dns_ldns)
    emu.addLayer(email)
    emu.addLayer(webmail)

    emu.render()

    docker = Docker(platform=platform)
    outdir = os.path.join(os.path.dirname(__file__), 'output_v2')
    emu.compile(docker, outdir, override=True)


if __name__ == '__main__':
    run()
