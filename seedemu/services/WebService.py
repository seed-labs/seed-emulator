from __future__ import annotations
from seedemu.core import Node, Service, Server
from typing import Dict, List

from .CAService import CAServer

WebServerFileTemplates: Dict[str, str] = {}

WebServerFileTemplates['nginx_site'] = '''\
server {{
    listen {port};
    root /var/www/html;
    index index.html;
    server_name {serverName};
    location / {{
        try_files $uri $uri/ =404;
    }}
}}
'''

class WebServer(Server):
    """!
    @brief The WebServer class.
    """

    __port: int
    __index: str

    def __init__(self):
        """!
        @brief WebServer constructor.
        """
        super().__init__()
        self.__port = 80
        self._server_name = ['_']
        self.__index = '<h1>{nodeName} at {asn}</h1>'
        self.__enable_https = False
        self.__enable_https_func = None
        

    def setPort(self, port: int) -> WebServer:
        """!
        @brief Set HTTP port.

        @param port port.

        @returns self, for chaining API calls.
        """
        self.__port = port

        return self

    def setIndexContent(self, content: str) -> WebServer:
        """!
        @brief Set content of index.html.

        @param content content. {nodeName} and {asn} are available and will be
        filled in.

        @returns self, for chaining API calls.
        """
        self.__index = content

        return self
    
    def setServerNames(self, serverNames: List[str]) -> WebServer:
        """!
        @brief Set server names.

        @param serverNames list of server names.

        @returns self, for chaining API calls.
        """
        self._server_name = serverNames

        return self
    
    def setCAServer(self, ca: CAServer) -> WebServer:
        """!
        @brief Get certificates from a particular CA server.

        @param ca CA server.

        @returns self, for chaining API calls.
        """
        self.__enable_https_func = ca.enableHTTPSFunc
        return self
    
    def enableHTTPS(self) -> WebServer:
        """!
        @brief Enable TLS.

        @returns self, for chaining API calls.
        """
        self.__enable_https = True
        return self
    
    def install(self, node: Node):
        """!
        @brief Install the service.
        """
        node.addSoftware('nginx-light')
        node.setFile('/var/www/html/index.html', self.__index.format(asn = node.getAsn(), nodeName = node.getName()))
        node.setFile('/etc/nginx/sites-available/default', WebServerFileTemplates['nginx_site'].format(port = self.__port, serverName = ' '.join(self._server_name)))
        node.appendStartCommand('service nginx start')
        node.appendClassName("WebService")
        if self.__enable_https:
            self.__enable_https_func(node, self)

    def print(self, indent: int) -> str:
        out = ' ' * indent
        out += 'Web server object.\n'

        return out

class WebService(Service):
    """!
    @brief The WebService class.
    """

    def __init__(self):
        """!
        @brief WebService constructor.
        """
        super().__init__()
        self.addDependency('Base', False, False)
        self.addDependency('Routing', False, False)

    def _createServer(self) -> Server:
        return WebServer()

    def getName(self) -> str:
        return 'WebService'

    def print(self, indent: int) -> str:
        out = ' ' * indent
        out += 'WebServiceLayer\n'

        return out