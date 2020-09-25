from seedsim.layers import Base, Ebgp
from seedsim.renderer import Renderer

base = Base()

ix100 = base.createInternetExchange(100)

as150 = base.createAutonomousSystem(150)
as150.createNetwork("net0")
as150_r1 = as150.createRouter("r1")
as150_r1.joinNetworkByName("ix100")
as150_h1 = as150.createHost("h1")
as150_h1.joinNetworkByName("net0")


as151 = base.createAutonomousSystem(151)
as151.createNetwork("net0") 
as151_r1 = as151.createRouter("r1")
as151_r1.joinNetworkByName("ix100")
as151_h1 = as151.createHost("h1")
as151_h1.joinNetworkByName("net0")

ebgp = Ebgp()
ebgp.addPrivatePeering(100, 150, 151)

r = Renderer()

r.addLayer(ebgp)
r.addLayer(base)


print("Layers ========")
print(r)

print("Renderer output ========")

r.render()