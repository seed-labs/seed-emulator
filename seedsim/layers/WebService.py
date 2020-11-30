from .Service import Service, Server
from seedsim.core import Node
from seedsim.core.enums import NodeRole
from typing import List, Dict

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

    __node: Node
    __port: int
    __index: str

    def __init__(self, node: Node):
        """!
        @brief WebServer constructor.

        @param node node.
        """
        asn = node.getAsn()
        self.__node = node
        self.__port = 80
        self.__index = '<h1>Web Server node {} at AS{}</h1>'.format(node.getName(), node.getAsn())
        

    def setPort(self, port: int):
        """!
        @brief Set HTTP port.

        @param port port.
        """
        ## ! todo
        self.__port = port

    def setIndexContent(self, content: str):
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
        self.__node.setFile('/var/www/html/index.html', self.__index)
        self.__node.setFile('/etc/nginx/sites-available/default', WebServerFileTemplates['nginx_site'].format(port = self.__port))
        self.__node.addStartCommand('service nginx start')
        
    def print(self, indent: int) -> str:
        out = ' ' * indent
        out += 'Server: as{}/{}\n'.format(self.__node.getAsn(), self.__node.getName())

        return out

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
        server: WebServer = node.getAttribute('__web_service_server')
        if server != None: return server
        server = WebServer(node)
        self.__servers.append(server)
        node.setAttribute('__web_service_server', server)
        return server

    def onRender(self):
        for server in self.__servers:
            server.install()

    def print(self, indent: int) -> str:
        out = ' ' * indent
        out += 'WebServiceLayer:\n'

        indent += 4
        out += ' ' * indent

        out += 'Installed Nodes:\n'
 
        for server in self.__servers:
            out += server.print(indent + 4) 

        return out       