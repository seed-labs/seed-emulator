from seedemu import *
from seedemu.core.enums import NetworkType
from seedemu.services.ChainlinkService.ChainlinkTemplates import ChainlinkUserTemplate, ChainlinkFileTemplate, LinkTokenDeploymentTemplate
 
class ChainlinkUserServer(Server):
    """
    @brief The Chainlink virtual user server.
    """
    __node: Node
    __emulator: Emulator
    __rpc_url: str
    __rpc_vnode_name: str = None
    __init_node_name: str = None
    __init_node_url: str
    __faucet_node_url: str
    __faucet_vnode_name: str = None
    __faucet_port: int = 80
    __chain_id: int = 1337
    __rpc_port: int = 8545
    __number_of_normal_servers: int = None
    __url: str = "https://min-api.cryptocompare.com/data/pricemultifull?fsyms=ETH&tsyms=USD"
    __path: str = "RAW,ETH,USD,PRICE"
    
    def __init__(self):
        """
        @brief ChainlinkServer Constructor.
        """
        super().__init__()

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
        eth_node = self.__emulator.getServerByVirtualNodeName(self.__rpc_vnode_name)
        # Dynamically set the chain id and rpc port
        self.__chain_id = eth_node.getChainId()
        self.__rpc_port = eth_node.getGethHttpPort()
        
        self.__installSoftware()
        if self.__rpc_vnode_name is not None:
            self.__rpc_url = self.__getIPbyEthNodeName(self.__rpc_vnode_name)
        
        if self.__rpc_url is None:
            raise Exception('RPC address not set')
        
        if self.__init_node_name is not None:
            self.__init_node_url = self.__getIPbyEthNodeName(self.__init_node_name)
            
        if self.__init_node_url is None:
            raise Exception('Init node url address not set')
        
        if self.__faucet_vnode_name is not None:
            self.__faucet_node_url = self.__getIPbyEthNodeName(self.__faucet_vnode_name)
            
        if self.__faucet_node_url is None:
            raise Exception('Faucet URL not set')
        
        # Check if the chainlink init node is up and running
        self.__node.setFile('/check_init_node.sh', ChainlinkFileTemplate['check_init_node'].format(init_node_url=self.__init_node_url))
        self.__node.appendStartCommand('bash /check_init_node.sh')       
        # Get the link token and oracle contract addresses
        self.__node.setFile('./requests/get_contract_addresses.py', ChainlinkUserTemplate['get_contract_addresses'].format(init_node_url=self.__init_node_url, number_of_normal_servers=self.__number_of_normal_servers))
        self.__node.appendStartCommand(f'python3 ./requests/get_contract_addresses.py')
        # Import and deploy the user contract
        self.__deployUserContract()
        self.__setContractAddresses()
        self.__fundUserContract()
        self.__requestETHPrice()
    
    def __installSoftware(self):
        """
        @brief Install the software.
        """
        software_list = ['ipcalc', 'jq', 'iproute2', 'sed', 'curl', 'python3', 'python3-pip']
        for software in software_list:
            self.__node.addSoftware(software)
        self.__node.addBuildCommand('pip3 install web3==5.31.1')
    
    def __deployUserContract(self):
        """
        @brief Deploy the user contract.
        """
        self.__node.setFile('./contracts/user_contract.abi', ChainlinkUserTemplate['user_contract_abi'])
        self.__node.setFile('./contracts/user_contract.bin', ChainlinkUserTemplate['user_contract_bin'])
        self.__node.setFile('./contracts/deploy_user_contract.py', ChainlinkUserTemplate['deploy_user_contract'].format(rpc_url=self.__rpc_url, faucet_url=self.__faucet_node_url, rpc_port=self.__rpc_port, faucet_port=self.__faucet_port, chain_id=self.__chain_id))
        self.__node.appendStartCommand(f'python3 ./contracts/deploy_user_contract.py')
        self.__node.appendStartCommand('echo "User contract deployed."')
        
    def __setContractAddresses(self):
        """
        @brief Set the contract addresses in the user contract.
        """
        self.__node.setFile('./contracts/set_contract_addresses.py', ChainlinkUserTemplate['set_contract_addresses'].format(rpc_url=self.__rpc_url, faucet_url=self.__faucet_node_url, rpc_port=self.__rpc_port, faucet_port=self.__faucet_port, chain_id=self.__chain_id))
        self.__node.appendStartCommand(f'python3 ./contracts/set_contract_addresses.py')
        self.__node.appendStartCommand('echo "Contract addresses set."')
        
    def __fundUserContract(self):
        """
        @brief Fund the user contract.
        """
        self.__node.setFile('./contracts/link_token.abi', LinkTokenDeploymentTemplate['link_token_abi'])
        self.__node.setFile('./contracts/fund_user_contract.py', ChainlinkUserTemplate['fund_user_contract'].format(rpc_url=self.__rpc_url, chain_id=self.__chain_id, rpc_port=self.__rpc_port, faucet_url=self.__faucet_node_url, faucet_port=self.__faucet_port))
        self.__node.appendStartCommand(f'python3 ./contracts/fund_user_contract.py')     
        
    def __requestETHPrice(self):
        """
        @brief Request the ETH price.
        """
        self.__node.setFile('./contracts/request_eth_price.py', ChainlinkUserTemplate['request_eth_price'].format(rpc_url=self.__rpc_url, chain_id=self.__chain_id, rpc_port=self.__rpc_port, faucet_url=self.__faucet_node_url, faucet_port=self.__faucet_port, url=self.__url, path=self.__path, number_of_normal_servers=self.__number_of_normal_servers))
        self.__node.appendStartCommand(f'python3 ./contracts/request_eth_price.py')
        
    def setChainlinkServiceInfo(self, init_node_name: str, number_of_normal_servers: int):
        """
        @brief Set the chainlink init node
        """
        self.__init_node_name = init_node_name
        self.__number_of_normal_servers = number_of_normal_servers
        return self
    
    def setRpcByUrl(self, address: str):
        """
        @brief Set the ethereum RPC address.

        @param address The RPC address or hostname for the chainlink node
        """
        self.__rpc_url = address
        return self
        
    def setLinkedEthNode(self, name:str):
        """
        @brief Set the ethereum RPC address.

        @param vnode The name of the ethereum node
        """
        self.__rpc_vnode_name=name
        return self
    
    def setFaucetServerInfo(self, vnode: str, port = 80):
         """
            @brief Set the faucet server information.
         """

         self.__faucet_vnode_name = vnode
         self.__faucet_port = port    
         return self
    

    def __getIPbyEthNodeName(self, vnode:str):
        """
        @brief Get the IP address of the ethereum node.
        
        @param vnode The name of the ethereum node
        """
        node = self.__emulator.getBindingFor(vnode)
        address: str = None
        ifaces = node.getInterfaces()
        assert len(ifaces) > 0, 'Node {} has no IP address.'.format(node.getName())
        for iface in ifaces:
            net = iface.getNet()
            if net.getType() == NetworkType.Local:
                address = iface.getAddress()
                break
        return address
    
    def print(self, indent: int) -> str:
        out = ' ' * indent
        out += 'Chainlink user server object.\n'
        return out
 
    
class ChainlinkUserService(Service):
    """
    @brief The Chainlink service class.
    """
    def __init__(self):
        """
        @brief ChainlinkService constructor.
        """
        super().__init__()
        self.addDependency('Base', False, False)

    def _createServer(self) -> ChainlinkUserServer:
        self._log('Creating Chainlink User server.')
        return ChainlinkUserServer()
    
    def installInitializer(self, vnode:str) -> Server:
        if vnode in self._pending_targets.keys(): 
            return self._pending_targets[vnode]

        s = self._createInitializerServer()
        self._pending_targets[vnode] = s

        return self._pending_targets[vnode]
            
    def configure(self, emulator: Emulator):
        super().configure(emulator)
        targets = self.getTargets()
        for (server, node) in targets:
            server.configure(node, emulator)

    def getName(self) -> str:
        return 'ChainlinkExampleService'

    def print(self, indent: int) -> str:
        out = ' ' * indent
        out += 'ChainlinkExampleServiceLayer\n'
        return out
    

