from seedsim.core import Simulator
from seedsim.layers import Base, Routing, Ebgp
from seedsim.components import BgpAttackerComponent

###############################################################################

sim = Simulator()

base = Base()
routing = Routing()
ebgp = Ebgp()

bgp_attack = BgpAttackerComponent()

###############################################################################

base.createInternetExchange