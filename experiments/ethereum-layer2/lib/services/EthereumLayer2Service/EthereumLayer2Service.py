from __future__ import annotations
from typing import Dict, List
from sys import stderr

from seedemu.core import Node, Service, Server, Emulator, BaseSystem
from seedemu.core.enums import NetworkType

from .EthereumLayer2Template import EthereumLayer2Template, EthereumLayer2Account, EthereumLayer2Config, EthereumLayer2Node, WEB_SERVER_PORT


def getIPByNode(node: Node) -> str:
    """!
    @brief Utility func to get the IP address of the node.

    @param node The physical node.
    """
    address: str = None
    ifaces = node.getInterfaces()
    assert len(ifaces) > 0, "Node {} has no IP address.".format(node.getName())
    for iface in ifaces:
        net = iface.getNet()
        if net.getType() == NetworkType.Local:
            address = iface.getAddress()
            break
    return address


class EthereumLayer2Server(Server):
    """!
    @brief Layer2Server class.
    """

    __id: int
    __l2Blockchain: EthereumLayer2Blockchain
    __l1VNode: str
    __l1Port: int
    __httpPort: int
    __wsPort: int
    __isSequencer: bool
    __isDeployer: bool

    def __init__(self, id: int, l2Blockchain: EthereumLayer2Blockchain, type: EthereumLayer2Node):
        """!
        @brief create a new Layer2Server instance.
        @param id The id of the server.
        @param l2Blockchain The layer2 blockchain.
        @param type The type of the server. Support type: NON_SEQUENCER/SEQUENCER/DEPLOYER
        """
        super().__init__()

        self._id = id
        self.__l1VNode = None
        self.__l1Port = None
        self.__isSequencer = False
        self.__isDeployer = False
        self.__l2Blockchain = l2Blockchain
        self._base_system = (
            BaseSystem.SEEDEMU_SC_DEPLOYER if type == EthereumLayer2Node.DEPLOYER else BaseSystem.SEEDEMU_OP_STACK
        )
        self.__httpPort = 8545
        self.__wsPort = 8546

        if type == EthereumLayer2Node.SEQUENCER:
            self.__setSequencer(True)
        elif type == EthereumLayer2Node.DEPLOYER:
            self.__setDeployer(True)

    def getID(self) -> int:
        """!
        @brief Get the id of the server.

        @return The id of the server.
        """
        return self._id

    def __setSequencer(self, isSequencer: bool) -> EthereumLayer2Server:
        """!
        @brief Set the server as a sequencer.

        @param True to set the server as a sequencer, False otherwise.

        @return self, for chaining.
        """
        assert not (
            self.__isDeployer and isSequencer
        ), "Layer2Server::setSequencer(): cannot be both sequencer and deployer"
        self.__isSequencer = isSequencer
        return self

    def __setDeployer(self, isDeployer: bool) -> EthereumLayer2Server:
        """!
        @brief Set the server as a deployer.

        @param True to set the server as a deployer, False otherwise.

        @return self, for chaining.
        """
        assert not (
            self.__isSequencer and isDeployer
        ), "Layer2Server::setDeployer(): cannot be both sequencer and deployer"
        self.__isDeployer = isDeployer
        return self

    def setL1VNode(self, vnode: str, port: int) -> EthereumLayer2Server:
        """!
        @brief Set the Ethereum vnode and the geth http port the server should connect to.

        @param vnode The name of the vnode.
        @param port The Ethereum node geth http port.

        @return self, for chaining.
        """
        self.__l1VNode = vnode
        self.__l1Port = port

    def setHttpPort(self, port: int) -> EthereumLayer2Server:
        """!
        @brief Set the Layer2 geth http port of the server.

        @param port The Layer2 geth http port.

        @return self, for chaining.
        """
        self.__httpPort = port
        return self

    def setWSPort(self, port: int) -> EthereumLayer2Server:
        """!
        @brief Set the Layer2 geth ws port of the server.

        @param port The Layer2 geth ws port.

        @return self, for chaining.
        """
        self.__wsPort = port
        return self

    def getHttpPort(self) -> int:
        """!
        @brief Get the Layer2 geth http port of the server.

        @return The Layer2 geth http port.
        """
        return self.__httpPort

    def getWSPort(self) -> int:
        """!
        @brief Get the Layer2 geth ws port of the server.

        @return The Layer2 geth ws port.
        """
        return self.__wsPort

    def getL1VNode(self) -> tuple[str, int] | None:
        """!
        @brief Get the Ethereum vnode and the geth http port.

        @return The Ethereum vnode and the geth http port or None if not set.
        """
        if self.__l1VNode is None or self.__l1Port is None:
            return None
        return self.__l1VNode, self.__l1Port

    def getL2Blockchain(self) -> EthereumLayer2Blockchain:
        """!
        @brief Get the layer2 blockchain the server is connected to.

        @return The layer2 blockchain instance.
        """
        return self.__l2Blockchain

    def isSequencer(self) -> bool:
        """!
        @brief Check if the server is a sequencer.

        @return True if the server is a sequencer, False otherwise.
        """
        return self.__isSequencer

    def isDeployer(self) -> bool:
        """!
        @brief Check if the server is a deployer.

        @return True if the server is a deployer, False otherwise.
        """
        return self.__isDeployer

    def install(self, node: Node):
        """!
        @brief add commands for installing layer2 to nodes.

        @param node The physical node to install layer2.
        """
        if self.isDeployer():
            self.__installDeployer(node)
        else:
            self.__install(node)

        # Add universal commands
        # node.addBuildCommand("sed -i 's/net0/eth0/g' /start.sh")
        # node.insertStartCommand(0, "sed -i 's/net0/eth0/g' /ifinfo.txt")
        
        node.appendStartCommand(
            f"bash ./luancher.sh &> out.log",
            fork=True,
        )

    def __addScript(self, node: Node, scriptPath: str, script: str):
        """!
        @brief Import the script to the node.

        @param node The physical node to install layer2.
        @param scriptPath The container path to save the script.
        @param script The script content.
        """
        node.setFile(scriptPath, script)

    def __installDeployer(self, node: Node):
        """!
        @brief Build and setup the smart contract deployer.

        @param node The physical node.
        """
        template = EthereumLayer2Template(self.isSequencer())

        node.setFile("/l2/.env", self.__getEnvs(template))
        self.__addScript(node, "/l2/scripts/getting-started/config.sh", template.CHAIN_CONFIG)
        self.__addScript(node, "/l2/luancher.sh", template.SC_DEPLOYER)
        node.appendStartCommand("cd /l2")

    def __install(self, node: Node):
        """!
        @brief Build and setup the layer2 (sequencer/non-sequencer) server.

        @param node The physical node.
        """
        template = EthereumLayer2Template(self.isSequencer())

        # Set the environment variables
        node.setFile("/.env", self.__getEnvs(template))

        # Add the luanchers
        node.setFile("/luancher.sh", template.getNodeLauncher())
        [
            self.__addScript(
                node, f"/start_{component.value}.sh", template.getSubLauncher(component)
            )
            for component in template.getComponents()
        ]

    def __getIPByVNode(self, vnode: str) -> str:
        """
        @brief Get the node's IP address by vnode.

        @param vnode The name of the node.

        @return The IP address of the node.
        """
        node = self.__l2Blockchain.getLayer2Service().getEmulator().getBindingFor(vnode)
        return getIPByNode(node)

    def __getL1RPC(self) -> str:
        """!
        @breif Get the Ethereum RPC URL to connect.

        @return The Ethereum RPC URL.
        """
        l1VNode: str
        l1Port: int
        if self.getL1VNode() is not None:
            l1VNode, l1Port = self.getL1VNode()
        else:
            l1VNode, l1Port = self.__l2Blockchain.getL1VNode()
        assert (
            l1VNode is not None and l1Port is not None
        ), "Layer2Server::install(): L1 node is not set"

        l1NodeIP = self.__getIPByVNode(l1VNode)
        assert l1NodeIP is not None, "Layer2Server::install(): L1 node IP is None"

        return f"http://{l1NodeIP}:{l1Port}"

    def __getEnvs(self, template: EthereumLayer2Template) -> str:
        """!
        @brief Synthesize the environment variables.

        @param template The template to generate the environment variables.

        @return The environment variables.
        """

        l1RPC = self.__getL1RPC()

        assert (
            self.__l2Blockchain.getSequencerAddress() is not None
        ), "Layer2Server::install(): sequencer address is not set"

        template.setEnv(
            {
                EthereumLayer2Config.L1_RPC_URL.value: l1RPC,
                EthereumLayer2Config.L1_RPC_KIND.value: "basic",
                EthereumLayer2Config.L2_CHAIN_ID.value: self.__l2Blockchain.getChainID(),
                EthereumLayer2Config.GETH_HTTP_PORT.value: self.getHttpPort(),
                EthereumLayer2Config.GETH_WS_PORT.value: self.getWSPort(),
                EthereumLayer2Config.SEQ_RPC.value: self.__l2Blockchain.getSequencerAddress(),
                EthereumLayer2Config.DEPLOYMENT_CONTEXT.value: "getting-started",
                EthereumLayer2Config.DEPLOYER_URL.value: self.__l2Blockchain.getDeployerAddress(),
            }
        )

        [
            template.setAccountEnv(accType, acc, sk)
            for accType in EthereumLayer2Account
            for acc, sk in self.__l2Blockchain.getAdminAccount(accType).items()
        ]

        return template.exportEnvFile()


class EthereumLayer2Blockchain:
    """!
    @brief Layer2Blockchain class.
    Multiple Layer2Blockchain instances with different config can exist in
    the same emulator.
    """

    __chainID: int
    __pendingTargets: List[str]
    __chainName: str
    __sequencerAddress: str
    __sequencerCount: int
    __deployerAddress: str
    __deployerCount: int
    __adminAccounts: Dict[EthereumLayer2Account, Dict[str, str]]
    __l1VNode: str
    __l1Port: int

    def __init__(self, service: EthereumLayer2Service, chainName: str, chainID: int):
        self.__layer2Service = service
        self.__chainName = chainName
        self.__chainID = chainID
        self.__pendingTargets = []
        self.__sequencerAddress = None
        self.__sequencerCount = 0
        self.__deployerAddress = None
        self.__deployerCount = 0
        self.__adminAccounts = {}
        self.__l1VNode = None
        self.__l1Port = None

    def _log(self, msg: str):
        """!
        @brief Logging method.

        @param msg The message to log.
        """
        print("==== Layer2Blockchain: {}".format(msg), file=stderr)

    def createNode(
        self, vnode: str, type: EthereumLayer2Node = EthereumLayer2Node.NON_SEQUENCER
    ) -> EthereumLayer2Server:
        """!
        @brief Create a new layer2 node.

        @param vnode The name of the node.
        @param type(optional) default:NON_SEQUENCER The type of the node.

        @return The created layer2 server.
        """
        if type == EthereumLayer2Node.SEQUENCER:
            assert (
                self.__sequencerCount == 0
            ), "Layer2Blockchain::createNode(): sequencer node already exists"
            self.__sequencerCount += 1
        elif type == EthereumLayer2Node.DEPLOYER:
            assert (
                self.__deployerCount == 0
            ), "Layer2Blockchain::createNode(): deployer node already exists"
            self.__deployerCount += 1
        self.__pendingTargets.append(vnode)
        return self.__layer2Service.installByL2Blockchain(vnode, self, type)

    def setAdminAccount(
        self, type: EthereumLayer2Account, acc: tuple[str, str]
    ) -> EthereumLayer2Blockchain:
        """!
        @brief Set an admin account for the layer2 blockchain.

        @param type The type of the admin account.
        @param acc The admin account in the format of (address, private key).

        @return self, for chaining.
        """

        self.__adminAccounts[type] = {acc[0]: acc[1]}
        return self

    def getAdminAccount(self, type: EthereumLayer2Account) -> Dict[str, str]:
        """!
        @brief Get the admin account by account type.

        @param type The type of the admin account.

        @return The admin account in the format of {address: private key}.
        """
        return self.__adminAccounts[type]

    def getChainID(self) -> int:
        """!
        @brief Get the chain ID.

        @return The chain ID.
        """
        return self.__chainID

    def getChainName(self) -> str:
        """!
        @brief Get the chain name.

        @return The chain name.
        """
        return self.__chainName

    def getSequencerAddress(self) -> str:
        """!
        @brief Get the configured sequencer address.

        @return The sequencer address.
        """
        return self.__sequencerAddress

    def getDeployerAddress(self) -> str:
        """!
        @brief Get the configured deployer address.

        @return The deployer address.
        """
        return self.__deployerAddress

    def getLayer2Service(self) -> EthereumLayer2Service:
        """!
        @brief Get the layer2 service instance the blockchain belongs to.

        @return The layer2 service instance.
        """
        return self.__layer2Service

    def _doConfigure(self, node: Node, server: EthereumLayer2Server):
        """!
        @brief Retrieve the sequencer and deployer address from server.

        @param node The physical node.
        @param server The layer2 server.
        """
        self._log(
            "configuring as{}/{} as an l2 node...".format(node.getAsn(), node.getName())
        )

        if server.isSequencer() and self.__sequencerAddress is None:
            self.__sequencerAddress = "http://{}:{}".format(
                getIPByNode(node), server.getHttpPort()
            )
        elif server.isDeployer() and self.__deployerAddress is None:
            self.__deployerAddress = "http://{}:{}".format(
                getIPByNode(node), WEB_SERVER_PORT
            )

    def setL1VNode(self, vnode: str, port: int) -> EthereumLayer2Blockchain:
        """!
        @brief Set the Ethereum vnode and the geth http port for all the nodes
        in the layer2 blockchain.

        @param vnode The name of the vnode.
        @param port The Ethereum node geth http port.
        """
        self.__l1VNode = vnode
        self.__l1Port = port

        return self

    def getL1VNode(self) -> tuple[str, int]:
        """!
        @brief Get the configured Ethereum vnode and the geth http port.

        @return The Ethereum vnode and the geth http port.
        """
        return self.__l1VNode, self.__l1Port


class EthereumLayer2Service(Service):
    """
    @brief Layer2Service class.
    The Class enables user to create and manage layer2 blockchains in
    the emulator.
    """

    __blockchains: Dict[str, EthereumLayer2Blockchain]
    __blockchain_id: int
    __serial: int
    __emulator: Emulator

    def __init__(self):
        """!
        @brief create a new Layer2Service instance.
        """
        super().__init__()

        self.__serial = 0
        self.__blockchains = {}
        self.__blockchain_id = 42069
        self.__emulator = None
        self.addDependency("Base", False, False)

    def getName(self) -> str:
        """!
        @brief Get the name of the service.

        @return The name of the service.
        """
        return "Layer2Service"

    def getEmulator(self) -> Emulator:
        """!
        @brief Get the connected emulator instance.

        @return The emulator instance.
        """
        return self.__emulator

    def installByL2Blockchain(
        self, vnode: str, l2Blockchain: EthereumLayer2Blockchain, type: EthereumLayer2Node
    ) -> EthereumLayer2Server:
        """!
        @brief Install the service on a layer 2 server identified by given name.
        Used by the Layer2Blockchain class.

        @param vnode The name of the layer2 server.
        @param l2Blockchain The layer2 blockchain of the server.
        @param type The type of the layer2 server.

        @return The layer2 server.
        """
        if vnode not in self._pending_targets.keys():
            self._pending_targets[vnode] = self._createServer(l2Blockchain, type)

        return self._pending_targets[vnode]

    def createL2Blockchain(self, chainName: str, chainID: int = -1) -> EthereumLayer2Blockchain:
        """!
        @brief create a layer2 blockchain.

        @param chainName The name of the blockchain.
        @param chainID(optional) The ID of the blockchain.
        """
        if chainID < 0:
            chainID = self.__blockchain_id
            self.__blockchain_id += 1

        self.__blockchains[chainName] = EthereumLayer2Blockchain(self, chainName, chainID)
        return self.__blockchains[chainName]

    def _doConfigure(self, node: Node, server: EthereumLayer2Server):
        """!
        @brief Callback method to configure a layer2 server.

        @param node The physical node the server attached.
        @param server The layer2 server.
        """
        server.getL2Blockchain()._doConfigure(node, server)

    def configure(self, emulator: Emulator):
        """!
        @brief Callback method to configure the service.

        @param emulator The connected emulator instance.
        """
        self.__emulator = emulator
        super().configure(emulator)

    def _doInstall(self, node: Node, server: EthereumLayer2Server):
        """!
        @brief Callback method to install a layer2 server on a node.

        @param node The physical node.
        @param server The layer2 server.
        """
        self._log("installing l2 on as{}/{}...".format(node.getAsn(), node.getName()))
        server.install(node)

    def _createServer(self, l2Blockchain: EthereumLayer2Blockchain, type: EthereumLayer2Node) -> Server:
        """!
        @brief Create a new layer2 server with the given blockchain.

        @param l2Blockchain The layer2 blockchain.
        @param type The type of the server.

        @return The created layer2 server.
        """
        self.__serial += 1
        return EthereumLayer2Server(self.__serial, l2Blockchain, type)
