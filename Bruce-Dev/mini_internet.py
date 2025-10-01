from seedemu import *
import os, sys

HOSTS_PER_AS = 2

###############################################################################
# Set the platform information
script_name = os.path.basename(__file__)

if len(sys.argv) == 1:
    platform = Platform.AMD64
elif len(sys.argv) == 2:
    if sys.argv[1].lower() == 'amd':
        platform = Platform.AMD64
    elif sys.argv[1].lower() == 'arm':
        platform = Platform.ARM64
    else:
        print(f"Usage:  {script_name} amd|arm")
        sys.exit(1)
else:
    print(f"Usage:  {script_name} amd|arm")
    sys.exit(1)

emu   = Emulator()
ebgp  = Ebgp()
base  = Base()
ovpn  = OpenVpnRemoteAccessProvider()

###############################################################################
# Create internet exchanges
ix100 = base.createInternetExchange(100)
ix101 = base.createInternetExchange(101)
ix102 = base.createInternetExchange(102)
ix103 = base.createInternetExchange(103)
ix104 = base.createInternetExchange(104)
ix105 = base.createInternetExchange(105)

# Customize names (for visualization purpose)
ix100.getPeeringLan().setDisplayName('NYC-100')
ix101.getPeeringLan().setDisplayName('San Jose-101')
ix102.getPeeringLan().setDisplayName('Chicago-102')
ix103.getPeeringLan().setDisplayName('Miami-103')
ix104.getPeeringLan().setDisplayName('Boston-104')
ix105.getPeeringLan().setDisplayName('Huston-105')


###############################################################################
# Create Transit Autonomous Systems 

## Tier 1 ASes
Makers.makeTransitAs(base, 2, [100, 101, 102, 105], 
        [(100, 101), (101, 102), (100, 105)] 
)

Makers.makeTransitAs(base, 3, [100, 103, 104, 105], 
        [(100, 103), (100, 105), (103, 105), (103, 104)]
)

Makers.makeTransitAs(base, 4, [100, 102, 104], 
        [(100, 104), (102, 104)]
)

## Tier 2 ASes
Makers.makeTransitAs(base, 11, [102, 105], [(102, 105)])
Makers.makeTransitAs(base, 12, [101, 104], [(101, 104)])


###############################################################################
# Create single-homed stub ASes. 
Makers.makeStubAsWithHosts(emu, base, 150, 100, HOSTS_PER_AS)
Makers.makeStubAsWithHosts(emu, base, 151, 100, HOSTS_PER_AS)
Makers.makeStubAsWithHosts(emu, base, 152, 101, HOSTS_PER_AS)
Makers.makeStubAsWithHosts(emu, base, 153, 101, HOSTS_PER_AS)
Makers.makeStubAsWithHosts(emu, base, 154, 102, HOSTS_PER_AS)
Makers.makeStubAsWithHosts(emu, base, 160, 103, HOSTS_PER_AS)
Makers.makeStubAsWithHosts(emu, base, 161, 103, HOSTS_PER_AS)
Makers.makeStubAsWithHosts(emu, base, 162, 103, HOSTS_PER_AS)
Makers.makeStubAsWithHosts(emu, base, 163, 104, HOSTS_PER_AS)
Makers.makeStubAsWithHosts(emu, base, 164, 104, HOSTS_PER_AS)
Makers.makeStubAsWithHosts(emu, base, 170, 105, HOSTS_PER_AS)
Makers.makeStubAsWithHosts(emu, base, 171, 105, HOSTS_PER_AS)

# An example to show how to add a host with customized IP address
as154 = base.getAutonomousSystem(154)
as154.getNetwork("net0").enableRemoteAccess(ovpn)
as154.createNetwork("net1")
router1 = as154.createRouter('router1')
router1.joinNetwork('net0')
router1.joinNetwork("net1")
for counter in range(HOSTS_PER_AS):
    name = 'host_{}'.format(counter + 3)
    host = as154.createHost(name)
    host.joinNetwork("net1")


as163 = base.getAutonomousSystem(163)
as163.getNetwork('net0').enableRemoteAccess(ovpn)
new_host = as154.createHost('host_new').joinNetwork('net0', address = '10.154.0.129')
as2 = base.getAutonomousSystem(2)
new_host_2 = as2.createHost('host_new_2').joinNetwork('net_101_102', address = '10.2.1.129')

o = OptionRegistry().sysctl_netipv4_conf_rp_filter({'all': False, 'default': False, 'net0': False}, mode = OptionMode.RUN_TIME)
new_host.setOption(o)

o = OptionRegistry().sysctl_netipv4_udp_rmem_min(5000, mode = OptionMode.RUN_TIME)
new_host.setOption(o)

###############################################################################
# Peering via RS (route server). The default peering mode for RS is PeerRelationship.Peer, 
# which means each AS will only export its customers and their own prefixes. 
# We will use this peering relationship to peer all the ASes in an IX.
# None of them will provide transit service for others. 

ebgp.addRsPeers(100, [2, 3, 4])
ebgp.addRsPeers(102, [2, 4])
ebgp.addRsPeers(104, [3, 4])
ebgp.addRsPeers(105, [2, 3])

# To buy transit services from another autonomous system, 
# we will use private peering  

ebgp.addPrivatePeerings(100, [2],  [150, 151], PeerRelationship.Provider)
ebgp.addPrivatePeerings(100, [3],  [150], PeerRelationship.Provider)

ebgp.addPrivatePeerings(101, [2],  [12], PeerRelationship.Provider)
ebgp.addPrivatePeerings(101, [12], [152, 153], PeerRelationship.Provider)

ebgp.addPrivatePeerings(102, [2, 4],  [11, 154], PeerRelationship.Provider)
ebgp.addPrivatePeerings(102, [11], [154], PeerRelationship.Provider)

ebgp.addPrivatePeerings(103, [3],  [160, 161, 162], PeerRelationship.Provider)

ebgp.addPrivatePeerings(104, [3, 4], [12], PeerRelationship.Provider)
ebgp.addPrivatePeerings(104, [4],  [163], PeerRelationship.Provider)
ebgp.addPrivatePeerings(104, [12], [164], PeerRelationship.Provider)

ebgp.addPrivatePeerings(105, [3],  [11, 170], PeerRelationship.Provider)
ebgp.addPrivatePeerings(105, [11], [171], PeerRelationship.Provider)


###############################################################################
# Add layers to the emulator

emu.addLayer(base)
emu.addLayer(Routing())
emu.addLayer(ebgp) 
emu.addLayer(Ibgp())
emu.addLayer(Ospf())

dhcp = DHCPService()

# Default DhcpIpRange : x.x.x.101 ~ x.x.x.120
# Set DhcpIpRange : x.x.x.125 ~ x.x.x.140
dhcp.install('dhcp-01').setIpRange(125, 140)
dhcp.install('dhcp-02')


# Customize the display name (for visualization purpose)
emu.getVirtualNode('dhcp-01').setDisplayName('DHCP Server 1')
emu.getVirtualNode('dhcp-02').setDisplayName('DHCP Server 2')


# Create new hosts in AS-151 and AS-161, use them to host the DHCP servers.
# We can also host it on an existing node.
as151 = base.getAutonomousSystem(151)
as151.createHost('dhcp-server-01').joinNetwork('net0')

as161 = base.getAutonomousSystem(161)
as161.createHost('dhcp-server-02').joinNetwork('net0')

# Bind the DHCP virtual node to the physical node.
emu.addBinding(Binding('dhcp-01', filter = Filter(asn=151, nodeName='dhcp-server-01')))
emu.addBinding(Binding('dhcp-02', filter = Filter(asn=161, nodeName='dhcp-server-02')))


# Create new hosts in AS-151 and AS-161
# Make them to use dhcp instead of static ip
as151.createHost('dhcp-client-01').joinNetwork('net0', address = "dhcp")
as151.createHost('dhcp-client-02').joinNetwork('net0', address = "dhcp")

as161.createHost('dhcp-client-03').joinNetwork('net0', address = "dhcp")
as161.createHost('dhcp-client-04').joinNetwork('net0', address = "dhcp")

# Add the dhcp layer
emu.addLayer(dhcp)

# Render the emulation
emu.render()

# # Attach the Internet Map container to the emulator
docker = Docker(platform=platform)
emu.compile(docker, './output', override=True)