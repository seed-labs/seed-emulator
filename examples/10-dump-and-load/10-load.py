from seedsim.core import Simulator
from seedsim.layers import Base
from seedsim.compiler import Docker

###############################################################################

sim = Simulator()

sim.load('10-dump.bin')

###############################################################################

base: Base = sim.getLayer('Base')

print(base)

###############################################################################

sim.render()

###############################################################################

sim.compile(Docker(), './dump-and-load')