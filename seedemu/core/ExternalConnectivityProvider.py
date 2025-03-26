from typing import List, Tuple, Dict
# theese would be circular imports
#from seedemu.core import Node, Router, Network
#from seedemu.core.enums import NodeRole, NetworkType

# alternatives:  InteriorBridgeway, InsideOutConnector, InsideOutGateway
# OutboundAccessProvider, EgressProvider, ExternalReachabilityProvider, External/UplinkProvider
#   ExitPointProvider, LocalNetworkGateway, SimulationExitProvider, OutboundConnectivityProvider
class ExternalConnectivityProvider():
    """!
    @brief this class provides connectivity for emulated nodes
    from within an emulated network to the external 'real' Internet
    via the hosts network.
    It mediates between hosts who might have a service installed
    that requires RealWorldConnectivity (i.e. DevService (git,go,cargo etc.))
    the ('local') network and a RealWorldRouter who actually provides the ExternalReachability.
    This is the exact opposite of what the RemoteAccessProvider does.

    It achieves this, by making the host's default gateway router into a RealWorldRouter.
    The user need not bother with minding this himself(can keep using AS::createRouter()
    and any extra functionality will be 'mixed'in on demand later automatically).

    """
    def __init__(self):
        self.__requesters_per_net = {}


    # this is probably not the right signature anymore !!
    # brNet is actually only required for brnode.seal() in Routing::render()
    # where it is already available through emulator.getServiceNetwork()
    # configureSimulationExit()
    '''
    def configureExternalLink(self, emulator: 'Emulator', netObject: 'Network', brNode: 'Node', brNet: 'Network'):
        """
        @param netObject a local network, whose nodes shall have 'external connectivity' through their default gateway
        @param brNode reference to a service node that is not part of the emulation. # does this still apply
            The configureExternalLink method will join the brNet/netObject networks.
            Do not join them manually on the brNode.
        @param brNet reference to a network that is not part of the emulation. (service net)
        This network will have access NAT to the real internet.
        """
        from seedemu.core import Node, Router, Network, promote_to_real_world_router
        from seedemu.core.enums import NodeRole, NetworkType
        self._log('setting up ExternalReachability for {} in AS{}...'.format(netObject.getName(), brNode.getAsn()))

        assert netObject.getType() == NetworkType.Local
        assert brNode.getRole() in [NodeRole.Router, NodeRole.BorderRouter], 'only routers may have external reachability'

        #TODO: brNode = promote_to_real_world_router(brNode, False)
        # ---------------------------------------------------------------------------------------------------
        #this is all handled inside RealWorldRouter!!!
        #brNode.addSoftware('bridge-utils')
        #brNode.appendStartCommand('ip route add default via {} dev {}'.format(brNet.getPrefix()[1], brNet.getName()))

        #brNode.joinNetwork(brNet.getName())
        #brNode.joinNetwork(netObject.getName()) # is it an error to join the same net twice  ?!
    '''

    def requestExternalLink(self, pnode: 'Node', net: 'Network' ):
        """! @brief remembers who requested external connectivity on which network.

        This is later used in RoutingLayer::render() to determine who becomes the RealWorldRouter on a net,
        and who becomes whose default gateway
        """
        from seedemu.core import Node, Router, Network
        from seedemu.core.enums import NodeRole, NetworkType

        assert net.getType() == NetworkType.Local
        if net in self.__requesters_per_net:
            self.__requesters_per_net[net].add(pnode) # add(pnode.getName())
        else:
            self.__requesters_per_net[net] = set([pnode]) # set([pnode.getName()])

    # since Networks are Registrable we can call getRegistryInfo() and obtain the scope ->
    # which will be the AS -> so the node name is enough info to uniquely identify it
    # (because node and net will have the same ASN)

    def getExternalNodesForNet(self, net: 'Network') -> List[str]:
        if net in self.__requesters_per_net:
            return list(self.__requesters_per_net[net])
        else: return []

    def resolveRWA(self, emulator: 'Emulator', net: 'Network' ) -> Tuple[List['Node'], Dict['Node', 'Node']]:
        """
        return a list of router nodes, that shall become RWRs
        and a dict that maps RWA requesting nodes to their respective RWR (on their local net)
        """
        from seedemu.core.enums import NodeRole
        from seedemu.core import Network

        rwr_candidates = []
        gateway_candidates_by_hosts = {}
        router_roles = [NodeRole.Router, NodeRole.BorderRouter]

        # nodes that request to phone 'out' the simulation
        req_nodes = self.getExternalNodesForNet(net)
        # routers which request external access for some reason
        req_rnodes = [n for n in req_nodes if n.getRole() in router_roles]
        if len(req_rnodes) > 0: rwr_candidates = req_rnodes
        else:
            # pick one of the routers associated to this net
            rwr_candidates = [n for n in net.getAssociations() if n.getRole() in router_roles]

        for n in [n for n in req_nodes if n.getRole() not in router_roles]:

            #gateway_candidates_by_hosts[n.getName()] = rwr_candidates[0].getName()
            gateway_candidates_by_hosts[n] = rwr_candidates[0]

        return  rwr_candidates, gateway_candidates_by_hosts

    def getName(self) -> str:
        return 'IPRoute' # or IPtablesExitProvider sth.