import networkx as nnx
from .FromTopo import *
from .TopoAlgo import *
from .FromTopoTiers import graphFromTiersTopoFile
from seedemu.core import AutonomousSystem
from enum import Enum

class ResolutionLevel(Enum):
    Default = "default"
    # nodes with degree '1' are interpretet as routers
    RouterLevel = "router_lvl"
    # nodes with degree '1' are interpretet as endhosts
    HostLevel = "host_lvl"

class TopoFormat(Enum):
    """
    @brief Internet Simulator Topology File Formats Enum
    """
    ORBIS = "orbis"
    BRITE = "brite"
    ROCKETFUEL = "rocketfuel"
    TIERS = "tiers"
    # GRAPHML
    # todo: add a custom new one, that also specifies the net for routers

class ASTopology:
    """
    @brief representation of an AutonomousSystem's internal topology i.e. Routers, Hosts and who is connected to who
    """
    @staticmethod
    def _resLvlForFormat( fmt: TopoFormat ) -> ResolutionLevel:
        if fmt == TopoFormat.ORBIS:
            return ResolutionLevel.HostLevel
        elif fmt == TopoFormat.BRITE:
            return ResolutionLevel.HostLevel
        elif fmt == TopoFormat.TIERS:
            return ResolutionLevel.RouterLevel
        elif fmt == TopoFormat.ROCKETFUEL:
            # RocketFuel files contain ISP ASes at a router level
            return ResolutionLevel.RouterLevel
        else:
            raise NotImplementedError()
        
    def __init__(self):
        self._graph = nnx.Graph()
        self._res_lvl = ResolutionLevel.Default

    def from_file(self, fname: str , fmt: TopoFormat, res: ResolutionLevel =ResolutionLevel.Default ):
        """
        @brief loads the topology file
        """
        if res == ResolutionLevel.Default:
            self._res_lvl = ASTopology._resLvlForFormat(fmt)
        else:
            self._res_lvl = res

        if fmt == TopoFormat.ORBIS:
            graphFromOrbisTopoFile2( fname, self._graph)
        elif fmt== TopoFormat.BRITE:
            graphFromBRITETopoFile(self._graph,fname)
        elif fmt==TopoFormat.TIERS:
            self._graph = graphFromTiersTopoFile(fname)
        elif fmt==TopoFormat.ROCKETFUEL:
            self._graph = graphFromRocketfuelTopoFile(fname)
        else:
            raise NotImplementedError('unsupported topology file format: {}'.format(fmt) )

        return self

    def getHosts(self):
        if self._res_lvl == ResolutionLevel.HostLevel:
            # endhosts have no children themselves ( node degree is one)
            return getEndhosts(self._graph)
        else:
            # all nodes are routers, there are no hosts
            return []
    
    def getRouters(self):
        if self._res_lvl == ResolutionLevel.HostLevel:
            # a router must have children ( degree greater than one )
            return getRouters(self._graph)
        else:
            # all nodes are routers
            return self._graph.nodes()

    def getEdgeRouters(self):
        if self._res_lvl == ResolutionLevel.HostLevel:
            return getEdgeRouters(self)
        elif self._res_lvl == ResolutionLevel.RouterLevel:
            # interpret nodes with degree one as edge routers that are attached to endhosts
            return getEndhosts(self._graph)
    
    def edges(self, node: int):
        return list(self._graph.edges(node))
    


class IntraASTopoReader(object):
    """
    @brief reads for Intra Domain Topology of an Autonomous System from file
    """

    def __init__(self):
        """
        """

        # maybe factor out the 'read_file()' in its own method, that might fail
    def generateAS(self, topo: ASTopology, system: AutonomousSystem ):
        """
        @brief make the AS's topology 
        @param system the AS whose topology is to be constructed from file.
                It is assumed to still be empty  .
        @param
        """
        routers = topo.getRouters()
        router_nets = dict()


        router_nodes= dict()        
        # create routers and their networks
        for r in routers:
            router = system.createRouter("{:0>3d}".format(r)) 
            router_nodes[ r ] = router

            netname = "net_{:0>3d}".format(r)
            net = system.createNetwork(netname)
            router.joinNetwork(netname)
            router_nets[r] = net

        link_nets = dict()

        # depending on the resolution level of the topology this might be empty
        endhosts = topo.getHosts()

        # connect routers
        for i,r in enumerate(routers):

            j=0
            for e in topo.edges(r):               
                assert e[0] == r
                r2 =e[1]
                if r2 in endhosts: continue

                if frozenset([r, r2]) not in link_nets:
                    j+=8 # incr to not set host bits
               # 
               #     net = link_nets[frozenset([r, r2])]
               #     if r not in net.getAssociations():
               #         router_nodes[r].joinNetwork(net.getName())
               #     if r2 not in net.getAssociations():
               #         router_nodes[r2].joinNetwork(net.getName())

               # else:
                    nname = 'net{:0>3d}_{:0>3d}'.format(r,r2)                    
                    net = system.createNetwork(nname ,prefix='{}.{}.{}.{}/29'.format( int(i/254 +1), i % 254 , int(j/254),j % 254), direct = False )
                    assert net.getName() == nname
                    router_nodes[r].joinNetwork(net.getName(),'{}.{}.{}.{}'.format( int(i/254 +1), i % 254 , int(j/254),j % 254 +2 ) )
                    router_nodes[r2].joinNetwork(net.getName(),'{}.{}.{}.{}'.format( int(i/254 +1), i % 254 , int(j/254),j % 254 +3  ) )

                    link_nets[frozenset([r,r2])] = net

        for h in endhosts:
            # for endhosts, there is only one edge, to its sole parent
            edge = topo.edges(h)[0]
            host = system.createHost( "node{}_{:0>3d}".format(system.getAsn(),h) )
            host.joinNetwork( router_nets[edge[1] ].getName() )

        return system