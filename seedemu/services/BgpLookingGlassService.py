from __future__ import annotations
from seedemu.core import Node, Service, Server, Emulator, ScopedRegistry, Router
from typing import Dict, Optional, Set, Tuple
import json

from seedemu.layers._bgp_metadata import get_bgp_backend

BIRDCTRL='/run/bird/bird.ctl'

LookingGlassFileTemplates: Dict[str, str] = {}

LookingGlassFileTemplates["proxy"] = """\
#!/usr/bin/env python3
import json
import os
import subprocess
from http.server import BaseHTTPRequestHandler, HTTPServer

backend = os.environ.get("SEED_LG_BACKEND", "bird")
bird_socket = os.environ.get("SEED_LG_BIRD_SOCKET", "/run/bird/bird.ctl")

def run_bird(args):
    try:
        proc = subprocess.run(
            ["birdc", "-s", bird_socket] + args,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=8,
        )
        return {"ok": proc.returncode == 0, "output": proc.stdout}
    except Exception as exc:
        return {"ok": False, "output": str(exc)}

def run_frr(commands):
    args = []
    for command in commands:
        args.extend(["-c", command])
    try:
        proc = subprocess.run(
            ["vtysh"] + args,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=8,
        )
        return {"ok": proc.returncode == 0, "output": proc.stdout}
    except Exception as exc:
        return {"ok": False, "output": str(exc)}

class Handler(BaseHTTPRequestHandler):
    def _json(self, payload):
        data = json.dumps(payload).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.path.startswith("/api/protocols"):
            if backend == "frr":
                self._json(run_frr(["show bgp summary", "show ip ospf neighbor"]))
            else:
                self._json(run_bird(["show", "protocols"]))
            return
        if self.path.startswith("/api/routes"):
            if backend == "frr":
                self._json(run_frr(["show bgp ipv4 unicast", "show ip route bgp"]))
            else:
                self._json(run_bird(["show", "route", "all"]))
            return
        body = b"SEED BGP route-state proxy\\n"
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):
        return

if __name__ == "__main__":
    port = int(os.environ.get("SEED_LG_PROXY_PORT", "8000"))
    HTTPServer(("0.0.0.0", port), Handler).serve_forever()
"""

LookingGlassFileTemplates["frontend"] = """\
#!/usr/bin/env python3
import json
import os
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.request import urlopen

routers = json.loads(os.environ.get("SEED_LG_ROUTERS", "{}"))
proxy_port = int(os.environ.get("SEED_LG_PROXY_PORT", "8000"))
title = os.environ.get("SEED_LG_TITLE", "SEED BGP Looking Glass")

def fetch(host, path):
    try:
        with urlopen(f"http://{host}:{proxy_port}{path}", timeout=8) as resp:
            return json.loads(resp.read().decode("utf-8", errors="replace"))
    except Exception as exc:
        return {"ok": False, "output": str(exc)}

def state():
    out = {}
    for name, host in routers.items():
        out[name] = {
            "host": host,
            "protocols": fetch(host, "/api/protocols"),
            "routes": fetch(host, "/api/routes"),
        }
    return out

class Handler(BaseHTTPRequestHandler):
    def _send(self, content, content_type):
        data = content.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.path.startswith("/api/state"):
            self._send(json.dumps({"routers": state()}), "application/json")
            return
        self._send(f'''<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <title>{title}</title>
  <style>
    body {{ margin: 0; font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; background: #f7f8fb; color: #111827; }}
    header {{ padding: 16px 20px; border-bottom: 1px solid #d1d5db; background: #ffffff; }}
    main {{ padding: 16px 20px; display: grid; gap: 14px; }}
    section {{ border: 1px solid #d1d5db; border-radius: 8px; background: #ffffff; overflow: hidden; }}
    h1 {{ margin: 0; font-size: 20px; }}
    h2 {{ margin: 0; padding: 10px 12px; font-size: 16px; background: #eef2f7; }}
    h3 {{ margin: 12px 12px 6px; font-size: 13px; }}
    pre {{ margin: 0 12px 12px; padding: 10px; overflow: auto; white-space: pre-wrap; background: #111827; color: #e5e7eb; border-radius: 6px; }}
  </style>
</head>
<body>
  <header><h1>{title}</h1><div>Classic route-state view backed by router route state.</div></header>
  <main id="root"></main>
  <script>
    async function refresh() {{
      const res = await fetch('/api/state');
      const payload = await res.json();
      const root = document.getElementById('root');
      root.innerHTML = '';
      for (const [name, data] of Object.entries(payload.routers)) {{
        const section = document.createElement('section');
        section.innerHTML = `<h2>${{name}} <small>${{data.host}}</small></h2>
          <h3>Protocols</h3><pre>${{data.protocols.output || ''}}</pre>
          <h3>Routes</h3><pre>${{data.routes.output || ''}}</pre>`;
        root.appendChild(section);
      }}
    }}
    refresh();
    setInterval(refresh, 3000);
  </script>
</body>
</html>''', "text/html")

    def log_message(self, fmt, *args):
        return

if __name__ == "__main__":
    port = int(os.environ.get("SEED_LG_FRONTEND_PORT", "5000"))
    HTTPServer(("0.0.0.0", port), Handler).serve_forever()
"""

class BgpLookingGlassServer(Server):
    """!
    @brief the BGP looking glass server. A looking glass server has two parts,
    proxy and frontend. Proxy runs on routers and talk with BIRD to get routing
    information, and frontend is the actual "looking glass" page.
    """

    __routers: Set[Tuple[Optional[int], str]]
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
        node.addSoftware('python3')
        node.setFile('/opt/seed-lg/proxy.py', LookingGlassFileTemplates["proxy"])
        node.setFile('/opt/seed-lg/frontend.py', LookingGlassFileTemplates["frontend"])

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

    def addRouter(self, asn: int, routerName: str) -> BgpLookingGlassServer:
        """!
        @brief add a router whose route-state should be exposed by this looking glass.

        @param asn AS number of the router.
        @param routerName name of the router.

        @returns self, for chaining API calls.
        """
        self.__routers.add((int(asn), str(routerName)))

        return self

    def attach(self, routerName: str) -> BgpLookingGlassServer:
        """!
        @brief compatibility API for adding a router in the service node's AS.

        @param routerName name of the router

        @returns self, for chaining API calls.
        """
        self.__routers.add((None, str(routerName)))

        return self

    def getAttached(self) -> Set[Tuple[Optional[int], str]]:
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

        self.__installLookingGlass(node)

        for target_asn, router_name in self.__routers:
            resolved_asn = asn if target_asn is None else target_asn
            sreg = ScopedRegistry(str(resolved_asn), self.__sim.getRegistry())
            assert sreg.has('rnode', router_name), 'looking glass router as{}/{} not found'.format(resolved_asn, router_name)
            router: Router = sreg.get('rnode', router_name)
            backend = get_bgp_backend(router)
            assert backend in {"bird", "frr"}, (
                "BgpLookingGlassService currently supports Bird and FRR routers only; "
                f"as{router.getAsn()}/{router.getName()} uses backend={backend}"
            )

            _node: Node = router.getAttribute('__looking_glass_node', node)

            assert _node == node, 'router as{}/{} already attached to another looking glass node (as{}/{})'.format(
                router.getAsn(), router.getName(), _node.getAsn(), _node.getName()
            )

            self.__installLookingGlass(router)

            if backend == "bird":
                router.appendStartCommand('while [ ! -e "{}" ]; do echo "lg: waiting for bird...";  sleep 1; done'.format(
                    BIRDCTRL
                ))
            elif backend == "frr":
                router.appendStartCommand('while ! vtysh -c "show version" >/dev/null 2>&1; do echo "lg: waiting for frr..."; sleep 1; done')
            else:
                raise ValueError(
                    f"BgpLookingGlassService does not support backend={backend} "
                    f"for as{router.getAsn()}/{router.getName()}"
                )
            
            router.appendStartCommand('SEED_LG_BACKEND="{}" SEED_LG_BIRD_SOCKET="{}" SEED_LG_PROXY_PORT={} python3 /opt/seed-lg/proxy.py'.format(
                backend, BIRDCTRL, self.__proxy_port
            ), True)

            display_name = router.getName() if resolved_asn == asn else 'as{}_{}'.format(resolved_asn, router.getName())
            routers[display_name] = str(router.getLoopbackAddress())

        for (router, address) in routers.items():
            node.appendStartCommand('echo "{} {}.lg.as{}.net" >> /etc/hosts'.format(address, router, asn))

        node.appendStartCommand("SEED_LG_ROUTERS='{}' SEED_LG_PROXY_PORT={} SEED_LG_FRONTEND_PORT={} SEED_LG_TITLE='AS{} looking glass' python3 /opt/seed-lg/frontend.py".format(
            json.dumps(routers), self.__proxy_port, self.__frontend_port, asn
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
