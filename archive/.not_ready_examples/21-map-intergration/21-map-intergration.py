from seedemu.layers import Base, Routing, Ebgp
from seedemu.services import WebService
from seedemu.compiler import Docker
from seedemu.core import Emulator, Binding, Filter

# Initialize the emulator and layers
emu = Emulator()
base = Base()
routing = Routing()
ebgp = Ebgp()
web = WebService()

###############################################################################
# Create an Internet Exchange
ix100 = base.createInternetExchange(100)

# Set map metadata
ix100_net = ix100.getPeeringLan()
ix100_net.setDisplayName('Seattle Internet Exchange')
ix100_net.setDescription('The largest IX in Seattle.')

###############################################################################
# Create and set up the AS 150

# Create an autonomous system 
as150 = base.createAutonomousSystem(150)

# Create a network 
net150 = as150.createNetwork('net0')

# Set map metadata
net150.setDisplayName('AS150 Backbone')
net150.setDescription('This is the main network of AS150.')

# Create a router and connect it to two networks
as150_router = as150.createRouter('router0')
as150_router.joinNetwork('net0')
as150_router.joinNetwork('ix100')

# Set more map metadata
as150_router.setDisplayName('AS150 Core Router')
as150_router.setDescription('The core router of AS150.')

# Create a host called web and connect it to a network
as150.createHost('web').joinNetwork('net0')

# Create a web service on virtual node, give this node a name
web.install('web150')

# Bind the virtual node to a host 
emu.addBinding(Binding('web150', filter = Filter(nodeName = 'web', asn = 150)))


###############################################################################
# Create and set up the AS 151
# It is similar to what is done to AS 150

as151 = base.createAutonomousSystem(151)
as151.createNetwork('net0')

as151.createHost('web').joinNetwork('net0')
web.install('web151')
emu.addBinding(Binding('web151', filter = Filter(nodeName = 'web', asn = 151)))

as151_router = as151.createRouter('router0')
as151_router.joinNetwork('net0')
as151_router.joinNetwork('ix100')

###############################################################################
# Create and set up the AS 152
# It is similar to what is done to AS 150

as152 = base.createAutonomousSystem(152)
as152.createNetwork('net0')

as152.createHost('web').joinNetwork('net0')
web.install('web152')
emu.addBinding(Binding('web152', filter = Filter(nodeName = 'web', asn = 152)))

as152_router = as152.createRouter('router0')
as152_router.joinNetwork('net0')
as152_router.joinNetwork('ix100')

###############################################################################
# Peering the ASes

ebgp.addRsPeer(100, 150)
ebgp.addRsPeer(100, 151)
ebgp.addRsPeer(100, 152)

###############################################################################
# Rendering 

emu.addLayer(base)
emu.addLayer(routing)
emu.addLayer(ebgp)
emu.addLayer(web)

emu.render()

###############################################################################
# Compilation

emu.compile(Docker(internetMapEnabled = True), './output')
