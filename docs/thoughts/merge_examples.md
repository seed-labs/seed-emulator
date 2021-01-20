# Simulator merging: examples

## Case 0: ovelapping IX, no overlapping AS, RS-peering pre-configured

```py
# Scenario: two simulators:
#   - SimulatorA has AS150 and IX100, and many other ASes in IX100 (but no 
#     AS151). AS150 is peered with IX100's RS.
#   - SimulatorB has AS151 and IX100, and many other ASes in IX100 (but no 
#     AS150). AS151 is peered with IX100's RS.
#
# Goal: merge A and B, as AS150 and AS151 both peered with RS at IX100, they
# connect the two simulations.

mergedSimulator = simulatorA.merge(simulatorB)

# that's it.
```

## Case 1: no overlapping IX or AS, create new common IX

```py
# Scenario: two simulators:
#   - SimulatorA has AS150 and IX101, and many other ASes in IX101.
#   - SimulatorB has AS151 and IX102, and many other ASes in IX102.
#
# Goal: merge A and B, create new IX100, have AS150 and AS151 peer at IX100.

###############################################################################
# case A: create the IX after merging
###############################################################################
mergedSimulator = simulatorA.merge(simulatorB)

newBase = mergedSimulator.getLayer('Base')

ix100 = newBase.createInternetExchange(100)

as150 = newBase.getAutonomousSystem(150)
as151 = newBase.getAutonomousSystem(151)

as150.getRouter('router0').joinNetwork(ix100)
as151.getRouter('router0').joinNetwork(ix100)

mergedSimulator.getLayer('Bgp').addRsPeering(100, 150)
mergedSimulator.getLayer('Bgp').addRsPeering(100, 151)

###############################################################################
# case B: create the IX before merging
###############################################################################
baseA = simulatorA.getLayer('Base')
baseB = simulatorB.getLayer('Base')

ix100A = baseA.createInternetExchange(100)
ix100B = baseB.createInternetExchange(100)

as150 = baseA.getAutonomousSystem(150)
as151 = baseB.getAutonomousSystem(151)

as150.getRouter('router0').joinNetwork(ix100A)
as151.getRouter('router0').joinNetwork(ix100B)

simulatorA.getLayer('Bgp').addRsPeering(100, 150)
simulatorB.getLayer('Bgp').addRsPeering(100, 151)

mergedSimulator = simulatorA.merge(simulatorB)
```

## Case 3: no overlapping IX or AS, reuse existing IX

```py
# Scenario: two simulators:
#   - SimulatorA has AS150 and IX101, and many other ASes in IX101.
#   - SimulatorB has AS151 and IX102, and many other ASes in IX102. AS151
#     peered with IX102's RS.
#
# Goal: merge A and B, have AS150 and AS151 peer at IX102 via RS.

###############################################################################
# case A: join the IX after merging
###############################################################################
mergedSimulator = simulatorA.merge(simulatorB)

newBase = mergedSimulator.getLayer('Base')

ix102 = newBase.getInternetExchange(102)

as150 = newBase.getAutonomousSystem(150)

as150.getRouter('router0').joinNetwork(ix100)

mergedSimulator.getLayer('Bgp').addRsPeering(100, 150)

###############################################################################
# case B: join the IX before merging
###############################################################################
baseA = simulatorA.getLayer('Base')
baseB = simulatorB.getLayer('Base')

ix102A = baseA.createInternetExchange(102)

as150 = baseA.getAutonomousSystem(150)

as150.getRouter('router0').joinNetwork(ix102A)

simulatorA.getLayer('Bgp').addRsPeering(102, 150)

mergedSimulator = simulatorA.merge(simulatorB)
```