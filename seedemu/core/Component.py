from seedemu.core import Emulator
from typing import List

class Component(object):
    """!
    @brief Component interface.
    """

    def get(self) -> Emulator:
        """!
        @brief get the emulator with component.
        """
        raise NotImplementedError('get not iImplemented.')

    def getVirtualNodes() -> List[str]:
        """!
        @brief get list of virtual nodes.
        """
        return []