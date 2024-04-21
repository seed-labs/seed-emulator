from typing import List, Dict,Tuple
import networkx as nx
from . import DataProvider, FromSCIONTopoJSON

from ipaddress import IPv4Network
from seedemu.layers.Scion import LinkType as ScLinkType


def LinkTypeFromTopo(link_type: str, dir: Tuple[int,int] =(-1,-1) ) -> ScLinkType:
    """
    @param link_type link-type edge attribute encoded as '{from_asn}#LINK_TYPE#{to_asn}' 
            The ASNs denote the direction in which the link type holds.
    @param dir the edge (from_ASN, to_ASN) for which the actual LinkType is sought
    If the link type of edge (A,B) is CHILD, and dir is (B,A) then this method returns 'PARENT'
    """
    types = link_type.split('#')
    if types[1] == "CORE":
        if dir[0]>0:
            #same direction
            if int(types[0]) == dir[0]:
                return ScLinkType.Core
            elif int(types[2]) == dir[0]:
                # opposite edge direction 
                return ScLinkType.Core
            else:
                raise AssertionError('invalid edge ')   
        else:
            return ScLinkType.Core
    elif types[1] == "CHILD":
        if dir[0]>1:
            # same direction
            if int(types[0]) == dir[0]:
                assert int(types[2]) == dir[1]
                return ScLinkType.Transit
            elif int(types[2]) == dir[0]:
                # opposite edge direction - relation has to be inverted Child->parent , parent->child
                assert int(types[0]) == dir[1]
                return ScLinkType.Transit # actually wrong !!
            else:
                raise AssertionError('invalid edge ')   
            
        return ScLinkType.Transit    
    
    elif types[1] == "PARENT":

        return ScLinkType.Transit
    elif types[1] == "PEER":
        return ScLinkType.Peer


class CrossConnectNetAssigner:
    def __init__(self, prefix = "10.254.0.0/16"):
        self.subnet_iter = IPv4Network(prefix).subnets(new_prefix=28)
        self.xc_nets = {}

    def next_addr(self, asn_a: int, asn_b: int):
        net = frozenset([asn_a,asn_b])
        if net not in self.xc_nets:
            hosts = next(self.subnet_iter).hosts()
            next(hosts) # Skip first IP (reserved for Docker)
            self.xc_nets[net] = hosts
        return "{}/28".format(next(self.xc_nets[net]))

class ScionTopoJsonProvider(DataProvider):
    """!
    @brief data source for the topology generator that reads topology.json files from real SCION deployments.
            Use this to run virtual experiments with your configuration without jeopardising the physical deployment.

    All links between ASes are implementes via XC cross connects.

    It is not complete yet, i.e. link mtu attributes from the file are ignored etc.
    TODO: 
        - set MTU of the xc{} network to value specified for the corresponding link
                tricy because the net is only first created in Node::configure() when rendering
                Might be realised with Hook::postconfigure()
                loop over all routers , call Node::getCrossConnects() and get the xc net from it

    """
    
    def __init__(self, filename: str , assigner: CrossConnectNetAssigner = CrossConnectNetAssigner() ):
        """
        @brief loads topology from file
        @param assigner will be used to assign addresses to border routers for cross connections
        """
        self._assigner = assigner
        self._graph = FromSCIONTopoJSON( filename )

    def getAttributes(self, asn: int) -> Dict[str,any]:

        val = self._graph.nodes[asn]
        return val

    def getSCIONCrossConnects(self, from_asn: int) -> Dict[int, List[ Tuple[str,ScLinkType,Tuple[int,int]]]]:
        # peerasn -> ListOf:  address, LinkType, (IFID_a,IFID_b) # peername can be constructed as 'br{}'.format(IFID_b)
        cross_connects = {}

        #  dict that maps from and to ASNs of a link to the corresponding SCION InterfaceID
        ifids = nx.get_edge_attributes(self._graph, 'ifids') 
        link_types = nx.get_edge_attributes(self._graph, 'linkAtoB')

        
        for edge in self._graph.edges(from_asn):
            peer_asn = edge[1]
            assert peer_asn != from_asn
            assert edge[0] == from_asn
            if peer_asn not in cross_connects:
                cross_connects[peer_asn] = [ ]

            for (k,link_type) in [ (k,v) for (k,v) in link_types.items() if ( k[0] == from_asn and k[1] == peer_asn ) or (  k[1] == from_asn and k[0] == peer_asn )]:

                asifid = ifids[(k[0],k[1],k[2])]
                from_ifid = asifid[from_asn]
                to_ifid = asifid[peer_asn]

                type = LinkTypeFromTopo(link_type, (from_asn,peer_asn) )
           
                cross_connects[peer_asn] .append(  ( self._assigner.next_addr(from_asn,peer_asn), type, (from_ifid, to_ifid ) ) )

        return cross_connects

    def getCertIssuer(self, asn: int ) -> int:
        """
        @brief return the scion core AS that issues the certificates for the given non-core AS
        @param ASN of a non-core scion AS      
        """
        issuer = nx.get_node_attributes(self._graph, 'cert_issuer')
        ia = nx.get_node_attributes(self._graph,'ia')

        if asn in issuer:
            iss = issuer[asn]
            vals = [k for k,v in ia.items() if v == iss ]
            assert len(vals ) == 1
            return vals[0]
        else: 
            assert IndexError('no cert issuer for AS {}'.format(asn))

    def isCore(self, asn: int )-> bool:
        """
        @brief is the AS denoted by ASN asn a Core AS ?!
        """
        attr = nx.get_node_attributes(self._graph,'core')
        if asn not in attr:
            return False
        else:
            value = attr[asn]
            return value
        
    def getASInterfaces(self, asn: int) ->List[int]:
        return sum( map(lambda x: [  v[2][0] for v in x ],  self.getSCIONCrossConnects(asn).values() ) , [])

    def getLinkAttributes(self, asn: int , if_id: int):
        assert if_id != 0
        return {}
    
    def getASes(self) -> List[int]:
        """
        @brief return a list of all the AutonomousSystems there are
        """
        return list( self._graph.nodes() )

    def getName(self) -> str:
        """!
        @brief Get name of this data provider.

        @returns name of the layer.
        """
        return "ScionTopoJsonProvider"

    def getPrefixes(self, asn: int) -> List[str]:
        """!
        @brief Get list of prefixes announced by the given ASN.
        @param asn asn.

        @returns list of prefixes.
        used for AutonomousSystem::createNetwork() by the generator
        and thus may be 'auto'
        """
        return ["auto"]

    def getPeers(self, asn: int) -> Dict[int, str]: # why not add the Id of the IX where they peer here
        """!
        @brief Get a dict of peer ASNs of the given ASN.
        @param asn asn.

        @returns dict where key is asn and value is peering relationship.
        the peering relationship is currently used by Ebgp::addPrivatePeering() by the default Generator
        """
        return {}

    def getInternetExchanges(self, asn: int) -> List[int]:
        """!
        @brief Get list of internet exchanges joined by the given ASN.
        @param asn asn.

        @returns list of tuples of internet exchange ID. Use
        getInternetExchangeMembers to get other members.
        """
        return []

    def getInternetExchangeMembers(self, id: int) -> Dict[int, str]:
        """!
        @brief Get internet exchange members for given IX ID.
        @param id internet exchange ID provided by getInternetExchanges.

        @returns dict where key is ASN and value is IP address in the exchange.
        value can also be 'auto' - > it will be used as an argument to Node::joinNetwork()
        Note that if an AS has multiple addresses in the IX, only one should be
        returned.
        """
        return {}

    def getInternetExchangePrefix(self, id: int) -> str:
        """!
        @brief Get internet exchange peering lan prefix for given IX ID.
        @param id internet exchange ID provided by getInternetExchanges.

        @returns prefix in cidr format.
        used for Base::createInternetExchange() by the default generator  and can be 'auto'
        """
        raise NotImplementedError('getInternetExchangeSubnet not implemented.')

    def _log(self, message: str):
        """!
        @brief Log to stderr.
        """
        print("==== {}DataProvider: {}".format(self.getName(), message))
