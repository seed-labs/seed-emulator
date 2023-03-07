from .DockerPreBuiltImage import DockerPreBuiltImage


class UbuntuImage(DockerPreBuiltImage):
    @property
    def _base_image(self):
        return "ubuntu:20.04"

    @property
    def _software(self) -> set:
        """!
        brief get the installed software if using a pre-built image.
        """
        return set({})
    
    @property
    def _subset(self) -> DockerPreBuiltImage:
        """!
        brief
        """
        return None