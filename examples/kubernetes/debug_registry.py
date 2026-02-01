from seedemu.core import Emulator
from seedemu.layers import Base

emu = Emulator()
base = Base()
emu.addLayer(base)

net100 = base.createInternetExchange(100)
base.createAutonomousSystem(150)

emu.render()

print("\nREGISTRY KEYS:")
for key in emu.getRegistry().getAll().keys():
    print(key)

print("\nNetwork Object Dir:")
print(dir(net100))
