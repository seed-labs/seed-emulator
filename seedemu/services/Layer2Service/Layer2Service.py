from __future__ import annotations
from typing import Dict, List
from sys import stderr

from seedemu.core import Node, Service, Server, Emulator, BaseSystem
from seedemu.core.enums import NetworkType
from seedemu.compiler import DockerImage, Docker

L2_LABEL = "layer2.{key}"


class Layer2Server(Server):

    __id: int
    __l2Blockchain: Layer2Blockchain
    __rpcPort: int
    __wsPort: int
    __isSequencer: bool

    def __init__(self, id: int, l2Blockchain: Layer2Blockchain):
        """!
        @brief create a new class Layer2Server.
        """
        super().__init__()

        self.__isSequencer = False
        self.__l2Blockchain = l2Blockchain
        self._id = id
        self._base_system = BaseSystem.LAYER2
        self.__rpcPort = 8545
        self.__wsPort = 8546

    def getID(self) -> int:
        return self._id

    def setSequencer(self, isSequencer: bool) -> Layer2Server:
        self.__isSequencer = isSequencer
        return self

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

    def install(self, node: Node):
        """!
        @brief add commands for installing layer2 to nodes.

        @param node node.
        """

        l1VNode: str
        l1Port: int
        l1VNode, l1Port = self.__l2Blockchain.getL1VNode()
        assert (
            l1VNode is not None and l1Port is not None
        ), "Layer2Server::install(): L1 node is not set"

        l1NodeIP = self.__getIPByVNode(l1VNode)
        assert l1NodeIP is not None, "Layer2Server::install(): L1 node IP is None"

        l1RPC: str = f"http://{l1NodeIP}:{l1Port}"

        node.importFile(
            "/home/hua/courses/CIS700-AIS/seed-emulator/examples/layer2/l2/.env",
            "/.env",
        )
        if self.__isSequencer:
            for script in [
                "_op-batcher",
                "_op-geth",
                "_op-node",
                "_op-proposer",
                "_seq",
            ]:
                node.importFile(
                    f"/home/hua/courses/CIS700-AIS/seed-emulator/examples/layer2/l2/start{script}.sh",
                    f"/start{script}.sh",
                )
                node.addBuildCommand(f"chmod +x /start{script}.sh")
        else:
            for script in ["_op-geth_ns", "_op-node_ns", "_ns"]:
                node.importFile(
                    f"/home/hua/courses/CIS700-AIS/seed-emulator/examples/layer2/l2/start{script}.sh",
                    f"/start{script}.sh",
                )
                node.addBuildCommand(f"chmod +x /start{script}.sh")

        node.importFile(
            "/home/hua/courses/CIS700-AIS/seed-emulator/examples/layer2/l2/deployments/getting-started/L2OutputOracleProxy.json",
            "/L2OutputOracleProxy.json",
        )
        node.addBuildCommand("sed -i 's/net0/eth0/g' /start.sh")
        assert (
            self.__l2Blockchain.getSequencerAddress() is not None
        ), "Layer2Server::install(): sequencer address is not set"
        node.appendStartCommand(
            f"/start{'_seq' if self.__isSequencer else '_ns'}.sh {self.__l2Blockchain.getSequencerAddress()} {l1RPC} &> out.log",
            fork=True,
        )

    def __getIPByVNode(self, vnode: str):
        """
        @brief Get the IP address of the ethereum node.

        @param vnode The name of the ethereum node
        """
        node = self.__l2Blockchain.getLayer2Service().getEmulator().getBindingFor(vnode)
        address: str = None
        ifaces = node.getInterfaces()
        assert len(ifaces) > 0, "Node {} has no IP address.".format(node.getName())
        for iface in ifaces:
            net = iface.getNet()
            if net.getType() == NetworkType.Local:
                address = iface.getAddress()
                break
        return address


class Layer2Blockchain:

    __chainID: int
    __pendingTargets: List[str]
    __chainName: str
    __sequencerAddress: str
    __nonSequencerAddresses: List[str]
    __l1VNode: Node
    __l1Port: int

    def __init__(self, service: Layer2Service, chainName: str, chainID: int):
        self.__layer2Service = service
        self.__chainName = chainName
        self.__chainID = chainID
        self.__pendingTargets = []
        self.__sequencerAddress = None
        self.__nonSequencerAddresses = []
        self.__l1VNode = None
        self.__l1Port = None

    def _log(self, msg: str):
        print("==== Layer2Blockchain: {}".format(msg), file=stderr)

    def createNode(self, vnode: str) -> Layer2Server:
        self.__pendingTargets.append(vnode)
        return self.__layer2Service.installByL2Blockchain(vnode, self)

    def getChainID(self) -> int:
        return self.__chainID

    def getChainName(self) -> str:
        return self.__chainName

    def getSequencerAddress(self) -> str:
        return self.__sequencerAddress

    def getLayer2Service(self) -> Layer2Service:
        return self.__layer2Service

    def _doConfigure(self, node: Node, server: Layer2Server):
        self._log(
            "configuring as{}/{} as an l2 node...".format(node.getAsn(), node.getName())
        )

        if server.isSequencer() and self.__sequencerAddress is None:
            ifaces = node.getInterfaces()
            assert (
                len(ifaces) > 0
            ), "Layer2Service::_doConfigure(): node as{}/{} has not interfaces".format()
            self.__sequencerAddress = "http://{}:{}".format(
                str(ifaces[0].getAddress()), server.getRPCPort()
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
        self, vnode: str, l2Blockchain: Layer2Blockchain
    ) -> Layer2Server:
        """!
        @brief Install the service on a node identified by given name.
        """
        if vnode not in self._pending_targets.keys():
            self._pending_targets[vnode] = self._createServer(l2Blockchain)

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

    def _createServer(self, l2Blockchain: Layer2Blockchain) -> Server:
        self.__serial += 1
        return Layer2Server(self.__serial, l2Blockchain)
