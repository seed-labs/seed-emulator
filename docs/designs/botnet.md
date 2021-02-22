
# Botnet

## What is Botnet?

A botnet is a number of Internet-connected devices, each of which is running one or more bots. Botnets can be used to perform Distributed Denial-of-Service (DDoS) attacks, steal data, send spam, and allow the attacker to access the device and its connection.

Our emulator allows user to create Botnet service, including C2 (Command & Control) server and BotClient components. Each of service can be installed in any node in the emulator.

## Botnet Service API

### Install Botnet service example

**Comment:** Please add detailed explanation to show users how to use 
the class. Basically, you need to explain your code. 

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

**Comment:** This example is too simplified. Please add at least two bots
in this example. 



### seedsim.services.BotnetService

The class of Botnet C2 service. C2 server is used for maintaining communications with compromised systems within a target network. The instance of BotnetService() could invoke installByName API to install C2 service on a specific host by providing Autonomous System Number and Host Name.

After installation, user can attach to the docker instance of C2 server. Then go to ```/tmp/byob/byob/``` folder, by runing ```python3 server.py --port 445``` to launch the console of C2 service. More detail usage about C2 console, type ```help``` or see [Byob Document](https://github.com/malwaredllc/byob).

### seedsim.services. BotnetClientService

The class of Bot client service (usually refer to compromised systems). The instance of BotnetClientService() could invoke installByName API to install C2 service on a specific host by providing Autonomous System Number and Host Name.

### seedsim.services. BotnetClientService#setServer

This class has a method called ```setServer``` to setup the Bot client. An Bot client instance is required to setup some basic configuration. The following are attributes of ```setServer``` method.

| Attribute   |      Type     |  Description |
|-------------|:-------------:|-------------:|
| c2_server   |  Required, String | IP address of C2 server. In order to tell Bot client who is the c2_server, and when docker instance has launched, Bot client will continously connect to C2 server|
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

....#create as and host
c = bot_client.installByName(asn, host_name)
c.setServer(c2_server_ip, enable_dga=True, dga=dga)

```

**Comment:**  With dga, I thought that IP address is not used. 
Why is it still in the code?  Please also add comments to the 
code above. 



## Demonstration 

**Comment:** You have shown me the demonstration of the botnet. Can you 
write down what you have demonstrated, just like what you did during
the demonstration? All the files that are needed should be stored 
somewhere, so others can duplicate your demonstration.
