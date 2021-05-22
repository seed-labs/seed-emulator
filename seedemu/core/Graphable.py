from __future__ import annotations
from typing import List, Dict
from .Printable import Printable
from .Registry import Registry, Registrable
from .Emulator import Emulator
from copy import deepcopy

class Vertex:
    """!
    @brief a vertex in graph.
    """

    name: str
    group: str
    shape: str

    def __init__(self, name: str, group: str = None, shape: str = 'ellipse'):
        """!
        @brief Vertex constructor.

        @param name name.
        @param group cluster name.
        @param shape shape.
        """

        ## name of the node.
        self.name = name

        ## group of the node, nodes within same group will be put into the same
        ## cluster.
        self.group = group

        ## shape of the node
        self.shape = shape

    def getId(self):
        """!
        @brief Get the unique id of this node. 
        """
        return str(self.group) + "::" + str(self.name)

class Edge:
    """!
    @brief an edge in graph.
    """

    a: str
    b: str
    label: str
    alabel: str
    blabel: str    
    style: str 

    def __init__(self, a: str, b: str, label: str = None, alabel: str = None, blabel: str = None, style: str = 'solid'):
        """!
        @brief Edge constructor.

        @param a source node.
        @param b destination node.
        @param label middle lable.
        @param alabel lable on the source side.
        @param blabel lable on the destination side.
        @param style style.
        """

        ## name of vertex, if directed, this is src
        self.a = a

        ## name of vertex, if directed, this is dest
        self.b = b

        ## label on the middle of the edge
        self.label = label

        ## label on the a side of the edge
        self.alabel = alabel

        ## label on the b side of the edge
        self.blabel = blabel

        ## style of the edge
        self.style = style

class Graph(Printable):
    """!
    @brief a graph.
    """

    name: str
    directed: bool
    vertices: Dict[str, Vertex]
    edges: List[Edge]

    def __init__(self, name: str, directed: bool):
        """!
        @brief Graph constructor.

        @param name name.
        @param directed directed graph?
        """

        ## name of the graph.
        self.name = name

        ## directed graph?
        self.directed = directed

        ## list of vertices
        self.vertices = {}

        ## list of edges
        self.edges = []

    def copy(self, graph: Graph):
        """!
        @brief Copy all edges, vertices from another graph.

        @param graph graph to copy from
        """

        self.edges += deepcopy(graph.edges)
        self.vertices.update(deepcopy(graph.vertices))

    def addVertex(self, name: str, group: str = None, shape: str = 'ellipse'):
        """!
        @brief add a new node.
        
        @param name name of the node.
        @param group (optional) name of the culster.
        @param shape (optional) shape of the vertex.

        @throws AssertionError if vertex already exist.
        """
        assert not self.hasVertex(name, group), '{}: vertex with name {} already exist.'.format(self.name, name)
        v = Vertex(name, group, shape)
        self.vertices[v.getId()] = v

    def hasVertex(self, name: str, group: str = None):
        """!
        @brief Test if a vertex exists.

        @todo 

        @returns True if exist.
        """
        return Vertex(name, group).getId() in self.vertices

    def __findVertex(self, name: str, group: str = None):
        if self.hasVertex(name, group):
            return self.vertices[Vertex(name, group).getId()]
        assert group == None, '{}: {}::{} is not a vertex.'.format(self.name, group, name)
        for v in self.vertices.values():
            if v.name == name: return v
        assert False, '{}: {}::{} is not a vertex.'.format(self.name, group, name)

    def addEdge(self, a: str, b: str, agroup: str = None, bgroup: str = None, label: str = None, alabel: str = None, blabel: str = None, style: str = 'solid'):
        """!
        @brief add a new edge
        @throws AssertionError if vertex a or b does not exist.
        """
        self.edges.append(Edge(self.__findVertex(a, agroup).getId(), self.__findVertex(b, bgroup).getId(), label, alabel, blabel, style))

    def hasEdge(self, a: str, b: str):
        """!
        @brief Test if an edge exists.

        @returns True if exist.
        """
        pass

    def toGraphviz(self) -> str:
        """!
        @brief Convert graph to graphviz dot format.

        @todo todo

        @returns graphviz source.
        """
        out = '{} "{}" {{\n'.format('digraph' if self.directed else 'graph', self.name)
        vlines = []
        cluster_vlines = {}
        indent = 4

        out += ' ' * indent
        out += 'label = "{}"\n'.format(self.name)

        for v in self.vertices.values():
            options = ' '
            if v.name != None: options += 'label="{}" '.format(v.name)
            if v.shape != None: options += 'shape="{}" '.format(v.shape)
            vline = '"{}" [{}]\n'.format(v.getId(), options)
            
            if v.group != None:
                if v.group not in cluster_vlines: cluster_vlines[v.group] = []
                cluster_vlines[v.group].append(vline)
            else: vlines.append(vline)

        for line in vlines:
            out += ' ' * indent
            out += line
        
        cluster_id = 0
        for (l, c) in cluster_vlines.items():
            out += ' ' * indent
            out += 'subgraph cluster_{} {{\n'.format(cluster_id)
            indent += 4

            out += ' ' * indent
            out += 'label = "{}"\n'.format(l)

            for line in c:
                out += ' ' * indent
                out += line

            indent -= 4
            out += ' ' * indent
            out += '}\n'

            cluster_id += 1


        for e in self.edges:
            out += ' ' * indent
            options = ' '
            if e.label != None: options += 'label="{}" '.format(e.label)
            if e.alabel != None: options += 'taillabel="{}" '.format(e.alabel)
            if e.blabel != None: options += 'headlabel="{}" '.format(e.blabel)
            if e.style != None: options += 'style="{}" '.format(e.style)
            out += '"{}" {} "{}" [{}]\n'.format(e.a, '->' if self.directed else '--', e.b, options)

        out += '}'

        return out


    def print(self, indent: int) -> str:
        out = ' ' * indent
        out += 'Graph "{}":\n'.format(self.name)

        indent += 4
        out += ' ' * indent
        out += 'Vertices:\n'

        indent += 4
        for v in self.vertices.values():
            out += ' ' * indent
            out += '"{}", group "{}"\n'.format(v.name, v.group)

        indent -= 4
        out += ' ' * indent
        out += 'Edges:\n'

        indent += 4
        for e in self.edges:
            out += ' ' * indent
            out += '"{}" {} "{}"\n'.format(e.a, '->' if self.directed else '--', e.b)

        return out

class Graphable(Registrable):
    """!
    @brief Graphable. All layers that can produce graphs will have this
    prototype.
    """

    __graphs: Dict[str, Graph]
    __graphs_created: bool
    _n_graphs = 0

    def __init__(self):
        """!
        @brief Graphable constructor.
        """
        self.__graphs = {}
        self.__graphs_created = False

    def _addGraph(self, name: str, directed: bool) -> Graph:
        """!
        @brief create a new graph. This is to be called by internal classes to
        create graph. If a graph already exists, it will be returned.

        @return newly created graph.
        @throws AssertionError if graph already exist.
        """
        if name in self.__graphs: return self.__graphs[name]
        g = Graph(name, directed)
        self.__graphs[name] = g
        return g
    
    def getName(self) -> str:
        """!
        @brief Get name of this graph provider.
        """
        raise NotImplementedError('getName not implemented.')

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

    def _doCreateGraphs(self, emulator: Emulator):
        """!
        @brief handle graph creation, should be implemented by all graphable
        classes.

        @param emulator emulator object.
        """
        raise NotImplementedError('_doCreateGraphs not implemented.')

    def createGraphs(self, emulator: Emulator):
        """!
        @brief Create graphs.

        @param emulator emulator object.

        Call this method to ask the class to create graphs.
        """
        assert emulator.rendered(), 'Simulation needs to be redered before graphs can be created.'
        reg = emulator.getRegistry()
        reg.register('seedemu', 'graph', str(len(reg.getByType('seedemu', 'graph'))), self)
        if self.__graphs_created: return
        self._doCreateGraphs(emulator)
        self.__graphs_created = True