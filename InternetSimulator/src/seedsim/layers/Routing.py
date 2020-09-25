from .Layer import Layer
from seedsim.core import Registry, ScopedRegistry, Node, Interface, Network
from typing import List, Dict
from functools import partial

RoutingFileTemplates: Dict[str, str] = {}

RoutingFileTemplates["protocol"] = """protocol {protocol} {name} {{{body}}}
"""

RoutingFileTemplates["rs_bird"] = """router id {routerId};
protocol device {{
}}
"""

RoutingFileTemplates["rnode_bird"] = """router id {routerId};
protocol device {{
}}
protocol kernel {{
    import none;
    export all;
}}
"""

def addProtocol(node: Node, protocol: str, name: str, body: str):
    """!
    @brief Add a new protocol to BIRD on the given node.

    This method is to be injected in to router node class objects.

    @param node node to operator on.
    @param protocol protocol type. (e.g., bgp, ospf)
    @param name protocol name.
    @param body protocol body.
    """
    node.appendFile("/etc/bird/bird.conf", RoutingFileTemplates["protocol"].format(
        protocol = protocol,
        name = name,
        body = body
    ))

class Routing(Layer):
    """!
    @brief The Routing layer.

    This layer provides routing support for routers and hosts. i.e., (1) install
    BIRD on router nodes and allow BGP/OSPF to work, (2) setup kernel and device
    protocols, and (3) setup defult routes for host nodes.
    """

    __reg: Registry = Registry()
    
    def getName(self) -> str:
        return "Routing"

    def getDependencies(self) -> List[str]:
        return ["Base"]

    def onRender(self):
        for ((scope, type, name), obj) in self.__reg.getAll().items():
            if type == 'rs':
                rs_node: Node = obj
                rs_node.addSoftware('bird')
                rs_node.addStartCommand('bird -d', True)
                self._log("Bootstraping bird.conf for RS {}...".format(name))

                rs_ifaces = rs_node.getInterfaces()
                assert len(rs_ifaces) == 1, "rs node {} has != 1 interfaces".format(rs_node.getName())

                rs_iface = rs_ifaces[0]

                rs_node.addProtocol = partial(addProtocol, rs_node) # "inject" the method
                rs_node.setFile("/etc/bird/bird.conf", RoutingFileTemplates["rs_bird"].format(
                    routerId = rs_iface.getAddress()
                ))
                
            if type == 'rnode':
                self._log("Bootstraping bird.conf for AS{} Router {}...".format(scope, name))

                rnode: Node = obj
                rnode.addSoftware('bird')
                rnode.addStartCommand('bird -d', True)

                r_ifaces = rnode.getInterfaces()
                assert len(r_ifaces) > 0, "router node {}/{} has no interfaces".format(rs_node.getAsn(), rs_node.getName())

                r_iface = r_ifaces[0]

                rnode.addProtocol = partial(addProtocol, rnode) # "inject" the method
                rnode.setFile("/etc/bird/bird.conf", RoutingFileTemplates["rnode_bird"].format(
                    routerId = r_iface.getAddress()
                ))

            if type == 'hnode':
                hifaces: List[Interface] = obj.getInterfaces()
                assert len(hifaces) == 1, 'Host {} in as{} has != 1 interfaces'.format(name, scope)
                hif = hifaces[0]
                hnet: Network = hif.getNet()
                rif: Interface = None

                cur_scope = ScopedRegistry(scope)
                for router in cur_scope.getByType('rnode'):
                    if rif != None: break
                    for riface in router.getInterfaces():
                        if riface.getNet() == hnet:
                            rif = riface
                            break
                
                assert rif != None, 'Host {} in as{} in network {}: no router'.format(name, scope, hnet.getName())
                self._log("!! TODO: Set default route for host {} ({}) to router {}".format(name, hif.getAddress(), rif.getAddress()))

    def print(self, indent: int) -> str:
        out = ' ' * indent
        out += 'RoutingLayer:\n'

        indent += 4
        out += ' ' * indent

        out += '<RoutingLayer does not have configurable options>\n'


        return out