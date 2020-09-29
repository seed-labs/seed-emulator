from .Service import Service, Server
from seedsim.core import Node
from seedsim.core.enums import NodeRole
from typing import List

class WebServer(Server):
    """!
    @brief The WebServer class.
    """

    __node: Node
    __port: int
    __content: str

    def __init__(self, node: Node):
        """!
        @brief WebServer constructor.

        @param node node.
        """
        asn = node.getAsn()
        self.__node = node
        self.__port = 80
        self.__content = '<h1>Web Server node {} at AS{}</h1>'.format(node.getName(), node.getAsn())
        

    def setPort(self, port: int):
        """!
        @brief Set HTTP port.

        @param port port.
        """
        self.__port = port

    def setContent(self, content: str):
        """!
        @brief Set content of index.html.

        @param content content.
        """
        self.__content = content
    
    def install(self):
        """!
        @brief Install the service.
        """
        self.__node.addSoftware('nginx-light')
        

class WebService(Service):
    """!
    @brief The WebService class.
    """

    __servers: List[WebServer]

    def __init__(self):
        """!
        @brief WebService constructor.
        """
        self.__servers = []

    def getName(self) -> str:
        return 'WebService'

    def getDependencies(self) -> List[str]:
        return ['Base']

    def _doInstall(self, node: Node) -> WebServer:
        """!
        @brief Install the web service on given node.

        @param node node to install the web service on.

        @returns Handler of the installed web service.
        @throws AssertionError if node is not host node.
        """
        pass

    def onRender(self):
        for server in self.__servers:
            server.install()
