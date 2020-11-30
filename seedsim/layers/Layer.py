from typing import List, Dict, Tuple
from seedsim.core import Printable, Registrable
from sys import stderr
from enum import Enum


class Layer(Printable, Registrable):
    """!
    @brief The layer interface.
    """

    dependencies: Dict[str, List[Tuple[str, bool]]] = {}

    def addDependency(self, layerName: str, reverse: bool, optional: bool):
        """!
        @brief add layer dependency.

        @param layerName name of the layer.
        @param reverse add as reverse dependency. Regular dependency requires
        the given layer to be rendered before the current layer. Reverse
        dependency requires the given layer to be rendered after the current
        layer. 
        @param optional continue render even if the given layer does not exist.
        Does not work for reverse dependencies.
        """

        _current = layerName if reverse else self.getName()
        _target = self.getName() if reverse else layerName

        if _current not in self.dependencies:
            self.dependencies[_current] = []

        self.dependencies[_current].append((_target, optional))

    def getName(self) -> str:
        """!
        @brief Get name of this layer.

        This method should return a unique name for this layer. This will be
        used by the renderer to resolve dependencies relationships.

        @returns name of the layer.
        """
        raise NotImplementedError('getName not implemented')

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
