#!/usr/bin/env python
# encoding: utf-8
# __author__ = 'Demon'
from .. Service import Service, Server
from seedsim.core import Node
from .. DomainNameService import DomainNameServer
from typing import List, Dict
import pkgutil

DomainRegistrarServerFileTemplates: Dict[str, str] = {}

DomainRegistrarServerFileTemplates['nginx_site'] = '''\
server {{
    listen {port};
    root /var/www/html;
    index index.php index.html;
    server_name _;
    location / {{
        try_files $uri $uri/ =404;
    }}
    location ~ \.php$ {{
        include snippets/fastcgi-php.conf;
        fastcgi_pass unix:/run/php/php7.4-fpm.sock;
    }}
}}
'''
DomainRegistrarServerFileTemplates['web_app_file'] = pkgutil.get_data(__name__, 'config/index.php').decode("utf-8")
DomainRegistrarServerFileTemplates['web_app_file2'] = pkgutil.get_data(__name__, 'config/domain.php').decode("utf-8")

class DomainRegistrarServer(Server):
    """!
    @brief The DomainRegistrarServer class.
    """

    __node: Node
    __port: int
    __index: str

    def __init__(self, node: Node):
        """!
        @brief DomainRegistrarServer constructor.

        @param node node.
        """
        asn = node.getAsn()
        self.__node = node
        self.__port = 80
        self.__index = '<?php phpinfo() ?>'

    def setPort(self, port: int):
        """!
        @brief Set HTTP port.

        @param port port.
        """
        ## ! todo
        self.__port = port

    def install(self):
        """!
        @brief Install the service.
        """
        self.__node.addSoftware('nginx-light php7.4-fpm')
        self.__node.setFile('/var/www/html/index.php', DomainRegistrarServerFileTemplates['web_app_file'])
        self.__node.setFile('/var/www/html/domain.php', DomainRegistrarServerFileTemplates['web_app_file2'])
        self.__node.setFile('/etc/nginx/sites-available/default', DomainRegistrarServerFileTemplates['nginx_site'].format(port = self.__port))
        self.__node.addStartCommand('service nginx start;/etc/init.d/php7.4-fpm start')

    def print(self, indent: int) -> str:
        out = ' ' * indent
        out += 'Server: as{}/{}\n'.format(self.__node.getAsn(), self.__node.getName())

        return out

class DomainRegistrarService(Service):
    """!
    @brief The DomainRegistrarService class.
    """

    __servers: List[DomainRegistrarServer]

    def __init__(self):
        """!
        @brief DomainRegistrarService constructor.
        """
        self.__servers = []
        self.addDependency('Base', False, False)

    def getName(self) -> str:
        return 'DomainRegistrarService'

    def _doInstall(self, node: Node) -> DomainRegistrarServer:
        """!
        @brief Install the DomainRegistrar service on given node.

        @param node node to install the DomainRegistrar service on.

        @returns Handler of the installed DomainRegistrar service.
        @throws AssertionError if node is not host node.
        """
        dns_server: DomainNameServer = node.getAttribute('__domain_name_service_server')
        if dns_server == None: raise NotImplementedError('This node does not install com TLD DNS server, install it first.')



        server: DomainRegistrarServer = node.getAttribute('__domain_registrar_service_server')
        if server != None: return server
        server = DomainRegistrarServer(node)

        self.__servers.append(server)
        node.setAttribute('__domain_registrar_service_server', server)
        return server

    def onRender(self):
        for server in self.__servers:
            server.install()

    def print(self, indent: int) -> str:
        out = ' ' * indent
        out += 'DomainRegistrarService:\n'

        indent += 4
        out += ' ' * indent

        out += 'Installed Nodes:\n'

        for server in self.__servers:
            out += server.print(indent + 4)

        return out