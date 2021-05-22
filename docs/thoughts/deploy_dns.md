

## Deploying DNS Infrastructure

```py
# The DNSInfrastructure class provides everything that we need
dns = DNSInfrastructure()
dns.loadZones("dns.json")  # Load prepared zones
dns.addZone(...)           # Or create an DNS infrastructure from scratch

# Load the prebuilt emulator (or built one from scratch)
sim = Emulator()
sim.load("sim.josn")

# Deploy the DNS services to the emulator by installing zones
# on IP. For anycast, this will install to all the instances
h = sim.getHostByIP("192.168.50.3")
if h is not None:
   dns.install(dns.getZone("."), "192.168.50.3" )
else: 
   # The developers can choose to add an AS to the emulator
   # and then do the install

h = sim.getHostByIP("182.153.0.39")
if h is not None:
   dns.install(dns.getZone("com"), "182.153.0.39")

# Add the DNS to the emulator
sim.addLayer(dns)

# Render the emulator
sim.render()
```

