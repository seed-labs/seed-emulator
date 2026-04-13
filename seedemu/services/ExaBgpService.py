from __future__ import annotations

import json
from typing import Dict, List, Optional, Tuple

from seedemu.core import Emulator, Node, ScopedRegistry, Server, Service
from seedemu.layers.Routing import Router
from seedemu.layers._bgp_metadata import install_router_bgp_session


ExaBgpFileTemplates: Dict[str, str] = {}

ExaBgpFileTemplates["event_sink"] = """\
#!/usr/bin/env python3
import json
import os
import sys
import time

out_path = os.environ.get("EXABGP_EVENT_LOG", "/var/log/exabgp/events.jsonl")
os.makedirs(os.path.dirname(out_path), exist_ok=True)

for raw in sys.stdin:
    line = raw.strip()
    if not line:
        continue
    try:
        payload = json.loads(line)
    except Exception:
        payload = {"raw": line}
    payload["_ts"] = int(time.time())
    with open(out_path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(payload, ensure_ascii=False) + "\\n")
"""

ExaBgpFileTemplates["dashboard"] = """\
#!/usr/bin/env python3
import json
import os
from pathlib import Path

from flask import Flask, jsonify, Response

app = Flask(__name__)
event_log = Path(os.environ.get("EXABGP_EVENT_LOG", "/var/log/exabgp/events.jsonl"))
title = os.environ.get("EXABGP_DASHBOARD_TITLE", "ExaBGP Event Viewer")


def _tail_events(limit: int = 200):
    if not event_log.exists():
        return []
    lines = event_log.read_text(encoding="utf-8", errors="replace").splitlines()[-limit:]
    out = []
    for line in lines:
        try:
            out.append(json.loads(line))
        except Exception:
            out.append({"raw": line})
    return out


@app.route("/")
def index():
    html = f\"\"\"<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <title>{title}</title>
  <style>
    body {{ font-family: monospace; margin: 0; background: #0d1321; color: #eef2ff; }}
    header {{ padding: 16px 20px; background: #111827; position: sticky; top: 0; }}
    main {{ padding: 20px; display: grid; gap: 12px; }}
    .card {{ background: #172033; border: 1px solid #2b3a55; border-radius: 10px; padding: 12px; }}
    .meta {{ color: #93c5fd; }}
    .kind {{ color: #fbbf24; }}
    pre {{ white-space: pre-wrap; word-break: break-word; margin: 0; }}
  </style>
</head>
<body>
  <header>
    <h1>{title}</h1>
    <div>Live BGP event stream rendered from ExaBGP JSON output.</div>
  </header>
  <main id="events"></main>
  <script>
    async function refresh() {{
      const res = await fetch('/api/events');
      const payload = await res.json();
      const root = document.getElementById('events');
      root.innerHTML = '';
      for (const evt of payload.events.reverse()) {{
        const card = document.createElement('section');
        card.className = 'card';
        const meta = document.createElement('div');
        meta.className = 'meta';
        meta.textContent = new Date((evt._ts || 0) * 1000).toISOString();
        const kind = document.createElement('div');
        kind.className = 'kind';
        kind.textContent = evt.type || evt.neighbor?.message?.update ? 'bgp-update' : 'event';
        const pre = document.createElement('pre');
        pre.textContent = JSON.stringify(evt, null, 2);
        card.appendChild(meta);
        card.appendChild(kind);
        card.appendChild(pre);
        root.appendChild(card);
      }}
    }}
    refresh();
    setInterval(refresh, 2000);
  </script>
</body>
</html>\"\"\"
    return Response(html, mimetype="text/html")


@app.route("/api/events")
def events():
    return jsonify({"events": _tail_events()})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("EXABGP_DASHBOARD_PORT", "5000")))
"""

ExaBgpFileTemplates["config"] = """\
process exabgp_json_sink {{
  run /usr/bin/env python3 /opt/exabgp/event_sink.py;
  encoder json;
}}

neighbor {peer_address} {{
  router-id {local_address};
  local-address {local_address};
  local-as {local_asn};
  peer-as {peer_asn};
  family {{
    ipv4 unicast;
  }}
  api {{
    processes [ exabgp_json_sink ];
  }}
{static_block}
}}
"""

ExaBgpFileTemplates["static_block"] = """\
  static {{
{routes}
  }}
"""

class ExaBgpServer(Server):
    __emulator: Emulator | None
    __router_asn: int | None
    __router_name: str | None
    __local_asn: int
    __announce_prefixes: List[str]
    __dashboard_port: int
    __enable_dashboard: bool

    def __init__(self):
        super().__init__()
        self.__emulator = None
        self.__router_asn = None
        self.__router_name = None
        self.__local_asn = 65010
        self.__announce_prefixes = []
        self.__dashboard_port = 5000
        self.__enable_dashboard = True
        self.setDisplayName("ExaBGP Control Plane Tool")

    def bind(self, emulator: Emulator):
        self.__emulator = emulator

    def attachToRouter(self, router_name: str, router_asn: int | None = None) -> "ExaBgpServer":
        self.__router_name = str(router_name)
        self.__router_asn = int(router_asn) if router_asn is not None else None
        return self

    def setLocalAsn(self, asn: int) -> "ExaBgpServer":
        self.__local_asn = int(asn)
        return self

    def addAnnouncement(self, prefix: str) -> "ExaBgpServer":
        self.__announce_prefixes.append(str(prefix))
        return self

    def enableDashboard(self, port: int = 5000) -> "ExaBgpServer":
        self.__enable_dashboard = True
        self.__dashboard_port = int(port)
        return self

    def disableDashboard(self) -> "ExaBgpServer":
        self.__enable_dashboard = False
        return self

    def _resolve_peer(self, node: Node) -> Tuple[Router, str, str]:
        assert self.__emulator is not None, "ExaBgpServer not bound to emulator"
        router_asn = self.__router_asn if self.__router_asn is not None else node.getAsn()
        scope = ScopedRegistry(str(router_asn), self.__emulator.getRegistry())
        assert self.__router_name is not None and scope.has("rnode", self.__router_name), (
            f"router as{router_asn}/{self.__router_name} not found for ExaBGP peer"
        )
        router = scope.get("rnode", self.__router_name)
        assert isinstance(router, Router)

        local_address = ""
        peer_address = ""
        for node_iface in node.getInterfaces():
            for router_iface in router.getInterfaces():
                if node_iface.getNet() != router_iface.getNet():
                    continue
                local_address = str(node_iface.getAddress())
                peer_address = str(router_iface.getAddress())
                break
            if local_address and peer_address:
                break

        assert local_address and peer_address, (
            f"ExaBGP node as{node.getAsn()}/{node.getName()} does not share a network with as{router.getAsn()}/{router.getName()}"
        )
        return router, local_address, peer_address

    def _install_router_peer(self, router: Router, *, local_address: str, peer_address: str):
        session_name = f"exabgp_{self.__local_asn}"
        install_router_bgp_session(
            router,
            {
                "name": session_name,
                "kind": "ebgp",
                "local_address": peer_address,
                "local_asn": router.getAsn(),
                "peer_address": local_address,
                "peer_asn": self.__local_asn,
                "import_community": None,
                "local_pref": None,
                "export_policy": "all",
                "next_hop_self": True,
                "route_server_client": False,
            },
        )

    def install(self, node: Node):
        router, local_address, peer_address = self._resolve_peer(node)
        self._install_router_peer(router, local_address=local_address, peer_address=peer_address)

        node.addSoftware("python3 python3-pip")
        node.addBuildCommand("python3 -m pip install --no-cache-dir exabgp flask")
        node.setFile("/opt/exabgp/event_sink.py", ExaBgpFileTemplates["event_sink"])
        node.setFile("/opt/exabgp/dashboard.py", ExaBgpFileTemplates["dashboard"])

        static_block = ""
        if self.__announce_prefixes:
            routes = "\n".join(f"    route {prefix} next-hop self;" for prefix in self.__announce_prefixes)
            static_block = ExaBgpFileTemplates["static_block"].format(routes=routes)

        node.setFile(
            "/etc/exabgp/exabgp.conf",
            ExaBgpFileTemplates["config"].format(
                local_address=local_address,
                local_asn=self.__local_asn,
                peer_address=peer_address,
                peer_asn=router.getAsn(),
                static_block=static_block,
            ),
        )
        node.appendStartCommand("mkdir -p /var/log/exabgp /opt/exabgp")
        node.appendStartCommand("chmod +x /opt/exabgp/event_sink.py /opt/exabgp/dashboard.py")
        if self.__enable_dashboard:
            node.appendStartCommand(
                f"EXABGP_EVENT_LOG=/var/log/exabgp/events.jsonl EXABGP_DASHBOARD_PORT={self.__dashboard_port} "
                f"EXABGP_DASHBOARD_TITLE={json.dumps(f'ExaBGP Looking Glass as{node.getAsn()}/{node.getName()}')} "
                "python3 /opt/exabgp/dashboard.py",
                True,
            )
        node.appendStartCommand(
            "EXABGP_EVENT_LOG=/var/log/exabgp/events.jsonl "
            "exabgp /etc/exabgp/exabgp.conf >/var/log/exabgp/exabgp.log 2>&1",
            True,
        )


class ExaBgpService(Service):
    __emulator: Emulator | None

    def __init__(self):
        super().__init__()
        self.__emulator = None
        self.addDependency("Routing", False, False)
        self.addDependency("Ebgp", False, True)
        self.addDependency("FrrBgp", False, True)

    def _createServer(self) -> Server:
        return ExaBgpServer()

    def _doConfigure(self, node: Node, server: ExaBgpServer):
        super()._doConfigure(node, server)
        assert self.__emulator is not None
        server.bind(self.__emulator)

    def configure(self, emulator: Emulator):
        self.__emulator = emulator
        return super().configure(emulator)

    def getName(self) -> str:
        return "ExaBgpService"
