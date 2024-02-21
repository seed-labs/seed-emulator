# Service related FAQs

## Q01. How to get ip address?

If you have access to the Node object, you can retrieve its IP address. For example, in the Server::install(self, node: Node) step, since the node object is passed as a parameter, you can use it within the install method to obtain the IP address as follows:

```python

class NewServer(Server):
    def install(self, node:Node):
        address: str = None
        ifaces = node.getInterfaces()
        assert len(ifaces) > 0, 'Node {} has no IP address.'.format(node.getName())
        for iface in ifaces:
            net = iface.getNet()
            if net.getType() == NetworkType.Local:
                address = iface.getAddress()
                break
```


## Q02. How to make a change on all nodes?

Depending on specific server configurations, you may need to modify all other nodes. For example, in the case of DomainNameCachingService, whenever a server is added, you need to inform other nodes about the IP information of the DNS caching server. Similarly, if you intend to create a PKI service, all nodes must possess the root server's certificate. In such cases, you can follow the procedure below to fetch and modify specific or all nodes.

We will utilize the Registry of the Emulator to get all nodes object. Emulator manages registry contains information about objects in the emulator. Consider a register as a database. [more details](./00-creating-a-new-layer.md#working-with-the-registry)

### step 1. Passing Emulator object information to the Server class.
Since the Server class lacks information about the emulator object, it's necessary for the service layer to pass the emulator object to the Server class through the following process. Override the `Service::configure(self, emulator: Emulator)` method. (Please remember to call `super().render(emulator)` when you override the method so that the service interface can handle the rest of the installation process.) Then, create the Server::configure(self, emulator: Emulator) method as follows to pass the Emulator object to all server objects when called from the Service::configure method.


```python
# Service Class
class NewService(Service):
    ...

    def configure(self, emulator:Emulator):
        super().configure(emulator)
        
        for (server, node) in self.getTargets():
            server.configure(emulator)
        
        return

# Server Class
class NewServer(Server):
    ...
    def configure(self, emulator:Emulator):
        self.__emulator = emulator
        return
    ...
```

### step 2. Using Emulator Registry  to retrieve desired objects (hnode, rnode, rs, ...).
Now that the Server class has access to the Emulator object, it's possible to retrieve all node objects through the registry information of the Emulator. You can use Registry::getByScope to retrieve all objects corresponding to a specific scope or Registry::getByType to retrieve objects based on a specific type. Alternatively, if you know the scope, type, and name of the specific object you want to retrieve, you can use Registry::get. Typically, the scope is represented by ASN values, and the types include `net`, `rnode`, `hnode`, and `rs`, among others. 

If you retrieve a node (hnode, rnode, or rs), since that object is an instance of the Node class, you can also use the method described in [Q01](#01-how-to-get-ip-address) to obtain the IP information of each Node.


```python
reg = self.__emulator = emulator.getRegistry()
# get all hnode(host nodes) in registry
for hnode in reg.getByType('hnode'):
    # make change on hnode

# get all rnode(router nodes) in registry
for rnode in reg.getByType('rnode'):
    # make change on rnode

# get all hnode in asn 150
scoped_reg = ScopedRegistry("150", reg)
for hnode_150 in scoped_reg.getByType('hnode'):
    # make change on hnode_150

```
