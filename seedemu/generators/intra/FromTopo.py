import re
import networkx as nx

def graphFromBRITETopoFile( topofile: str ):
    G = nx.Graph()
    return graphFromBRITETopoFile(G,topofile)


def graphFromBRITETopoFile(G: nx.Graph, topofile: str ):
    """
    @brief reads BRITE topology file into networkx graph
    Brite format starts with 'Nr.nodes Nr.edges\n' 
    followed by Nr.nodes x lines of node records 
    followed by Nr.edges x lines of edge records
    """
     

    with  open(topofile, "r") as file:
        fstline = file.readline()

        totals = fstline.split()

        # read all nodes
        for i in range(0,int(totals[0])):
           line = file.readline()
           token = line.split()
# NodeId xpos ypos indegree outgdegree ASid type
           G.add_node( int(token[0]) , id = token[0],pos=( int(token[1]),int(token[2]) ), AS=int(token[5]), type=token[6] )

        #read all edges
        for i in range(0,int(totals[1])) :  
            line = file.readline()
            token = line.split()
            link_attr = {}
            link_attr["length"] = token[3]
            link_attr["delay"] = token[4]
            link_attr["bandwith"] = token[5]
            # EdgeId from to length delay bandwidth ASfrom ASto type
            G.add_edge( int(token[1]), int(token[2]),**link_attr)

    return G


def graphFromOrbisTopoFile2(  topofile: str , G: nx.Graph):
    """
    @brief reads ORBIS topology file into networkx Graph 
    ORBIS format is really just a list of edges aka 'from-node to-node\n'
    """
    with  open(topofile, "r") as file:
       
 
        while True :  
            line = file.readline()
            if( line == ''):
                break
            token = line.split()
            fro=int(token[0])
            to=int(token[1])
            G.add_node(fro,id=fro)
            G.add_node(to,id=to)
            G.add_edge( fro, to)
    return G

def graphFromOrbisTopoFile( topofile: str ):
    """
    @brief reads ORBIS topology file into networkx Graph 
    ORBIS format is really just a list of edges aka 'from-node to-node\n'
    """
    G = nx.Graph()
   
    return graphFromOrbisTopoFile2(G,topofile)

def graphToOrbisTopoFile(topofile: str, g ):
    """
    @brief the opposite of graphFromOrbisTopoFile()
    stores graph to file as list of edges aka 'from-node to-node\n'
    """
    with open(topofile, "w") as file:
        for e in g.edges():
            file.write("{fro} {to}\n".format(fro = e[0],to=e[1]) )

def graphOldFromOrbisTopoFile( topofile: str ):
    G = nx.Graph()
   

    with  open(topofile, "r") as file:
       
 
        while True :  
            line = file.readline()
            if( line == ''):
                break
            token = line.split()
       
            G.add_edge( int(token[0]), int(token[1]))
    nodeIDS ={}            
    for i,n in enumerate(G.nodes()):
        nodeIDS[n ] ={"id": str(i)}
    nx.set_node_attributes(G,nodeIDS)
    return G     
  

def graphFromRocketfuelTopoFile(  topofile: str ) -> nx.Graph:
    """
    @brief reads Rocketfuel topology file into networkx graph
    Rockketfuel files are either of MAP .cch or WEIGHTS .intra format.


    Each line of the .cch format is:

    uid @loc [+] [bb] (num_neigh) [&ext] -> <nuid-1> <nuid-2> ... {-euid} ... =name[!] rn

    or:

        -euid =externaladdress rn

    Fields enclosed in []'s are optional. 

    uid
        A unique identifier of the node.  Negative unique identifiers are external (euids).
    loc
        The node's location. A location of "T" implies that the
        router's location is ambiguous: possibly because it is
        connected to routers of different locations.
    + 
        If present, the node's location was derived from dns, 
        If absent, the node's location was derived from its connectivity.
    bb
        If present,  the node is a backbone node (connects to other cities)
        If absent, it is an access (gateway) or customer router
    num_neigh
        The number of neighbors of this node, which is the same as
        the count of neighbors after the "->" sign.
    ext
        If the router connects to other routers outside the ISP,
        this is how many external connectsions are present.
    nuid-k
        The uids of each neighbor.  The map is symmetric.
        Links to external addresses are enclosed in {}'s.
        Links to other routers within the ISP are enclosed in <>'s.
    name
        A DNS name of this node; only the "best" name is printed
        when multiple names are found (for instance, names of aliases).
    ! 
        If present, this router didn't respond to alias resolution:
        it might not be a distinct router.   Usually these aren't in 
        the core to confuse the topology, but they are a source of uncertainty.
    rn
        The distance from a named gateway or backbone router.
        Considering only those labelled r0 excludes all external
        connections and customer routers. 
        r0 or r1 adds one hop away.  n is capped at 5.
  
    """

    reader = RocketfuelTopologyReader()
    return reader.read(topofile)



class RocketfuelTopologyReader:
    """
    Hajime Tazaki (tazaki@sfc.wide.ad.jp) 2010
    """
    ROCKETFUEL_MAPS_LINE = r'^(-*[0-9]+)[ 	]+(@[?A-Za-z0-9,+-]+)[ 	]+(\+)*[ 	]*(bb)*[ 	]*\(([0-9]+)\)[ 	]+(&[0-9]+)*[ 	]*->[ 	]*(<[0-9 	<>]+>)*[ 	]*(\{-[0-9\{\} 	-]+\})*[ 	]+=([A-Za-z0-9.!-]+)[ 	]+r([0-9])[ 	]*$'
    ROCKETFUEL_WEIGHTS_LINE = r'^([^ 	]+)[ 	]+([^ 	]+)[ 	]+([0-9.]+)[ 	]*$'

    def __init__(self):        
        self.graph = nx.Graph()

    def read(self, filename :str ):
        with open(filename, 'r') as topgen:
            lines = topgen.readlines()

        file_type = self.get_file_type(lines[0])

        for line_number, line in enumerate(lines[1:], start=2):
            line = line.strip()
            if file_type == 'MAPS':
                self.parse_maps_line(line)
            elif file_type == 'WEIGHTS':
                self.parse_weights_line(line)
            else:
                print(f"Unknown file format at line {line_number}: {line}")

        print(f"Rocketfuel topology created with {self.graph.number_of_nodes()} nodes and {self.graph.number_of_edges()} edges")
        return self.graph

    def get_file_type(self, line):
        if re.match(self.ROCKETFUEL_MAPS_LINE, line):
            return 'MAPS'
        elif re.match(self.ROCKETFUEL_WEIGHTS_LINE, line):
            return 'WEIGHTS'
        else:
            return 'UNKNOWN'

    def parse_maps_line(self, line):
        match = re.match(self.ROCKETFUEL_MAPS_LINE, line)
        if match:
            g =  match.groups()#[1:]
            uid, loc, dns, bb, num_neigh, _neighbors, _externs,_, name, radius = g
            dns = bool(dns)
            bb = bool(bb)
            num_neigh = int(num_neigh)
            radius = int(radius)

            self.graph.add_node(uid, loc=loc, dns=dns, bb=bb, name=name, radius=radius)

            neighs = match.group(7)  # group 6 -> '&6'
            if neighs:
                neighs = [neigh[1:-1] for neigh in neighs.split(">")[:-1]]
                for neigh in neighs:
                    self.graph.add_edge(uid, neigh)

    def parse_weights_line(self, line):
        """
   
        """
        match = re.match(self.ROCKETFUEL_WEIGHTS_LINE, line)
        if match:
            sname, tname, weight = match.groups()
            weight = float(weight)

            self.graph.add_edge(sname, tname, weight=weight)
