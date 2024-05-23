from seedemu import *
from seedemu.core.Node import Node
from seedemu.core.Service import Server
from seedemu.core.enums import NetworkType
from seedemu.services.ChainlinkService.ChainlinkTemplates import *
import re

class ChainlinkServer(Server):
    """
    @brief The Chainlink virtual node server.
    """
    __name:str
    __username: str = "seed@example.com"
    __password: str = "blockchainemulator"
    __eth_server_url: str
    __eth_server_ws_port: int
    __eth_server_http_port: int
    __init_server_url: str
    __init_server_port: int
    __faucet_server_url:str
    __faucet_server_port: int
    __chain_id: int

    def __init__(self):
        """
        @brief ChainlinkServer Constructor.
        """
        super().__init__()
        self._base_system = BaseSystem.SEEDEMU_CHAINLINK

    def _setEthServerInfo(self, eth_server_url:str, eth_server_http_port:int, eth_server_ws_port:int, chain_id:int):
        self.__eth_server_url = eth_server_url
        self.__eth_server_http_port = eth_server_http_port
        self.__eth_server_ws_port = eth_server_ws_port
        self.__chain_id = chain_id
        return self

    def _setEthInitAndInfoServerInfo(self, init_server_url:str, init_server_port:int):
        self.__init_server_url = init_server_url
        self.__init_server_port = init_server_port
        return self

    def _setFaucetServerInfo(self, faucet_server_url:str, faucet_server_port:int):
        self.__faucet_server_url = faucet_server_url
        self.__faucet_server_port = faucet_server_port
        return self


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
        self.__setConfigurationFiles(node)
        self.__chainlinkStartCommands(node)
        node.setFile('/chainlink/send_fund_request.sh', ChainlinkFileTemplate['send_get_eth_request'].format(faucet_server_url=self.__faucet_server_url, faucet_server_port=self.__faucet_server_port, rpc_url=self.__eth_server_url, rpc_port=self.__eth_server_http_port))
        node.appendStartCommand('bash /chainlink/send_fund_request.sh')
        node.setFile('/chainlink/check_init_node.sh', ChainlinkFileTemplate['check_init_node'].format(init_node_url=self.__init_server_url,
                                                                                                   init_node_port=self.__init_server_port,
                                                                                                   contract_name =LinkTokenDeploymentTemplate['link_token_name']))
        node.appendStartCommand('bash /chainlink/check_init_node.sh')
        self.__deploy_oracle_contract(node)
        node.setFile('/chainlink/send_flask_request.sh', ChainlinkFileTemplate['send_flask_request'].format(init_node_url=self.__init_server_url,
                                                                                                         init_node_port=self.__init_server_port,
                                                                                                         contract_name=self.__name))
        node.appendStartCommand('bash /chainlink/send_flask_request.sh')
        node.setFile('/chainlink/create_chainlink_jobs.sh', ChainlinkFileTemplate['create_jobs'])
        node.appendStartCommand('bash /chainlink/create_chainlink_jobs.sh')
        node.appendStartCommand('tail -f /chainlink/chainlink_logs.txt')

    def __installSoftware(self, node:Node):
        """
        @brief Install the software.
        """
        software_list = ['ipcalc', 'jq', 'iproute2', 'sed', 'postgresql', 'postgresql-contrib', 'curl', 'python3', 'python3-pip']
        for software in software_list:
            node.addSoftware(software)
        node.addBuildCommand('pip3 install web3==5.31.1')

    def __setConfigurationFiles(self, node:Node):
        """
        @brief Set configuration files.
        """
        config_content = ChainlinkFileTemplate['config'].format(rpc_url=self.__eth_server_url, chain_id=self.__chain_id, rpc_ws_port=self.__eth_server_ws_port, rpc_port=self.__eth_server_http_port)
        node.setFile('/chainlink/config.toml', config_content)
        node.setFile('/chainlink/db_secrets.toml', ChainlinkFileTemplate['secrets'])
        node.setFile('/chainlink/password.txt', ChainlinkFileTemplate['api'].format(username=self.__username, password=self.__password))
        node.setFile('/chainlink/jobs/getUint256.toml', ChainlinkJobsTemplate['getUint256'])
        node.setFile('/chainlink/jobs/getBool.toml', ChainlinkJobsTemplate['getBool'])

    def __chainlinkStartCommands(self, node:Node):
        """
        @brief Add start commands.
        """
        start_commands = """
service postgresql restart
su - postgres -c "psql -c \\"ALTER USER postgres WITH PASSWORD 'mysecretpassword';\\""
nohup chainlink node -config /chainlink/config.toml -secrets /chainlink/db_secrets.toml start -api /chainlink/password.txt > /chainlink/chainlink_logs.txt 2>&1 &
"""
        node.appendStartCommand(start_commands)

    def __deploy_oracle_contract(self, node:Node):
        """
        @brief Deploy the oracle contract.
        """
        node.setFile('/contracts/deploy_oracle_contract.py', OracleContractDeploymentTemplate['oracle_contract_deploy'].format(rpc_url = self.__eth_server_url,
                                                                                                                                      rpc_port = self.__eth_server_http_port,
                                                                                                                                      init_node_url=self.__init_server_url,
                                                                                                                                      init_node_port=self.__init_server_port,
                                                                                                                                      contract_name = LinkTokenDeploymentTemplate['link_token_name'],
                                                                                                                                      chain_id=self.__chain_id, faucet_url=self.__faucet_server_url, faucet_port=self.__faucet_server_port))
        node.setFile('/contracts/oracle_contract.abi', OracleContractDeploymentTemplate['oracle_contract_abi'])
        node.setFile('/contracts/oracle_contract.bin', OracleContractDeploymentTemplate['oracle_contract_bin'])
        node.appendStartCommand(f'python3 ./contracts/deploy_oracle_contract.py')

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
    __faucet_url:str
    __faucet_port: int
    __eth_init_info_server_vnode_name:str
    __eth_init_info_server_url:str
    __eth_init_info_server_port:int
    __eth_server_vnode_name:str
    __eth_server_url:str
    __eth_server_http_port:int
    __eth_server_ws_port:int
    __chain_id:int

    def __init__(self):
        """
        @brief ChainlinkService constructor.
        """
        super().__init__()
        self.addDependency('EthereumService', False, False)

    def _createServer(self) -> ChainlinkServer:
        self._log('Creating Chainlink server.')
        return ChainlinkServer()

    def __getIPbyEthNodeName(self, emulator:Emulator, vnode:str):
        """
        @brief Get the IP address of the ethereum node.

        @param vnode The name of the ethereum node
        """
        node = emulator.getBindingFor(vnode)
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
        @brief configure the node. Some services may need to by configure before
        rendered.

        This is currently used by the DNS layer to configure NS and gules
        records before the actual installation.

        @param node node
        @param server server
        """
        server:ChainlinkServer = server
        server._setEthServerInfo(eth_server_url=self.__eth_server_url,
                                eth_server_http_port=self.__eth_server_http_port,
                                eth_server_ws_port=self.__eth_server_ws_port,
                                chain_id=self.__chain_id)

        server._setEthInitAndInfoServerInfo(init_server_url=self.__eth_init_info_server_url,
                                           init_server_port=self.__eth_init_info_server_port)

        server._setFaucetServerInfo(faucet_server_url=self.__faucet_url,
                                   faucet_server_port=self.__faucet_port)

        return


    def configure(self, emulator: Emulator):
        for vnode, server in self._pending_targets.items():
            server.setName(vnode)
        print(self.__faucet_vnode_name)
        self.__faucet_url = self.__getIPbyEthNodeName(emulator, self.__faucet_vnode_name)
        print(self.__faucet_url, self.__faucet_vnode_name)
        self.__eth_server_url = self.__getIPbyEthNodeName(emulator, self.__eth_server_vnode_name)
        print(self.__eth_server_vnode_name, self.__eth_server_url)
        self.__eth_init_info_server_url = self.__getIPbyEthNodeName(emulator, self.__eth_init_info_server_vnode_name)

        self.__faucet_port = emulator.getServerByVirtualNodeName(self.__faucet_vnode_name).getPort()
        eth_server:EthereumServer = emulator.getServerByVirtualNodeName(self.__eth_server_vnode_name)
        self.__eth_server_http_port = eth_server.getGethHttpPort()
        self.__eth_server_ws_port= eth_server.getGethWsPort()
        self.__chain_id = eth_server.getChainId()
        self.__eth_init_info_server_port = emulator.getServerByVirtualNodeName(self.__eth_init_info_server_vnode_name).getPort()

        super().configure(emulator)

    def setEthServer(self, vnode:str):
        self.__eth_server_vnode_name = vnode
        return self

    def setFaucetServer(self, vnode: str):
        self.__faucet_vnode_name = vnode
        return self

    def setEthInitInfoServer(self, vnode:str):
        self.__eth_init_info_server_vnode_name = vnode
        return self

    def getName(self) -> str:
        return 'ChainlinkService'

    def print(self, indent: int) -> str:
        out = ' ' * indent
        out += 'ChainlinkServiceLayer\n'
        return out
