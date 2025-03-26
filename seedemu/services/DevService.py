from __future__ import annotations
from typing import Dict
import re

from  seedemu.core.enums import NodeRole, NetworkType
from seedemu.core import Node, Server, Service, Emulator, Network, ExternalConnectivityProvider, promote_to_real_world_router
from typing import List, Tuple, Dict, Set
from enum import Enum
from  urllib.parse import urlparse,unquote
from pathlib import PurePosixPath
import os.path


ServerTemplates: Dict[str, str] = {}

ServerTemplates['command'] = """

echo "development container started on: $HOSTNAME $CONTAINER_NAME"
"""

ServerTemplates['repo'] = """
RUN git clone {repourl} -b {branch} {dir}
"""

ServerTemplates['build'] = """

RUN [ ! -d /home/root ] && mkdir -p /home/root
#doesnt seem to work quite yet - attachment to container is just as fast as if this line is commented out :/
RUN curl -Lk 'https://code.visualstudio.com/sha/download?build=stable&os=linux-deb-x64'  --output /home/root/vscode.deb && apt install /home/root/vscode.deb -y

{extensions}
"""

class AccessMode(Enum):
    """
    desired access modifier for git repo checkouts:
    either 'private' for only this DevServer/Node instance alone, in a separate named volume
    or 'shared' for multiple DevServer/Node instances using a joint checkout
    located in the same named volume, that is mounted into each of them
    """
    private="PRIVATE"
    shared="SHARED"


class DevServer(Server):
    """!
    @brief installs stuff in the container that is required to use it for remote development
    """

    __id: int
    # maybe add custom build command here and custom software
    #[( dir-to-clone-into, branch-to-checkout, repo-url, access-modifier )]
    __repos: List[(str,str,str,AccessMode)]
    #  repos that have to be checked out will most likely vary by node
    # and so do the software stacks required for each project

    # VSCode extensions that shall be installed in the service
    __vscode_extensions: List[str]

    def checkoutRepo(self, url: str, path: str, branch: str ,mode: AccessMode = AccessMode.private ):
        """!
        @brief  checks out the git repository with the given URL and branch in a Docker Volume
        @param path an absolute path to the directory where you want the repo to reside in the container
        @param mode  if you want to share the checkout(actually the containing docker volume)
          with other DevServer instances or rather have your own separate copy
          in a dedicated docker volume only mounted into this DevServer instance
        """

        self.__repos.append( (url,path,branch,mode) )

        return self

    def __init__(self,service, id: int):
        """!
        @brief constructor.
        """
        super().__init__()
        self.__service = service
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
         # Developing Software requires Internet connection
         # for i.e. git, go get, cargo build, pip install etc. ..
        # node.requestReachOutside()

        node.addSoftware("git") # wget curl build-essential clang gpg

        extens = ''
        for e in self.getVSCodeExtensions():
            extens += 'RUN code --no-sandbox --user-data-dir /home/root/.vscode --install-extension %s\n' % e
        # code doesnt like to be run as super user -> maybe useradd here ?!
        # if only vscode cli is installed gives error:
        #   No installation of Visual Studio Code stable was found.
        #   Install it from your system's package manager or https://code.visualstudio.com, restart your shell, and try again.
        #   f you already installed Visual Studio Code and we didn't detect it, run `code version use stable --install-dir /path/to/installation`

        # node.addDockerCommand(ServerTemplates['build'].format(extensions=extens))

        for (u,p,b,m) in self.__repos:

            path = urlparse(u).path
            parts = PurePosixPath(    unquote(path)).parts
            volname = parts[-2] + '-' + parts[-1] # gituser-repo

            if m == AccessMode.private:
                node.addDockerCommand(ServerTemplates['repo'].format(repourl=u, branch=b, dir=p ) )
                volname += node.getName()
            else:
                # in shared mode only clone the repo if we are the fst DevService to request it
                dep = self.__service.checkoutShared(u, b, node)
                # the node running the DevServer can only start after the node that initializes the shared checkout
                #if dep != None:
                #    node.addStartUpDependency(dep)# TODO: add startup dependencies between containers in SEED
                #else:
                node.addDockerCommand(ServerTemplates['repo'].format(repourl=u, branch=b, dir=p ) )

            node.addPersistentStorage(p, volname)

            # this should share the installed extensions among all DevServers
            node.addPersistentStorage('/root/.vscode-server', 'vscodeserver')

        node.appendStartCommand(ServerTemplates['command'])
        node.appendClassName("DevServer")

    def print(self, indent: int) -> str:
        out = ' ' * indent
        out += 'DevServer.\n'
        return out


class ContainerDevelopmentService(Service):
    """!
    @brief Container Development service class.

    It manages the allocation of named docker volumes to DevServer instances
    that share a joint checkout of a repo.
    Also it arranges for the nodes with a DevServer to be connected to the internet,
    i.e. to download dependencies in the course of a build.

    It can be subclassed to i.e. also share a programming language installation
    , build cache and downloaded dependencies.

    """
    __dev_cnt: int =0
    __gituname: str = 'John Doe'
    __gitmail: str = 'john.doe@mail.com'

    #_shared_checkouts: dict(Pair,List)

    def __init__(self, gitusrname: str, gitusrmail: str):
        """!
        @brief
        """
        self.__gituname = gitusrname
        self.__gitmail = gitusrmail

        self._shared_checkouts = dict()
        super().__init__()

        self.addDependency('Base', False, False)
        self.addDependency('Scion', False, True)

        # in the course of configuring the DevService layer
        # we might enable real-world-access on some networks,
        # whose implementation is up to the Routing layer
        self.addDependency('ScionRouting', True, False)


    def gitUser(self) -> str:
        """ return the name of the Git user """
        return self.__gituname

    def gitMail(self) -> str:
        """return the email address of the Git User"""
        return self.__gitmail

    def checkoutShared(self, repourl: str, branch: str, node ):
        """
        for a given shared repo checkout identified by (url,branch)
        returns the node, which is responsible for the initial initialization
        of the named volume or none if there is none
        """
        if (repourl, branch) in self._shared_checkouts.keys():
            return self._shared_checkouts[(repourl, branch)]
        else:
            self._shared_checkouts[(repourl, branch)] = node
            return None


    def _createServer(self) -> Server:
        d = DevServer(self, self.__dev_cnt)
        ContainerDevelopmentService.__dev_cnt += 1
        return d

    def install(self, vnode: str) -> Server:

        return super().install(vnode)

    def _configureGit(self, emu: Emulator):
        """
        to be able to push changes made in the DevServer build containers,
        the node has to have a keypair in ~/.ssh

        There is one node that initializes the shared volume.
        Therefore it needs to have some additional software installed: ssh-keygen

        The shared volume is then mounted under ~/.ssh into all DevServer nodes.

        Also a second shared volume:  ~/.config/git/config for 'git config --global'

        """
        if len(self.getPendingTargets()) ==0:
            return
        pnode = emu.getBindingFor( list(self.getPendingTargets().keys())[0] )

        pnode.addSoftware('openssh-client')

        pnode.addPersistentStorage('/root/.ssh', 'sshkeys') # not /home/root/ . . ?!
        pnode.addPersistentStorage('/root/.config/git', 'gitconf')

        # initialize the git config volume
        # --global -> /root/.gitconfig
        pnode.addDockerCommand('RUN mkdir -p /root/.config/git/')
        pnode.addDockerCommand('RUN git config -f /root/.config/git/config  user.name {}'.format( self.gitUser()) )
        pnode.addDockerCommand('RUN git config -f /root/.config/git/config  user.email {}'.format(self.gitMail()) )

        pnode.addDockerCommand('RUN echo $(ssh-keygen -t ed25519 -C "{}" -f /root/.ssh/id_ed25519 -N "" | grep -E ":(.*) ")'.format(self.gitMail() ) )
        #TODO: print the pub key to console somehow during build, so that user can add  key to GitHub, before 'docker-compose up'
        # only visible with --progress=plain option passed to docker-compose build
        pnode.appendStartCommand('eval "$(ssh-agent -s)"')
        pnode.appendStartCommand( 'ssh-add /root/.ssh/id_ed25519' )

        for vnode in list(self.getPendingTargets().keys())[1:]:
            node = emu.getBindingFor(vnode)
            node.addSoftware('openssh-client')
            node.appendStartCommand('eval "$(ssh-agent -s)"')
            node.appendStartCommand('ssh-add /root/.ssh/id_ed25519')
            node.addPersistentStorage('/root/.ssh', 'sshkeys')
            node.addPersistentStorage('/root/.config/git', 'gitconf')

    def _configureRealWorldAccess(self, emulator: Emulator):
        """ in order to able to git-push any changes made on the build/dev-container checkouts
            the nodes with a DevServer installation need external 'RealWorld' connectivity
            on their local net (out of the simulation).
            This function takes care of that by making the node's default gateway a 'RealWorldRouter'
        """
        # ATTENTION: this means names of virtual hosts with DevServices must be globally unique :| !!
        for vnode in self.getPendingTargets().keys():
            pnode = emulator.getBindingFor(vnode) # or resolvVnode(vnode) ?!


            # a router with DevService installed on it -> (is its own gateway to service net / real world)
            if pnode.getRole() == NodeRole.Router or pnode.getRole() == NodeRole.BorderRouter:
                pnode = promote_to_real_world_router(pnode, False)
                # continue


            allnets_of_pnode: Set[Network] = set() # note: hosts can be in at most one local-net (have single interface)
            for inf in pnode.getInterfaces():
                net = inf.getNet()
                # DevService could also be installed on a router node
                # which might only be connected to networks of type other-than 'Local'
                # but this is handled above
                if net.getType() == NetworkType.Local:
                    if net in allnets_of_pnode:
                        print("multihomed host: %s" % vnode ) # this should be impossible

                    allnets_of_pnode.add(net)

            #  It would be nice if i could just call 'net.enableRealWorldAccess()' or sth here and be done with it

            # only routers will be in more than one net
            for  net in allnets_of_pnode:
                p = emulator.getExternalConnectivityProvider()
                net.enableExternalConnectivity(p)
                # p = net.getExternalConnectivityProvider()
                p.requestExternalLink(pnode, net)


    def configure(self, emulator: Emulator):

        self._configureGit(emulator)

        self._configureRealWorldAccess(emulator)

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

devsvc.install('dev150_0').checkoutRepo(url= "https://github.com/your-username/your-project.git",
                                        dir="/home/root/pan",branch="awesome-feature")
                        .addVSCodeExtension('golang.Go')

"""

class GolangDevService(ContainerDevelopmentService):
    """!
    @brief Container Development service that provides
    a shared Go installation to all its DevServers it creates.

    A manual Go installation is done on the fst DevServer that is created by this service,
    into a directory that points to a named docker volume,
    which is then mounted into all other DevServer instances under the same path.
    This way, they share modules downloaded into GOMODCACHE,
    tools/executables installed into GOBIN,
    and any gained build progress through GOCACHE

    """

    def __init__(self, uname: str, mail: str): # TODO: maybe add golang-version argument here
        """!
        @brief
        @param uname github user name
        @param mail github email
        """

        super().__init__(uname, mail)

        self.addDependency('Base', False, False)
        self.addDependency('Scion', False, True)

    def configure(self, emulator: Emulator):
        super().configure(emulator)
        targets = list(self.getPendingTargets().keys())
        if len(targets) ==0:
            return
        # where to download Golang
        go_url = 'https://go.dev/dl/go1.24.0.linux-amd64.tar.gz'

        pnode = emulator.getBindingFor( targets[0] )
        # pnode has to initialize the named docker volumes with the Go installation
        pnode.addSoftware("wget ca-certificates unzip findutils ") #  protobuf-compiler"

        # contains the protobuf installation
        pnode.addPersistentStorage('/root/.local', 'protobuf')
        # contains GOROOT (actual installation)
        pnode.addPersistentStorage('/usr/local/go', 'usrlocalgo')
        # contains GOPATH  - downloaded modules, installed tools/executables
        pnode.addPersistentStorage('/go', 'gopath')
        # contains GOENV
        pnode.addPersistentStorage('/root/.config/go', 'goenv')
        # contains GOCACHE
        pnode.addPersistentStorage('/root/.cache/go-build', 'gocache')

        pnode.addDockerCommand('RUN mkdir /root/.local && wget https://github.com/protocolbuffers/protobuf/releases/download/v29.3/protoc-29.3-linux-x86_64.zip && unzip protoc-29.3-linux-x86_64.zip -d /root/.local ')

        pnode.addDockerCommand(f'RUN wget -O- "{go_url}" --connect-timeout 1.5 | tar  -xz -C /usr/local ')
        pnode.addDockerCommand('ENV PATH=$PATH:/usr/local/go/bin:/go/bin:/root/.local/protoc-29.3-linux-x86_64/bin')

        pnode.addDockerCommand('RUN go env -w GOPATH=/go')
        # language server for IDE
        pnode.addDockerCommand('RUN go install golang.org/x/tools/gopls@latest' )
        # protobuf compiler
        pnode.addDockerCommand('RUN go install google.golang.org/protobuf/cmd/protoc-gen-go@latest' )
        pnode.addDockerCommand('RUN go install google.golang.org/grpc/cmd/protoc-gen-go-grpc@latest')
        # Go debugger
        pnode.addDockerCommand('RUN go install github.com/go-delve/delve/cmd/dlv@latest' )


        for vnode in targets[1:]:
            node = emulator.getBindingFor(vnode)

            # required for 'go install' to verify TLS certs
            node.addSoftware("ca-certificates ") #protobuf-compiler

            node.addDockerCommand('ENV PATH=$PATH:/usr/local/go/bin:/go/bin:/root/.local/protoc-29.3-linux-x86_64/bin')
            # contains the protobuf installation
            node.addPersistentStorage('/root/.local', 'protobuf',volume={'nocopy':True})
            # contains GOROOT (actual installation)
            node.addPersistentStorage('/usr/local/go', 'usrlocalgo',volume={'nocopy':True})
            # contains GOPATH  - downloaded modules, installed tools/executables
            node.addPersistentStorage('/go', 'gopath',volume={'nocopy':True})
            # contains GOENV
            node.addPersistentStorage('/root/.config/go', 'goenv',volume={'nocopy':True})
            # contains GOCACHE
            node.addPersistentStorage('/root/.cache/go-build', 'gocache',volume={'nocopy':True})

    def getName(self) -> str:
        return 'GolangDevService'

    def print(self, indent: int) -> str:
        out = ' ' * indent
        out += 'GolangDevService\n'
        return out