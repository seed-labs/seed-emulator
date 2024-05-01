# DHCP

In this example, we show how to deploy a dhcp server inside the 
SEED Emulator and how to set a host's ip with the installed dhcp server.
We first create dhcp servers on `AS151` and `AS152` controller.
We then 2 hosts in each AS to get ip address from the installed dhcp server.

See the comments in the code for detailed explanation.

We can utilize DHCP on `C03-bring-your-own-internet`. When we connect external 
devices such as computer, smartphone, and IoT device to a internet emulator, 
the installed dhcp will assign ip address to the newly attached devices so that
they can communicate with the nodes inside the emulator and use internet service.   

## Step 1) Deploy a dhcp

```python
# Create a DHCP server (virtual node).
dhcp = DHCPService()

# Default DhcpIpRange : x.x.x.101 ~ x.x.x.120
# Set DhcpIpRange : x.x.x.125 ~ x.x.x.140
dhcp.install('dhcp-01').setIpRange(125, 140)
dhcp.install('dhcp-02')


# Customize the display name (for visualization purpose)
emu.getVirtualNode('dhcp-01').setDisplayName('DHCP Server 1')
emu.getVirtualNode('dhcp-02').setDisplayName('DHCP Server 2')


# Create new host in AS-151 and AS-161, use them to host the DHCP servers.
# We can also host it on an existing node.
as151 = base.getAutonomousSystem(151)
as151.createHost('dhcp-server-01').joinNetwork('net0')

as161 = base.getAutonomousSystem(161)
as161.createHost('dhcp-server-02').joinNetwork('net0')

# Bind the DHCP virtual node to the physical node.
emu.addBinding(Binding('dhcp-01', filter = Filter(asn=151, nodeName='dhcp-server-01')))
emu.addBinding(Binding('dhcp-02', filter = Filter(asn=161, nodeName='dhcp-server-02')))
```

Use method `DHCPServer:setIpRange` to set the ip range to assign. 
The default IP range of Emulator is as below.
- host ip range : 71-99
- dhcp ip range : 101-120
- router ip range : 254-200

`DHCPServer:setIpRange` can change dhcp ip range. To change entire ip range, 
we can use `Network:setHostIpRange()`, `Network:setDhcpIpRange()`, and 
`Network:setRouterIpRange()`. 


### Step 2) Set host to use dhcp

```python
# Create new hosts in AS-151, use it to host the Host which use dhcp instead of static ip
as151.createHost('dhcp-client-01').joinNetwork('net0', address = "dhcp")
as151.createHost('dhcp-client-02').joinNetwork('net0', address = "dhcp")

# Create new hosts in AS-161, use it to host the Host which use dhcp instead of static ip
as161.createHost('dhcp-client-01').joinNetwork('net0', address = "dhcp")
as161.createHost('dhcp-client-01').joinNetwork('net0', address = "dhcp")

```

