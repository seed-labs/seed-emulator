#!/usr/bin/env python
# encoding: utf-8
# __author__ = 'Demon'
from ..Service import Service, Server
from seedsim.core import Node
from typing import Dict
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

    __port: int

    def __init__(self):
        """!
        @brief DomainRegistrarServer constructor.

        @param node node.
        """
        self.__port = 80

    def setPort(self, port: int):
        """!
        @brief Set HTTP port.

        @param port port.
        """
        ## ! todo
        self.__port = port

    def install(self, node: Node):
        """!
        @brief Install the service.
        """
        node.addSoftware('nginx-light php7.4-fpm')
        node.setFile('/var/www/html/index.php', DomainRegistrarServerFileTemplates['web_app_file'])
        node.setFile('/var/www/html/domain.php', DomainRegistrarServerFileTemplates['web_app_file2'])
        node.setFile('/etc/nginx/sites-available/default', DomainRegistrarServerFileTemplates['nginx_site'].format(port = self.__port))
        node.appendStartCommand('service nginx start')
        node.appendStartCommand('service php7.4-fpm start')

    def print(self, indent: int) -> str:
        out = ' ' * indent
        out += 'DomainRegistrarServer\n'

        return out

class DomainRegistrarService(Service):
    """!
    @brief The DomainRegistrarService class.
    """

    def __init__(self):
        """!
        @brief DomainRegistrarService constructor.
        """
        super().__init__()
        self.addDependency('Base', False, False)

    def getName(self) -> str:
        return 'DomainRegistrarService'

    def _createServer(self) -> DomainRegistrarServer:
        return DomainRegistrarServer()

    def _doConfigure(self, node: Node, server: Server):
        assert node.getAttribute('__domain_name_service_server') != None, 'DomainNameService required on node to use DomainRegistrarService.'

    def print(self, indent: int) -> str:
        out = ' ' * indent
        out += 'DomainRegistrarService\n'

        return out