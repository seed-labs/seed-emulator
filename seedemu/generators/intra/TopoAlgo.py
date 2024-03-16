import networkx as nnx
import toolz

def _compute_border_router_candidates(G):
    """
    @return a list of nodes/routers from the core of the network,
        sorted ascendingly by how many links they have to non-core routers
        as a measure of 'how internal' the nodes are
    """
    
    center = nnx.center(G) 
    s = set(center)
    nonCenter = [x for x in G.nodes() if x not in s]

    centerd =0
    noncent= 1
    nodeAttr = {}
    for x in center:
        nodeAttr[int(x)] =centerd
    for x in nonCenter:
        nodeAttr[int(x)] = noncent    
    centerSubgraph = G.subgraph(center)

  

    edgesInG = { n : list( nnx.edges(G,n) ) for n in centerSubgraph.nodes() }
    edgesInCenter = {n : list( nnx.edges(centerSubgraph,n)  ) for n in centerSubgraph.nodes() }

    edgesToNonCenter = toolz.dicttoolz.itemmap( lambda kv: (kv[0], len(kv[1]) - len(edgesInCenter[kv[0]])  ), edgesInG)

    sortedEdges  = list(edgesToNonCenter.values())

    sortedEdges.sort(reverse=True)
    maxEdges = sortedEdges[0]


    sortedEdgesD = {k: v for k, v in sorted( edgesToNonCenter.items(), key=lambda item: item[1])}

    srtEdgToNcenter = dict(sorted( edgesToNonCenter.items(), key=lambda item: item[1]))

    return srtEdgToNcenter.keys()

def _getDegreeWithoutEndhosts(G, n):
    """
    returns degree with all connected nodes of degree one (Endhosts) not counting
    """

    deg = G.degree[n]

    for e in G.edges(n):
        assert e[0 ] ==n
        if G.degree[e[1]] ==1:
            deg -=1
    return deg


def _compute_topo(G):
    """
    @brief returns a tuple (end_hosts, edge_routers, edge_router_parents )
    """
    nodecnt = len(G.nodes() )
    print(nodecnt)
    
    endHosts  =[] # nodes with degree one
    edge_routers = [] # parents of endhosts
    # maps an edge router node to its parents (node connected to it, with degree greater than 1)
    edge_router_parents = dict() 
    for i in G.nodes():
        if G.degree[i] == 1:
            endHosts.append( i )
            outedg = list( G.edges(i) ) # has only length one since degree is one
            edg = outedg[0][1]
            assert outedg[0][0] == i
            # check if for all nodes 'x' connected to edg except one holds: degree(x)==1
            degr_gt_one = 0
            parent = -1
            for e in list( G.edges(edg) ):
                assert e[0] == edg
                #if G.degree[e[1]] > 1: # subtract nr of endhosts from degree
                if _getDegreeWithoutEndhosts(G,e[1])>1:
                    degr_gt_one += 1
                    parent = e[1]
                    if degr_gt_one >1:
                        # this node 'edg' must belong to the core (it is connected to two other routers)
                        parent = -1
                        break

            if degr_gt_one == 1:
                assert parent !=-1
                edge_routers.append( edg )
                edge_router_parents[edg] =[parent]


    edge_router_parent_childs = dict()
    for ch, ep in edge_router_parents.items():
        assert len(ep)==1
        if ep[0] in edge_router_parent_childs:
            edge_router_parent_childs[ep[0]].append(ch)
        else:
            edge_router_parent_childs[ep[0]]=[ch]

    return endHosts,edge_routers,edge_router_parent_childs.keys()


def getRouters(G):
    """
    @brief return a list of all nodes in the graph that are routers not hosts ( degress more than one)
    """
    hosts = getEndhosts(G)
    return [ x for x in G.nodes() if x not in hosts ]

def getEndhosts(G):
    """
    @brief return a list of all Endhost (nodes with degree 1)
    """
    return _compute_topo(G)[0]

def getEdgeRouters(G):
    """
    @brief return a list of nodes, that have only nodes with degree '1' ( EndHosts ) as children
    """
    return _compute_topo(G)[1]

def getEdgeRouterParents(G):
    """
    @brief 
    """
    return _compute_topo(G)[2]

def getCenterNodes(G):
    """
    @return a list of nodes (routers) that are in the center
    """
    center = nnx.center(G)
    return list(center)

def getCenterSubgraph(G):
    """
    @brief return the core of the network formed by internal /non-edge routers and their connecting links
    """
    center = nnx.center(G) 
        
    return G.subgraph(center)



