from seedsim.layers import Base, Routing, Ebgp, DomainNameService, DomainNameCachingService, Dnssec, WebService
from seedsim.renderer import Renderer
from seedsim.compiler import Docker

base = Base()
routing = Routing()
ebgp = Ebgp()
web = WebService()
dns = DomainNameService()
dnssec = Dnssec()
ldns = DomainNameCachingService(setResolvconf = True)

renderer = Renderer()
docker_compiler = Docker()

###############################################################################

base.createInternetExchange(100)

###############################################################################

example_com = dns.getZone('example.com.')

###############################################################################

as150 = base.createAutonomousSystem(150)

root_server = as150.createHost('root_server')

as150_router = as150.createRouter('router0')

as150_net = as150.createNetwork('net0')

routing.addDirect(as150_net)

root_server.joinNetwork(as150_net)
as150_router.joinNetwork(as150_net)

as150_router.joinNetworkByName('ix100')

dns.hostZoneOn('.', root_server)

###############################################################################

as151 = base.createAutonomousSystem(151)

com_server = as151.createHost('com_server')

as151_router = as151.createRouter('router0')

as151_net = as151.createNetwork('net0')

routing.addDirect(as151_net)

com_server.joinNetwork(as151_net)
as151_router.joinNetwork(as151_net)

as151_router.joinNetworkByName('ix100')

dns.hostZoneOn('com.', com_server)

###############################################################################

as152 = base.createAutonomousSystem(152)

example_com_web = as152.createHost('example_web')
web.installOn(example_com_web)

example_com_server = as152.createHost('example_com_server')

as152_router = as152.createRouter('router0')

as152_net = as152.createNetwork('net0')

routing.addDirect(as152_net)

example_com_web.joinNetwork(as152_net)
example_com_server.joinNetwork(as152_net)
as152_router.joinNetwork(as152_net)

as152_router.joinNetworkByName('ix100')

dns.hostZoneOn('example.com.', example_com_server)

example_com.addRecord(
    '@ A {}'.format(example_com_web.getInterfaces()[0].getAddress())
)

###############################################################################

as153 = base.createAutonomousSystem(153)

local_dns = as153.createHost('local_dns')
ldns.installOn(local_dns)

client = as153.createHost('client')

as153_router = as153.createRouter('router0')

as153_net = as153.createNetwork('net0')

routing.addDirect(as153_net)

local_dns.joinNetwork(as153_net)
client.joinNetwork(as153_net)
as153_router.joinNetwork(as153_net)

as153_router.joinNetworkByName('ix100')

###############################################################################

dnssec.enableOn('.')
dnssec.enableOn('com.')
dnssec.enableOn('example.com.')

###############################################################################

ebgp.addRsPeer(100, 150)
ebgp.addRsPeer(100, 151)
ebgp.addRsPeer(100, 152)
ebgp.addRsPeer(100, 153)

###############################################################################

renderer.addLayer(base)
renderer.addLayer(routing)
renderer.addLayer(ebgp)
renderer.addLayer(dns)
renderer.addLayer(ldns)
renderer.addLayer(dnssec)
renderer.addLayer(web)

renderer.render()

###############################################################################

docker_compiler.compile('./dns-infra')