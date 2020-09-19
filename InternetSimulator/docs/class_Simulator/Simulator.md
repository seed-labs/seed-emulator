class `Simulator`
---

Thought:

- Make a global "object registry." Basically, a Python dictionary that maps names to the corresponding object (`Network`, `Router`, `AS`, etc.) Since they all have different naming conventions, this should be fine (i.e., we won't have name conflict).
- Move `<add/get>Host`/`<add/get>BGPRouter` to class `AS`. It makes the `Simulator` class cleaner. As long as we have the "object registry" as described above, we can always retrive the object with name.


### __init__ (self, str name)
Simulator constructor.

### addIX (self, str name, int asn, str net_name)
Add an Internet Exchange.

### addAS (self, str name, int asn, str as_type, str net_name)
Add an AS.

### getASByName (self, str name)
Get AS/IX by name.

### getASByASN (self, int asn)
Get AS by ASN.

### addNetwork (self, str name, str network, str netmask, str type)
Add a Netwrok.

### getNetwork (self, str name)
Get a Netwrok.

### addBGPRouter (self, int asn, str ixp, str type)
Add a BGP router.

### getRouter (self, str name)
Get a BGP router.

### addHost (self, str name, Host host)
Add a BGP router.

### getHost (self, str name)
Get a Host.

### listRouters (self)
Print the details to stdout.

### listHosts (self)
Print the details to stdout.

### listNetworks (self)
Print the details to stdout.

### listASes (self)
Print the details to stdout.

### listIXPs (self)
Print the details to stdout.

### generateHosts (self, int total)
Create the host list.

### createHostDockerFiles (self)
Create Dockerfile for all hosts.

### createRouterDockerFiles (self)
Create Dockerfile for all routers.

### createDockerComposeFile (self)
Create docker-compose.yml.

### getASFromCSV (self, str filename)
Read the AS data from CSV file.

### getPeeringsFromCSV (self, filename)
Read the peering data from CSV file.
