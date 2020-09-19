class `Router`
---

### __init__ (self, str name, sim)
Router constructor.

### printDetails (self)
Print the details to stdout.

### listInterfaces (self)
Print the interfaces details to stdout.

### addInterface (self, str name, str ip)
Add an interface to router.

### createBirdConf_OSPF (self)
Get Bird's OSPF config.

### createDockerComposeEntry (self)
Get the docker compose file as string.


class `BgpRouter`
---

### __init__ (self, str name, int asn, int ixp, sim)
BGPRouter constructor.

### getIP_on_IXP_Network (self)
Get IP address on the IX peering LAN.

### getIP_on_Internal_Network (self)
Get IP address on the internal LAN.

### getASN (self)
Get ASN.

### getType (self)
Get type of the BGPRouter.

### initializeNetwork (self)
Create the internal LAN.

### addPeer (self, peername)
Add a peer.

### listPeers (self)
Print the list of peers to stdout.

### printDetails (self)
Print the details to stdout.

### createBirdConf_BGP (self)
Get Bird's BGP config.

### createBirdConf_IBGP (self)
Get Bird's IBGP config.

class `RouteServer`
---

### __init__ (self, str name, int ixp, sim)
RouteServer constructor.

### getIP_on_IXP_Network (self)
Get IP address on the IX peering LAN.

### getASN (self)
Get ASN of the RouteServer.

### getType (self)
Get type of the RouteServer.

### addPeer (self, str peername)
Add a peer.

### initializeNetwork (self)
Create the IX peering LAN.

### listPeers (self)
Print the list of peers to stdout.

### printDetails (self)
Print the details to stdout.

### createBirdConf_BGP (self)
Get Bird's BGP config.
