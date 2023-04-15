from seedemu.core import ScopedRegistry, Node, Interface, Network, Emulator, Layer, Router, RealWorldRouter, BaseSystem
from typing import List, Dict
from ipaddress import IPv4Network

RoutingFileTemplates: Dict[str, str] = {}

RoutingFileTemplates["rs_bird"] = """\
router id {routerId};
protocol device {{
}}
"""

RoutingFileTemplates["rnode_bird_direct_interface"] = """
    interface "{interfaceName}";
"""

RoutingFileTemplates["rnode_bird"] = """\
router id {routerId};
ipv4 table t_direct;
protocol device {{
}}
protocol kernel {{
    ipv4 {{
        import all;
        export all;
    }};
    learn;
}}
"""

RoutingFileTemplates['rnode_bird_direct'] = """
    ipv4 {{
        table t_direct;
        import all;
    }};
{interfaces}
"""


class Routing(Layer):
    """!
    @brief The Routing layer.

    This layer provides routing support for routers and hosts. i.e., (1) install
    BIRD on router nodes and allow BGP/OSPF to work, (2) setup kernel and device
    protocols, and (3) setup default routes for host nodes.

    When this layer is rendered, two new methods will be added to the router
    node and can be used by other layers: (1) addProtocol: add new protocol
    block to BIRD, and (2) addTable: add new routing table to BIRD.

    This layer also assign loopback address for iBGP/LDP, etc., for other
    protocols to use later and as router id.
    """

    __loopback_assigner: IPv4Network
    __loopback_pos: int

    def __init__(self, loopback_range: str = '10.0.0.0/16'):
        """!
        @brief Routing layer constructor.

        @param loopback_range (optional) network range for assigning loopback
        IP addresses.
        """
        super().__init__()
        self.__loopback_assigner = IPv4Network(loopback_range)
        self.__loopback_pos = 1
        self.addDependency('Base', False, False)

    def getName(self) -> str:
        return "Routing"

    def __installBird(self, node: Node):
        """!
        @brief Install bird on node, and handle the bug.
        """
        # node.addBuildCommand('mkdir -p /usr/share/doc/bird2/examples/')
        # node.addBuildCommand('touch /usr/share/doc/bird2/examples/bird.conf')
        # node.addBuildCommand('apt-get update && apt-get install -y --no-install-recommends bird2')
        node.setBaseSystem(BaseSystem.SEEDEMU_ROUTER)

    def configure(self, emulator: Emulator):
        reg = emulator.getRegistry()
        for ((scope, type, name), obj) in reg.getAll().items():
            if type == 'rs':
                rs_node: Node = obj
                self.__installBird(rs_node)
                rs_node.appendStartCommand('[ ! -d /run/bird ] && mkdir /run/bird')
                rs_node.appendStartCommand('bird -d', True)
                self._log("Bootstrapping bird.conf for RS {}...".format(name))

                rs_ifaces = rs_node.getInterfaces()
                assert len(rs_ifaces) == 1, "rs node {} has != 1 interfaces".format(rs_node.getName())

                rs_iface = rs_ifaces[0]

                if not issubclass(rs_node.__class__, Router): rs_node.__class__ = Router
                rs_node.setFile("/etc/bird/bird.conf", RoutingFileTemplates["rs_bird"].format(
                    routerId = rs_iface.getAddress()
                ))

            if type == 'rnode':
                rnode: Router = obj
                if not issubclass(rnode.__class__, Router): rnode.__class__ = Router

                self._log("Setting up loopback interface for AS{} Router {}...".format(scope, name))

                lbaddr = self.__loopback_assigner[self.__loopback_pos]

                rnode.appendStartCommand('ip li add dummy0 type dummy')
                rnode.appendStartCommand('ip li set dummy0 up')
                rnode.appendStartCommand('ip addr add {}/32 dev dummy0'.format(lbaddr))
                rnode.setLoopbackAddress(lbaddr)
                self.__loopback_pos += 1

                self._log("Bootstrapping bird.conf for AS{} Router {}...".format(scope, name))

                self.__installBird(rnode)

                r_ifaces = rnode.getInterfaces()
                assert len(r_ifaces) > 0, "router node {}/{} has no interfaces".format(rnode.getAsn(), rnode.getName())

                ifaces = ''
                has_localnet = False

                for iface in r_ifaces:
                    net = iface.getNet()
                    if net.isDirect():
                        has_localnet = True
                        ifaces += RoutingFileTemplates["rnode_bird_direct_interface"].format(
                            interfaceName = net.getName()
                        )

                rnode.setFile("/etc/bird/bird.conf", RoutingFileTemplates["rnode_bird"].format(
                    routerId = rnode.getLoopbackAddress()
                ))

                rnode.appendStartCommand('[ ! -d /run/bird ] && mkdir /run/bird')
                rnode.appendStartCommand('bird -d', True)

                if has_localnet: rnode.addProtocol('direct', 'local_nets', RoutingFileTemplates['rnode_bird_direct'].format(interfaces = ifaces))

    def render(self, emulator: Emulator):
        reg = emulator.getRegistry()
        for ((scope, type, name), obj) in reg.getAll().items():
            if type == 'rs' or type == 'rnode':
                assert issubclass(obj.__class__, Router), 'routing: render: adding new RS/Router after routing layer configured is not currently supported.'

            if type == 'rnode':
                rnode: Router = obj
                if issubclass(rnode.__class__, RealWorldRouter):
                    self._log("Sealing real-world router as{}/{}...".format(rnode.getAsn(), rnode.getName()))
                    rnode.seal()

            if type in ['hnode', 'csnode']:
                hnode: Node = obj
                hifaces: List[Interface] = hnode.getInterfaces()
                assert len(hifaces) == 1, 'Host {} in as{} has != 1 interfaces'.format(name, scope)
                hif = hifaces[0]
                hnet: Network = hif.getNet()
                rif: Interface = None

                cur_scope = ScopedRegistry(scope, reg)
                for router in cur_scope.getByType('rnode'):
                    if rif != None: break
                    for riface in router.getInterfaces():
                        if riface.getNet() == hnet:
                            rif = riface
                            break

                assert rif != None, 'Host {} in as{} in network {}: no router'.format(name, scope, hnet.getName())
                self._log("Setting default route for host {} ({}) to router {}".format(name, hif.getAddress(), rif.getAddress()))
                hnode.appendStartCommand('ip rou del default 2> /dev/null')
                hnode.appendStartCommand('ip route add default via {} dev {}'.format(rif.getAddress(), rif.getNet().getName()))

    def print(self, indent: int) -> str:
        out = ' ' * indent
        out += 'RoutingLayer: BIRD 2.0.x\n'

        return out