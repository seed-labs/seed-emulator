from seedemu.layers import Base, Routing, Mpls, Ebgp
from seedemu.renderer import Renderer
from seedemu.compiler import GcpDistributedDocker
from seedemu.core import Registry

# topology:
#
#        |  AS150's MPLS backbone                         |
#        |          ____________ ibgp ___________         |
#        |         /                             \        |
# as151 -|- as150_r1 -- as150_r2 -- as150_r3 -- as150_r4 -|- as152 
#        |                                                |
# Note that IBGP session is only between as150_r1 and as150_r4. Meaning as150_r2
# and as150_r3 does not have routing table from as151 and as152.
#
# 
# traceroute (as152 to as151):
#
# Start: 2020-10-22T19:37:07+0000
# HOST: 0e58e675b98b Loss%   Snt   Last   Avg  Best  Wrst StDev
#  1.|-- 10.152.0.254  0.0%    10    0.1   0.1   0.1   0.1   0.0
#  2.|-- 10.101.0.150  0.0%    10    0.1   0.1   0.1   0.2   0.0
#  3.|-- ???          100.0    10    0.0   0.0   0.0   0.0   0.0
#  4.|-- ???          100.0    10    0.0   0.0   0.0   0.0   0.0
#  5.|-- 10.150.0.254  0.0%    10    0.1   0.1   0.1   0.2   0.0
#  6.|-- 10.100.0.151  0.0%    10    0.3   0.2   0.1   0.3   0.1
#  7.|-- 10.151.0.71   0.0%    10    0.2   0.2   0.1   0.3   0.0
#
# hop 3, 4 is mpls router (as150_r2 and as150_r3), they do not have the route to
# as151 or as152, so their response can't get back.
# 
#
# tcpdump on as150_r2, interface net1:
# 
# root@d5d8ad0d6d48 / # tcpdump -i net1 -n mpls
# tcpdump: verbose output suppressed, use -v or -vv for full protocol decode
# listening on net1, link-type EN10MB (Ethernet), capture size 262144 bytes
# 19:39:33.831880 MPLS (label 21, exp 0, [S], ttl 61) IP 10.152.0.71 > 10.151.0.71: ICMP echo request, id 123, seq 1, length 64
# 19:39:33.832051 MPLS (label 19, exp 0, [S], ttl 61) IP 10.151.0.71 > 10.152.0.71: ICMP echo reply, id 123, seq 1, length 64
# 19:39:34.877246 MPLS (label 21, exp 0, [S], ttl 61) IP 10.152.0.71 > 10.151.0.71: ICMP echo request, id 123, seq 2, length 64
# 19:39:34.877314 MPLS (label 19, exp 0, [S], ttl 61) IP 10.151.0.71 > 10.152.0.71: ICMP echo reply, id 123, seq 2, length 64
# ^C
# 4 packets captured
# 4 packets received by filter
# 0 packets dropped by kernel

base = Base()
routing = Routing()
mpls = Mpls()
bgp = Ebgp()

ix100 = base.createInternetExchange(100)
ix101 = base.createInternetExchange(101)

as150 = base.createAutonomousSystem(150)

as150.createNetwork('net0')
as150.createNetwork('net1')
as150.createNetwork('net2')

r1 = as150.createRouter('r1')
r2 = as150.createRouter('r2')
r3 = as150.createRouter('r3')
r4 = as150.createRouter('r4')

r1.joinNetworkByName('ix100')
r1.joinNetworkByName('net0')

r2.joinNetworkByName('net0')
r2.joinNetworkByName('net1')

r3.joinNetworkByName('net1')
r3.joinNetworkByName('net2')

r4.joinNetworkByName('net2')
r4.joinNetworkByName('ix101')

mpls.enableOn(150)

as151 = base.createAutonomousSystem(151)
as152 = base.createAutonomousSystem(152)

as151.createNetwork('net0')
as152.createNetwork('net0')




as151.createHost('h').joinNetworkByName('net0')
as152.createHost('h').joinNetworkByName('net0')

as151_r = as151.createRouter('r')
as151_r.joinNetworkByName('net0')
as151_r.joinNetworkByName('ix100')

as152_r = as152.createRouter('r')
as152_r.joinNetworkByName('net0')
as152_r.joinNetworkByName('ix101')

bgp.addPrivatePeering(100, 150, 151)
bgp.addPrivatePeering(101, 150, 152)

r = Renderer()

r.addLayer(base)
r.addLayer(routing)
r.addLayer(mpls)
r.addLayer(bgp)

r.render()

c = GcpDistributedDocker()

c.compile('test')

mpls.createGraphs()
for graph in mpls.getGraphs().values():
    print(graph)
    print(graph.toGraphviz())