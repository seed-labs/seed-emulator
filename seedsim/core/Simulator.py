from __future__ import annotations
from .Merger import Merger
from .Registry import Registry
from typing import List

class Simulator:

    __registry: Registry
    __rendered: bool

    def __init__(self):
        self.__rendered = False
        self.__registry = Registry()

    def addLayer(self, layer: Layer):
        """!
        @brief Add a layer.

        @param layer layer to add.
        @throws AssertionError if layer already exist.
        """

        lname = layer.getName()
        assert lname not in self.__layers, 'layer {} already added.'.format(lname)
        self.__registry.register('seedsim', 'layer', lname, layer)

    def getLayer(self, layerName: str) -> Layer:
        self.__registry.get('seedsim', 'layer', layerName)

    def render(self):
        raise NotImplementedError('todo')

    def getRegistry(self) -> Registry: 
        return self.__registry

    def removeLayer(self, layerName: str) -> bool:
        raise NotImplementedError('todo')

    def merge(self, other: Simulator, mergers: List[Merger]) -> Simulator:
        raise NotImplementedError('todo')

    def dump(self, fileName: str):
        raise NotImplementedError('todo')

    def load(self, fileName: str):
        raise NotImplementedError('todo')
