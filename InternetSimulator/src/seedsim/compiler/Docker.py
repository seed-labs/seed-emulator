from seedsim.core import Registry
from .Compiler import Compiler

class Docker(Compiler):
    """!
    @brief The Docker compiler class.

    Docker is one of the compiler driver. It compiles the lab to docker
    containers.
    """

    def getName(self) -> str:
        return "Docker"

    def _doCompile(self, registry: Registry):
        for ((scope, type, name), obj) in registry.getAll().items():

            if type == 'rnode':
                self._log('!! TODO: compiling router node {} for as{}'.format(name, scope))

            if type == 'hnode':
                self._log('!! TODO: compiling host node {} for as{}'.format(name, scope))

            if type == 'rs':
                self._log('!! TODO: compiling rs node for {}'.format(name))

            if type == 'net':
                self._log('!! TODO: creating network: {}/{}'.format(scope, name))
