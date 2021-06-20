#!/usr/bin/env python
# encoding: utf-8
# __author__ = 'Demon'
from seedemu.core import Node, Service, Server
from typing import Dict

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
DomainRegistrarServerFileTemplates['web_app_file'] = '''\
<!doctype html>
<html lang="en">
  <head>
    <!-- Required meta tags -->
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1, shrink-to-fit=no">

    <!-- Bootstrap CSS -->
    <link rel="stylesheet" href="https://stackpath.bootstrapcdn.com/bootstrap/4.1.3/css/bootstrap.min.css" integrity="sha384-MCw98/SFnGE8fJT3GXwEOngsV7Zt27NXFoaoApmYm81iuXoPkFOJwJ8ERdknLPMO" crossorigin="anonymous">

    <title>Domain Registrar Service</title>
  </head>
  <body>
    <h1>Domain Registrar Service</h1>
    <!-- Optional JavaScript -->
    <!-- jQuery first, then Popper.js, then Bootstrap JS -->
    <script src="https://code.jquery.com/jquery-3.3.1.slim.min.js" integrity="sha384-q8i/X+965DzO0rT7abK41JStQIAqVgRVzpbzo5smXKp4YfRvH+8abtTE1Pi6jizo" crossorigin="anonymous"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/popper.js/1.14.3/umd/popper.min.js" integrity="sha384-ZMP7rVo3mIykV+2+9J3UJ46jBk0WLaUAdn689aCwoqbBJiSnjAK/l8WvCWPIPm49" crossorigin="anonymous"></script>
    <script src="https://stackpath.bootstrapcdn.com/bootstrap/4.1.3/js/bootstrap.min.js" integrity="sha384-ChfqqxuZUCnJSK3+MXmPNIyE6ZbWh2IMqE241rYiqJxyMiZ6OW/JmZQ5stwEULTy" crossorigin="anonymous"></script>



    <div class="card text-center">
      <div class="card-header">
        <ul class="nav nav-tabs card-header-tabs">
          <li class="nav-item">
            <a class="nav-link active" href="#">Buy new domain</a>
          </li>
          <li class="nav-item">
            <a class="nav-link" href="#">Link</a>
          </li>
        </ul>
      </div>
      <div class="card-body">
        <form action="domain.php" method="GET">
          <h5 class="card-title">Input the domain you want to buy</h5>
              <div class="input-group mb-16">
                <input type="text" class="form-control" name="dname" id="dname" placeholder="google">
                <div class="input-group-append">
                  <span class="input-group-text" id="basic-addon2">.com</span>
                </div>
              </div>
              <br />
          <button type="submit" class="btn btn-primary">Buy!</button>
        </form>
      </div>
    </div>
  </body>
</html>
'''

DomainRegistrarServerFileTemplates['web_app_file2'] = '''\
<!doctype html>
<html lang="en">
  <head>
    <!-- Required meta tags -->
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1, shrink-to-fit=no">

    <!-- Bootstrap CSS -->
    <link rel="stylesheet" href="https://stackpath.bootstrapcdn.com/bootstrap/4.1.3/css/bootstrap.min.css" integrity="sha384-MCw98/SFnGE8fJT3GXwEOngsV7Zt27NXFoaoApmYm81iuXoPkFOJwJ8ERdknLPMO" crossorigin="anonymous">

    <title>Domain Registrar Service</title>
  </head>
  <body>
    <h1>Domain Registrar Service</h1>
    <!-- Optional JavaScript -->
    <!-- jQuery first, then Popper.js, then Bootstrap JS -->
    <script src="https://code.jquery.com/jquery-3.3.1.slim.min.js" integrity="sha384-q8i/X+965DzO0rT7abK41JStQIAqVgRVzpbzo5smXKp4YfRvH+8abtTE1Pi6jizo" crossorigin="anonymous"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/popper.js/1.14.3/umd/popper.min.js" integrity="sha384-ZMP7rVo3mIykV+2+9J3UJ46jBk0WLaUAdn689aCwoqbBJiSnjAK/l8WvCWPIPm49" crossorigin="anonymous"></script>
    <script src="https://stackpath.bootstrapcdn.com/bootstrap/4.1.3/js/bootstrap.min.js" integrity="sha384-ChfqqxuZUCnJSK3+MXmPNIyE6ZbWh2IMqE241rYiqJxyMiZ6OW/JmZQ5stwEULTy" crossorigin="anonymous"></script>



    <div class="card text-center">
      <div class="card-header">
        <ul class="nav nav-tabs card-header-tabs">
          <li class="nav-item">
            <a class="nav-link active" href="#"><?php echo $_GET['dname']; ?></a>
          </li>
        </ul>
      </div>
      <div class="card-body">
        <form action="domain.php?dname=<?php echo $_GET['dname']; ?>" method="POST">
          <h5 class="card-title">Add resolve record</h5>
              <table class="table table-bordered">
                <thead>
                  <tr>
                    <th scope="col">Host Record</th>
                    <th scope="col">Record Type</th>
                    <th scope="col">Record value</th>
                    <th scope="col">TTL</th>
                  </tr>
                </thead>
                <tbody>
                  <tr>
                    <th scope="row"><input type="text" class="form-control" name="dname" value="<?php echo $_GET['dname']; ?>" readonly></th>
                    <td>A</td>
                    <td><input type="text" class="form-control" name="dvalue" placeholder="IP address"></td>
                    <td>10</td>
                  </tr>
                </tbody>
              </table>
          <button type="submit" class="btn btn-primary">Submit</button>
        </form>
      </div>
    </div>
  </body>
</html>
<?php
if(!empty($_POST['dname']) && !empty($_POST['dvalue']) ){
  $domain_name = $_POST['dname'];
  $ip_address = $_POST['dvalue'];
  $register_command = 'echo "update add '.$domain_name.'.com 60 A '.$ip_address.'\nsend\n" | nsupdate';
  $escaped_command = escapeshellcmd($register_command);
  system($escaped_command);

  echo "<script>alert('success on adding record!');window.history.back();</script>";

}

?>
'''

class DomainRegistrarServer(Server):
    """!
    @brief The DomainRegistrarServer class.

    FIXME requires internet to work. what if the emulation is not connected to the internet.
    FIXME need to work on non-TLD server. consider nsupdate and use some sort of way to "attach" to TLD servers.
    FIXME don't install this on TLD server. see last FIXME too.
    """

    __port: int

    def __init__(self):
        """!
        @brief DomainRegistrarServer constructor.
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
        node.addSoftware('nginx-light php7.4-fpm') # Install nginx and php
        node.setFile('/var/www/html/index.php', DomainRegistrarServerFileTemplates['web_app_file']) #index page for domain register service
        node.setFile('/var/www/html/domain.php', DomainRegistrarServerFileTemplates['web_app_file2']) # domain names register page.
        node.setFile('/etc/nginx/sites-available/default', DomainRegistrarServerFileTemplates['nginx_site'].format(port = self.__port)) # setup nginx
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
        # In order to identify if the target node has DomainNameService.
        assert "DomainNameService" in node.getAttribute('services') , 'DomainNameService required on node to use DomainRegistrarService.'

    def print(self, indent: int) -> str:
        out = ' ' * indent
        out += 'DomainRegistrarService\n'

        return out