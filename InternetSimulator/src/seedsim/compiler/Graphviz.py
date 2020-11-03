from .Compiler import Compiler
from seedsim.core import Registry, Node
from typing import Dict

class Graphviz(Compiler):
    """!
    @brief Compile the simulation topology to graphviz graph.

    @todo This should output the followings:
    - Physical connection (entire simulation)
    - Physical connection (one for each AS)
    - eBGP peerings (entire simulation)
    - iBGP peerings (one for each AS)
    - IX-level peering (one each IX)
    """

    __ip_node: Dict[str, Node] # ip to node mapping

    def getName(self) -> str:
        return 'Graphviz'

    def _doCompile(self, registry: Registry):

