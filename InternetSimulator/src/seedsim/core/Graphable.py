from typing import List

class Vertex:
    """!
    @brief a vertex in graph.
    """

    # label of the node.
    label: str

    # group of the node, nodes within same group will be put into the samle
    # cluster.
    group: str

class Edge:
    """!
    @brief an edge in graph.
    """
    a: Vertex
    b: Vertex

class Graph:
    """!
    @brief a graph.
    """

    # name.
    name: str

    # directed graph?
    directed: bool

    # list of vertices
    vertices: List[Vertex]

    # list of edges
    edges: List[Edge]

    def toGraphviz(self) -> str:
        """!
        @brief Convert graph to graphviz dot format.
        """


class Graphable:
    """!
    @brief Graphable. All layers that can produce graphs will have this
    prototype.
    """

    def getGraphs(self, name: str) -> List[Graph]:
        """!
        @brief Get all avaliable graphs.
        """
        raise NotImplementedError('getGraphs not implemented.')