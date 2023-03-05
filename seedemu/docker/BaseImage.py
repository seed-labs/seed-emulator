from DockerPreBuiltImage import DockerPreBuiltImage
from seedemu.docker.UbuntuImage import UbuntuImage

class BaseImage(DockerPreBuiltImage):
    @property
    def _base_image(self):
        return "handsonsecurity/seedemu-host"

    @property
    def _installedSoftware(self) -> set:
        """!
        brief get the installed software if using a pre-built image.
        """
        return set({'zsh', 'curl', 'nano', 'vim-nox', 'mtr-tiny', 'iproute2',
                    'iputils-ping', 'tcpdump', 'termshark', 'dnsutils', 'jq', 'ipcalc', 'netcat'})

    @property
    def _subset(self) -> DockerPreBuiltImage:
        """!
        brief
        """
        return UbuntuImage()
