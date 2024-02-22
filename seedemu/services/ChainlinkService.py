import random
from seedemu import *
from typing import List, Dict


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

class ChainlinkService:
    """
    ChainlinkService is a utility class for setting up Chainlink nodes within autonomous systems in the SEED Emulator environment.
    """

    def __init__(self, autonomous_systems: List[int], emulator: Emulator, number_of_nodes: int = 1):
        if not autonomous_systems:
            raise ValueError("Autonomous systems list cannot be empty.")
        if not emulator:
            raise ValueError("Emulator instance cannot be None.")
        if number_of_nodes < 1:
            raise ValueError("Number of nodes must be at least 1.")

        self.__asns = autonomous_systems
        self.__emu = emulator
        self.number_of_nodes = number_of_nodes
        self.created_chainlink_nodes = []
        self.__used_asns = []
        self.__base = self.__emu.getLayer('Base')

    def create_chainlink_nodes(self):
        for i in range(1, self.number_of_nodes+1):
            try:
                self.__setup_chainlink_node(i)
            except Exception as e:
                print(f"Error setting up Chainlink node {i + 1}: {e}")
        return self.created_chainlink_nodes

    def __setup_chainlink_node(self, node_number: int):
        unused_asns = [asn for asn in self.__asns if asn not in self.__used_asns]
        if not unused_asns:
            raise Exception("No more autonomous systems available.")

        asn = random.choice(unused_asns)
        self.__used_asns.append(asn)

        autonomous_system = self.__base.getAutonomousSystem(asn)
        chainlink_node_name = f"chainlink_node_{node_number}"
        cl_node_address = f"10.{asn}.0.171"
        node = autonomous_system.createHost(chainlink_node_name).joinNetwork('net0', address=cl_node_address)

        self.created_chainlink_nodes.append(node)

        # Setting up the node with Chainlink specific configurations
        self.__set_files(node, asn)
        self.__install_software(node)
        self.__add_commands(node)

    def __set_files(self, node: Node, asn: int):
        eth_node_ip_address = f"10.{asn}.0.71"
        config_template = ChainlinkFileTemplate['config'].format(ip_address=eth_node_ip_address)
        node.setFile('/config.toml', config_template)
        node.setFile('/secrets.toml', ChainlinkFileTemplate['secrets'])
        node.setFile('/api.txt', ChainlinkFileTemplate['api'])

    def __install_software(self, node: Node):
        software_list = ['ipcalc', 'jq', 'iproute2', 'sed', 'postgresql', 'postgresql-contrib']
        for software in software_list:
            node.addSoftware(software)

    def __add_commands(self, node: Node):
        node.appendStartCommand("""
service postgresql restart
su - postgres -c "psql -c \\"ALTER USER postgres WITH PASSWORD 'mysecretpassword';\\""
""")
        node.appendStartCommand('chainlink node -config /config.toml -secrets /secrets.toml start -api /api.txt')
