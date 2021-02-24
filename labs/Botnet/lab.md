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
from seedsim.core import Simulator
from seedsim.services import BotnetService, BotnetClientService
from seedsim.services import DomainRegistrarService
from seedsim.compiler import Docker

sim = Simulator() # create a emulator instance

sim.load('mini-internet.bin') # invoke load method to import mini internet emulator
```

After that, In this exist emulator, we already know we have many AS . We select AS150 as C2 server and install our C2 service on a host in it. The following code shows how can we deploy a C2 server in emulator.

```
bot = BotnetService()    # Create botnet service instance
bot_client = BotnetClientService() # Create botnet client service instance


base_layer = sim.getLayer('Base') # Get base layer from a existed emulator
as_150 = base_layer.getAutonomousSystem(150) # Get AS150 object
hosts = as_150.getHosts() # Get all host names in AS150
c2_server_ip = "10.150.0.71"

bot.installByName(150, hosts[0]) # Deploy C2 service in a host that in AS150
```
The above code


### Task1.B: Setup bot client


### Task1.C: How it works

 - Design activities to help students understand how Botnet works.


## Task 2. Launching Attacks Using Botnet

 - Design activities to help students use the Botnet
   in attacks. For example, launch a DDoS attack. 

 - Let's try to find 2-3 interesting things to do here.


## Task 3. Writing Your Own Programs

 - Ask students to write their own program, and push it to 
   each bot. Use a skeleton code to show students how 
   to write such a code. 


## Task 4. Evading Firewalls

Add DGA to the Botnet to make it more difficult to block. 
We will also change the IP address of the command & control.

