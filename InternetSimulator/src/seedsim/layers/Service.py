from .Layer import Layer
from seedsim.core import Node, Printable, ScopedRegistry
from seedsim.core.enums import NodeRole
from typing import Dict, List

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

    def getConflicts(self) -> List[str]:
        """!
        @brief Get a list of conflicting services.

        Override to change.

        @return list of service names.
        """
        return []

    def installOn(self, node: Node) -> Server:
        """!
        @brief Install the service on given node.

        @param node node to install the service on.

        @returns Handler of the installed service.
        @throws AssertionError if node is not host node.
        """
        assert node.getRole() == NodeRole.Host, 'node as{}/{} is not a host node'.format(node.getAsn(), node.getName())
        servicesdb: Dict = node.getAttribute('services', {})

        for (name, service_info) in servicesdb.items():
            service: Service = service_info['__self']
            assert name not in self.getConflicts(), '{} conflict with {} on as{}/{}.'.format(self.getName(), service.getName(), node.getAsn(), node.getName())
            assert self.getName() not in service.getConflicts(), '{} conflict with {} on as{}/{}.'.format(self.getName(), service.getName(), node.getAsn(), node.getName())

        m_name = self.getName()
        if m_name not in servicesdb:
            servicesdb[m_name] = {
                '__self': self
            }

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

