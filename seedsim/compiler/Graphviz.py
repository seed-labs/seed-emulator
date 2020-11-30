from .Compiler import Compiler
from seedsim.core import ScopedRegistry, Node, Graphable
from typing import Dict
from unicodedata import normalize
import re


class Graphviz(Compiler):
    """!
    @brief Get all graphable object and graph them.

    """

    def __slugify(self, filename):
        return ''.join([c for c in filename if c.isalpha() or c.isdigit() or c == ' ']).rstrip()

    def getName(self) -> str:
        return 'Graphviz'

    def _doCompile(self):
        reg = ScopedRegistry('seedsim')
        for obj in reg.getByType('graph'):
            graphs: Graphable = obj
            graphs.createGraphs()
            for graph in graphs.getGraphs().values():
                print(graph.toGraphviz(), file=open('{}.dot'.format(self.__slugify(graph.name)), 'w'))