from seedemu import *
from seedemu.core.Node import Node
from seedemu.core.Service import Server
from seedemu.core.enums import NetworkType
#from seedemu.services.ChainlinkService.ChainlinkTemplates import *
from .ChainlinkTemplates import *
from .ChainlinkBaseServer import *
from .ChainlinkUserServer import *
import re

class ChainlinkServer(ChainlinkBaseServer):
    """
    @brief The Chainlink virtual node server.
    """
    __name:str
    __username: str = "seed@example.com"
    __password: str = "blockchainemulator"
    __DIR: str = '/chainlink'

    def __init__(self):
        """
        @brief ChainlinkServer Constructor.
        """
        super().__init__()
        self._base_system = BaseSystem.SEEDEMU_CHAINLINK

    def setName(self, name: str):
        """
        @brief Set name.
        """
        self.__name = name

    def install(self, node: Node):
        """
        @brief Install the service.
        """

        self.__installSoftware(node)
        self.__installConfigurationFiles(node)
        self.__installLibrary(node)
        self.__installScriptFiles(node)


        # Start the Chainlink server 
        node.appendStartCommand(ChainlinkFileTemplate['start_commands'])
       
        # All the Chainlink commands are included in this shell script
        # This way, we can run it in the background, so it does not block
        # the start command of the container 
        node.appendStartCommand(f'bash {self.__DIR}/chainlink_setup.sh &') 


    def __installLibrary(self, node: Node):
        """
        @brief Install the library.
        """
        node.importFile(hostpath=BlockchainLibrary['ethereum_helper'],
                        containerpath=f'{self.__DIR}/EthereumHelper.py')
        node.importFile(hostpath=BlockchainLibrary['faucet_helper'],
                        containerpath=f'{self.__DIR}/FaucetHelper.py')
        node.importFile(hostpath=BlockchainLibrary['utility_server_helper'],
                        containerpath=f'{self.__DIR}/UtilityServerHelper.py')


    def __installScriptFiles(self, node:Node):
        """
        @brief Install the needed files.
        """

        # Set the oracle contracts 
        node.setFile(f'{self.__DIR}/contracts/oracle_contract.abi', 
                     OracleContractDeploymentTemplate['oracle_contract_abi'])
        node.setFile(f'{self.__DIR}/contracts/oracle_contract.bin', 
                     OracleContractDeploymentTemplate['oracle_contract_bin'])

        node.setFile(f'{self.__DIR}/chainlink_setup.sh', 
                     ChainlinkFileTemplate['setup_script'])

        node.setFile(f'{self.__DIR}/get_auth_sender.sh', 
                     ChainlinkFileTemplate['get_auth_sender'])

        node.setFile(f'{self.__DIR}/fund_auth_sender.py', 
                     ChainlinkFileTemplate['fund_auth_sender'].format(
                         faucet_server=self._faucet_server_ip, 
                         faucet_server_port=self._faucet_server_port)) 

        node.setFile(f'{self.__DIR}/deploy_oracle_contract.py', 
                     OracleContractDeploymentTemplate['deploy_oracle_contract'].format(
                        chain_id=self._chain_id, 
                        eth_server=self._eth_server_ip,
                        eth_server_http_port=self._eth_server_http_port,
                        util_server=self._util_server_ip,
                        util_server_port=self._util_server_port,
                        link_contract_name=LinkTokenFileTemplate['link_contract_name'],
                        faucet_server=self._faucet_server_ip, 
                        faucet_server_port=self._faucet_server_port))


        node.setFile(f'{self.__DIR}/register_contract.py', 
                     ChainlinkFileTemplate['register_contract'].format(
                           util_server=self._util_server_ip,
                           util_server_port=self._util_server_port,
                           node_name=self.__name))

        node.setFile(f'{self.__DIR}/create_jobs.sh', 
                     ChainlinkFileTemplate['create_jobs'])


    def __installSoftware(self, node:Node):
        """
        @brief Install the software.
        """
        software_list = ['ipcalc', 'jq', 'iproute2', 'sed', 'postgresql', 
                         'postgresql-contrib', 'curl', 'python3', 'python3-pip']
        for software in software_list:
            node.addSoftware(software)
        node.addBuildCommand('pip3 install web3==5.31.1')


    def __installConfigurationFiles(self, node:Node):
        """
        @brief Set configuration files.
        """
        config_content = ChainlinkFileTemplate['config'].format(
                             chain_id=self._chain_id, 
                             eth_server_ip=self._eth_server_ip, 
                             eth_server_ws_port=self._eth_server_ws_port, 
                             eth_server_http_port=self._eth_server_http_port)
        node.setFile(f'{self.__DIR}/config.toml', config_content)
        node.setFile(f'{self.__DIR}/db_secrets.toml', ChainlinkFileTemplate['secrets'])
        node.setFile(f'{self.__DIR}/password.txt', 
                     ChainlinkFileTemplate['api'].format(
                         username=self.__username, password=self.__password))
        node.setFile(f'{self.__DIR}/jobs/getUint256.toml', 
                     ChainlinkJobsTemplate['getUint256'])
        node.setFile(f'{self.__DIR}/jobs/getBool.toml',
                     ChainlinkJobsTemplate['getBool'])


    def setUsernameAndPassword(self, username: str, password: str):
        """
        Set the username and password for the Chainlink node API after validating them.

        @param username: The username for the Chainlink node API.
        @param password: The password for the Chainlink node API.
        """
        if not self.__validate_username(username):
            raise ValueError("The username must be a valid email address.")
        if not self.__validate_password(password):
            raise ValueError("The password must be between 16 and 50 characters in length.")

        self.__username = username
        self.__password = password
        return self

    def __validate_username(self, username: str) -> bool:
        """
        Check if the username is a valid email address.
        """
        pattern = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b")
        return re.fullmatch(pattern, username) is not None

    def __validate_password(self, password: str) -> bool:
        """
        Check if the password length is between 16 and 50 characters.
        """
        return 16 <= len(password) <= 50

    def print(self, indent: int) -> str:
        out = ' ' * indent
        out += 'Chainlink server object.\n'
        return out


class ChainlinkService(Service):
    """
    @brief The Chainlink service class.
    """
    __faucet_vnode_name: str
    __faucet_ip:str
    __faucet_port: int

    __util_server_vnode_name:str
    __util_server_ip:str
    __util_server_port:int

    __eth_server_vnode_name:str
    __eth_server_ip:str
    __eth_server_http_port:int
    __eth_server_ws_port:int

    __chain_id:int

    def __init__(self, eth_server:str='', faucet_server:str='', utility_server:str=''):
        """
        @brief ChainlinkService constructor.
        """
        super().__init__()
        self.addDependency('EthereumService', False, False)

        self.__eth_server_vnode_name  = eth_server
        self.__faucet_vnode_name      = faucet_server
        self.__util_server_vnode_name = utility_server


    def _createServer(self) -> ChainlinkServer:
        """!
        @brief Invoke by the install() method of this service
        """

        self._log('Creating Chainlink server.')
        return ChainlinkServer()


    def _createUserServer(self) -> ChainlinkUserServer:
        """!
        @brief Invoke by the installUserServer() method of this service
        """

        self._log('Creating Chainlink user node.')
        return ChainlinkUserServer()


    def installUserServer(self, vnode: str) -> ChainlinkUserServer:
        """!
        @brief Create a Chainlink user node 
        """

        if vnode in self._pending_targets.keys(): return self._pending_targets[vnode]

        s = self._createUserServer()
        self._pending_targets[vnode] = s

        return self._pending_targets[vnode]
 

    def __getIPbyVNodeName(self, emulator:Emulator, vnode:str):
        """
        @brief Get the IP address of a virtual node; the virtual node
        should have already been bound to a physical node. 

        @param vnode The name of the virtual node
        """
        node = emulator.getBindingFor(vnode)
        assert node != None, 'Virtual node {} has not been bound to a physical node yet.'.format(vnode)

        address: str = None
        ifaces = node.getInterfaces()
        assert len(ifaces) > 0, 'Node {} has no IP address.'.format(node.getName())
        for iface in ifaces:
            net = iface.getNet()
            if net.getType() == NetworkType.Local:
                address = iface.getAddress()
                break
        return address

    def _doConfigure(self, node: Node, server: Server):
        """!
        @brief Configure each server of the service. We mainly pass some of
        the essential information to each server object.

        @param node node
        @param server server
        """
        # There are two types of servers created by this service,
        # chainlink server and chainlink user node. They are both
        # subclass of ChainlinkBaseServer 
        server:ChainlinkBaseServer = server
        server._setEthServer(eth_server_ip=self.__eth_server_ip,
                             eth_server_http_port=self.__eth_server_http_port,
                             eth_server_ws_port=self.__eth_server_ws_port,
                             chain_id=self.__chain_id)

        server._setUtilityServer(util_server_ip=self.__util_server_ip,
                                 util_server_port=self.__util_server_port)

        server._setFaucetServer(faucet_server_ip=self.__faucet_ip,
                                faucet_server_port=self.__faucet_port)

        return


    def configure(self, emulator: Emulator):
        """!
        @brief Configure the service. An important step is to deploy the 
        LINK contract using the utility server. 

        """

        # Save the virtual node name in the server class 
        for vnode, server in self._pending_targets.items():
            server.setName(vnode)
        
        # Get the IP addresses of the servers 
        self.__faucet_ip      = self.__getIPbyVNodeName(emulator, 
                                               self.__faucet_vnode_name)
        self.__eth_server_ip  = self.__getIPbyVNodeName(emulator, 
                                               self.__eth_server_vnode_name)
        self.__util_server_ip = self.__getIPbyVNodeName(emulator, 
                                               self.__util_server_vnode_name)

        # Get the instance of the linked ethereum server 
        eth_server:EthereumServer = emulator.getServerByVirtualNodeName(
                                               self.__eth_server_vnode_name)
        assert eth_server != None, 'The linked Ethereum server does not exist!'

        # Get the instance of the faucet server 
        faucet = emulator.getServerByVirtualNodeName(self.__faucet_vnode_name)
        assert faucet != None, 'The faucet server does not exist!'

        # Get the instance of the utility server 
        utility:EthUtilityServer = emulator.getServerByVirtualNodeName(
                                               self.__util_server_vnode_name)
        assert utility != None, 'The Utility server does not exist!'

        # Use the utility server to deploy the Link contract
        utility.deployContractByContent(
            contract_name=LinkTokenFileTemplate['link_contract_name'],
            abi_content=LinkTokenFileTemplate['link_contract_abi'],
            bin_content=LinkTokenFileTemplate['link_contract_bin'])

        # Get the setup information (especially the port numbers)
        self.__chain_id             = eth_server.getChainId()
        self.__eth_server_http_port = eth_server.getGethHttpPort()
        self.__eth_server_ws_port   = eth_server.getGethWsPort()
        self.__util_server_port     = utility.getPort()
        self.__faucet_port          = faucet.getPort()

        # This will eventually invoke self._doConfigure(), which conducts
        # further configuration on each server of the Chainlink service. 
        super().configure(emulator)


    def setEthServer(self, vnode:str):
        self.__eth_server_vnode_name = vnode
        return self

    def setFaucetServer(self, vnode: str):
        self.__faucet_vnode_name = vnode
        return self

    def setUtilityServer(self, vnode:str):
        self.__util_server_vnode_name = vnode
        return self

    def getName(self) -> str:
        return 'ChainlinkService'

    def print(self, indent: int) -> str:
        out = ' ' * indent
        out += 'ChainlinkServiceLayer\n'
        return out
