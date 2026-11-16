from seedemu.layers import Base, Routing, Ebgp, Ospf, Ibgp, WebService, DomainNameService, DomainNameCachingService, Reality, CymruIpOriginService, Dnssec, ReverseDomainNameService, Mpls
from seedemu.renderer import Renderer
from seedemu.core import Registry
from seedemu.compiler import Docker, DistributedDocker, Graphviz, GcpDistributedDocker

base = Base()

ix100 = base.createInternetExchange(100)
ix101 = base.createInternetExchange(101)


as150 = base.createAutonomousSystem(150)
as150.createNetwork("net0")
as150.createNetwork("net-link").setDefaultLinkProperties(latency = 15, bandwidth = 1000000)
as150.createNetwork("net1")

as150_r1 = as150.createRouter("r1")
as150_r1.joinNetworkByName("ix100")
as150_r1.joinNetworkByName("net0")
as150_r1.joinNetworkByName("net-link")
as150_h1 = as150.createHost("h1")
as150_h1.joinNetworkByName("net0")
as150_r2 = as150.createRouter("r2")
as150_r2.joinNetworkByName("ix101")
as150_r2.joinNetworkByName("net-link")
as150_r2.joinNetworkByName("net1")
as150_h2 = as150.createHost("h2")
as150_h2.joinNetworkByName("net1")
as150_h3 = as150.createHost("h3")
as150_h3.joinNetworkByName("net1")

mpls = Mpls()
#mpls.enableOn(150)

as151 = base.createAutonomousSystem(151)
as151.createNetwork("net0") 
as151_r1 = as151.createRouter("r1")
as151_r1.joinNetworkByName("ix100").setLinkProperties(latency = 120)
as151_r1.joinNetworkByName("net0")
as151_h1 = as151.createHost("h1")
as151_h1.joinNetworkByName("net0")
as151_h2 = as151.createHost("h2")
as151_h2.joinNetworkByName("net0")
as151_h3 = as151.createHost("h3")
as151_h3.joinNetworkByName("net0")

as152 = base.createAutonomousSystem(152)
as152.createNetwork("net0")
as152_r1 = as152.createRouter("r1")
as152_r1.joinNetworkByName("ix101")
as152_r1.joinNetworkByName("net0")
as152_h1 = as152.createHost("h1")
as152_h1.joinNetworkByName("net0")

ebgp = Ebgp()
ebgp.addPrivatePeering(100, 150, 151)
ebgp.addPrivatePeering(101, 150, 152)
ebgp.addRsPeer(100, 150)
ebgp.addRsPeer(100, 151)

routing = Routing()




r = Renderer()

ospf = Ospf()
ibgp = Ibgp()

ws = WebService()

ws.installOnAll(150) # install on all hosts
ws.installOn(as151_h1)

dns = DomainNameService()
dns.getZone('example.com.').addRecord('@   A 127.0.0.1')
dns.getZone('example.com.').addRecord('www A 127.0.0.1')
dns.getZone('example2.com.').resolveTo('test', as151_h1)
dns.hostZoneOn('example.com.', as151_h1)
dns.hostZoneOn('example2.com.', as151_h1)
dns.hostZoneOn('com.', as150_h2)
dns.hostZoneOn('.', as150_h1)

ldns = DomainNameCachingService(autoRoot = True, setResolvconf = True)
ldns.installOn(as151_h3)
ldns.installOn(as150_h3)

real = Reality()
as11872 = base.createAutonomousSystem(11872)
as11872_rw = real.createRealWorldRouter(as11872)
as11872_rw.joinNetworkByName("ix100", "10.100.0.118")
ebgp.addRsPeer(100, 11872)

real.enableRealWorldAccessByName(150, 'net0')

cymru = CymruIpOriginService()
cymru.installOn(as150_h1)

rdns = ReverseDomainNameService()
rdns.installOn(as150_h1)
dns.hostZoneOn('arpa.', as150_h2)

dnssec = Dnssec()
dnssec.enableOn('example.com.')
dnssec.enableOn('com.')
dnssec.enableOn('.')

r.addLayer(ospf)
r.addLayer(routing)
r.addLayer(ebgp)
r.addLayer(base)
r.addLayer(ibgp)
r.addLayer(ws)
r.addLayer(dns)
r.addLayer(ldns)
r.addLayer(real)
r.addLayer(cymru)
r.addLayer(dnssec)
r.addLayer(rdns)
r.addLayer(mpls)

print("Layers =================")
print(r)

print("\n\n\n\nRenderer output ========")
r.render()

print("\n\n\n\nRegistry ===============")
reg = Registry()
print(reg)

print("\n\n\n\nCompiler output ========")
dcompiler = Docker()
#dcompiler.compile('./test/')

#ddcompiler = DistributedDocker()
#ddcompiler.compile('./test/')

#gcompiler = Graphviz()
#gcompiler.compile('./test/_graphs')

gdcompiler = GcpDistributedDocker()
gdcompiler.compile('./test/')