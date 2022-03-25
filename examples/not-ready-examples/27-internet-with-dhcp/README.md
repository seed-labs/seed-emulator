# Internet Service Provider
In this example, we show how the SEED Emulator to emulate the
Internet Service Provider that provides the Internet service 
to home (such as Spectrum). The scenario is described in the 
diagram as below.
![](pics/diagram-1.jpg)


## Step 1) Deploy a dhcp server
```
# Create a DHCP server (virtual node).
dhcp = DHCPService()

# Default DhcpIpRange : x.x.x.101 ~ x.x.x.120
# Set DhcpIpRange : x.x.x.125 ~ x.x.x.140
dhcp.install('dhcp-01')

# Customize the display name (for visualization purpose)
emu.getVirtualNode('dhcp-01').setDisplayName('DHCP Server')

# Create new host in AS-151, use it to host the DHCP server.
# We can also host it on an existing node.
as151 = base.getAutonomousSystem(151)
as151.createHost('dhcp-server').joinNetwork('net0')
```

## Step 2) Add a Host’s physical interface to the bridge

### Run bridge.sh

```
usage: ./bridge.sh -i {interface} -a {ASN}

ex) 
./bridge.sh -i eth0 -a 151
```

You can get the interface name through `ip addr` command.
It will be easier to find it before running the emulator 
as lots of virtual interfaces will be created once the emulator is up. 

## Step 3) Connect the wifi access point to the switch





