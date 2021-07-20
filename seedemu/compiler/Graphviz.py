from seedemu.core import Emulator, Compiler, Registry, ScopedRegistry, Node, Graphable

class Graphviz(Compiler):
    """!
    @brief Get all graphable object and graph them.

    """

    def __slugify(self, filename):
        return ''.join([c for c in filename if c.isalpha() or c.isdigit() or c == ' ']).rstrip()

    def getName(self) -> str:
        return 'Graphviz'

    def _doCompile(self, emulator: Emulator):
        reg = emulator.getRegistry()
        self._log('collecting graphs in the emulator...')

        for obj in list(reg.getAll().values()):
            cg = getattr(obj, 'createGraphs', None)

            if not callable(cg): continue

            graphs: Graphable = obj

            graphs.createGraphs(emulator)
            for graph in graphs.getGraphs().values():
                self._log('found graph: {}'.format(graph.name))
                print(graph.toGraphviz(), file=open('{}.dot'.format(self.__slugify(graph.name)), 'w'))