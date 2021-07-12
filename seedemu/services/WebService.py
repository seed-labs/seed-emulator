from __future__ import annotations
from seedemu.core import Node, Service, Server
from typing import Dict

WebServerFileTemplates: Dict[str, str] = {}

WebServerFileTemplates['nginx_site'] = '''\
server {{
    listen {port};
    root /var/www/html;
    index index.html;
    server_name _;
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
        self.__port = 80
        self.__index = '<h1>{nodeName} at {asn}</h1>'
        

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

        @param content content. {nodeName} and {asn} are avalaible and will be
        filled in.

        @returns self, for chaining API calls.
        """
        self.__index = content

        return self
    
    def install(self, node: Node):
        """!
        @brief Install the service.
        """
        node.addSoftware('nginx-light')
        node.setFile('/var/www/html/index.html', self.__index.format(asn = node.getAsn(), nodeName = node.getName()))
        node.setFile('/etc/nginx/sites-available/default', WebServerFileTemplates['nginx_site'].format(port = self.__port))
        node.appendStartCommand('service nginx start')
        
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

    def _createServer(self) -> Server:
        return WebServer()

    def getName(self) -> str:
        return 'WebService'

    def print(self, indent: int) -> str:
        out = ' ' * indent
        out += 'WebServiceLayer\n'

        return out