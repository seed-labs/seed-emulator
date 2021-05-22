# DNS service component binding mock test

## Scenario 1: multiple root dns servers, com servers.

### Expectation input explaination

 - dns-dump.bin: Service component, including 3 root servers, 2 com. servers, 1 net. server and example.com server.
 - internet-1.bin: Base component, including AS100,AS200,AS300,AS400,AS500.

### Connector type

Using ASN connector to randomly bind in different AS.
 
### Component connect code

```python
from seedsim.core import Configuration, Binding, Filter, Action
simA = Emulator()
simB = Emulator()
simA.load('dns-dump.bin')   # service component.
simB.load('internet-1.bin') # base component, has as[100,200,300,400,500]-host[1-10] nodes.

final_bindings = {}
dns: DomainNameService = simA.getLayer('DomainNameService')

for zone in dns.getZones(): # => ['.', 'com.', 'net.', 'example.com.']
	name_as_tupes = dns.getZoneServerNames(zone) # => if zone = '.' that will be [('root_server2', 154), ('root_server', 150), ('root_server1', 154)]
	
	for name_as in name_as_tupes: # each node in DNS , => e.g ('root_server', 150)
		node_name = name_as[0]
		if zone = '.' # if root server
			my_fileter = Filter(asn=200) # Install root servers only on AS200
			my_binding = Binding(filter=my_fileter) # specifies the binding of a single server in the component.
		elif zone = 'com.': # if com server
			my_fileter = Filter(asn=300) # Install com servers only on AS300
			my_binding = Binding(filter=my_fileter)
		else: # other zone.
			my_fileter = Filter(asn=400) # pick one of the nodes randomly.
			my_binding = Binding(filter=my_fileter)
		final_bindings[node_name] = my_binding
my_config = Configuration(final_bindings)

simB.connect(my_config,dns)
```

### Some thoughts

- ***How can we avoid repeated installation on the same host when the developer have used ASN connector 2 or more times?***

## Scenario 2: Anycast DNS server

### Expectation input explaination

 - dns-dump.bin: Service component, including 2 root servers, 1 com. server, 1 net. server and example.com server. Developer want to assign 2 root servers in anycast nodes.
 - internet-1.bin: Base component, including AS100,AS200,AS300,AS400,AS500. It has already implemented anycast feature within node named "anycast-host-0" and "anycast-host-1".

### Connector type

Using Node name to specifcally bind.

### Component connect code

```python
from seedsim.core import Configuration, Binding, Filter, Action
simA = Emulator()
simB = Emulator()
simA.load('dns-dump.bin')   # service component.
simB.load('internet-1.bin') # anycast base component, data sheet contains "anycast-host-0","anycast-host-1" and other nodes.

final_bindings = {}
dns: DomainNameService = simA.getLayer('DomainNameService')

#Get root server pin
root_1 = dns.getZoneServerNames('.')[0][0]
root_2 = dns.getZoneServerNames('.')[1][0]

#Bind root server in anycast nodes
final_bindings[root_1] = Binding(filter=Filter(node_name='anycast-host-0'))
final_bindings[root_2] = Binding(filter=Filter(node_name='anycast-host-1'))

#Randomly bind other zone
zones = dns.getZones() # => ['.', 'com.', 'net.', 'example.com.']
zones.remove('.') # Remove root zone, already handle that.
for zone in zones: 
	name_as_tupes = dns.getZoneServerNames(zone) 
	
	for name_as in name_as_tupes: 
		node_name = name_as[0]
		my_fileter = Filter(asn=400) # pick one of the nodes randomly.
		my_binding = Binding(filter=my_fileter)
		final_bindings[node_name] = my_binding

my_config = Configuration(final_bindings)

simB.connect(my_config, dns)
```

### Some thoughts

- ***If there are so many anycast nodes, can we add an ACTION to bind it in order by a TAG? Instead of writing many lines of code.***

## Scenario 3: More than 500 dns server

### expectation input explaination

 - dns-dump.bin: Service component, including 10 root servers, 10 com. server, 10 net. server and 470 different domain name NS server. 
 - internet-1.bin: Base component, including AS100,AS200,AS300,AS400,AS500.

### Connector type

Using IP prefix connector 

### Component connect code

```python
from seedsim.core import Configuration, Binding, Filter, Action
simA = Emulator()
simB = Emulator()
simA.load('dns-dump.bin')   # service component.
simB.load('internet-1.bin') # base component, including AS100,AS200,AS300,AS400,AS500.

final_bindings = {}
dns: DomainNameService = simA.getLayer('DomainNameService')

zones = dns.getZones() # => ['.', 'com.', 'net.', 'example.com.']
for zone in zones: 
	name_as_tupes = dns.getZoneServerNames(zone) 
	
	for name_as in name_as_tupes: 
		node_name = name_as[0] # node name in dns component
		my_fileter = Filter(prefix="10.200.0.0/23") #Install our 500 dns server in /23 CIDR prefix.
		my_binding = Binding(filter=my_fileter)
		final_bindings[node_name] = my_binding

my_config = Configuration(final_bindings)

simB.connect(my_config, dns)
```

### Some thoughts

- ***Also, if I use same ip prefix in a loop, how to avoid repeated installation issue?***

## Scenario 4: Real world DNS infrastructure

### expectation input explaination

 - dns-dump.bin: DNS Service component.
 	- Root server list
 		- a-root-server
 		- b-root-server
 		- c-root-server
 		- d-root-server
	- COM TLD server list
		- a-gtld-servers.net
		- b-gtld-servers.net 
		- c-gtld-servers.net
	- NET TLD server list
		- d-gtld-servers.net
		- e-gtld-servers.net
		- f-gtld-servers.net
	- EDU TLD server list
		- a-edu-servers.net 
		- b-edu-servers.net
		- c-edu-servers.net
	- CN TLD server list
		- a-dns.cn
		- b-dns.cn
		- c-dns.cn 
	- Dnspod 
		- ns[1-100]-dnspod.com
	- openDNS
		- ns1[1-200]-opendns.com
	- Google DNS
		- dns-google (can be installed by IP 8.8.8.8) 
	- Local DNS
		- local[1-50]-dns
 - internet-1.bin: Base component, including AS100,AS200,AS300,AS400,AS500.
 - website.bin: Web service component, including google.com, facebook.com

### Component connect code

```python
from seedsim.core import Configuration, Binding, Filter, Action
simA = Emulator()
simB = Emulator()
simC = Emulator()

simA.load('dns-dump.bin')   # dns service component.
simB.load('internet-1.bin') # base component.
simC.load('website.bin') # web service component.


dns_bindings = {}
dns: DomainNameService = simA.getLayer('DomainNameService')
web: WebService = simC.getLayer('WebService')

#Deploy DNS to base
dns_bindings['.*root-server'] = Binding(filter=Filter(asn=100)) # Deploy root servers
dns_bindings['.*gtld-servers.net'] = Binding(filter=Filter(prefix="192.10.1.0/24")) # Deploy com/net servers
dns_bindings['.*edu-servers.net'] = Binding(filter=Filter(node_name="EDU[1-10]")) # Deploy edu servers
dns_bindings['[a-z]-dns.cn'] = Binding(filter=Filter(node_name=".*CN")) # Deploy CN servers
dns_bindings['ns[1-100]-dnspod.com'] = Binding(filter=Filter(node_name=".*CN")) # Deploy dnspod
dns_bindings['dns-google'] = Binding(filter=Filter(ip="8.8.8.8")) # Deploy google public DNS
dns_bindings['local[1-50]-google'] = Binding(filter=Filter(any_services="DomainNameCachingService")) # Deploy local dns

#Deploy Web service to base
web_bindings['google-com'] = Binding(filter=Filter(asn=300, lambda="lambda service_name, node: not node.getServices().has('FirewallService')"))
web_bindings['facebook-com'] = Binding(filter=Filter(asn=400, not_services="WebService"))


dns_config = Configuration(dns_bindings)
web_config = Configuration(web_bindings)

simB.connect(dns_config,dns)
simB.connect(web_config,web)
```

### Some thoughts

- ***What if I want to deploy 50 local-dns to AS[1-50] respectively, for example, local1-dns in AS1, local2-dns in AS2 etc. How can I achieve that by API?***

