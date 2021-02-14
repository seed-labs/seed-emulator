from .Printable import Printable
from .Registry import Registrable
from .Simulator import Simulator
from .Configurable import Configurable

from sys import stderr
from typing import Set, Dict, Tuple


class Layer(Printable, Registrable, Configurable):
    """!
    @brief The layer interface.
    """

    __dependencies: Dict[str, Set[Tuple[str, bool]]]

    def __init__(self) -> None:
        super().__init__()
        self.__dependencies = {}

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

        if _current not in self.__dependencies:
            self.__dependencies[_current] = set()

        self.__dependencies[_current].add((_target, optional))

    def getDependencies(self) -> Dict[str, Set[Tuple[str, bool]]]:
        """!
        @brief Get dependencies.

        @return dependencies.
        """

        return self.__dependencies

    def getName(self) -> str:
        """!
        @brief Get name of this layer.

        This method should return a unique name for this layer. This will be
        used by the renderer to resolve dependencies relationships.

        @returns name of the layer.
        """
        raise NotImplementedError('getName not implemented')

    def render(self, simulator: Simulator) -> None:
        """!
        @brief Handle rendering.
        """
        raise NotImplementedError('render not implemented')

    def _log(self, message: str) -> None:
        """!
        @brief Log to stderr.
        """
        print("==== {}Layer: {}".format(self.getName(), message), file=stderr)
