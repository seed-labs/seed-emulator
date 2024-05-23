# SCION Bandwidth Test Client

This example demonstrates how to set up a SCION network for conducting bandwidth tests, using scion-bwtestclient, between Autonomous Systems (ASes) using SeedEmu. It includes configuring ASes, routers, hosts, and bandwidth test services.

## Initializing the bwtestclient Service

First, we initialize the bwtestclient service.

```python
from seedemu.services import ScionBwtestClientService
# other imports

# Create bandwidth test services
bwtest = ScionBwtestService()
bwtestclient = ScionBwtestClientService()
```

## Setting up Bandwidth Test Services

First we create scion-bwtestserver in every AS.

```python
# Bandwidth test server in AS-150
as150.createHost('bwtest').joinNetwork('net0', address='10.150.0.30')
bwtest.install('bwtest150').setPort(40002)
emu.addBinding(Binding('bwtest150', filter=Filter(nodeName='bwtest', asn=150)))

# Bandwidth test server in AS-151
as151.createHost('bwtest').joinNetwork('net0', address='10.151.0.30')
bwtest.install('bwtest151')
emu.addBinding(Binding('bwtest151', filter=Filter(nodeName='bwtest', asn=151)))

# Bandwidth test server in AS-152
as152.createHost('bwtest').joinNetwork('net0', address='10.152.0.30')
bwtest.install('bwtest152')
emu.addBinding(Binding('bwtest152', filter=Filter(nodeName='bwtest', asn=152)))

# Bandwidth test server in AS-153
as153.createHost('bwtestserver').joinNetwork('net0', address='10.153.0.30')
bwtest.install('bwtest153')
emu.addBinding(Binding('bwtest153', filter=Filter(nodeName='bwtestserver', asn=153)))
```

Now we create a scion-bwtestclient in one of the ASes

```python
# Bandwidth test client in AS-153
as153.createHost('bwtestclient').joinNetwork('net0', address='10.153.0.31').addSharedFolder("/var/log", "/absolute/path/to/logs/on/host")
bwtestclient.install('bwtestclient153').setServerAddr('1-151,10.151.0.30').setWaitTime(20)
emu.addBinding(Binding('bwtestclient153', filter=Filter(nodeName='bwtestclient', asn=153)))
```

**Notes:**
- the addSharedFolder("nodePath","hostPath") function makes sure that we can see the bwtestclient output without attaching to the container
- the setServerAddr() function specifies the server address of the bwtestserver
- the setWaitTime() function sets the number of seconds to wait after the container started before running the test. The default is 60 seconds.
- there are also other functions:
    - setPort() -- setting the port the server listens on
    - setPreference() -- set the preference for sorting paths (check bwtester documentation for more details)
    - setCS() -- Client->Server test parameter (default "3,1000,30,80kbps")
    - setSC() -- Server->Client test parameter (default "3,1000,30,80kbps")

## Rendering and Compilation

We add the configured layers to the emulator, render the network topology, and compile the configuration into Docker containers.

```python
# Rendering
emu.addLayer(bwtest)
emu.addLayer(bwtestclient)
```

