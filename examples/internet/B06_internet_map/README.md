# DHCP

In this example, we show how to deploy a dhcp server inside the 
SEED Emulator and how to set a host's ip with the installed dhcp server.
We first create dhcp servers on `AS151` controller.
Then, we create the internet_map container and set its asn, net, ip_address, and port_forwarding.
After the internet_map container is started, to enter the container and execute commands to trigger dhcp

See the comments in the code for detailed explanation.

## Step 1) Deploy a dhcp

```python
# Create a DHCP server (virtual node).
dhcp = DHCPService()

# Default DhcpIpRange : x.x.x.101 ~ x.x.x.120
# Set DhcpIpRange : x.x.x.125 ~ x.x.x.140
dhcp.install('dhcp-01').setIpRange(125, 140)

# Customize the display name (for visualization purpose)
emu.getVirtualNode('dhcp-01').setDisplayName('DHCP Server 1')

# Create new host in AS-151 and AS-161, use them to host the DHCP servers.
# We can also host it on an existing node.
as151 = base.getAutonomousSystem(151)
as151.createHost('dhcp-server-01').joinNetwork('net0')

# Bind the DHCP virtual node to the physical node.
emu.addBinding(Binding('dhcp-01', filter = Filter(asn=151, nodeName='dhcp-server-01')))
```

Use method `DHCPServer:setIpRange` to set the ip range to assign. 
The default IP range of Emulator is as below.
- host ip range : 71-99
- dhcp ip range : 101-120
- router ip range : 254-200

`DHCPServer:setIpRange` can change dhcp ip range. To change entire ip range, 
we can use `Network:setHostIpRange()`, `Network:setDhcpIpRange()`, and 
`Network:setRouterIpRange()`. 

### Step 2) Set params to InternetMap

```python
docker.attachInternetMap(
    asn=150, net='net0', ip_address='10.150.0.90',
    port_forwarding='8080:8080/tcp'
)
```


### Step 3) Set host to use dhcp

1. enter the internet_map container, `docker exec -it <internet_map container id> bash`
2. install the dhcp-client, `apt-get update && apt-get install -y --no-install-recommends isc-dhcp-client`
3. clear the original network interface address configuration, `ip addr flush eth0`
4. exec dhcp, `dhclient eth0`
5. test network, `ping 10.161.0.71` 

