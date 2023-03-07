from .DockerPreBuiltImage import DockerPreBuiltImage
from .BaseImage import BaseImage

class EthereumImage(DockerPreBuiltImage):
    @property
    def _base_image(self):
        return "handsonsecurity/seedemu-ethereum"

    @property
    def _installedSoftware(self) -> set:
        """!
        brief get the installed software if using a pre-built image.
        """
        return set({})

    @property
    def _subset(self) -> DockerPreBuiltImage:
        """!
        brief
        """
        return BaseImage()