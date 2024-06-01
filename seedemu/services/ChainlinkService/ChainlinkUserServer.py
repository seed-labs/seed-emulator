from seedemu import *
from seedemu.core.enums import NetworkType
from .ChainlinkTemplates import ChainlinkUserTemplate, ChainlinkFileTemplate
from .ChainlinkBaseServer import *
 

class ChainlinkUserServer(ChainlinkBaseServer):
    """
    @brief The Chainlink virtual user server.
    """

    __name: str
    __external_url: str = "https://min-api.cryptocompare.com/data/pricemultifull?fsyms=ETH&tsyms=USD"
    __path: str = "RAW,ETH,USD,PRICE"
    __number_of_normal_servers: int = 1

    
    def __init__(self): 
        """
        @brief ChainlinkServer Constructor.
        """
        super().__init__()


    
    def install(self, node: Node):
        """
        @brief Install the service.
        """

        self.__installSoftware(node)
        self.__setScriptFiles(node)
        
        # Get the Link contract address
        node.appendStartCommand('bash /chainlink_user/check_link_contract.sh')       

        # Get the Chainlink oracle contract addresses
        node.appendStartCommand('python3 /chainlink_user/get_contract_addresses.py')

        # Deploy user contract
        node.appendStartCommand('python3 ./contracts/deploy_user_contract.py')

        # Set the LINK token contract address and oracle contract 
        # addresses in the user contract
        node.appendStartCommand('python3 ./contracts/set_contract_addresses.py')

        # Invoke the Link token contract to get funding 
        node.appendStartCommand('python3 ./contracts/fund_user_contract.py')     

        # Request ETH Price
        node.appendStartCommand('python3 ./contracts/request_eth_price.py')
    
    def __installSoftware(self, node: Node):
        """
        @brief Install the software.
        """
        software_list = ['ipcalc', 'jq', 'iproute2', 'sed', 'curl', 'python3', 'python3-pip']
        for software in software_list:
            node.addSoftware(software)

        node.addBuildCommand('pip3 install web3==5.31.1')
    

    def __setScriptFiles(self, node: Node):
        """
        @brief Deploy the user contract.
        """
        # Check if the chainlink init node is up and running
        node.setFile('/chainlink_user/check_link_contract.sh',
             ChainlinkFileTemplate['check_link_contract'].format(
                    util_node_ip=self._util_server_ip,
                    util_node_port=self._util_server_port,
                    contract_name =LinkTokenFileTemplate['link_contract_name']))


        # Get the link token and oracle contract addresses
        node.setFile('/chainlink_user/get_contract_addresses.py', 
             ChainlinkUserTemplate['get_contract_addresses'].format(
                  util_server_ip=self._util_server_ip, 
                  number_of_normal_servers=self.__number_of_normal_servers))

        node.setFile('./contracts/user_contract.abi', 
                ChainlinkUserTemplate['user_contract_abi'])

        node.setFile('./contracts/user_contract.bin', 
                ChainlinkUserTemplate['user_contract_bin'])

        node.setFile('./contracts/deploy_user_contract.py', 
                ChainlinkUserTemplate['deploy_user_contract'].format(
                    rpc_url=self._eth_server_ip, 
                    rpc_port=self._eth_server_http_port, 
                    faucet_url=self._faucet_server_ip, 
                    faucet_port=self._faucet_server_port, 
                    chain_id=self._chain_id))

        node.setFile('./contracts/set_contract_addresses.py', 
                ChainlinkUserTemplate['set_contract_addresses'].format(
                    rpc_url=self._eth_server_ip, 
                    faucet_url=self._faucet_server_ip, 
                    rpc_port=self._eth_server_http_port, 
                    faucet_port=self._faucet_server_port, 
                    chain_id=self._chain_id))

        # The Link contract abi is needed for funding the user contract with
        # Link tokens 
        node.setFile('./contracts/link_token.abi', 
                LinkTokenFileTemplate['link_contract_abi'])

        node.setFile('./contracts/fund_user_contract.py', 
                ChainlinkUserTemplate['fund_user_contract'].format(
                    chain_id=self._chain_id, 
                    rpc_url=self._eth_server_ip, 
                    rpc_port=self._eth_server_http_port, 
                    faucet_url=self._faucet_server_ip, 
                    faucet_port=self._faucet_server_port))


        # The ...         
        node.setFile('./contracts/request_eth_price.py', 
                ChainlinkUserTemplate['request_eth_price'].format(
                    chain_id=self._chain_id,
                    rpc_url=self._eth_server_ip,
                    rpc_port=self._eth_server_http_port,
                    faucet_url=self._faucet_server_ip,
                    faucet_port=self._faucet_server_port,
                    url=self.__external_url,
                    path=self.__path,
                    number_of_normal_servers=self.__number_of_normal_servers))

    def setName(self, name: str):
        """
        @brief Set name.
        """
        self.__name = name
        
    def setChainlinkServiceInfo(self, number_of_normal_servers: int):
        """
        @brief Set the chainlink init node
        """
        self.__number_of_normal_servers = number_of_normal_servers
        return self

    
