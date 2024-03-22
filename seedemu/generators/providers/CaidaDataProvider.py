from typing import List, Dict
from sys import stderr
from . import graphFromXmlTopoFileAliased, DataProvider
from toolz.dicttoolz import *
from seedemu.layers.Scion import LinkType
import networkx as nx

class CaidaDataProvider(DataProvider):
    """!
    @brief data source for the topology generator.
    It is really just a wrapper around an networkx MultiGraph
    that contains ASes and their various interconnections,
    and at which IXp they happen.
    """
    _topofile: str

    def getASes(self) -> List[int]:
        return list( self._graph.nodes)

    def __init__(self, topofile: str):
        """
        @brief reads the topology file that is to be used
        """
        self._topofile = topofile
        self._graph = graphFromXmlTopoFileAliased(topofile)

    def getCertIssuer(self, asn: int ) ->int:
        
        assert not self.isCore(asn) # or return 'asn' if it is a Core AS itself

        # return the first best Core AS that asn is connected with
        candidates = [ k for (k,v) in self.getPeers(asn).items() if v == LinkType.Transit ]
        return candidates[0]
      
    def isCore(self, asn: int )-> bool:
        """
        @brief return whether the AS with this ASN is a CORE AS 
        """

        types = nx.get_node_attributes(self._graph, "type")
       
        if asn in types:
            return types[asn] == "core"
        else:
            return False
    
    

    def getName(self) -> str:
        """!
        @brief Get name of this data provider.

        @returns name of the layer.
        """
        return "CaidaDataProvider({})".format(self._topofile)

    def getPrefixes(self, asn: int) -> List[str]:
        """!
        @brief Get list of prefixes announced by the given ASN.
        @param asn asn.

        @returns list of prefixes.        
        """
        return ["auto"]

    def getPeers(self, asn: int) -> Dict[int, str]: # why not add the Id of the IX where they peer here
        """!
        @brief Get a dict of peer ASNs of the given ASN.
        @param asn asn.

        @returns dict where key is asn and value is peering relationship.       
        """

        peer_ases = {}
        peering_relations = nx.get_edge_attributes(self._graph, 'rel')

        # TODO: check that all multi edges between the same two ASes  actually do have the same peering relation as expected
        #  if not this code is broken
        types = keymap( lambda x: frozenset([x[0],x[1]]), peering_relations)
        for edge in nx.edges(self._graph, asn):
            assert edge[0] == asn
            key = frozenset([edge[0],edge[1]])

            if types[key] == "core":             
                if edge[0] == asn:
                    peer_ases[edge[1]] = LinkType.Core
                else:
                    peer_ases[edge[0]] = LinkType.Core
            elif types[key] == "customer":
                if edge[0] == asn:
                    peer_ases[edge[1]] = LinkType.Transit
                else:
                    peer_ases[edge[0]] = LinkType.Transit
            elif types[key] == "peer":
                if edge[0] == asn:
                    peer_ases[edge[1]] = LinkType.Peer
                else:
                    peer_ases[edge[1]] = LinkType.Peer

        return peer_ases

    def getInternetExchanges(self, asn: int) -> List[int]:
        """!
        @brief Get list of internet exchanges joined by the given ASN.
        @param asn ASN.

        @returns list of tuples of internet exchange ID. Use
        getInternetExchangeMembers to get other members.
        """

        ixps_by_asn = nx.get_node_attributes(self._graph, 'ixp_presences')
        return ixps_by_asn[asn]


    def getInternetExchangeMembers(self, ix_id: int) -> Dict[int, str]:
        """!
        @brief Get internet exchange members for given IX ID.
        @param id internet exchange ID provided by getInternetExchanges.

        @returns dict where key is ASN and value is IP address in the exchange.
        value can also be 'auto' - > it will be used as an argument to Node::joinNetwork()
        Note that if an AS has multiple addresses in the IX, only one should be
        returned.
        """
        asn2ip = dict()
        ixps = nx.get_edge_attributes(self._graph, 'ixp_id')

        # TODO: this is stupid. instead of iterating over the edges, iterate over the ixp map. There are by far less ixps than edges !!

        for edge in self._graph.edges(): # edge (u,v)   ixps (u,v, z)
            candidates = {k: v for k, v in ixps.items() if ( k[0]==edge[0] and k[1] == edge[1] or k[0]==edge[1] and k[1] == edge[0] ) and v == ix_id }
            
                        
            #if ixps[edge]  == ix_id:
            if len(candidates) > 0:
                if edge[0] not in asn2ip:
                    asn2ip[edge[0]] = "auto"

                if edge[1] not in asn2ip:
                    asn2ip[edge[1]] = "auto"

        assert len(asn2ip) > 0 # this usually means that 'ix_id' is some non-existent invalid Ix id
        return asn2ip

    def getInternetExchangePrefix(self, id: int) -> str:
        """!
        @brief Get internet exchange peering lan prefix for given IX ID.
        @param id internet exchange ID provided by getInternetExchanges.

        @returns prefix in cidr format.
        used for Base::createInternetExchange() by the default generator  and can be 'auto'
        """
        return "auto"   # only possible if there are less than 255 ASes and Ixps

    def _log(self, message: str):
        """!
        @brief Log to stderr.
        """
        print("==== {}CaidaDataProvider: {}".format(self.getName(), message), file=stderr)
