from seedsim.core import Simulator
from typing import List

class Component(object):
    """!
    @brief Component interface.
    """

    def get(self) -> Simulator:
        """!
        @brief get the simulator with component.
        """
        raise NotImplementedError('get not iImplemented.')

    def getVirtualNodes() -> List[str]:
        """!
        @brief get list of virtual nodes.
        """
        return []