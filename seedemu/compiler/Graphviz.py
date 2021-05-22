from seedemu.core.Emulator import Emulator
from .Compiler import Compiler
from seedemu.core import Registry, ScopedRegistry, Node, Graphable
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

    def _doCompile(self, emulator: Emulator):
        reg = ScopedRegistry('seedemu', emulator.getRegistry())
        for obj in reg.getByType('graph'):
            graphs: Graphable = obj
            graphs.createGraphs(emulator)
            for graph in graphs.getGraphs().values():
                print(graph.toGraphviz(), file=open('{}.dot'.format(self.__slugify(graph.name)), 'w'))