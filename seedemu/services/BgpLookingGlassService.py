from __future__ import annotations
from seedemu.core import Node, Service, Server, Emulator, ScopedRegistry
from seedemu.layers.Routing import Router
from typing import Set, Dict

from seedemu.layers._bgp_metadata import get_bgp_backend

BIRDCTRL='/run/bird/bird.ctl'
GO_VERSION='1.22.12'

class BgpLookingGlassServer(Server):
    """!
    @brief the BGP looking glass server. A looking glass server has two parts,
    proxy and frontend. Proxy runs on routers and talk with BIRD to get routing
    information, and frontend is the actual "looking glass" page.
    """

    __routers: Set[str]
    __sim: Emulator
    __frontend_port: int
    __proxy_port: int

    def __init__(self):
        """!
        @brief create a new class BgpLookingGlassServer.
        """
        super().__init__()
        self.__routers = set()
        self.__frontend_port = 5000
        self.__proxy_port = 8000

    def __installLookingGlass(self, node: Node):
        """!
        @brief add commands for installing looking glass to nodes.

        @param node node.
        """

        # bird-lg-go uses Go embed support, so we install a newer upstream Go toolchain
        # instead of relying on Ubuntu 20.04's older golang package.
        node.addSoftware('git')
        node.addSoftware('make')
        node.addSoftware('ca-certificates')
        node.addBuildCommand(
            "arch=\"$(dpkg --print-architecture)\"; "
            "case \"$arch\" in amd64) go_arch=amd64 ;; arm64) go_arch=arm64 ;; *) echo \"unsupported arch: $arch\"; exit 1 ;; esac; "
            f"curl -fsSL https://go.dev/dl/go{GO_VERSION}.linux-${{go_arch}}.tar.gz -o /tmp/go.tgz && "
            "rm -rf /usr/local/go && tar -C /usr/local -xzf /tmp/go.tgz && rm -f /tmp/go.tgz && "
            "ln -sf /usr/local/go/bin/go /usr/local/bin/go && ln -sf /usr/local/go/bin/gofmt /usr/local/bin/gofmt"
        )
        node.addBuildCommand('git clone https://github.com/xddxdd/bird-lg-go /lg')
        node.addBuildCommand('GOBIN=/usr/local/bin /usr/local/go/bin/go install github.com/kevinburke/go-bindata/go-bindata@v3.11.0')
        node.addBuildCommand('PATH=/usr/local/go/bin:$PATH make -C /lg')

    def setFrontendPort(self, port: int) -> BgpLookingGlassServer:
        """!
        @brief set frontend port for looking glass. (default: 5000)

        @param port port

        @returns self, for chaining API calls.
        """
        self.__frontend_port = port

        return self

    def getFrontendPort(self) -> int:
        """!
        @brief get frontend port.

        @returns frontend port.
        """
        return self.__frontend_port

    def setProxyPort(self, port: int) -> BgpLookingGlassServer:
        """!
        @brief set proxy port for looking glass. (default: 8000)

        @param port port

        @returns self, for chaining API calls.
        """
        self.__proxy_port = port

        return self

    def getProxyPort(self) -> int:
        """!
        @brief get proxy port.

        @returns proxy port.
        """
        return self.__proxy_port

    def attach(self, routerName: str) -> BgpLookingGlassServer:
        """!
        @brief add looking glass node on the router identified by given name.

        @param routerName name of the router

        @returns self, for chaining API calls.
        """
        self.__routers.add(routerName)

        return self

        return self

    def getAttached(self) -> Set[str]:
        """!
        @brief get routers to be attached.

        @return set of router names.
        """
        return self.__routers

    def bind(self, emulator: Emulator):
        """!
        @brief bind to the given emulator object; this will be called by the
        BgpLookingGlassService during the render-config stage. This will be used
        to search for router nodes during installation.

        @param emulator emulator object.
        """
        self.__sim = emulator

    def install(self, node: Node):
        routers: Dict[str, str] = {}
        asn = node.getAsn()
        sreg = ScopedRegistry(str(asn), self.__sim.getRegistry())

        self.__installLookingGlass(node)

        for obj in sreg.getByType('rnode'):
            router: Router = obj
            
            if router.getName() not in self.__routers: continue
            assert get_bgp_backend(router) == "bird", (
                "BgpLookingGlassService currently supports Bird routers only; "
                f"as{router.getAsn()}/{router.getName()} uses backend={get_bgp_backend(router)}"
            )

            _node: Node = router.getAttribute('__looking_glass_node', node)

            assert _node == node, 'router as{}/{} already attached to another looking glass node (as{}/{})'.format(
                router.getAsn(), router.getName(), _node.getAsn(), _node.getName()
            )

            self.__installLookingGlass(router)

            router.appendStartCommand('while [ ! -e "{}" ]; do echo "lg: waiting for bird...";  sleep 1; done'.format(
                BIRDCTRL
            ))
            
            router.appendStartCommand('/lg/proxy/proxy --bird "{}" --listen :{}'.format(
                BIRDCTRL, self.__proxy_port
            ), True)

            routers[router.getName()] = router.getLoopbackAddress()

        for (router, address) in routers.items():
            node.appendStartCommand('echo "{} {}.lg.as{}.net" >> /etc/hosts'.format(address, router, asn))

        node.appendStartCommand('/lg/frontend/frontend --domain lg.as{}.net --servers {} --proxy-port {} --listen :{} --title-brand "{}" --navbar-brand "{}"'.format(
            asn, ','.join(routers.keys()), self.__proxy_port, self.__frontend_port, 'AS{} looking glass'.format(asn), 'AS{} looking glass'.format(asn)
        ))

class BgpLookingGlassService(Service):
    """!
    @brief the BGP looking glass service.
    """

    __emulator: Emulator

    def __init__(self):
        super().__init__()
        self.addDependency('Routing', False, False)

    def _createServer(self) -> Server:
        return BgpLookingGlassServer()

    def _doConfigure(self, node: Node, server: BgpLookingGlassServer):
        super()._doConfigure(node, server)
        server.bind(self.__emulator)

    def configure(self, emulator: Emulator):
        self.__emulator = emulator
        return super().configure(emulator)

    def getName(self) -> str:
        return 'BgpLookingGlassService'

    def print(self, indent: int) -> str:
        out = ' ' * indent
        out += 'BgpLookingGlassServiceLayer\n'

        return out
