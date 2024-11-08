from seedemu.layers import Base, Routing, Ebgp, Dnssec
from seedemu.services import DomainNameService, DomainNameCachingService, WebService, CymruIpOriginService, ReverseDomainNameService
from seedemu.core import Emulator, Binding, Filter
from seedemu.compiler import Docker

emu = Emulator()

base = Base()
routing = Routing()
ebgp = Ebgp()
web = WebService()
dns = DomainNameService(autoNameServer = True)
dnssec = Dnssec()
ldns = DomainNameCachingService(autoRoot = True)
rdns = ReverseDomainNameService()
ip_origin = CymruIpOriginService()

###############################################################################

base.createInternetExchange(100)

###############################################################################

example_com = dns.getZone('example.com.')

###############################################################################

as150 = base.createAutonomousSystem(150)

root_server = as150.createHost('root_server')

as150_router = as150.createRouter('router0')

as150_net = as150.createNetwork('net0')



root_server.joinNetwork('net0')
as150_router.joinNetwork('net0')

as150_router.joinNetwork('ix100')

dns.install('root_server').addZone('.')
emu.addBinding(Binding('root_server', filter = Filter(asn = 150, nodeName = 'root_server')))

###############################################################################

as151 = base.createAutonomousSystem(151)

com_server = as151.createHost('com_server')
arpa_server = as151.createHost('arpa_server')

as151_router = as151.createRouter('router0')

as151_net = as151.createNetwork('net0')



com_server.joinNetwork('net0')
arpa_server.joinNetwork('net0')
as151_router.joinNetwork('net0')

as151_router.joinNetwork('ix100')

dns.install('com_server').addZone('com.')
dns.install('arpa_server').addZone('arpa.')

emu.addBinding(Binding('com_server', filter = Filter(asn = 151, nodeName = 'com_server')))
emu.addBinding(Binding('arpa_server', filter = Filter(asn = 151, nodeName = 'arpa_server')))

###############################################################################

as152 = base.createAutonomousSystem(152)

example_com_web = as152.createHost('example_web')

web.install('example_web')
emu.addBinding(Binding('example_web', filter = Filter(asn = 152, nodeName = 'example_web')))

example_com_server = as152.createHost('example_com_server')
cymru_com_server = as152.createHost('cymru_com_server')
v4_rdns_server = as152.createHost('v4_rdns_server')

as152_router = as152.createRouter('router0')

as152_net = as152.createNetwork('net0')



example_com_web.joinNetwork('net0', '10.152.0.200')
example_com.addRecord('@ A 10.152.0.100')

example_com_server.joinNetwork('net0')
cymru_com_server.joinNetwork('net0')
v4_rdns_server.joinNetwork('net0')
as152_router.joinNetwork('net0')

as152_router.joinNetwork('ix100')

dns.install('example_com_server').addZone('example.com.')
dns.install('cymru_com_server').addZone('cymru.com.')
dns.install('v4_rdns_server').addZone('in-addr.arpa.')

emu.addBinding(Binding('example_com_server', filter = Filter(asn = 152, nodeName = 'example_com_server')))
emu.addBinding(Binding('cymru_com_server', filter = Filter(asn = 152, nodeName = 'cymru_com_server')))
emu.addBinding(Binding('v4_rdns_server', filter = Filter(asn = 152, nodeName = 'v4_rdns_server')))

###############################################################################

as153 = base.createAutonomousSystem(153)

local_dns = as153.createHost('local_dns')

ldns.install('local_dns').setConfigureResolvconf(True)
emu.addBinding(Binding('local_dns', filter = Filter(asn = 153, nodeName = 'local_dns')))

client = as153.createHost('client')

as153_router = as153.createRouter('router0')

as153_net = as153.createNetwork('net0')



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

emu.addLayer(base)
emu.addLayer(routing)
emu.addLayer(ebgp)
emu.addLayer(dns)
emu.addLayer(ldns)
emu.addLayer(dnssec)
emu.addLayer(web)
emu.addLayer(rdns)
emu.addLayer(ip_origin)

emu.render()

###############################################################################

emu.compile(Docker(), './dns-misc')