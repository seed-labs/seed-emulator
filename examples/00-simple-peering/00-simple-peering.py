from seedemu.layers import Base, Routing, Ebgp
from seedemu.services import WebService
from seedemu.compiler import Docker
from seedemu.core import Emulator, Binding, Filter

emu = Emulator()

base = Base()
routing = Routing()
ebgp = Ebgp()
web = WebService()

###############################################################################

base.createInternetExchange(100)

###############################################################################

as150 = base.createAutonomousSystem(150)

as150_web = as150.createHost('web')
web.install('web150')
emu.addBinding(Binding('web150', filter = Filter(nodeName = 'web', asn = 150)))

as150_router = as150.createRouter('router0')
as150_net = as150.createNetwork('net0')

routing.addDirect(150, 'net0')

as150_web.joinNetwork('net0')
as150_router.joinNetwork('net0')

as150_router.joinNetwork('ix100')

###############################################################################

as151 = base.createAutonomousSystem(151)

as151_web = as151.createHost('web')
web.install('web151')
emu.addBinding(Binding('web151', filter = Filter(nodeName = 'web', asn = 151)))

as151_router = as151.createRouter('router0')

as151_net = as151.createNetwork('net0')

routing.addDirect(151, 'net0')

as151_web.joinNetwork('net0')
as151_router.joinNetwork('net0')

as151_router.joinNetwork('ix100')

###############################################################################

as152 = base.createAutonomousSystem(152)

as152_web = as152.createHost('web')
web.install('web152')
emu.addBinding(Binding('web152', filter = Filter(nodeName = 'web', asn = 152)))

as152_router = as152.createRouter('router0')

as152_net = as152.createNetwork('net0')

routing.addDirect(152, 'net0')

as152_web.joinNetwork('net0')
as152_router.joinNetwork('net0')

as152_router.joinNetwork('ix100')

###############################################################################

ebgp.addRsPeer(100, 150)
ebgp.addRsPeer(100, 151)
ebgp.addRsPeer(100, 152)

###############################################################################

emu.addLayer(base)
emu.addLayer(routing)
emu.addLayer(ebgp)
emu.addLayer(web)

emu.render()

###############################################################################

emu.compile(Docker(), './output')
