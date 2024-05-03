# Tor private network setup documentation

## Step 1

Run `17-base-component.py`, in order to reuse a base component. In this base component, there are 7 AS, which are `AS150,AS151,AS152,AS153,AS154,AS160,AS161`. Each of AS has 3 hosts. All of hosts are able to connect each other.

## Step 2

Import Tor modules and create Tor Service. Then load our base component. You can also see these code in `17-tor-private-network.py`

```python
from seedsim.core import Emulator, Binding, Filter, Action
from seedsim.compiler import Docker
from seedsim.services import TorService, TorNodeType
from seedsim.services import WebService


sim = Emulator()
tor = TorService()
web = WebService()

sim.load('base-component.bin')
```

## Step 3

Install tor nodes. Typically, a tor network should contains at least 5 types of node, i.e: DA node, CLIENT node, RELAY node, EXIT node, HS node. A normal tor connection would be like this:

`User---->socks connect to---->CLIENT---->RELAY---->RELAY1---->RELAY2---->EXIT---->HS---->Destination `

The Path (circuit) is dynamically chosen by tor program. DA(Dir Authority) node is responsible to maintain these nodes info by voting and consensus mechanism thereby ensure which nodes are available to use.

All relay nodes need to know the DA (Directory Authority) servers. This is done
by putting DA’s fingerprints in their configuration file, the fingerprints contains 
IP address of DA and public key of DA. This is done automatically by the emulator. 
DA will maintain all of nodes information and generate a best path to client. 
This path is called circuit in Tor network.
There can be multiple DA nodes, CLIENT only needs to work with one DA node each time. 


So we need to create these essential type of nodes. The following code shows how to create them:

```python
tor.install("da").setRole(TorNodeType.DA)
tor.install("da1").setRole(TorNodeType.DA)
tor.install("da2").setRole(TorNodeType.DA)
tor.install("client").setRole(TorNodeType.CLIENT)
tor.install("relay").setRole(TorNodeType.RELAY)
tor.install("relay1").setRole(TorNodeType.RELAY)
tor.install("exit").setRole(TorNodeType.EXIT)
```
As we can see, we created 3 DA nodes, 2 RELAY nodes, 1 CLIENT and 1 EXIT. That's a basic tor network .




## Step 4

Next, we would create a HS(Hidden Service) node and link it to destination host. Hidden Service is the last stop in a tor connection. In this node, it will point to a real destination host, in order to tell user where to go. The following example code shows how to create HS node and link to a webserver.

```python
#Create a webserver for verifying tor network
web.install("webserver")

#Create Tor hidden service, the hs node will point to webserver
onion_service = tor.install("hs")
onion_service.setRole(TorNodeType.HS)
onion_service.linkByVnode("webserver", 80)
```

As we can see, we firstly create a webserver, then create a Tor node, set its role to be HS. After that, we use linkByVnode API to link this HS node to a webserver (virtual node name should be keep the same). 80 means the port number you want to forward to.

## Step 5

Add bindings for all virtual nodes.

```python3
#Add bindings
sim.addBinding(Binding('da*', filter = Filter(asn = 150)))
sim.addBinding(Binding('client', filter = Filter(asn = 151), action=Action.FIRST))
sim.addBinding(Binding('relay*', filter = Filter(asn = 152)))
sim.addBinding(Binding('exit', filter = Filter(asn = 153)))
sim.addBinding(Binding('hs', filter = Filter(asn = 154)))
sim.addBinding(Binding('webserver', filter = Filter(asn = 160)))
```

As we can see. We installed DA in the AS150, CLIENT nodes in the first node of AS151 etc.

Lastly, we add tor layer and web layer to our emulator. Then render them.

## Step 6

Run `17-tor-private-network.py`. Then go to tor-private-network folder, build and run all container by `running docker-compose build && docker-compose up`.

After all containers running. You would see the log in docker console. Then wait for all nodes to finish downloading fingerprints, you will see "fingerprint is ready" keyword in the log.

Now, let's verify if our tor network works. Because we installed CLIENT in the first node of AS151, so we know CLIENT IP address is 10.151.0.71. By default, the tor socket proxy port is 9050. That means we can connect to tor network by using socks://10.151.0.71:9050

Next, we need to know the onion address in HS server. Find HS server host in AS154, attach a shell to this container. In the folder `/tor/HS[random]/hs/hostname` file. The onion address should be there. For example: `z6jt5uqejnchx5gl4pmn36vu576l7wj4kvj37gbyiwtby3lbgbcudbyd.onion` .

Lastly, in your host (VM), connect CLIENT node and visit this onion address by using command:

`curl --socks5-hostname 10.151.0.71:9050 http://z6jt5uqejnchx5gl4pmn36vu576l7wj4kvj37gbyiwtby3lbgbcudbyd.onion`

You would the response like this:

```<h1>host1 at 160</h1>```

That means our tor network works fine. Because that onion address is already pointed to our webserver which installed in AS160.

> Notice: Sometimes, maybe you would see cannot resolve [random].onion address when you use CURL command. That's because the tor network is not very stable. It would continuously calculate the consenus, so the circuit would not be worked for everytime. Only one thing we can do is keep try it until it works. Or you can monitor the tor netword by connect its control port to see what happend inside of tor. You can install a tool called nyx by running apt-get install nyx. Then use command nyx -i 10.151.0.71:9051 to connect CLIENT node control port to monitor all connections. When you try to use curl to connect tor network. You can see what's the reason that cause the onion address resolve failed.


## Note

When we design the lab, we need to find ways to show students that Tor is 
protecting the communication. We need to show how the Tor works internally.
We can use a tool called `nyx` (see notes above) to 
connect to the control port of CLIENT node. This tool will show the path 
and all connections.

We can also put a sniffer on each RELAY node to track where packets go. 
