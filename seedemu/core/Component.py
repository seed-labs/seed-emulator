from seedemu.core import Emulator
from typing import List

class Component(object):
    """!
    @brief Component interface.
    """

    def __init__(self) -> None:
        super().__init__()

    def get(self) -> Emulator:
        """!
        @brief get the emulator with component.
        """
        raise NotImplementedError('get not iImplemented.')

    def getVirtualNodes(self) -> List[str]:
        """!
        @brief get list of virtual nodes.
        """
        return []