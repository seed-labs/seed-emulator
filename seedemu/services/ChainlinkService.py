from seedemu import *
from typing import Dict

# Templates for configuration files remain the same
ChainlinkFileTemplate: Dict[str, str] = {}

ChainlinkFileTemplate['config'] = """\
[Log]
Level = 'warn'

[WebServer]
AllowOrigins = '*'
SecureCookies = false

[WebServer.TLS]
HTTPSPort = 0

[[EVM]]
ChainID = '1337'

[[EVM.Nodes]]
Name = 'SEED Emulator'
WSURL = 'ws://{ip_address}:8546'
HTTPURL = 'http://{ip_address}:8545'
"""

ChainlinkFileTemplate['secrets'] = """\
[Password]
Keystore = 'mysecretpassword'
[Database]
URL = 'postgresql://postgres:mysecretpassword@localhost:5432/postgres?sslmode=disable'
"""

ChainlinkFileTemplate['api'] = """\
test@test.com
Seed@emulator123
"""

class ChainlinkServer(Server):
    """
    @brief The Chainlink protocol server.
    """
    __node: Node
    __emulator: Emulator
    __ip_address: str

    def __init__(self):
        """
        @brief ChainlinkServer Constructor.
        """
        super().__init__()

    def configure(self, node: Node, emulator: Emulator, ip_address: str):
        """
        @brief Configure the node.
        """
        self.__node = node
        self.__emulator = emulator
        self.__ip_address = ip_address

    def install(self, node: Node):
        """
        @brief Install the service.
        """
        software_list = ['ipcalc', 'jq', 'iproute2', 'sed', 'postgresql', 'postgresql-contrib']
        for software in software_list:
            node.addSoftware(software)

        # Set configuration files
        eth_node_asn = node.getAsn()
        eth_node_ip_address = f"10.{eth_node_asn}.0.71"
        config_content = ChainlinkFileTemplate['config'].format(ip_address=eth_node_ip_address)
        node.setFile('/config.toml', config_content)
        node.setFile('/secrets.toml', ChainlinkFileTemplate['secrets'])
        node.setFile('/api.txt', ChainlinkFileTemplate['api'])

        # Add start commands
        start_commands = """
service postgresql restart
su - postgres -c "psql -c \\"ALTER USER postgres WITH PASSWORD 'mysecretpassword';\\""
chainlink node start -d -p /chainlink/password.txt -a /chainlink/apicredentials.txt
"""
        node.appendStartCommand(start_commands)

    def print(self, indent: int) -> str:
        out = ' ' * indent
        out += 'Chainlink server object.\n'
        return out

class ChainlinkService(Service):
    """
    @brief The Chainlink service class.
    """
    def __init__(self):
        """
        @brief ChainlinkService constructor.
        """
        super().__init__()
        self.addDependency('Base', False, False)

    def _createServer(self) -> ChainlinkServer:
        return ChainlinkServer()

    def configure(self, emulator: Emulator):
        super().configure(emulator)
        targets = self.getTargets()
        for (server, node) in targets:
            ip_address = ''
            server.configure(node, emulator, ip_address)

    def getName(self) -> str:
        return 'ChainlinkService'

    def print(self, indent: int) -> str:
        out = ' ' * indent
        out += 'ChainlinkServiceLayer\n'
        return out
