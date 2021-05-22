# Emulator merging: examples

## Case 0: ovelapping IX, no overlapping AS, RS-peering pre-configured

```py
# Scenario: two emulators:
#   - EmulatorA has AS150 and IX100, and many other ASes in IX100 (but no 
#     AS151). AS150 is peered with IX100's RS.
#   - EmulatorB has AS151 and IX100, and many other ASes in IX100 (but no 
#     AS150). AS151 is peered with IX100's RS.
#
# Goal: merge A and B, as AS150 and AS151 both peered with RS at IX100, they
# connect the two emulations.

mergedEmulator = emulatorA.merge(emulatorB)

# that's it.
```

## Case 1: no overlapping IX or AS, create new common IX

```py
# Scenario: two emulators:
#   - EmulatorA has AS150 and IX101, and many other ASes in IX101.
#   - EmulatorB has AS151 and IX102, and many other ASes in IX102.
#
# Goal: merge A and B, create new IX100, have AS150 and AS151 peer at IX100.

###############################################################################
# case A: create the IX after merging
###############################################################################
mergedEmulator = emulatorA.merge(emulatorB)

newBase = mergedEmulator.getLayer('Base')

ix100 = newBase.createInternetExchange(100)

as150 = newBase.getAutonomousSystem(150)
as151 = newBase.getAutonomousSystem(151)

as150.getRouter('router0').joinNetwork(ix100)
as151.getRouter('router0').joinNetwork(ix100)

mergedEmulator.getLayer('Bgp').addRsPeering(100, 150)
mergedEmulator.getLayer('Bgp').addRsPeering(100, 151)

###############################################################################
# case B: create the IX before merging
###############################################################################
baseA = emulatorA.getLayer('Base')
baseB = emulatorB.getLayer('Base')

ix100A = baseA.createInternetExchange(100)
ix100B = baseB.createInternetExchange(100)

as150 = baseA.getAutonomousSystem(150)
as151 = baseB.getAutonomousSystem(151)

as150.getRouter('router0').joinNetwork(ix100A)
as151.getRouter('router0').joinNetwork(ix100B)

emulatorA.getLayer('Bgp').addRsPeering(100, 150)
emulatorB.getLayer('Bgp').addRsPeering(100, 151)

mergedEmulator = emulatorA.merge(emulatorB)
```

## Case 3: no overlapping IX or AS, reuse existing IX

```py
# Scenario: two emulators:
#   - EmulatorA has AS150 and IX101, and many other ASes in IX101.
#   - EmulatorB has AS151 and IX102, and many other ASes in IX102. AS151
#     peered with IX102's RS.
#
# Goal: merge A and B, have AS150 and AS151 peer at IX102 via RS.

###############################################################################
# case A: join the IX after merging
###############################################################################
mergedEmulator = emulatorA.merge(emulatorB)

newBase = mergedEmulator.getLayer('Base')

ix102 = newBase.getInternetExchange(102)

as150 = newBase.getAutonomousSystem(150)

as150.getRouter('router0').joinNetwork(ix100)

mergedEmulator.getLayer('Bgp').addRsPeering(100, 150)

###############################################################################
# case B: join the IX before merging
###############################################################################
baseA = emulatorA.getLayer('Base')
baseB = emulatorB.getLayer('Base')

ix102A = baseA.createInternetExchange(102)

as150 = baseA.getAutonomousSystem(150)

as150.getRouter('router0').joinNetwork(ix102A)

emulatorA.getLayer('Bgp').addRsPeering(102, 150)

mergedEmulator = emulatorA.merge(emulatorB)
```

## Case 4: overlapping AS, but no common network

```py
# Scenario: two emulators:
#   - EmulatorA has AS150 and IX100, and many other ASes in IX100.
#       - in this AS150, one router exists with name r0
#   - EmulatorB has AS150 and IX101, and many other ASes in IX101.
#       - in this AS150, one router exists with name r0
#
# Goal: merge A and B, let two AS150 be on their own.

# without renaming manually, objects (hosts, networks, routers) with same name
# will be remaned to "emulator.getName() + '_' + object.getName()"
emulatorB.getAutonomousSystem(150).getRouter('r0').rename('r1')

mergedEmulator = emulatorA.merge(emulatorB)
```

## Case 5: overlapping AS, but no common network, connect the AS

```py
# Scenario: two emulators:
#   - EmulatorA has AS150 and IX100, and many other ASes in IX100.
#       - in this AS150, one router exists with name r0
#   - EmulatorB has AS150 and IX101, and many other ASes in IX101.
#       - in this AS150, one router exists with name r0
#
# Goal: merge A and B, connect two AS150 with a new internal network.

# without renaming manually, objects (hosts, networks, routers) with same name
# will be remaned to "emulator.getName() + '_' + object.getName()"
emulatorB.getAutonomousSystem(150).getRouter('r0').rename('r1')

mergedEmulator = emulatorA.merge(emulatorB)

new_150 = mergedEmulator.getAutonomousSystem(150)

net1 = new_150.createNetwork('net1')

new_150.getRouter('r0').joinNetwork(net1)
new_150.getRouter('r1').joinNetwork(net1)
```

## Case 6: overlapping AS, has common network, allow both networks to exist.

```py
# Scenario: two emulators:
#   - EmulatorA has AS150 and IX100, and many other ASes in IX100.
#       - in this AS150, one internal network exist with name net0, prefix 
#         10.150.0.0/24
#   - EmulatorB has AS150 and IX101, and many other ASes in IX101.
#       - in this AS150, one internal network exist with name net0, prefix 
#         10.150.0.0/24
#
# Goal: Keep both networks as-it. So the 10.150.0.0/24 network is now an anycast
# network announced by AS150 at both exchanges. Note that the two AS150s are not
# connected.

# without renaming manually, objects (hosts, networks, routers) with same name
# will be remaned to "emulator.getName() + '_' + object.getName()"
emulatorB.getAutonomousSystem(150).getRouter('r0').rename('r1')
emulatorB.getAutonomousSystem(150).getNetwork('net0').rename('net1')

mergedEmulator = emulatorA.merge(emulatorB)
```

## Case 7: overlapping AS, has common network, renumber one of the network, connect the AS

```py
# Scenario: two emulators:
#   - EmulatorA has AS150 and IX100, and many other ASes in IX100.
#       - in this AS150, one internal network exist with name net0, prefix 
#         10.150.0.0/24
#   - EmulatorB has AS150 and IX101, and many other ASes in IX101.
#       - in this AS150, one internal network exist with name net0, prefix 
#         10.150.0.0/24
#
# Goal: Renumber the network in the emulator B to 10.150.254.0/24, connect the
# emulators with a new network.

# without renaming manually, objects (hosts, networks, routers) with same name
# will be remaned to "emulator.getName() + '_' + object.getName()"
emulatorB.getAutonomousSystem(150).getRouter('r0').rename('r1') 
netB = emulatorB.getAutonomousSystem(150).getNetwork('net0')

netB.rename('net254')
netB.renumber('10.150.254.0/24')

mergedEmulator = emulatorA.merge(emulatorB)

new_150 = mergedEmulator.getAutonomousSystem(150)

net1 = new_150.createNetwork('net1')

new_150.getRouter('r0').joinNetwork(net1)
new_150.getRouter('r1').joinNetwork(net1)
```

## Case 8: overlapping AS, no common network, create new router to connect two networks

```py
# Scenario: two emulators:
#   - EmulatorA has AS150 and IX100, and many other ASes in IX100.
#       - in this AS150, there's router r0 and network net0.
#   - EmulatorB has AS150 and IX101, and many other ASes in IX101.
#       - in this AS150, there's router r0 and network net1.
#
# Goal: merge A and B, connect two AS150 with a new router joining both net0 and
# net1.

# without renaming manually, objects (hosts, networks, routers) with same name
# will be remaned to "emulator.getName() + '_' + object.getName()"
emulatorB.getAutonomousSystem(150).getRouter('r0').rename('r1') 

mergedEmulator = emulatorA.merge(emulatorB)

new150 = mergedEmulator.getAutonomousSystem(150)

r2 = new150.createRouter('r2')

r2.joinNetworkByName('net0')
r2.joinNetworkByName('net1')
```
