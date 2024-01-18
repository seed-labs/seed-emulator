from __future__ import annotations
from typing import Dict
import re

from  seedemu.core.enums import NodeRole, NetworkType
from seedemu.core import Node, Server, Service, Emulator, Network
from typing import List, Tuple, Dict


ServerTemplates: Dict[str, str] = {}

# create tunnel where the container waits for you to attach
#RUN TUNNEL_URL="$(/home/root/code tunnel --accept-server-license-terms --name $CONTAINER_NAME)" && echo "export TUNNEL_URL=$TUNNEL_URL" >> /etc/profile
#echo "CODE_TUNNEL_URL= $TUNNEL_URL"
ServerTemplates['command'] = """

echo "development container started on: $HOSTNAME $CONTAINER_NAME"
"""

ServerTemplates['repo'] = """
RUN git clone {repourl} -b {branch} {dir}
VOLUME {dir}
"""

ServerTemplates['build'] = """

RUN wget -qO- "https://github.com/Kitware/CMake/releases/download/v3.28.1/cmake-3.28.1-linux-x86_64.tar.gz" | \
  tar --strip-components=1 -xz -C /usr/local && export PATH=$PATH:/usr/local/bin
RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y 
RUN export PATH=$PATH:~/.cargo/bin
RUN ~/.cargo/bin/rustup default nightly
RUN wget -O- "https://go.dev/dl/go1.21.5.linux-amd64.tar.gz" --connect-timeout 0.1 seconds | tar  -xz -C /usr/local && echo "export PATH=$PATH:/usr/local/go/bin" >> /etc/profile 
RUN export PATH=$PATH:/usr/local/go/bin && go install -v golang.org/x/tools/gopls@latest
RUN export PATH=$PATH:/usr/local/go/bin && go install -v github.com/go-delve/delve/cmd/dlv@latest
RUN ~/.cargo/bin/cargo install cargo-deb
RUN mkdir /home/root

# install VSCode CLI
#RUN curl -Lk 'https://code.visualstudio.com/sha/download?build=stable&os=cli-alpine-x64' --output /home/root/vscodecli.tar.gz 
#RUN cd /home/root/ && tar -xf vscodecli.tar.gz
#https://go.microsoft.com/fwlink/?LinkID=760868

#doesnt seem to work quite yet - attachment to container is just as fast as if this line is commented out :/
RUN curl -Lk 'https://code.visualstudio.com/sha/download?build=stable&os=linux-deb-x64'  --output /home/root/vscode.deb && apt install /home/root/vscode.deb -y

{extensions}
"""

class DevServer(Server):
    """!
    @brief installs stuff in the container that is required to use it for remote development
    """

    __id: int
    # maybe add custom build command here and custom software
    #[( dir-to-clone-into, branch-to-checkout, repo-url )]  
    __repos: [(str,str,str)]
    #  repos that have to be checked out will most likely vary by node 
    # and so do the software stacks required for each project
    
    # VSCode extensions that shall be installed in the service
    __vscode_extensions: [str]
    
    def checkoutRepo(self, url: str, path: str, branch: str ):
        """!
        @brief  checks out the git repository with the given URL and branch in a Docker Volume
        @param path an absolute path to the directory where you want the repo to reside in the container
        """

        self.__repos.append( (url,path,branch) )

        return self
    
    def __init__(self, id: int):
        """!
        @brief constructor.
        """
        super().__init__()
        self.__id = id
        self.__vscode_extensions = []
        self.__repos = []
      
    def addVSCodeExtension(self, ext: str):
        self.__vscode_extensions.append(ext)
        return self
    
    def getVSCodeExtensions(self):
        return self.__vscode_extensions

    def install(self, node: Node):
        """!
        @brief Install the service.
        """
         # Developing Software requires Internet connection for i.e. git, go get, cargo build, pip install etc. ..
        node.requestReachOutside()
              
        node.addSoftware("wget curl git build-essential clang gpg")
  
        extens = ''
        for e in self.getVSCodeExtensions():
            extens += 'RUN code --no-sandbox --user-data-dir /home/root/.vscode --install-extension %s\n' % e
        # code doesnt like to be run as super user -> maybe useradd here ?!
        # if only vscode cli is installed gives error: 
        #   No installation of Visual Studio Code stable was found.
        #   Install it from your system's package manager or https://code.visualstudio.com, restart your shell, and try again. 
        #   f you already installed Visual Studio Code and we didn't detect it, run `code version use stable --install-dir /path/to/installation`

        node.addDockerCommand(ServerTemplates['build'].format(extensions=extens))

        for (u,p,b) in self.__repos:
            node.addDockerCommand(ServerTemplates['repo'].format(repourl = u, branch=b, dir=p       ) )

       
        node.setCustomEnv("- TESTVAR={}".format(node.getName() ) )

        node.appendStartCommand(ServerTemplates['command'])
        node.appendClassName("DevServer")

    def print(self, indent: int) -> str:
        out = ' ' * indent
        out += 'DevServer.\n'
        return out


class ContainerDevelopmentService(Service):
    """!
    @brief Container Development service class.
    """
    __dev_cnt: int =0   
    __server: List[str] = []
    candidates = set()

    def __init__(self): 
        """!
        @brief 
        """
        super().__init__()

        self.addDependency('Base', False, False)     
        self.addDependency('Scion', False, True)    

    def _createServer(self) -> Server:    
        d = DevServer(self.__dev_cnt)
        ContainerDevelopmentService.__dev_cnt += 1 
        return d
    
    def install(self, vnode: str) -> Server:

        ContainerDevelopmentService.__server.append(vnode)

        return super().install(vnode)

    def configure(self, emulator: Emulator):

        # for all vnodes in self.__server find their local net/s  , uniqueify them
        # find of all the associated nodes with the net the routers
        # and finally create custom bridge DockerNetworks and register them 
        # with the emulators registry in order for them to be retrieved by the DockerRenderer later on

        
 
        grouped_candidates =dict() # routers grouped by their net 
        # ideally there is for each local net, which contains at least one host with a DevService configured
        # exactly one Router which is also the hosts default gateway

        # ATTENTION: this means names of virtual hosts with DevServices must be globally unique :| !!
        for vnode in self.__server:
            pnode = emulator.getBindingFor(vnode) # or resolvVnode(vnode) ?!

            if pnode.getRole() == NodeRole.Router:
                ContainerDevelopmentService.candidates.add(pnode)
                continue

            allnets: set(Network)= set()
            for inf in pnode.getInterfaces():
                net = inf.getNet()
                # in theorie a DevService could also be installed on a router node
                # which might only be connected to networks of type other-than 'Local'
                # but this is handled above
                if net.getType() == NetworkType.Local:
                    if net in allnets:
                        print("multihomed host: %s" % vnode )
                    
                    allnets.add( net)
            for  net in allnets:
                for node in net.getAssociations():
                    if node.getRole() == NodeRole.Router:
                        if net in grouped_candidates:
                            grouped_candidates[net].add(node)
                        else:
                            grouped_candidates[net]=set([node])
                        ContainerDevelopmentService.candidates.add(node)

            # mark the router as external connected and allocate a bridge-id
            # but do not create one yet 
            for c in ContainerDevelopmentService.candidates:
                c.setConnectedExternal()

        super().configure(emulator)
        
    def getName(self) -> str:
        return 'ContainerDevelopmentService'

    def print(self, indent: int) -> str:
        out = ' ' * indent
        out += 'ContainerDevelopmentService\n'
        return out

"""
USAGE:

devsvc = ContainerDevelopmentService()

...
as150.createHost('node150_0').joinNetwork('net0', address='10.150.0.30')

devsvc.install('dev150_0').checkoutRepo(url= "https://github.com/your-username/your-project.git", dir="/home/root/pan",branch="awesome-feature").addVSCodeExtension('golang.Go')

"""