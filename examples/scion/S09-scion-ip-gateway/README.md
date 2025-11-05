# SCION IP Gateway

In this example we demonstrate how to set up SCION IP gateways between ASes.

first we have to import the ScionSIGService class from seedemu.services

```python
from seedemu.services import ScionSIGService
```

Then we create the SIG service

```python
sig = ScionSIGService()
```

Now we can cerate hosts in ASes and install the SIG service. For this we also have to generate a SIG configuration using the setSigConfig() function. in the ScionAutonomosSystem class.

```python
# SIG in AS-150
as150.createHost("sig0").joinNetwork('net0')

as150.setSigConfig(sig_name="sig0",node_name="sig0",other_ia=(1,153), local_net = "172.16.11.0/24", remote_net = "172.16.12.0/24")
config = as150.getSigConfig("sig0")

sig.install("sig150").setConfig("sig0",config)
emu.addBinding(Binding('sig150', filter=Filter(nodeName='sig0', asn=150)))
```
Note that sig_name, node_name, other_ia, local_net, remote_net always have to be set where as the other parameters only need to be set if there are several sigs on the same node

Now we can create a SIG client in another AS

```python
as153.createHost("sig").joinNetwork('net0')

as153.setSigConfig(sig_name="sig0",node_name="sig", other_ia=(1,150), local_net = "172.16.12.0/24", remote_net = "172.16.11.0/24")
as153.setSigConfig(sig_name="sig1",node_name="sig", other_ia=(1,151), local_net = "172.16.13.0/24", remote_net = "172.16.14.0/24", ctrl_port=30260, data_port=30261, probe_port=30857)

config_sig0 = as153.getSigConfig("sig0")
config_sig1 = as153.getSigConfig("sig1")


sig.install("sig153").setConfig(sig_name="sig0",config=config_sig0)
sig.install("sig153").setConfig(sig_name="sig1",config=config_sig1)

emu.addBinding(Binding('sig153', filter=Filter(nodeName='sig', asn=153)))
```

Here we also see an example of having to set the ports in the sig config if there are several sigs on the same node.

At the end we should not forget to add the sig layer to the emulator

```python
emu.addService(sig)
```
