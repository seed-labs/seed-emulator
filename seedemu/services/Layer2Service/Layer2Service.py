from __future__ import annotations
from typing import Dict, List
from sys import stderr

from seedemu.core import Node, Service, Server, Emulator, BaseSystem
from seedemu.core.enums import NetworkType

from .Layer2Template import Layer2Template, L2Account, L2Config, L2Node, WEB_SERVER_PORT


def getIPByNode(node: Node) -> str:
    address: str = None
    ifaces = node.getInterfaces()
    assert len(ifaces) > 0, "Node {} has no IP address.".format(node.getName())
    for iface in ifaces:
        net = iface.getNet()
        if net.getType() == NetworkType.Local:
            address = iface.getAddress()
            break
    return address


# TODO: Add child classes for sequencer and deployer
class Layer2Server(Server):

    __id: int
    __l2Blockchain: Layer2Blockchain
    __rpcPort: int
    __wsPort: int
    __isSequencer: bool
    __isDeployer: bool

    def __init__(self, id: int, l2Blockchain: Layer2Blockchain, type: L2Node):
        """!
        @brief create a new class Layer2Server.
        """
        super().__init__()

        self._id = id
        self.__isSequencer = False
        self.__isDeployer = False
        self.__l2Blockchain = l2Blockchain
        self._base_system = BaseSystem.SC_DEPLOYER if type == L2Node.DEPLOYER else BaseSystem.LAYER2
        self.__rpcPort = 8545
        self.__wsPort = 8546

        if type == L2Node.SEQUENCER:
            self.setSequencer(True)
        elif type == L2Node.DEPLOYER:
            self.setDeployer(True)

    def getID(self) -> int:
        return self._id

    def setSequencer(self, isSequencer: bool) -> Layer2Server:
        assert not (
            self.__isDeployer and isSequencer
        ), "Layer2Server::setSequencer(): cannot be both sequencer and deployer"
        self.__isSequencer = isSequencer
        return self

    def setDeployer(self, isDeployer: bool) -> Layer2Server:
        assert not (
            self.__isSequencer and isDeployer
        ), "Layer2Server::setDeployer(): cannot be both sequencer and deployer"
        self.__isDeployer = isDeployer
        return self
    
    # TODO: Add setL1Node
    def setL1Node(self, vnode: str, port: int) -> Layer2Server:
        pass

    def setRPCPort(self, port: int) -> Layer2Server:
        self.__rpcPort = port
        return self

    def setWSPort(self, port: int) -> Layer2Server:
        self.__wsPort = port
        return self

    def getRPCPort(self) -> int:
        return self.__rpcPort

    def getWSPort(self) -> int:
        return self.__wsPort

    def getL2Blockchain(self) -> Layer2Blockchain:
        return self.__l2Blockchain

    def isSequencer(self) -> bool:
        return self.__isSequencer

    def isDeployer(self) -> bool:
        return self.__isDeployer

    def install(self, node: Node):
        """!
        @brief add commands for installing layer2 to nodes.

        @param node node.
        """
        if self.isDeployer():
            self.__installDeployer(node)
        else:
            self.__install(node)

        # Add universal commands
        node.addBuildCommand("sed -i 's/net0/eth0/g' /start.sh")
        node.appendStartCommand(
            f"./luancher.sh &> out.log",
            fork=True,
        )

    def __addScript(self, node: Node, scriptPath: str, script: str):
        node.setFile(scriptPath, script)
        node.addBuildCommand(f"chmod +x {scriptPath}")

    def __installDeployer(self, node: Node):
        template = Layer2Template(self.isSequencer())

        node.setFile("/l2/.env", self.__getEnvs(template))
        self.__addScript(node, "/l2/luancher.sh", template.SC_DEPLOYER)
        node.appendStartCommand("cd /l2")

    def __install(self, node: Node):
        template = Layer2Template(self.isSequencer())

        # Set the environment variables
        node.setFile("/.env", self.__getEnvs(template))

        # Add the luanchers
        node.setFile("/luancher.sh", template.getNodeLauncher())
        node.addBuildCommand("chmod +x /luancher.sh")
        [
            self.__addScript(
                node, f"/start_{component.value}.sh", template.getSubLauncher(component)
            )
            for component in template.getComponents()
        ]

    def __getIPByVNode(self, vnode: str):
        """
        @brief Get the IP address of the ethereum node.

        @param vnode The name of the ethereum node
        """
        node = self.__l2Blockchain.getLayer2Service().getEmulator().getBindingFor(vnode)
        return getIPByNode(node)

    def __getL1RPC(self):
        l1VNode: str
        l1Port: int
        l1VNode, l1Port = self.__l2Blockchain.getL1VNode()
        assert (
            l1VNode is not None and l1Port is not None
        ), "Layer2Server::install(): L1 node is not set"

        l1NodeIP = self.__getIPByVNode(l1VNode)
        assert l1NodeIP is not None, "Layer2Server::install(): L1 node IP is None"

        return f"http://{l1NodeIP}:{l1Port}"

    # TODO: Move this to Layer2Blockchain
    def __getEnvs(self, template: Layer2Template):

        l1RPC = self.__getL1RPC()

        assert (
            self.__l2Blockchain.getSequencerAddress() is not None
        ), "Layer2Server::install(): sequencer address is not set"

        template.setEnv(
            {
                L2Config.L1_RPC_URL.value: l1RPC,
                L2Config.L1_RPC_KIND.value: "basic",
                L2Config.SEQ_RPC.value: self.__l2Blockchain.getSequencerAddress(),
                L2Config.DEPLOYMENT_CONTEXT.value: "getting-started",
                L2Config.DEPLOYER_URL.value: self.__l2Blockchain.getDeployerAddress(),
            }
        )

        [
            template.setAccountEnv(accType, acc, sk)
            for accType in L2Account
            for acc, sk in self.__l2Blockchain.getAdminAccount(accType).items()
        ]

        return template.exportEnvFile()


class Layer2Blockchain:

    __chainID: int
    __pendingTargets: List[str]
    __chainName: str
    __sequencerAddress: str
    __deployerAddress: str
    __nonSequencerAddresses: List[str]
    __adminAccounts: Dict[L2Account, Dict[str, str]]
    __l1VNode: Node
    __l1Port: int

    def __init__(self, service: Layer2Service, chainName: str, chainID: int):
        self.__layer2Service = service
        self.__chainName = chainName
        self.__chainID = chainID
        self.__pendingTargets = []
        self.__sequencerAddress = None
        self.__deployerAddress = None
        self.__nonSequencerAddresses = []
        self.__adminAccounts = {}
        self.__l1VNode = None
        self.__l1Port = None

    def _log(self, msg: str):
        print("==== Layer2Blockchain: {}".format(msg), file=stderr)

    # TODO: Select node type at creation
    def createNode(self, vnode: str, type: L2Node = L2Node.NON_SEQUENCER) -> Layer2Server:
        self.__pendingTargets.append(vnode)
        return self.__layer2Service.installByL2Blockchain(vnode, self, type)

    def setAdminAccount(
        self, type: L2Account, acc: tuple[str, str]
    ) -> Layer2Blockchain:

        # TODO: check if the account is valid
        self.__adminAccounts[type] = {acc[0]: acc[1]}
        return self

    def getAdminAccount(self, type: L2Account) -> Dict[str, str]:
        return self.__adminAccounts[type]

    def getChainID(self) -> int:
        return self.__chainID

    def getChainName(self) -> str:
        return self.__chainName

    def getSequencerAddress(self) -> str:
        return self.__sequencerAddress

    def getDeployerAddress(self) -> str:
        return self.__deployerAddress

    def getLayer2Service(self) -> Layer2Service:
        return self.__layer2Service

    def _doConfigure(self, node: Node, server: Layer2Server):
        self._log(
            "configuring as{}/{} as an l2 node...".format(node.getAsn(), node.getName())
        )

        if server.isSequencer() and self.__sequencerAddress is None:
            self.__sequencerAddress = "http://{}:{}".format(
                getIPByNode(node), server.getRPCPort()
            )
        elif server.isDeployer() and self.__deployerAddress is None:
            self.__deployerAddress = "http://{}:{}".format(
                getIPByNode(node), WEB_SERVER_PORT
            )

    def setL1Node(self, vnode: str, port: int):
        self.__l1VNode = vnode
        self.__l1Port = port

    def getL1VNode(self) -> Node:
        return self.__l1VNode, self.__l1Port


class Layer2Service(Service):
    """
    @brief Layer2Service class.
    """

    __blockchains: Dict[str, Layer2Blockchain]
    __blockchain_id: int
    __serial: int
    __emulator: Emulator

    def __init__(self):
        """!
        @brief create a new class Layer2Service.
        """
        super().__init__()

        self.__serial = 0
        self.__blockchains = {}
        self.__blockchain_id = 42069
        self.__emulator = None
        self.addDependency("Base", False, False)

    def getName(self) -> str:
        return "Layer2Service"

    def getEmulator(self) -> Emulator:
        return self.__emulator

    def installByL2Blockchain(
        self, vnode: str, l2Blockchain: Layer2Blockchain, type: L2Node
    ) -> Layer2Server:
        """!
        @brief Install the service on a node identified by given name.
        """
        if vnode not in self._pending_targets.keys():
            self._pending_targets[vnode] = self._createServer(l2Blockchain, type)

        return self._pending_targets[vnode]

    def createL2Blockchain(self, chainName: str, chainID: int = -1) -> Layer2Blockchain:
        """!
        @brief create a layer2 rollup blockchain.
        """
        if chainID < 0:
            chainID = self.__blockchain_id
            self.__blockchain_id += 1

        self.__blockchains[chainName] = Layer2Blockchain(self, chainName, chainID)
        return self.__blockchains[chainName]

    def _doConfigure(self, node: Node, server: Layer2Server):
        server.getL2Blockchain()._doConfigure(node, server)

    def configure(self, emulator: Emulator):
        self.__emulator = emulator
        super().configure(emulator)

    def _doInstall(self, node: Node, server: Layer2Server):
        self._log("installing l2 on as{}/{}...".format(node.getAsn(), node.getName()))
        server.install(node)

    def _createServer(self, l2Blockchain: Layer2Blockchain, type: L2Node) -> Server:
        self.__serial += 1
        return Layer2Server(self.__serial, l2Blockchain, type)
