from seedemu.core import Emulator
from seedemu.layers import Base
from seedemu.compiler import Docker

###############################################################################

sim = Emulator()

sim.load('10-dump.bin')

###############################################################################

base: Base = sim.getLayer('Base')

print(base)

###############################################################################

sim.render()

###############################################################################

sim.compile(Docker(), './dump-and-load')