class `Network`
---

### __init__ (self, str name, str prefix, str netmask, str type, simulator)

### getIPByASN (self, int asn)
Assign IP addresses based on ASN.

### getIP (self, router=False, bgp=False)
Get IP address by type.

### getDefaultRT (self)
Get the router in this network.

### createDockerComposeEntry (self)
Get the docker compose file as string.

### printDetails (self)
Print the details to stdout.
