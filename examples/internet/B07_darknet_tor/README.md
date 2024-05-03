# Darknet (Tor Network)


In this example, we show how to deploy a darknet (Tor) inside the
SEED Emulator. We first create several types of Tor nodes,
and deploy them in randomly selected autonomous systems.
See the comments in the code for detailed explanation of the code. 
Here is the table of contents:


- [Deploy a Tor network inside the emulator](#deploy-tor)
- [Protect sender's identity](#sender-anonymity)
- [Protect server's identity](#server-anonymity)
- [Visit the secret web server](#visit-secret-server)
- [Notes on lab designs](#note-lab-design)


<a name="deploy-tor"></a>
## Deploy a Tor Network inside the Emulator 

Typically, a Tor network contain 5 types of nodes: DA (Dir Authority) node,
CLIENT node, RELAY node, EXIT node, HS (Hidden Service) node. 
In our example, we will create the following nodes. 

```python
vnodes = {
   "da-1":     TorNodeType.DA,
   "da-2":     TorNodeType.DA,
   "da-3":     TorNodeType.DA,
   "da-4":     TorNodeType.DA,
   "da-5":     TorNodeType.DA,
   "client-1": TorNodeType.CLIENT,
   "client-2": TorNodeType.CLIENT,
   "relay-1":  TorNodeType.RELAY,
   "relay-2":  TorNodeType.RELAY,
   "relay-3":  TorNodeType.RELAY,
   "relay-4":  TorNodeType.RELAY,
   "exit-1":   TorNodeType.EXIT,
   "exit-2":   TorNodeType.EXIT,
   "hidden-service": TorNodeType.HS
}
```

- DA (Dir Authority) node: DA nodes maintain the information of all the Tor nodes, 
  and they are responsible for generating paths (called Tor circuits) for clients.
  There can be multiple DA nodes, CLIENT only needs to work with one DA node each time. 
  All the nodes need to know the DA servers. This is done
  by putting DA’s fingerprints in their configuration files. 
  The fingerprints contain the IP address and the public key of DA.

- CLIENT node: This node will run a SOCKS5 proxy server. It helps outside machines
  to connect to the Tor network without using any Tor-aware software. If outside 
  machines already have Tor-aware software, such as Tor browser, they do not need to go 
  through any CLIENT node, because they are basically CLIENT nodes.

- RELAY node: This node relays the traffic to the next node. 

- EXIT node: The exit nodes are the final relays in the Tor circuit. They are the
  nodes that send the data to the destination. 

- HS (Hidden Service) node: This type of node is used to protect the server's 
  location. See [this section](#server-anonymity) for details.


<a name="sender-anonymity"></a>
## Protect Sender's Identity

We can use the Tor network to protect the sender 's identity, i.e. if you
visit a website using Tor, the website will not know where the request 
come from. Moreover, even if somebody can monitor some of the relay nodes,
it is still difficult for them to correlate the source and the destination.

To use the Tor network, we need to use a Tor-aware software,
such as a Tor browser, or we can use a Tor proxy. On the CLIENT
nodes, we already run such a proxy (Tor socket proxy), which listens to 
port 9050. Through these proxies, we can connect to
the Tor network. To find the IP addresses of these 
proxies, we can list all the container names, as 
the IP addresses are included in the container names 
as the suffix.

```
$ docker ps --format "{{.ID}}  {{.Names}}" | grep Tor
b1827bb8e0c6  as161h-Tor-client-2-10.161.0.73
71c4fecd57ab  as153h-Tor-client-1-10.153.0.74
...
142bfc0d9025  as160h-Tor-relay-3-10.160.0.74
4378a36764d2  as170h-Tor-webserver-10.170.0.73
983f6b0898d8  as154h-Tor-exit-1-10.154.0.74
...
1e04ae3c66c2  as154h-Tor-da-1-10.154.0.73
18229e6850f8  as151h-Tor-hidden-service-10.151.0.73
f91ba9d89fef  as160h-Tor-da-2-10.160.0.73
```

From the list above, we can find the names with `Tor-client`; 
these are proxy nodes. Let us pick `Tor-client-1`, whose IP address
is `10.153.0.74`. The port number for the proxy is `9050`.


We then go to any container (say its IP address is `a.b.c.d`), 
and try to access a web server (e.g., `http://10.163.0.71`)
via the proxy. We can use the `curl` command and specify the proxy.

```
# curl --socks5-hostname 10.153.0.74:9050 http://10.163.0.71
<h1>webservice_0 at 163</h1>
```

If we turn on `tcpdump` on the target server `10.163.0.71`, we can find out
that the request does not come from the IP address `a.b.c.d`; instead, it 
comes from one of the Tor nodes.
If we use the Map client to visualize
the traffic, we can use the filter `tcp && port 80` to see the 
last leg of the traffic. If we visit the same server from a different
container, we can see that the Tor node in the last leg is likely a 
different node. 


**Note:** The last node should be an EXIT node, but in our observation,
it can be DA, RELAY, or EXIT nodes. Not sure whether this is by design.
It could be that the number of EXIT nodes in our setup is too small. 


<a name="server-anonymity"></a>
## Protect Server's Identity/Location

Tor can also protect the server's identity (or location). 
This is through Tor's hidden service. 
In our emulator, we first create a web server, and then use
the hidden service node to protect the web server. 
In the following code, we create a web server node, put
some content inside its `hello.html` page. 

```
html = """
<html><body>
<h1>This is the secret web server!</h1>
</body></html>
"""

# Create a web server: we will use Tor to protect this server
emu.getLayer('WebService').install("webserver")
emu.getVirtualNode('webserver').setDisplayName('Tor-webserver') \
        .setFile(content=html, path="/var/www/html/hello.html")
```

We then create a HS (Hidden Service) node, and link
this node to our secret web server. If we want to visit the protected
web server, our request will reach this HS node, which will then
forward our traffic to the final destination. 
The following code create the HS node and link it to the web server.

```
tor.install('hidden-service').setRole(TorNodeType.HS).linkByVnode("webserver", 80)
```

<a name="visit-secret-server"></a>
## Visit the Secret Web Server

To visit this anonymous web server, we need to know its onion address.
We can find this address from the hidden-server container. It is 
stored in the `/tor/HS[random]/hs/hostname` file. In our case,
we see the following:
```
u5evj5gmyrsf7hkpaoi6iqclks5qn52x2wrvikx24osuutwxswjnjbid.onion
```

Now, we can visit this server from any container using `curl`, a Tor proxy,
and the onion address. We should be able to get the content put inside 
the `hello.html` page:

```
curl --socks5-hostname 10.153.0.74:9050 http://u5evj5gmyrsf7hkpaoi6iqclks5qn52x2wrvikx24osuutwxswjnjbid.onion/hello.html

<html><body>
<h1>This is the secret web server!</h1>
</body></html>
```

We can go to the web-server container, go to its  `/var/www/html` folder,
modify the `hello.html` file. Then we visit it again, and we will see that
the content returned will be changed accordingly. This confirms that
the content does come from the web server.



Notice: Sometimes, maybe you would see the 
"cannot resolve [random].onion address" error message when you use the `curl` command. 
That's because the Tor network may not be stable (or the number of DA nodes is too low).
It would continuously calculate the consensus.
You can keep trying it until it works, or restart the containers. 
You can also monitor the Tor network by connecting to its control port to see what
happens inside Tor. You can install a tool called `nyx`,
and run `nyx -i <ip of CLIENT node>:9051` to connect to the 
CLIENT node's control port. This way, you can monitor all the connections. 
When you try to use `curl` to connect to the Tor network, 
you can see what has caused the issue.


<a name="note-lab-design"></a>
## Note for Lab Design (Furture Work)

When we design labs based on darknet, we need to find ways to show students that Tor is 
protecting the communication. We need to show how the Tor works internally.
We can use a tool called `nyx` (see notes above) to 
connect to the control port of CLIENT node. This tool will show the path 
and all connections.

We can also put a sniffer on each RELAY node to track where packets go. 
