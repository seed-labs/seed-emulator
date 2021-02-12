from seedsim.layers import Base, Routing, Ebgp, DomainNameService, DomainNameServer, DomainNameCachingService, Dnssec, WebService
from seedsim.core import Simulator
from seedsim.compiler import Docker

sim = Simulator()

base = Base()
routing = Routing()
ebgp = Ebgp()
web = WebService()
dns = DomainNameService()
dnssec = Dnssec()
ldns = DomainNameCachingService()

###############################################################################

base.createInternetExchange(100)

###############################################################################

example_com = dns.getZone('example.com.')

###############################################################################

as150 = base.createAutonomousSystem(150)

root_server = as150.createHost('root_server')

as150_router = as150.createRouter('router0')

as150_net = as150.createNetwork('net0')

routing.addDirect(150, 'net0')

root_server.joinNetwork('net0')
as150_router.joinNetwork('net0')

as150_router.joinNetwork('ix100')

dns.installByName(150, 'root_server').addZone(dns.getZone('.'))

###############################################################################

as151 = base.createAutonomousSystem(151)

com_server = as151.createHost('com_server')

as151_router = as151.createRouter('router0')

as151_net = as151.createNetwork('net0')

routing.addDirect(151, 'net0')

com_server.joinNetwork('net0')
as151_router.joinNetwork('net0')

as151_router.joinNetwork('ix100')

dns.installByName(151, 'com_server').addZone(dns.getZone('com.'))

###############################################################################

as152 = base.createAutonomousSystem(152)

example_com_web = as152.createHost('example_web')
web.installByName(152, 'example_web')

example_com_server = as152.createHost('example_com_server')

as152_router = as152.createRouter('router0')

as152_net = as152.createNetwork('net0')

routing.addDirect(152, 'net0')

example_com_web.joinNetwork('net0', '10.152.0.200')
example_com_server.joinNetwork('net0')
as152_router.joinNetwork('net0')

as152_router.joinNetwork('ix100')

dns.installByName(152, 'example_com_server').addZone(dns.getZone('example.com.'))

example_com.addRecord('@ A 10.152.0.200')

###############################################################################

as153 = base.createAutonomousSystem(153)

local_dns = as153.createHost('local_dns')
ldns.installByName(153, 'local_dns')

client = as153.createHost('client')

as153_router = as153.createRouter('router0')

as153_net = as153.createNetwork('net0')

routing.addDirect(153, 'net0')

local_dns.joinNetwork('net0')
client.joinNetwork('net0')
as153_router.joinNetwork('net0')

as153_router.joinNetwork('ix100')

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

sim.addLayer(base)
sim.addLayer(routing)
sim.addLayer(ebgp)
sim.addLayer(dns)
sim.addLayer(ldns)
sim.addLayer(dnssec)
sim.addLayer(web)

sim.render()

###############################################################################

sim.compile(Docker(), './dns-infra')