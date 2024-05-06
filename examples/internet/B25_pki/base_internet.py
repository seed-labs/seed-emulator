from seedemu.compiler import Docker
from seedemu.core import Binding, Emulator, Filter, Action
from seedemu.layers import Base, Ebgp, Ibgp, Ospf, Routing, PeerRelationship, EtcHosts

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
    for i in range(6):
        host = as150.createHost('host_{}'.format(i)).joinNetwork('net0')

    as151 = base.createAutonomousSystem(151)
    as151.createNetwork('net0')
    as151.createRouter('router0').joinNetwork('net0').joinNetwork('ix101')
    for i in range(2):
        host = as151.createHost('host_{}'.format(i)).joinNetwork('net0')

    ebgp.addPrivatePeering(100, 2, 150, abRelationship = PeerRelationship.Provider)
    ebgp.addPrivatePeering(101, 2, 151, abRelationship = PeerRelationship.Provider)

    emu.addLayer(base)
    emu.addLayer(EtcHosts())
    emu.addLayer(routing)
    emu.addLayer(ebgp)
    emu.addLayer(ibgp)
    emu.addLayer(ospf)

    ###########################################################

    if dumpfile is not None:
        emu.dump(dumpfile)
    else:
        emu.render()
        emu.compile(Docker(), './output', override=True)
        
if __name__ == "__main__":
    run()
