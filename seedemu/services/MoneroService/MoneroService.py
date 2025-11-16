from __future__ import annotations

import os
from typing import Dict, Iterator, List, Optional, Tuple

from seedemu.core.Emulator import Emulator
from seedemu.core.Node import Node
from seedemu.core.Service import Server, Service
from seedemu.core.enums import NetworkType
from seedemu.core.BaseSystem import BaseSystem

from .MoneroEnum import (
    MoneroBinarySource,
    MoneroMiningTrigger,
    MoneroNetworkType,
    MoneroNodeKind,
    MoneroNodeRole,
    MoneroSeedConnectionMode,
)
from .MoneroServer import MoneroBaseServer, MoneroFullNodeServer, MoneroLightNodeServer
from .MoneroUtil import (
    MoneroNetworkDefaults,
    MoneroNodeOptions,
    MoneroWalletSpec,
    build_endpoint,
    infer_default_ports,
)


class MoneroService(Service):
    """Entry point for the Monero blockchain service.

    Similar to ``EthereumService``, the ``MoneroService`` keeps track of the
    mapping between virtual nodes and Monero blockchains, and during the render
    phase invokes each server's ``install()`` method to provision the software.
    Blockchain- and node-specific logic is delegated to :class:`MoneroNetwork`
    to keep the semantics clean.
    """

    def __init__(self):
        super().__init__()
        self.__serial = 0
        self.__networks: Dict[str, MoneroNetwork] = {}

    
    # Service interface
    
    def getName(self) -> str:
        return "MoneroService"

    def _createServer(self) -> Server:
        raise AssertionError("Install Monero nodes via MoneroNetwork.createNode() instead")

    def configure(self, emulator: Emulator):
        """Inject binding information and let ``MoneroNetwork`` derive connectivity.

        Args:
            emulator: Active :class:`seedemu.core.Emulator` instance orchestrating
                the deployment.
        """

        super().configure(emulator)
        for network in self.__networks.values():
            network.configure(emulator)

    def _doInstall(self, node: Node, server: Server):
        """Hook invoked during installation to emit debugging logs.

        Args:
            node: Physical node to deploy onto.
            server: Service-specific server instance responsible for rendering.
        """

        if isinstance(server, MoneroBaseServer):
            if server.getBinarySource() == MoneroBinarySource.MIRROR:
                node.setBaseSystem(BaseSystem.SEEDEMU_MONERO)

        self.log(f"install {server.__class__.__name__} on as{node.getAsn()}/{node.getName()}")

        super()._doInstall(node, server)

    
    # Blockchain management
    
    def createBlockchain(
        self,
        name: str,
        net_type: MoneroNetworkType = MoneroNetworkType.TESTNET,
        defaults: Optional[MoneroNetworkDefaults] = None,
    ) -> "MoneroNetwork":
        """Create and register a logical Monero blockchain.

        This aligns with EthereumService.createBlockchain().

        Args:
            name: Unique blockchain identifier.
            net_type: Blockchain type which influences default ports and flags.
            defaults: Optional defaults to clone instead of inferring automatically.

        Returns:
            The newly created :class:`MoneroNetwork` instance.
        """
        assert name not in self.__networks, f"Duplicated Monero blockchain name: {name}"

        defaults = defaults.clone() if defaults else infer_default_ports(net_type)
        defaults.net_type = net_type

        network = MoneroNetwork(self, name, defaults)
        self.__networks[name] = network
        return network

    def getBlockchainNames(self) -> List[str]:
        """Return the names of registered blockchains."""
        return list(self.__networks.keys())

    def getBlockchain(self, name: str) -> "MoneroNetwork":
        """Return the blockchain object with the given name."""
        return self.__networks[name]

    
    # Internal helpers
    
    def _register_node(
        self, vnode: str, network: "MoneroNetwork", options: MoneroNodeOptions
    ) -> MoneroBaseServer:
        """Register a virtual node with the service and return its server instance.

        Args:
            vnode: Virtual node identifier within the emulator.
            network: Monero network the node belongs to.
            options: Node options that control runtime behaviour.

        Returns:
            The :class:`MoneroBaseServer` responsible for rendering the node.
        """
        if vnode in self._pending_targets:
            return self._pending_targets[vnode]  # Allow idempotent calls

        self.__serial += 1

        if options.kind == MoneroNodeKind.LIGHT:
            server: MoneroBaseServer = MoneroLightNodeServer(self.__serial, network, options)
        else:
            server = MoneroFullNodeServer(self.__serial, network, options)

        self._pending_targets[vnode] = server
        return server

    def log(self, message: str):
        print(f"[MoneroService] {message}")


class MoneroNetwork:
    """Representation of a private Monero network (testnet or emulated mainnet).

    The network keeps default configuration, port allocators, and node instances,
    and during ``configure`` fills in runtime information such as IP addresses
    and ports.
    """

    def __init__(self, service: MoneroService, name: str, defaults: MoneroNetworkDefaults):
        self._service = service
        self._name = name
        self._defaults = defaults
        self._nodes: Dict[str, MoneroBaseServer] = {}
        self._default_mining_address: Optional[str] = None
        self._p2p_counter = defaults.default_p2p_port
        self._rpc_counter = defaults.default_rpc_port
        self._zmq_counter = defaults.default_zmq_port
        self._wallet_rpc_counter = defaults.light_wallet_rpc_start

        # Track allocated ports to avoid accidental reuse. Key is (port, purpose).
        self._allocated_ports: Dict[Tuple[int, str], str] = {}

    
    # Public API
    
    def getName(self) -> str:
        return self._name

    def setDefaultMiningAddress(self, address: str) -> "MoneroNetwork":
        self._default_mining_address = address
        return self

    def setFixedDifficulty(self, difficulty: int) -> "MoneroNetwork":
        self._defaults.fixed_difficulty = difficulty
        return self

    def setSeedConnectionMode(self, mode: MoneroSeedConnectionMode) -> "MoneroNetwork":
        self._defaults.seed_connection_mode = mode
        return self

    def setDefaultWalletTemplate(self, spec: MoneroWalletSpec) -> "MoneroNetwork":
        self._defaults.wallet = spec.clone()
        return self

    def createNode(
        self,
        vnode: str,
        *,
        kind: MoneroNodeKind = MoneroNodeKind.FULL,
        role: Optional[MoneroNodeRole] = None,
        enable_mining: Optional[bool] = None,
        mining_threads: Optional[int] = None,
        mining_address: Optional[str] = None,
        wallet: Optional[MoneroWalletSpec] = None,
        binary_source: Optional[MoneroBinarySource] = None,
        mining_trigger: Optional[MoneroMiningTrigger] = None,
        connect_mode: Optional[MoneroSeedConnectionMode] = None,
        options: Optional[MoneroNodeOptions] = None,
    ) -> MoneroBaseServer:
        """Create a Monero node inside this network.

        Args:
            vnode: Virtual node name used during binding.
            kind: Node kind (full/pruned/light).
            role: Optional default role for the node.
            enable_mining: Explicit mining toggle.
            mining_threads: Number of CPU threads for mining.
            mining_address: Explicit mining address to use.
            wallet: Wallet template override.
            binary_source: Source of Monero binaries (mirror/custom).
            mining_trigger: Mining trigger strategy override.
            connect_mode: Seed connection mode override.
            options: Optional pre-configured :class:`MoneroNodeOptions`.

        Returns:
            The server abstraction for the newly created node.
        """
        opts = options.clone() if options else MoneroNodeOptions()

        opts.kind = kind
        opts.role = role or (MoneroNodeRole.STANDALONE if kind == MoneroNodeKind.LIGHT else MoneroNodeRole.CLIENT)
        opts.name = opts.name or vnode

        # Inherit network-level boolean defaults when ``options`` is None
        if options is None:
            opts.persist_data = self._defaults.persist_data
            opts.binary_source = self._defaults.binary_source
            opts.mining_trigger = self._defaults.mining_trigger
            opts.connect_mode = self._defaults.seed_connection_mode

        if enable_mining is not None:
            opts.enable_mining = enable_mining
        if mining_threads is not None:
            opts.mining_threads = mining_threads
        if mining_address is not None:
            opts.mining_address = mining_address

        # Handle wallet configuration while avoiding shared references
        if wallet is not None:
            opts.wallet = wallet.clone()
        elif options is None:
            opts.wallet = self._defaults.wallet.clone()
        else:
            if opts.wallet is not None:
                opts.wallet = opts.wallet.clone()
            else:
                opts.wallet = self._defaults.wallet.clone()

        if binary_source is not None:
            opts.binary_source = binary_source
        if mining_trigger is not None:
            opts.mining_trigger = mining_trigger
        if connect_mode is not None:
            opts.connect_mode = connect_mode

        if opts.kind == MoneroNodeKind.PRUNED:
            if opts.role == MoneroNodeRole.SEED:
                raise AssertionError(
                    "Pruned nodes cannot act as seed nodes; use MoneroNodeKind.FULL instead."
                )
            if opts.enable_mining:
                self.log(
                    f"[{self._name}] Node {vnode} runs in pruned mode; mining has been disabled automatically."
                )
                opts.enable_mining = False

        self._apply_defaults(vnode, opts)

        server = self._service._register_node(vnode, self, opts)
        self._nodes[vnode] = server
        return server

    def createSeedNode(
        self,
        vnode: str,
        *,
        enable_mining: bool = False,
        mining_threads: Optional[int] = None,
        mining_address: Optional[str] = None,
        wallet: Optional[MoneroWalletSpec] = None,
        binary_source: Optional[MoneroBinarySource] = None,
        mining_trigger: Optional[MoneroMiningTrigger] = None,
        connect_mode: MoneroSeedConnectionMode = MoneroSeedConnectionMode.EXCLUSIVE,
        options: Optional[MoneroNodeOptions] = None,
    ) -> MoneroBaseServer:
        """Create a full node with seed role and optional mining."""

        server = self.createNode(
            vnode,
            kind=MoneroNodeKind.FULL,
            role=MoneroNodeRole.SEED,
            wallet=wallet,
            binary_source=binary_source,
            mining_trigger=mining_trigger,
            connect_mode=connect_mode,
            options=options,
        )

        server.setSeedRole()

        if enable_mining:
            server.enableMining(
                threads=mining_threads,
                address=mining_address,
                trigger=mining_trigger,
            )
        else:
            server.disableMining()

        return server

    def createClientNode(
        self,
        vnode: str,
        *,
        enable_mining: bool = False,
        mining_threads: Optional[int] = None,
        mining_address: Optional[str] = None,
        wallet: Optional[MoneroWalletSpec] = None,
        binary_source: Optional[MoneroBinarySource] = None,
        mining_trigger: Optional[MoneroMiningTrigger] = None,
        connect_mode: MoneroSeedConnectionMode = MoneroSeedConnectionMode.EXCLUSIVE,
        options: Optional[MoneroNodeOptions] = None,
    ) -> MoneroBaseServer:
        """Create a full node with client role and optional mining."""

        server = self.createNode(
            vnode,
            kind=MoneroNodeKind.FULL,
            role=MoneroNodeRole.CLIENT,
            wallet=wallet,
            binary_source=binary_source,
            mining_trigger=mining_trigger,
            connect_mode=connect_mode,
            options=options,
        )

        server.setClientRole()

        if enable_mining:
            server.enableMining(
                threads=mining_threads,
                address=mining_address,
                trigger=mining_trigger,
            )
        else:
            server.disableMining()

        return server

    def createPrunedNode(
        self,
        vnode: str,
        *,
        wallet: Optional[MoneroWalletSpec] = None,
        binary_source: Optional[MoneroBinarySource] = None,
        connect_mode: MoneroSeedConnectionMode = MoneroSeedConnectionMode.EXCLUSIVE,
        options: Optional[MoneroNodeOptions] = None,
    ) -> MoneroBaseServer:
        """Create a pruned node; wallet stays enabled while mining is disabled."""

        if options and options.enable_mining:
            raise AssertionError("Pruned nodes do not support mining; disable options.enable_mining.")

        server = self.createNode(
            vnode,
            kind=MoneroNodeKind.PRUNED,
            role=MoneroNodeRole.CLIENT,
            enable_mining=False,
            wallet=wallet,
            binary_source=binary_source,
            connect_mode=connect_mode,
            options=options,
        )

        server.setClientRole().disableMining()

        return server

    def createLightWallet(
        self,
        vnode: str,
        *,
        wallet: Optional[MoneroWalletSpec] = None,
        options: Optional[MoneroNodeOptions] = None,
    ) -> MoneroBaseServer:
        """Create a light wallet node and register it with the network.

        Args:
            vnode: Virtual node identifier.
            wallet: Wallet specification template.
            options: Optional preconfigured node options.

        Returns:
            The ``MoneroBaseServer`` representing the light wallet node.
        """
        return self.createNode(vnode, kind=MoneroNodeKind.LIGHT, wallet=wallet, options=options)

    def configure(self, emulator: Emulator):
        """Populate runtime metadata (binding info, seed lists, RPC endpoints)."""
        if not self._nodes:
            return

        binding_lookup: Dict[str, Tuple[Node, str]] = {}
        seed_endpoints: List[Tuple[str, str]] = []
        fullnode_rpc: List[str] = []

        for vnode, server in self._nodes.items():
            node = emulator.getBindingFor(vnode)
            ip = self._get_primary_ip(node)
            server.set_binding(node, ip)
            binding_lookup[vnode] = (node, ip)

            if server.is_seed():
                endpoint = build_endpoint(ip, server.get_p2p_port())
                seed_endpoints.append((vnode, endpoint))

            if server.is_full_node() and server.get_rpc_port() is not None:
                fullnode_rpc.append(build_endpoint(ip, server.get_rpc_port()))

        for vnode, server in self._nodes.items():
            server.set_binding_lookup(binding_lookup)
            if server.is_seed():
                # Interconnect seed nodes while excluding the current node
                other_seeds = [endpoint for peer, endpoint in seed_endpoints if peer != vnode]
            else:
                other_seeds = [endpoint for _, endpoint in seed_endpoints]
            server.set_seed_endpoints(other_seeds)
            server.set_fullnode_rpc_endpoints(fullnode_rpc)

    
    # Internal utilities
    
    def _apply_defaults(self, vnode: str, opts: MoneroNodeOptions):
        """Apply network-level defaults and auto-assign ports for a node.

        Args:
            vnode: Node identifier used for logging.
            opts: Options object to mutate in-place.
        """
        defaults = self._defaults

        if opts.data_dir == "/var/lib/monero":
            opts.data_dir = os.path.join("/var/lib/monero", f"{self._name}-{opts.name}")

        if opts.log_dir == "/var/log/monero":
            opts.log_dir = os.path.join("/var/log/monero", f"{self._name}-{opts.name}")

        if opts.p2p_bind_port is None:
            opts.p2p_bind_port = self._alloc_port("p2p")

        rpc_auto_assigned = False
        zmq_auto_assigned = False

        if opts.kind != MoneroNodeKind.LIGHT:
            if opts.rpc_bind_port is None:
                opts.rpc_bind_port = self._alloc_port("rpc")
                rpc_auto_assigned = True

            if opts.zmq_bind_port is None:
                opts.zmq_bind_port = self._alloc_port("zmq")
                zmq_auto_assigned = True

            if self._defaults.auto_assign_ports or rpc_auto_assigned:
                while opts.rpc_bind_port in {opts.p2p_bind_port, opts.zmq_bind_port}:
                    opts.rpc_bind_port = self._alloc_port("rpc")

            if self._defaults.auto_assign_ports or zmq_auto_assigned:
                while opts.zmq_bind_port in {opts.p2p_bind_port, opts.rpc_bind_port}:
                    opts.zmq_bind_port = self._alloc_port("zmq")

        if defaults.fixed_difficulty and not opts.fixed_difficulty:
            opts.fixed_difficulty = defaults.fixed_difficulty

        if opts.enable_mining and opts.mining_threads <= 0:
            opts.mining_threads = defaults.default_mining_threads

        # Seed nodes do not wait for themselves
        if opts.role == MoneroNodeRole.SEED and opts.wait_for_seed:
            opts.wait_for_seed = False

        # Enable wallet RPC by default on light nodes
        if opts.kind == MoneroNodeKind.LIGHT:
            opts.enable_wallet = True
            opts.wallet.enable_rpc = True

        # Wallet template
        wallet_template = opts.wallet.clone()

        if not wallet_template.wallet_path:
            wallet_template.wallet_path = os.path.join(opts.data_dir, "wallets", f"{opts.name}.wallet")
        if not wallet_template.primary_address_path:
            wallet_template.primary_address_path = os.path.join(opts.data_dir, "wallets", f"{opts.name}.address")

        if wallet_template.enable_rpc:
            default_wallet_port = self._defaults.wallet.rpc_bind_port
            wallet_auto_assigned = False
            if wallet_template.rpc_bind_port <= 0:
                wallet_template.rpc_bind_port = self._alloc_port("wallet_rpc")
                wallet_auto_assigned = True
            elif (
                self._defaults.auto_assign_ports
                and wallet_template.rpc_bind_port == default_wallet_port
                and wallet_template is not opts.wallet
            ):
                wallet_template.rpc_bind_port = self._alloc_port("wallet_rpc")
                wallet_auto_assigned = True

            if self._defaults.auto_assign_ports or wallet_auto_assigned:
                collisions = {port for port in [
                    opts.p2p_bind_port,
                    opts.rpc_bind_port,
                    opts.zmq_bind_port,
                ] if port is not None}
                while wallet_template.rpc_bind_port in collisions:
                    wallet_template.rpc_bind_port = self._alloc_port("wallet_rpc")

        opts.wallet = wallet_template

        # Record port assignments to help diagnose conflicts
        self._mark_port(opts.p2p_bind_port, "p2p", opts.name)
        if opts.rpc_bind_port is not None:
            self._mark_port(opts.rpc_bind_port, "rpc", opts.name)
        if opts.zmq_bind_port is not None:
            self._mark_port(opts.zmq_bind_port, "zmq", opts.name)
        if wallet_template.enable_rpc:
            self._mark_port(wallet_template.rpc_bind_port, "wallet-rpc", opts.name)

    def _alloc_port(self, category: str) -> int:
        """Allocate the next available port for the given ``category``.

        Categories include ``p2p``, ``rpc``, ``zmq``, and ``wallet_rpc``. A simple
        linear counter is used; more complex port planning can be achieved by
        explicitly setting values on :class:`MoneroNodeOptions`.
        """

        if not self._defaults.auto_assign_ports:
            return {
                "p2p": self._defaults.default_p2p_port,
                "rpc": self._defaults.default_rpc_port,
                "zmq": self._defaults.default_zmq_port,
                "wallet_rpc": self._defaults.light_wallet_rpc_start,
            }[category]

        if category == "p2p":
            port = self._p2p_counter
            self._p2p_counter += 1
            return port
        if category == "rpc":
            port = self._rpc_counter
            self._rpc_counter += 1
            return port
        if category == "zmq":
            port = self._zmq_counter
            self._zmq_counter += 1
            return port
        if category == "wallet_rpc":
            port = self._wallet_rpc_counter
            self._wallet_rpc_counter += 1
            return port
        raise AssertionError(f"Unknown port category: {category}")

    def _mark_port(self, port: Optional[int], purpose: str, vnode: str):
        """Track which node claimed a specific port purpose.

        Args:
            port: Port number that was allocated.
            purpose: Port type (p2p/rpc/zmq/wallet-rpc).
            vnode: Node identifier that owns the port.
        """
        if port is None:
            return
        key = (port, purpose)
        existing = self._allocated_ports.get(key)
        if existing and existing != vnode:
            self.log(f"WARNING: port {port} ({purpose}) is used by both {existing} and {vnode}")
        else:
            self._allocated_ports[key] = vnode

    def _get_primary_ip(self, node: Node) -> str:
        """Return the IP address on the local network used for service bindings."""
        for iface in node.getInterfaces():
            if iface.getNet().getType() == NetworkType.Local:
                return str(iface.getAddress())
        raise AssertionError(f"Node {node.getName()} has no local network interface")

    def get_network_flag(self) -> Optional[str]:
        net_type = self._defaults.net_type
        if net_type == MoneroNetworkType.TESTNET:
            return "--testnet"
        if net_type == MoneroNetworkType.STAGENET:
            return "--stagenet"
        if net_type == MoneroNetworkType.MAINNET:
            return None
        return None

    def get_default_mining_address(self) -> Optional[str]:
        return self._default_mining_address

    def log(self, message: str):
        self._service.log(f"[{self._name}] {message}")

    
    # Debug helpers
    
    def iterNodes(self) -> Iterator[MoneroBaseServer]:
        """Yield each registered node server."""
        return iter(self._nodes.values())

    def getSeeds(self) -> List[str]:
        """Return the names of all nodes acting as seeds."""
        return [name for name, server in self._nodes.items() if server.is_seed()]

    def getFullNodes(self) -> List[str]:
        """Return the names of all nodes that run full/pruned daemons."""
        return [name for name, server in self._nodes.items() if server.is_full_node()]



