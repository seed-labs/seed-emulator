from __future__ import annotations
from .Merger import Merger
from seedsim.layers import Layer
from typing import List

class SimulatorObject(object):
    """!
    @brief base class of all simulator object.
    """

    def getTypeName(self) -> str:
        """!
        @brief Get type name of the current object. 
        """
        raise NotImplementedError("getTypeName not implemented.")

    def shouldMerge(self, other: SimulatorObject) -> bool:
        """!
        @brief Test if two object should be merged. This is called when merging
        simulator.

        @param other the other object
        """
        raise NotImplementedError("equals not implemented.")

class Simulator:

    __layers: List[Layer]

    def addLayer(self, layer: Layer):
        pass

    def getLayer(self, layerName: str) -> Layer:
        pass

    def merge(self, other: Simulator, mergers: List[Merger]) -> Simulator
        pass
