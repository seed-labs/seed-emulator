# Core Classes

We list our core base classes here:

- ```AS```: Autonomous System
- ```IX```: Internet Exchange
- ```Network```: Network
- ```Router```: General router class
- ```Service```: For services installed on hosts, such as DNS, Firewall, etc. 
- ```Internet```: 


## Internet Classes

- ```DNSInfrastructure```: Consider this as a layer of the Internet. We can overlay this infrastructure layer to the existing Internet simulator. We need to figure out how to do the overlay. A simple idea is to map each DNS server to one of the host machines inside the simulator (or add them to the network they belong to). Basically, in this layer, we only need to create the root server, TLD server, and various nameservers, and we assign each of them an IP address. When we overlay this to the Internet, we hook them to the networks inside the Internet.  


## Router Classes

We list customized Router classes here.

- ```BGPRouter (Router)```: BGP router
- ```RouteServer (Router)```: Router server in IXP

## Host Classes

We list customized Host classes here.


## Service Classes

We list customized Service classes here.

- ```WebService```: For running web services
- ```TelnetService```: For running telnet services
- ```DNSService```: For DNS service
- ```FirewallService```: For running firewall
- ```IDSService```: For running intrusion detection services
- ```SnifferService```: For running sniffing via ```tcpdump```
- ```VPNService```: For running VPN server via ```openvpn```