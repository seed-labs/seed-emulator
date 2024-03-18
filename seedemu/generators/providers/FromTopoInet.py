import networkx as nx

def graphFromInetTopoFile(topofile: str):
    G = nx.MultiGraph()
    return graphFromInetTopoFile(G,topofile)

def graphFromInetTopoFile( G: nx.MultiGraph, topofile: str ) -> nx.MultiGraph:
    """
    @brief reads Inet topology file into networkx graph
    Inet format starts with 'Nr.nodes Nr.edges\n'
    followed by Nr.nodes x lines of node-records
    followed by Nr.edges x lines of edge records

    edge-records look like 'from-node to-node weight\n'
    """

    with  open(topofile, "r") as file:
        fstline = file.readline()

        totals = fstline.split()
        nodecount = totals[0]
        edgecount = totals[1]

        # read all nodes
        for i in range(0,int(nodecount)):
           line = file.readline()
           token = line.split()
           G.add_node( int(token[0]) , id = token[0] )

        #read all edges
        for i in range(0,int(edgecount)) :  
            line = file.readline()
            token = line.split()
            link_attr = {}
            link_attr["Weight"] = token[2]
            G.add_edge( int(token[0]), int(token[1]),**link_attr)

    return G        
