from seedemu.core import Simulator
from seedemu.layers import Base
from seedemu.compiler import Docker

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