from .Layer import Layer
from seedsim.core import Node, Printable, ScopedRegistry
from seedsim.core.enums import NodeRole
from typing import Dict

class Server(Printable):
    """!
    @brief Server class.

    The Server class is the handler for installed services.
    """

class Service(Layer):
    """!
    @brief Service base class.

    The base class for all Services.
    """

    def _doInstall(self, node: Node) -> Server:
        """!
        @brief Install the service on node.

        @param node node to install the service on.
        """
        raise NotImplementedError('_doInstall not implemented')

    def _getStorage(self) -> Dict[str, object]:
        """!
        @brief Get a node-specific service storage.

        @returns dict for storage.
        """

    def installOn(self, node: Node) -> Server:
        """!
        @brief Install the service on given node.

        @param node node to install the service on.

        @returns Handler of the installed service.
        @throws AssertionError if node is not host node.
        """
        assert node.getRole() == NodeRole.Host, 'node as{}/{} is not a host node'.format(node.getAsn(), node.getName())
        servicesdb = node.getAttribute('services', {})
        m_name = self.getName()
        if m_name not in servicesdb:
            servicesdb[m_name] = {}

        return self._doInstall(node)

    def installOnAll(self, asn: int) -> Dict[int, Dict[str, Server]]:
        """!
        @brief install the service on all host nodes in the given AS.

        @param asn ASN.

        @returns Dict of Dict, the inner dict is Dict[Node name, Server] and the
        outer dict is Dict[Asn, inner Dict].
        """
        scope = ScopedRegistry(str(asn))
        for host in scope.getByType('hnode'):
            self.installOn(host)

