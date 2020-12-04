from seedsim.layers import Base, Routing, Ebgp, Ibgp, Ospf, Mpls
from seedsim.layers import WebService, DomainNameService, DomainNameCachingService, Dnssec
from seedsim.layers import CyrmuIpOriginService, ReverseDomainNameService
from seedsim.compiler import Docker
from seedsim.compiler import Compiler

base = Base()
routing = Routing()
ebgp = Ebgp()
ibgp = Ibgp()
ospf = Ospf()
mpls = Mpls()
web = WebService()
dns = DomainNameService()
ldns = DomainNameCachingService()
dnssec = Dnssec()
cyrmu = CyrmuIpOriginService()
rdns = ReverseDomainNameService()

###############################################################################

rendrer = Renderer()

###############################################################################

docker_compiler = Docker()

###############################################################################