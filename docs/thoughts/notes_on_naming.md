# Naming and Referencing Objects

In our code, we often need to add the referencs of an object to another object, for example, in IXP, we will add peering relationships. For each peering, we need to reference two BGP routers. The question is do we put the actual reference of the object or else?

Through my implementation, sometimes I use the actual object reference, sometimes I use the name. That caused a lot of confusion. Eventually, I decided to adopt the **reference by name** approach. For example, if an AS has a list of routers, it will be a list of router names. Here are some details:

- **Naming convention**: Each entity in our simulator has a unique name. When the entity is created, the name will be given. We will define the template for names. For example, in the current implementation, bgp router's name is like the following ```rt_as150_ix100```, indicating this is a BGP router from ```as15``` and it is located at ```ix100```.We will have a design documents on the naming conventions.<br> 
**Note on names**: Names need to be intuitive and easy to recognize, because when we build the container, these will be the container names. When users look at the container name, they should immediately know the role of that container. Therefore, the names are not only for the internal uses of the program,  they are also used by the actual users of the simulator.

- **Mapping names to objects**: We will have a central place to map each name to objects. In the simulator class, here is what we have. I used the dictionary data structure, with the key being the name, and the value being the reference to the actual objects. 

```
     self.networks = {}
     self.hosts = {}
     self.routers = {}
     self.ASes = {}
     self.IXPs = {}
```

- **Referencing the objects**: When we need to add these objects to other objects, such as adding to the peers list of a BGP router, we only add names. We use the ```set``` data structure to make sure that the elements are unique. 
```
   self.peers = set()  # Initialize the set

   self.peers.add(peername)  # Add to the set
```

- **Naming for containers** (added on 12/8/2020): When we generate the `docker-compose.yml` file, we should
use `container_name` to give each container a name, instead of letting docker to 
generate a name for us. This name should encode essential information about 
the container to make it user friendly. The name should use this format: `ASN-Role-IP`. 
The `ASN` is the autonomous system number, such as `AS150`. For Internet Exchanges,
we should use `IX` as the prefix, such as `IX100`. The `Role` should spell out the
main purpose of the container, such as `router`, `host`, `rs` (router server), `dns`,
`web`, etc. The `IP` part should be the IP address of the container.


