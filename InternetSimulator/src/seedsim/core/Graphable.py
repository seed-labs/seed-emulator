from typing import List, Dict

class Vertex:
    """!
    @brief a vertex in graph.
    """

    # name of the node.
    name: str

    # group of the node, nodes within same group will be put into the samle
    # cluster.
    group: str

    def __init__(self, name: str, group: str = None):
        """!
        @brief Vertex constructor.
        """
        self.name = name
        self.group = group

class Edge:
    """!
    @brief an edge in graph.
    """

    def __init__(self, a: str, b: str, label: str = None, alabel: str = None, blabel: str = None):
        """!
        @brief Edge constructor.
        """
        self.a = a
        self.b = b
        self.label = label
        self.alabel = alabel
        self.blabel = blabel

    # name of vertex, if directed, this is src
    a: str

    # name of vertex, if directed, this is dest
    b: str

    # label on the middle of the edge
    label: str

    # label on the a side of the edge
    alabel: str

    # label on the b side of the edge
    blabel: str

class Graph:
    """!
    @brief a graph.
    """

    # name.
    name: str

    # directed graph?
    directed: bool

    # list of vertices
    vertices: Dict[str, Vertex]

    # list of edges
    edges: List[Edge]

    def __init__(self, name: str, directed: bool):
        """!
        @brief Graph constructor.
        """
        self.name = name
        self.directed = directed
        self.vertices = {}
        self.edges = []

    def addVertex(self, name: str, group: str = None):
        """!
        @brief add a new node.
        
        @param name name of the node.
        @param group (optional) name of the culster.
        @throws AssertionError if vertex already exist.
        """
        assert name not in self.__vertices, 'vertex with name {} already exist.'.format(name)
        self.vertices[name] = Vertex(name, group)

    def addEdge(self, a: str, b: str, label: str = None, alabel: str = None, blabel: str = None):
        """!
        @brief add a new edge
        @throws AssertionError if vertex a or b does not exist.
        """
        assert a in self.__vertices, ' {} not a vertex.'.format(a)
        assert b in self.__vertices, ' {} not a vertex.'.format(b)
        self.edges.append(Edge(a, b, label, alabel, blabel))

    def toGraphviz(self) -> str:
        """!
        @brief Convert graph to graphviz dot format.

        @todo todo

        @returns graphviz source.
        """
        pass

class Graphable:
    """!
    @brief Graphable. All layers that can produce graphs will have this
    prototype.
    """

    __graphs: Dict[str, Graph]

    def __init__(self):
        """!
        @brief Graphable constructor.
        """
        self.__graphs = {}

    def _addGraph(self, name: str, directed: bool) -> Graph:
        """!
        @brief create a new graph. This is to be called by internal classes to
        create graph.

        @return newly created graph.
        @throws AssertionError if graph already exist.
        """
        assert name not in self.__graphs, 'graph {} already exist'.format(name)
        g = Graph(name, directed)
        self.__graphs[name] = g
        return g

    def getGraph(self, name: str) -> Graph:
        """!
        @brief get a graph by name.

        @param name name.

        @returns graph.
        @throws AssertionError if graph does not exist.
        """
        assert name in self.__graphs, 'graph {} does not exist'.format(name)
        return self.__graphs[name]

    def getGraphs(self) -> Dict[str, Graph]:
        """!
        @brief Get all avaliable graphs.

        @returns all graphs.
        """
        return self.__graphs