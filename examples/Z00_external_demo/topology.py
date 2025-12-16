from seedemu.compiler import Docker
from seedemu.core import Emulator
from seedemu.layers import Base, Routing
from seedemu.layers.external import ExternalComponent, ExternalComponentLayer
from seedemu.core.ExternalEmulation import ExternalEmuSpec


def main():
    emu = Emulator()
    base = Base()
    routing = Routing()
    ext_layer = ExternalComponentLayer()

    asn = 65000
    as0 = base.createAutonomousSystem(asn)

    # Internal network (so r0 has a "normal" interface)
    as0.createNetwork("net0", prefix="10.65.0.0/24")
    r0 = as0.createRouter("r0")
    r0.joinNetwork("net0")

    # Create IX100 and connect r0 to it with a MANUAL IP (no auto ASN->IX mapping)
    base.createInternetExchange(100)          # creates network name "ix100"
    r0.joinNetwork("ix100", "10.0.0.1")       # IMPORTANT: no "/24" here

    # External component definition (what Task 2 is about)
    ext = ExternalComponent(
        name="ext-r0",
        role="router",
        asn=asn,
        impl_type="generic",
    )

    ext.addInterface(
        name="eth0",
        network="ix100",
        ip="10.0.0.2/24",
        mac="02:00:00:00:00:01",
    )

    ext_layer.addComponent(ext)
    emu.addLayer(base)
    emu.addLayer(routing)
    emu.addLayer(ext_layer)

    
    emu.render()
    print("Registered externals in Emulator:", list(emu.getExternalComponents().keys()))

    emu.compile(Docker(), output="output", override=True)
    print("Compiled to .\\output")

    print("External component definition created:")
    print(f"  Name: {ext.name}")
    print(f"  Role: {ext.role}")
    print(f"  ASN:  {ext.asn}")
    for iface in ext.interfaces:
        print(f"  Interface {iface.name}: network={iface.network}, ip={iface.ip}, mac={iface.mac}")

if __name__ == "__main__":
    main()
