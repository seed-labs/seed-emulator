from __future__ import annotations
from .Merger import Merger
from .Registry import Registry
from seedsim.layers import Layer
from typing import List

class Simulator:

    __reg: Registry
    __rendered: bool

    def __init__(self):
        self.__rendered = false
        self.__reg = Registry()

    def addLayer(self, layer: Layer):
         """!
        @brief Add a layer.

        @param layer layer to add.
        @throws AssertionError if layer already exist.
        """

        lname = layer.getName()
        assert lname not in self.__layers, 'layer {} already added.'.format(lname)
        self.__reg.register('seedsim', 'layer', lname, layer)

    def getLayer(self, layerName: str) -> Layer:
        self.__reg.get('seedsim', 'layer', layerName)

    def render()
        raise NotImplementedError('todo')

    def removeLayer(self, layerName: str) -> bool:
        raise NotImplementedError('todo')

    def merge(self, other: Simulator, mergers: List[Merger]) -> Simulator
        raise NotImplementedError('todo')

    def export(self, fileName: str):
        raise NotImplementedError('todo')

    def import(self, fileName: str):
        raise NotImplementedError('todo')
