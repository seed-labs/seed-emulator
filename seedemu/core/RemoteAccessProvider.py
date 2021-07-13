from __future__ import annotations
from sys import stderr

class RemoteAccessProvider(object):
    """!
    @brief Implements logic for provide remote access to emulated network.
    """

    def _log(self, message: str) -> None:
        """!
        @brief Log to stderr.

        @param message message.
        """
        print("==== {}RemoteAccessProvider: {}".format(self.getName(), message), file=stderr)

    def configureRemoteAccess(self, emulator: Emulator, netObject: Network, brNode: Node, brNet: Network):
        """!
        @brief configure remote access on a given network at given AS.

        @param emulator emulator object reference.
        @param netObject network object reference.
        @param brNode reference to a service node that is not part of the
        emulation. This node can be used to run software (like VPN server) for
        remote access. The configureRemoteAccess method will join the
        brNet/netObject networks. Do not join them manually on the brNode.
        @param brNet reference to a network that is not part of the emulation.
        This network will have access NAT to the real internet. 
        """
        raise NotImplementedError("configureRemoteAccess not implemented.")

    def getName(self) -> str:
        """!
        @brief Get the name of the provider.

        @returns name.
        """
        raise NotImplementedError("getName not implemented.")