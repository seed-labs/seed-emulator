from DockerPreBuiltImage import DockerPreBuiltImage
from seedemu.docker.BaseImage import BaseImage

class RouterImage(DockerPreBuiltImage):
    @property
    def _base_image(self):
        return "handsonsecurity/seedemu-router"

    @property
    def _installedSoftware(self) -> set:
        """!
        brief get the installed software if using a pre-built image.
        """
        return set({"bird2"})
    
    @property
    def _subset(self) -> DockerPreBuiltImage:
        """!
        brief
        """
        return BaseImage()