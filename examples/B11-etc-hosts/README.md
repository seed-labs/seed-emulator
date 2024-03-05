# Enable local DNS service using `EtcHosts` layer

This example demonstrates how we can enable a local DNS service using the `EtcHosts` layer.
This layer will add the IP address and hostnames of all the nodes in the emulator to the `/etc/hosts` file.
The `/etc/hosts` file is a simple text file that associates IP addresses with hostnames.
It is used to resolve hostnames to IP addresses.

The default hostname of a node is of the form `<scope>-<name>`. For example, the default hostname of a node named `node1` in the autonomous system `154` is `154-node1`. However, we can add additional hostnames to a node using the `custom_host_names` parameter of the `Node` constructor or the `addHostName` method of the `Node` class. The `EtcHosts` layer will add these custom hostnames to the `/etc/hosts` file.

Following are some examples of how to add a custom hostname to a node:

1. Pass the custom hostnames as a list to the `Node` constructor:
```
node = Node('node_name', NodeRole.Host, 154, custom_host_names=['custom_hostname1', 'custom_hostname2'])
```

2. Add a new custom hostname using the `addHostName` method:
```
node.addHostName('custom_hostname3')
```

3. Pass the custom hostnames as a list to the `createHost` method of the `AutonomousSystem` class:
```
as152.createHost('database', custom_host_names=["database.com"]).joinNetwork('net0', address = '10.152.0.4')
```

In this example, we will create a new host with custom host name on top of the mini-internet component and then enable `EtcHosts` layer.

## Load the Mini-Internet Component

```
emu.load('../B00-mini-internet/base-component.bin')
```

## Create a New Host with Custom Hostname

```
base: Base = emu.getLayer('Base')
as152 = base.getAutonomousSystem(152)
as152.createHost('database', custom_host_names=["database.com"]).joinNetwork('net0', address = '10.152.0.4')
```

## Add EtcHosts Layer

```
etc_hosts = EtcHosts()
emu.addLayer(etc_hosts)
```
