from typing import List
from seedsim.core import Printable, Registrable
from sys import stderr

class Layer(Printable, Registrable):
    """!
    @brief The layer interface.
    """

    def getName(self) -> str:
        """!
        @brief Get name of this layer.

        This method should return a unique name for this layer. This will be
        used by the renderer to resolve dependencies relationships.

        @returns name of the layer.
        """
        raise NotImplementedError('getName not implemented')

    def getDependencies(self) -> List[str]:
        """!
        @brief Get a list of names of dependencies layers.

        @returns list of names of layers.
        """
        raise NotImplementedError('getDependencies not implemented')

    def onRender(self) -> None:
        """!
        @brief Handle rendering.
        """
        raise NotImplementedError('onRender not implemented')

    def _log(self, message: str) -> None:
        """!
        @brief Log to stderr.
        """
        print("==== {}Layer: {}".format(self.getName(), message), file=stderr)
