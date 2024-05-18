# Building a DNS Infrastructure Component

This example demonstrates how we can build a DNS infrastructure as a component. 
We generate a mini DNS infrastructure and save it into a file as 
a DNS component. This component can be loaded into other emulators, which
means deploying the DNS infrastructure in those emulators. 
In this mini DNS, we created the following nameservers:

- Root servers: `a-root-server` and `b-root-server`
- COM servers: `a-com-server` and `b-com-server`
- NET server: `a-net-server`
- EDU server: `a-edu-server`
- Two ccTLD servers: `a-cn-server` and `b-cn-server`
- `twitter.com` nameserver: `ns-twitter-com`
- `google.com` nameserver: `ns-google-com`
- `example.net` nameserver: `ns-example-net`
- `syr.edu` nameserver: `ns-syr-edu`
- `weibo.cn` nameserver: `ns-weibo-cn`


## Creating Virtual Nameserver 

We will create the DNS infrastructure at the DNS layer, 
so each node created is a virtual node, which is not bound to
any physical node. This is very important, because we are building
a component, which can be deployed in different emulators. 

```
dns.install('a-root-server').addZone('.').setMaster()   # Master server
dns.install('b-root-server').addZone('.')               # Slave server
```

Each of the lines above first create a virtual node, and then install
a zone (root zone) on the node. If two zones are installed on two different nodes,
one of them can be set to Master, so the other can get the data 
from the master node.  

Creating nodes for other zones is similar.
The DNS layer in the emulator will manage their relationships. For example,
the nameserver of the `com.` zone will be automatically registered to the 
nameserver of the root zone.  This is done by adding the essential records
to the root's zone file.


##  Adding DNS Records to Zone

We can add records to each zone file. See the following example. 

```
dns.getZone('twitter.com.').addRecord('@ A 1.1.1.1')
dns.getZone('google.com.').addRecord('@ A 2.2.2.2')
```

##  Customization for visualization

When the nodes are displayed on the map, we would like to display a more 
friendly name, instead of the unique name assigned to each virtual node. 
We can do the following. When this virtual node is bound to a physical 
node, the display name will be inherited by the physical node. 

```
emu.getVirtualNode('a-root-server').setDisplayName('Root-A')
```

##  Saving the DNS component to File

After adding the DNS layer to the emulator, we can save the entire DNS
infrastructure to a file. Other emulators can then deploy this DNS
infrastructure in their emulation by loading this component. 

```
emu.addLayer(dns)
emu.dump('dns-component.bin')
```
