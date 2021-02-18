# Internet Simulator

The goal of this project is to build a simulator of the Internet, containing necessary components that will enable us to build replicas of the real-world Internet infrastructure. 

We can already experiment with small-scale attacks like ARP poisoning, TCP hijacking, and DNS poisoning, but our goal is to provide a simulation where users are allowed to conduct attacks on a macroscopic level. The simulation will enable users to launch attacks against the entire Internet. The simulator for the Internet allows users to experiment with various Internet technologies that people usually would not have access to, like BGP. This simulator will enable users to perform a nation-level BGP hijack to bring down the Internet for an entire nation, perform MITM on a core ISP router, or launch DNS poisoning attacks on the TLD name servers.

Users can join the simulated Internet with VPN client software. This simulation is completely transparent to users joining it, allowing many different possibilities. This allows users to conduct and experience in real-time, as if it was happening in the real world. Simulation is popular in every field of engineering, especially for those activities that are expensive or dangerous to conduct. However, popular Internet simulators usually do not do well in a real-time application, as they are mainly designed to be used for research and runs slow. Also, lots of no-for-research-use simulators have very high system requirements, rendering them unfeasible for large-scale simulations.

## Table of Contents

   * [Internet Simulator](#internet-simulator)
      * [Table of Contents](#table-of-contents)
      * [Design](#design)
      * [Case study](#case-study)
         * [BGP peering](#bgp-peering)
         * [Transit provider](#transit-provider)
         * [MPLS transit provider](#mpls-transit-provider)
         * [Fun with DNS](#fun-with-dns)
            * [DNS infrastructure](#dns-infrastructure)
            * [Local DNS](#local-dns)
            * [DNSSEC](#dnssec)
            * [Reverse domain name and IP origin](#reverse-domain-name-and-ip-origin)
         * [A miniature internet](#a-miniature-internet)
         * [Botnet](#botnet)
         * [Bitcoin](#bitcoin)
      * [Advance topics](#advance-topics)
         * [Hook into the rendering](#hook-into-the-rendering)
         * [Buliding new compiler](#buliding-new-compiler)
         * [Buliding new service](#buliding-new-service)
         * [Buliding new layer](#buliding-new-layer)
         * [Creating new graphs](#creating-new-graphs)


## Design

See [design.md](design.md)

## Case study

### BGP peering

### Transit provider

### MPLS transit provider

### Fun with DNS

#### DNS infrastructure

#### Local DNS

#### DNSSEC

#### Reverse domain name and IP origin

### A miniature internet

### Botnet
 * **What is Botnet?**
 	
 	A botnet is a number of Internet-connected devices, each of which is running one or more bots. Botnets can be used to perform Distributed Denial-of-Service (DDoS) attacks, steal data, send spam, and allow the attacker to access the device and its connection.
 	
 	Our emulator allows user to create Botnet service, including C2 (Command & Control) server and BotClient components. Each of service can be installed in any node in the emulator.
 	
 * **Botnet Service API**
 	*  Install Botnet service example
 	
 	```
 	from seedsim.services import BotnetClientService, BotnetService
 	
 	bot = BotnetService()
	bot_client = BotnetClientService()
	
 	as_150 = base.createAutonomousSystem(150)
 	as_151 = base.createAutonomousSystem(151)
 	c2_server = as_150.createHost('c2_server')
 	bot_server = as_151.createHost('bot')
 	
 	c2_server_ip = "10.150.0.71"
 	bot.installByName(150, 'c2_server')
 	c = bot_client.installByName(151, 'bot')
 	c.setServer(c2_server_ip)
 	```
 	
 	* seedsim.services.BotnetService

 		The class of Botnet C2 service. C2 server is used for maintaining communications with compromised systems within a target network. The instance of BotnetService() could invoke installByName API to install C2 service on a specific host by providing Autonomous System Number and Host Name.
 		
 		After installation, user can attach to the docker instance of C2 server. Then go to ```/tmp/byob/byob/``` folder, by runing ```python3 server.py --port 445``` to launch the console of C2 service. More detail usage about C2 console, type ```help``` or see [Byob Document](https://github.com/malwaredllc/byob).
 		
 	* seedsim.services. BotnetClientService
 		
 		The class of Bot client service (usually refer to compromised systems). The instance of BotnetClientService() could invoke installByName API to install C2 service on a specific host by providing Autonomous System Number and Host Name.
 		
 	* seedsim.services. BotnetClientService#setServer
 		
 		This class has a method called ```setServer``` to setup the Bot client. An Bot client instance is required to setup some basic configuration. The following are attributes of ```setServer``` method.
 		
 		| Attribute   |      Type     |  Description |
		|-------------|:-------------:|-------------:|
		| c2_server   |  Required, String | IP address of C2 server. In order to tell Bot client who is the c2_server, and when docker instance has launched, Bot client will continously connect to C2 server|
		| enable_dga  |    Optional, Bool   |   By default, it is False, when we set it to True, Bot client will adopt DGA feature to generate multiple domains and randomly choose one of them to connect. User need to register these domains, let them resolve to C2 server by using [Domain Registrar Service](), the default DGA function code in the following.|
		| dga         | Optional, function |  When you enable DGA featrue, and want to use your own DGA function, you can define a function named ```dga``` with a list return. Bot client service will pass your DGA function to target docker instance, and randomly choose one of your domain list to connect.  If dga is not set and enable_dga is True, it will use default function.|
		
		The following is an example of using self define dga function:
		
		```
		###########################################

		def dga() -> list:
		    #Generate 10 domains for the given time.
		    domain_list = []
		    domain = ""
		    import math, datetime
		    today = datetime.datetime.utcnow()
		    hour = today.hour
		    day = today.day
		    minute = today.minute
		    minute = int(math.ceil(minute/5))*5
		
		    for i in range(16):
		        day = ((day ^ 8 * day) >> 11) ^ ((day & 0xFFFFFFF0) << 17)
		        hour = ((hour ^ 4 * hour) >> 25) ^ 16 * (hour & 0xFFFFFFF8)
		        minute = ((minute ^ (minute << 13)) >> 19) ^ ((minute & 0xFFFFFFFE) << 12)
		        domain += chr(((day ^ hour ^ minute) % 25) + 97)
		        if i > 6:
		            domain_list.append(domain+ ".com")
		
		    return domain_list
		
		##########################################
		
		....#create as and host
		c = bot_client.installByName(asn, host_name)
		c.setServer(c2_server_ip, enable_dga=True, dga=dga)
		
		```
		
		

### Bitcoin

## Advance topics

### Hook into the rendering

### Buliding new compiler

### Buliding new service

### Buliding new layer

### Creating new graphs

