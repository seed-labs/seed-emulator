from seedemu.compiler import Docker
from seedemu.core import Binding, Emulator, Filter, Action
from seedemu.layers import Base, Ebgp, Ibgp, Ospf, Routing, PeerRelationship
from seedemu.services import DomainNameCachingService, DomainNameService

def run(dumpfile = None):
    emu = Emulator()
    base = Base()
    routing = Routing()
    ebgp = Ebgp()
    ibgp = Ibgp()
    ospf = Ospf()

    ###########################################################

    ix100 = base.createInternetExchange(100)
    ix101 = base.createInternetExchange(101)

    ix100.getPeeringLan().setDisplayName('NYC-100')
    ix101.getPeeringLan().setDisplayName('San Jose-101')

    as2 = base.createAutonomousSystem(2)

    as2.createNetwork('net0')

    # Create two routers and link them in a linear structure:
    # ix100 <--> r1 <--> r2 <--> ix101
    # r1 and r2 are BGP routers because they are connected to internet exchanges
    as2.createRouter('r1').joinNetwork('net0').joinNetwork('ix100')
    as2.createRouter('r2').joinNetwork('net0').joinNetwork('ix101')

    as150 = base.createAutonomousSystem(150)
    as150.createNetwork('net0')
    as150.createRouter('router0').joinNetwork('net0').joinNetwork('ix100')
    for i in range(9):
        host = as150.createHost('host_{}'.format(i)).joinNetwork('net0')

    as151 = base.createAutonomousSystem(151)
    as151.createNetwork('net0')
    as151.createRouter('router0').joinNetwork('net0').joinNetwork('ix101')
    for i in range(2):
        host = as151.createHost('host_{}'.format(i)).joinNetwork('net0')

    ebgp.addPrivatePeering(100, 2, 150, abRelationship = PeerRelationship.Provider)
    ebgp.addPrivatePeering(101, 2, 151, abRelationship = PeerRelationship.Provider)

    emu.addLayer(base)
    emu.addLayer(routing)
    emu.addLayer(ebgp)
    emu.addLayer(ibgp)
    emu.addLayer(ospf)

    ###########################################################
    # Create a DNS layer
    dns = DomainNameService()

    # Create two nameservers for the root zone
    dns.install('a-root-server').addZone('.').setMaster()   # Master server
    dns.install('b-root-server').addZone('.')               # Slave server

    # Create nameservers for TLD and ccTLD zones
    # https://itp.cdn.icann.org/en/files/root-system/identification-tld-private-use-24-01-2024-en.pdf
    dns.install('ns-net').addZone('net.')
    dns.install('ns-com').addZone('com.')
    dns.install('ns-seedca-net').addZone('seedCA.net.')
    dns.install('ns-seedca-com').addZone('seedCA.com.')
    dns.install('ns-example32-com').addZone('example32.com.')
    dns.install('ns-bank32-com').addZone('bank32.com.')

    emu.addLayer(dns)

    emu.addBinding(Binding('a-root-server', filter=Filter(asn=150), action=Action.FIRST))
    emu.addBinding(Binding('b-root-server', filter=Filter(asn=150), action=Action.FIRST))
    emu.addBinding(Binding('ns-net', filter=Filter(asn=150), action=Action.FIRST))
    emu.addBinding(Binding('ns-com', filter=Filter(asn=150), action=Action.FIRST))
    emu.addBinding(Binding('ns-seedca-net', filter=Filter(asn=150), action=Action.FIRST))
    emu.addBinding(Binding('ns-seedca-com', filter=Filter(asn=150), action=Action.FIRST))
    emu.addBinding(Binding('ns-example32-com', filter=Filter(asn=150), action=Action.FIRST))
    emu.addBinding(Binding('ns-bank32-com', filter=Filter(asn=150), action=Action.FIRST))

    ###########################################################
    # Create two local DNS servers (virtual nodes).
    ldns = DomainNameCachingService()
    ldns.install('global-dns')

    # Customize the display name (for visualization purpose)
    emu.getVirtualNode('global-dns').setDisplayName('Global DNS')

    as151 = base.getAutonomousSystem(151)
    as151.createHost('local-dns').joinNetwork('net0', address = '10.151.0.53')

    emu.addBinding(Binding('global-dns', filter = Filter(asn=151, nodeName="local-dns")))

    # Add 10.153.0.53 as the local DNS server for all the other nodes
    base.setNameServers(['10.151.0.53'])

    # Add the ldns layer
    emu.addLayer(ldns)

    ###########################################################

    if dumpfile is not None:
        emu.dump(dumpfile)
    else:
        emu.render()
        emu.compile(Docker(), './output', override=True)
        
if __name__ == "__main__":
    run()
