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
simA = Simulator()
simB = Simulator()
simA.load('dns-dump.bin')   # service component.
simB.load('internet-1.bin') # base component, has as[100,200,300,400,500]-host[1-10] nodes.

final_bindings = {}
dns: DomainNameService = sim.getLayer('DomainNameService')

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
simB.connect(my_config)
```

### Results

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
simA = Simulator()
simB = Simulator()
simA.load('dns-dump.bin')   # service component.
simB.load('internet-1.bin') # anycast base component, data sheet contains "anycast-host-0","anycast-host-1" and other nodes.

final_bindings = {}
dns: DomainNameService = sim.getLayer('DomainNameService')

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

simB.connect(my_config)
```

### Results

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
simA = Simulator()
simB = Simulator()
simA.load('dns-dump.bin')   # service component.
simB.load('internet-1.bin') # base component, including AS100,AS200,AS300,AS400,AS500.

final_bindings = {}
dns: DomainNameService = sim.getLayer('DomainNameService')

zones = dns.getZones() # => ['.', 'com.', 'net.', 'example.com.']
for zone in zones:
	name_as_tupes = dns.getZoneServerNames(zone)

	for name_as in name_as_tupes:
		node_name = name_as[0] # node name in dns component
		my_fileter = Filter(prefix="10.200.0.0/23") #Install our 500 dns server in /23 CIDR prefix.
		my_binding = Binding(filter=my_fileter)
		final_bindings[node_name] = my_binding

my_config = Configuration(final_bindings)

simB.connect(my_config)
```

### Results

- ***Also, if I use same ip prefix in a loop, how to avoid repeated installation issue?***

## Scenario 4: Private network DNS infrastructure

## Scenario 5: DNS load balance

## Scenario 6:
