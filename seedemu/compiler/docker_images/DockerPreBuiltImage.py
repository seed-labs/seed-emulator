from __future__ import annotations
from abc import ABCMeta, abstractmethod
from typing import Set, List

from seedemu.compiler import DockerImage

class DockerPreBuiltImage(DockerImage, metaclass=ABCMeta):
    """!
    @brief The DockerImage class.

    This class represents a candidate image for docker compiler.
    """

    def __init__(self, software: List[str]=[]) -> None:
        super().__init__(name=self._base_image, software=self._software, local=False, subset=self._subset)

    @property
    @abstractmethod
    def _base_image(self):
        pass

    @property
    @abstractmethod
    def _software(self) -> set:
        """!
        brief get the installed software if using a pre-built image.
        """

    @property
    @abstractmethod
    def _subset(self) -> DockerPreBuiltImage:
        """!
        brief
        """