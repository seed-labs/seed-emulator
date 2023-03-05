from __future__ import annotations
from abc import ABCMeta, abstractmethod
from typing import Set, List

from seedemu.compiler import Docker

class DockerPreBuiltImage(Docker.DockerImage, metaclass=ABCMeta):
    """!
    @brief The DockerImage class.

    This class represents a candidate image for docker compiler.
    """

    def __init__(self, software: List[str]=[]) -> None:
        name = self._base_image
        not_installed_software = []
        self._allInstalledSoftware = self.getAllInstalledSoftware()
        for soft in software:
            if soft not in self._allInstalledSoftware:
                not_installed_software.append(soft)
        super().__init__(name, not_installed_software, local=False)

    @property
    @abstractmethod
    def _base_image(self):
        pass

    @property
    @abstractmethod
    def _installedSoftware(self) -> set:
        """!
        brief get the installed software if using a pre-built image.
        """

    @property
    @abstractmethod
    def _subset(self) -> DockerPreBuiltImage:
        """!
        brief
        """
    
    def getAllInstalledSoftware(self)->set:
        if self._subset == None:
            return self._installedSoftware
        else:
            return self._installedSoftware.union(self._subset.getAllInstalledSoftware())

    def addSoftwares(self, software) -> Docker.DockerImage:
        for soft in software:
            if soft not in self._allInstalledSoftware:
                self.__software.add(soft)
        return self