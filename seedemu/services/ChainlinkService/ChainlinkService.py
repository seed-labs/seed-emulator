from seedemu import *
from typing import Dict
from seedemu.core.Node import Node

from seedemu.core.Service import Server
import pdb
from enum import Enum
from seedemu.services.ChainlinkService.ContractTemplates import *


# Templates for configuration files remain the same
ChainlinkFileTemplate: Dict[str, str] = {}

ChainlinkFileTemplate['config'] = """\
[Log]
Level = 'info'

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
    @brief The Chainlink virtual node server.
    """
    __node: Node
    __emulator: Emulator
    __eth_node_ip_address: str

    def __init__(self):
        """
        @brief ChainlinkServer Constructor.
        """
        super().__init__()
        self._base_system = BaseSystem.SEEDEMU_CHAINLINK

    def configure(self, node: Node, emulator: Emulator):
        """
        @brief Configure the node.
        """
        self.__node = node
        self.__emulator = emulator

    def install(self, node: Node):
        """
        @brief Install the service.
        """
        ChainlinkServerCommands().installSoftware(node)
        
        if self.__eth_node_ip_address is None:
            raise Exception('RPC address not set')
        
        ChainlinkServerCommands().setConfigurationFiles(node, self.__eth_node_ip_address)
        ChainlinkServerCommands().chainlinkStartCommands(node)
        
    def setRPCAddress(self, address: str):
        """
        @brief Set the ethereum RPC address.

        @param address The RPC address for the chainlink node
        """
        self.__eth_node_ip_address = address

    def print(self, indent: int) -> str:
        out = ' ' * indent
        out += 'Chainlink server object.\n'
        return out
            
class ChainlinkInitializerServer(Server):
    """
    @brief The Chainlink initializer class.
    """
    
    class DeploymentType(Enum):
        CURL = 1
        WEB3 = 2

    __node: Node
    __emulator: Emulator
    __deploymentType: str
    __owner: str
    __rpcURL: str
    __privateKey: str
    
    def __init__(self):
        """
        @brief ChainlinkServer Constructor.
        """
        super().__init__()
        self._base_system = BaseSystem.SEEDEMU_CHAINLINK

    def configure(self, node: Node, emulator: Emulator):
        """
        @brief Configure the node.
        """
        pdb.set_trace()
        self.__node = node
        self.__emulator = emulator

    def installInitializer(self, node: Node):
        """
        @brief Install the service.
        """
        if self.__rpcURL is None:
            raise Exception('RPC address not set')
        
        # Add software dependency
        ChainlinkServerCommands().installSoftware(node)
        ChainlinkServerCommands().installInitSoftware(node)
        ChainlinkServerCommands().setConfigurationFiles(node, self.__rpcURL)
                
        # if self.__deploymentType == DeploymentType.CURL:
        #     # Deploy the contracts using curl
        #     deployThroughCURL(self.owner)
        if self.__deploymentType == "web3":
            # Deploy the contracts using web3
            self.deployThroughWeb3()
            
        ChainlinkServerCommands().chainlinkStartCommands(node)
            
    def setContractOwner(self, owner: str):
        """
        @brief Set the owner of the contracts
        
        @param owner The owner of the contracts
        """
        self.__owner = owner

    def setDeploymentType(self, deploymentType: str = "web3"):
        """
        @brief Set the deployment type.
        
        @param deploymentType The deployment type.
        """
        self.__deploymentType = deploymentType
            
    def setOwnerPrivateKey(self, privateKey: str):
        """
        @brief Set the owner private key.
        
        @param privateKey The private key of the owner.
        """
        self.__privateKey = privateKey
        
    def setRPCURL(self, rpcURL: str):
        """
        @brief Set the RPC URL.
        
        @param rpcURL The RPC URL.
        """
        self.__rpcURL = rpcURL
        
    def deployThroughWeb3(self):
        """
        @brief Deploy the contracts using web3.
        
        @param owner The owner of the contracts
        @param rpcURL The RPC URL
        @param privateKey The private key of the owner
        """
        # Deploy the contracts using web3
        self.__node.setFile('/contracts/deploy_linktoken_contract.py', LinkTokenDeploymentTemplate['link_token_contract'].format(rpc_url = self.__rpcURL, private_key = self.__privateKey))
        self.__node.setFile('/contracts/link_token.abi', LinkTokenDeploymentTemplate['link_token_abi'])
        self.__node.setFile('/contracts/link_token.bin', LinkTokenDeploymentTemplate['link_token_bin'])
        self.__node.appendStartCommand(f'python3 ./contracts/deploy_linktoken_contract.py')
        self.__node.appendStartCommand('echo "LinkToken contract deployed"')
        self.__node.setFile('/contracts/deploy_oracle_contract.py', OracleContractDeploymentTemplate['oracle_contract_deploy'].format(rpc_url = self.__rpcURL, private_key = self.__privateKey, owner_address = self.__owner))
        self.__node.setFile('/contracts/oracle_contract.abi', OracleContractDeploymentTemplate['oracle_contract_abi'])
        self.__node.setFile('/contracts/oracle_contract.bin', OracleContractDeploymentTemplate['oracle_contract_bin'])
        self.__node.appendStartCommand(f'python3 ./contracts/deploy_oracle_contract.py')
        self.__node.appendStartCommand('echo "Oracle contract deployed"')
        
        
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
        self.addDependency('EthereumService', False, False)

    def _createServer(self) -> ChainlinkServer:
        self._log('Creating Chainlink server.')
        return ChainlinkServer()

    def _createInitializerServer(self) -> ChainlinkInitializerServer:
        return ChainlinkInitializerServer()

    def configure(self, emulator: Emulator):
        super().configure(emulator)
        targets = self.getTargets()
        for (server, node) in targets:
            server.configure(node, emulator)

    def getName(self) -> str:
        return 'ChainlinkService'

    def print(self, indent: int) -> str:
        out = ' ' * indent
        out += 'ChainlinkServiceLayer\n'
        return out
    

class ChainlinkServerCommands:
    def __init__(self):
        pass
    
    def installSoftware(self, node: Node):
        """
        @brief Install the software.
        """
        software_list = ['ipcalc', 'jq', 'iproute2', 'sed', 'postgresql', 'postgresql-contrib']
        for software in software_list:
            node.addSoftware(software)
    
    def installInitSoftware(self, node: Node):
        """
        @brief Install the software.
        """
        software_list = ['curl', 'python3', 'python3-pip']
        for software in software_list:
            node.addSoftware(software)
        node.addBuildCommand('pip3 install web3==5.31.1')
        
    def setConfigurationFiles(self, node: Node, eth_node_ip_address: str):
        """
        @brief Set configuration files.
        """
        config_content = ChainlinkFileTemplate['config'].format(ip_address=eth_node_ip_address)
        node.setFile('/config.toml', config_content)
        node.setFile('/secrets.toml', ChainlinkFileTemplate['secrets'])
        node.setFile('/api.txt', ChainlinkFileTemplate['api'])
        
    def chainlinkStartCommands(self, node: Node):
        """
        @brief Add start commands.
        """
        start_commands = """
service postgresql restart
su - postgres -c "psql -c \\"ALTER USER postgres WITH PASSWORD 'mysecretpassword';\\""
chainlink node -config /config.toml -secrets /secrets.toml start -api /api.txt
"""
        node.appendStartCommand(start_commands)
        