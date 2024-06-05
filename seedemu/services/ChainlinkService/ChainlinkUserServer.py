from seedemu import *
from seedemu.core.enums import NetworkType
#from .ChainlinkTemplates import ChainlinkUserTemplate, ChainlinkFileTemplate
from .ChainlinkTemplates import *
from .ChainlinkBaseServer import *
 

class ChainlinkUserServer(ChainlinkBaseServer):
    """
    @brief The Chainlink virtual user server.
    """

    __name: str
    __external_url: str = "https://min-api.cryptocompare.com/data/pricemultifull?fsyms=ETH&tsyms=USD"
    __path: str = "RAW,ETH,USD,PRICE"
    __number_of_normal_servers: int = 1

    __DIR = "/chainlink_user"
    __chainlink_servers: list

    
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
        self.__installLibrary(node)
        self.__installScriptFiles(node)
        
        # This script includes all the commands 
        node.appendStartCommand(f'bash {self.__DIR}/chainlink_user_setup.sh &')

    
    def __installSoftware(self, node: Node):
        """
        @brief Install the software.
        """
        software_list = ['ipcalc', 'jq', 'iproute2', 'sed', 'curl', 'python3', 'python3-pip']
        for software in software_list:
            node.addSoftware(software)

        node.addBuildCommand('pip3 install web3==5.31.1')
    

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


    def __installScriptFiles(self, node: Node):
        """
        @brief Install the script files and smart contracts 
        """

        node.setFile(f'{self.__DIR}/contracts/user_contract.abi', 
                ChainlinkUserTemplate['user_contract_abi'])

        node.setFile(f'{self.__DIR}/contracts/user_contract.bin', 
                ChainlinkUserTemplate['user_contract_bin'])

        node.setFile(f'{self.__DIR}/chainlink_user_setup.sh',
                     ChainlinkUserTemplate['setup_script'])

        # Get the link token and oracle contract addresses
        node.setFile(f'{self.__DIR}/get_oracle_addresses.py', 
             ChainlinkUserTemplate['get_oracle_addresses'].format(
                  util_server=self._util_server_ip, 
                  util_server_port=self._util_server_port, 
                  oracle_contract_names=self.__chainlink_servers,
                  link_contract_name=LinkTokenFileTemplate['link_contract_name']))


        node.setFile(f'{self.__DIR}/deploy_user_contract.py', 
                ChainlinkUserTemplate['deploy_user_contract'].format(
                    eth_server=self._eth_server_ip, 
                    eth_server_http_port=self._eth_server_http_port, 
                    faucet_server=self._faucet_server_ip, 
                    faucet_server_port=self._faucet_server_port, 
                    chain_id=self._chain_id))

        node.setFile(f'{self.__DIR}/set_contract_addresses.py', 
                ChainlinkUserTemplate['set_contract_addresses'].format(
                    eth_server=self._eth_server_ip, 
                    eth_server_http_port=self._eth_server_http_port, 
                    faucet_server=self._faucet_server_ip, 
                    faucet_server_port=self._faucet_server_port, 
                    chain_id=self._chain_id))

        # The Link contract abi is needed for funding the user contract with
        # Link tokens 
        node.setFile(f'{self.__DIR}/contracts/link_token.abi', 
                LinkTokenFileTemplate['link_contract_abi'])

        node.setFile(f'{self.__DIR}/fund_user_contract.py', 
                ChainlinkUserTemplate['fund_user_contract'].format(
                    chain_id=self._chain_id, 
                    eth_server=self._eth_server_ip, 
                    eth_server_http_port=self._eth_server_http_port)) 

        node.setFile(f'{self.__DIR}/request_eth_price.py', 
                ChainlinkUserTemplate['request_eth_price'].format(
                    chain_id=self._chain_id,
                    eth_server=self._eth_server_ip,
                    eth_server_http_port=self._eth_server_http_port,
                    faucet_server=self._faucet_server_ip,
                    faucet_server_port=self._faucet_server_port,
                    external_url=self.__external_url,
                    path=self.__path))

    def setName(self, name: str):
        """
        @brief Set name.
        """
        self.__name = name
        
    def setChainlinkServiceInfo(self, number_of_normal_servers: int):
        """
        @brief Set the chainlink service info 
        """
        self.__number_of_normal_servers = number_of_normal_servers
        return self

    def setChainlinkServers(self, servers: list):
        """
        @brief Set the chainlink servers info 
        """
        self.__chainlink_servers = servers
        return self

    
