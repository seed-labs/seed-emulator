from seedsim.layers import Base
from seedsim.core import Registry

base = Base()

as150 = base.createAutonomousSystem(150)
as150.createNetwork("net0")

as151 = base.createAutonomousSystem(151)
as151.createNetwork("net0") 
as151.createNetwork("net1")

as151_r1 = as151.createRouter("r1")
as151_r1.joinNetworkByName("net0")

as151_r2 = as151.createRouter("r2")
as151_r2.joinNetworkByName("net0")

as151_h1 = as151.createHost("h1")
as151_h1.joinNetworkByName("net0")

print(base)
print(Registry())