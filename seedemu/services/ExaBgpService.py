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
open(out_path, "a", encoding="utf-8").close()

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

ExaBgpFileTemplates["live_control"] = """\
#!/usr/bin/env python3
import os
import stat
import sys
import time

fifo_path = os.environ.get("EXABGP_LIVE_FIFO", "/run/exabgp/live.in")
log_path = os.environ.get("EXABGP_LIVE_LOG", "/var/log/exabgp/live-control.log")
os.makedirs(os.path.dirname(fifo_path), exist_ok=True)
os.makedirs(os.path.dirname(log_path), exist_ok=True)

try:
    if os.path.exists(fifo_path) and not stat.S_ISFIFO(os.stat(fifo_path).st_mode):
        os.unlink(fifo_path)
    if not os.path.exists(fifo_path):
        os.mkfifo(fifo_path, 0o666)
    os.chmod(fifo_path, 0o666)
except FileExistsError:
    pass

def log(message: str) -> None:
    with open(log_path, "a", encoding="utf-8") as fh:
        fh.write(f"{int(time.time())} {message}\\n")

log(f"ready fifo={fifo_path}")

while True:
    with open(fifo_path, "r", encoding="utf-8", errors="replace") as fifo:
        for raw in fifo:
            command = raw.strip()
            if not command or command.startswith("#"):
                continue
            print(command, flush=True)
            log(command)
"""

ExaBgpFileTemplates["dashboard"] = """\
#!/usr/bin/env python3
import json
import os
from pathlib import Path

from flask import Flask, jsonify, Response

app = Flask(__name__)
event_log = Path(os.environ.get("EXABGP_EVENT_LOG", "/var/log/exabgp/events.jsonl"))
live_log = Path(os.environ.get("EXABGP_LIVE_LOG", "/var/log/exabgp/live-control.log"))
title = os.environ.get("EXABGP_DASHBOARD_TITLE", "ExaBGP Event Viewer")


def _tail_events(limit: int = 200):
    out = []
    if event_log.exists():
        for line in event_log.read_text(encoding="utf-8", errors="replace").splitlines()[-limit:]:
            try:
                out.append(json.loads(line))
            except Exception:
                out.append({"type": "exabgp-log", "raw": line})
    if live_log.exists():
        for line in live_log.read_text(encoding="utf-8", errors="replace").splitlines()[-limit:]:
            if not line.strip():
                continue
            ts, _, command = line.partition(" ")
            out.append({"type": "live-control", "_ts": int(ts) if ts.isdigit() else 0, "command": command or line})
    return sorted(out, key=lambda item: item.get("_ts", 0))[-limit:]


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
        kind.textContent = evt.type || (evt.neighbor?.message?.update ? 'bgp-update' : 'event');
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

process exabgp_live_control {{
  run /usr/bin/env python3 /opt/exabgp/live_control.py;
  encoder text;
  respawn false;
}}

{neighbor_blocks}
"""

ExaBgpFileTemplates["static_block"] = """\
  static {{
{routes}
  }}
"""

class ExaBgpServer(Server):
    __emulator: Optional[Emulator]
    __local_asn: int
    __announce_prefixes: List[str]
    __dashboard_port: int
    __enable_dashboard: bool
    __peers: List[Dict[str, object]]
    __resolved_peers: List[Tuple[Dict[str, object], Router, str, str]]

    def __init__(self):
        super().__init__()
        self.__emulator = None
        self.__local_asn = 65010
        self.__announce_prefixes = []
        self.__dashboard_port = 5000
        self.__enable_dashboard = True
        self.__peers = []
        self.__resolved_peers = []
        self.setDisplayName("ExaBGP Control Plane Tool")

    def bind(self, emulator: Emulator):
        self.__emulator = emulator

    def attachToRouter(self, router_name: str, router_asn: Optional[int] = None) -> "ExaBgpServer":
        self.__peers = []
        self.addPeer(router_name, router_asn=router_asn)
        return self

    def addPeer(
        self,
        router_name: str,
        router_asn: Optional[int] = None,
        session_name: Optional[str] = None,
        router_relationship: str = "customer",
    ) -> "ExaBgpServer":
        relationship = str(router_relationship or "customer").strip().lower() or "customer"
        if relationship not in {"customer", "peer", "provider", "unfiltered"}:
            raise ValueError(f"unsupported router relationship: {router_relationship}")
        self.__peers.append(
            {
                "router_name": str(router_name),
                "router_asn": int(router_asn) if router_asn is not None else None,
                "session_name": str(session_name).strip() if session_name is not None else None,
                "router_relationship": relationship,
            }
        )
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

    def _resolve_peer(self, node: Node, peer: Dict[str, object]) -> Tuple[Router, str, str]:
        assert self.__emulator is not None, "ExaBgpServer not bound to emulator"
        router_asn = int(peer["router_asn"]) if peer.get("router_asn") is not None else node.getAsn()
        scope = ScopedRegistry(str(router_asn), self.__emulator.getRegistry())
        router_name = str(peer["router_name"])
        assert scope.has("rnode", router_name), (
            f"router as{router_asn}/{router_name} not found for ExaBGP peer"
        )
        router = scope.get("rnode", router_name)
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

    def _peer_relationship_params(self, relationship: str) -> Tuple[Optional[str], Optional[int], str]:
        if relationship == "customer":
            return "CUSTOMER_COMM", 30, "all"
        if relationship == "peer":
            return "PEER_COMM", 20, "local_and_customer"
        if relationship == "provider":
            return "PROVIDER_COMM", 10, "local_and_customer"
        return None, None, "all"

    def _install_router_peer(
        self,
        router: Router,
        *,
        local_address: str,
        peer_address: str,
        session_name: str,
        relationship: str,
    ):
        import_community, local_pref, export_policy = self._peer_relationship_params(relationship)
        install_router_bgp_session(
            router,
            {
                "name": session_name,
                "kind": "ebgp",
                "local_address": peer_address,
                "local_asn": router.getAsn(),
                "peer_address": local_address,
                "peer_asn": self.__local_asn,
                "import_community": import_community,
                "local_pref": local_pref,
                "export_policy": export_policy,
                "next_hop_self": True,
                "route_server_client": False,
            },
        )

    def configureOnNode(self, node: Node):
        assert self.__peers, "ExaBgpServer requires at least one peer"
        if self.__resolved_peers:
            return
        for index, peer in enumerate(self.__peers):
            router, local_address, peer_address = self._resolve_peer(node, peer)
            session_name = str(peer.get("session_name") or "")
            if not session_name:
                if len(self.__peers) == 1:
                    session_name = f"exabgp_{self.__local_asn}"
                else:
                    session_name = f"exabgp_{self.__local_asn}_{router.getName()}_{index}"
            self._install_router_peer(
                router,
                local_address=local_address,
                peer_address=peer_address,
                session_name=session_name,
                relationship=str(peer.get("router_relationship") or "customer"),
            )
            self.__resolved_peers.append((peer, router, local_address, peer_address))

    def install(self, node: Node):
        self.configureOnNode(node)
        node.addBuildCommand(
            "apt-get update && "
            "apt-get install -y --no-install-recommends "
            "-o Dpkg::Options::=--force-unsafe-io "
            "exabgp python3-flask && "
            "rm -rf /var/lib/apt/lists/*"
        )
        node.setFile("/opt/exabgp/event_sink.py", ExaBgpFileTemplates["event_sink"])
        node.setFile("/opt/exabgp/live_control.py", ExaBgpFileTemplates["live_control"])
        node.setFile("/opt/exabgp/dashboard.py", ExaBgpFileTemplates["dashboard"])

        neighbor_blocks: List[str] = []
        routes = ""
        if self.__announce_prefixes:
            routes = "\n".join(f"    route {prefix} next-hop self;" for prefix in self.__announce_prefixes)
        static_block = ExaBgpFileTemplates["static_block"].format(routes=routes) if routes else ""
        for _peer, router, local_address, peer_address in self.__resolved_peers:
            neighbor_blocks.append(
                (
                    "neighbor {peer_address} {{\n"
                    "  router-id {local_address};\n"
                    "  local-address {local_address};\n"
                    "  local-as {local_asn};\n"
                    "  peer-as {peer_asn};\n"
                    "  family {{\n"
                    "    ipv4 unicast;\n"
                    "  }}\n"
                    "  api {{\n"
                    "    processes [ exabgp_json_sink exabgp_live_control ];\n"
                    "  }}\n"
                    "{static_block}"
                    "}}\n"
                ).format(
                    peer_address=peer_address,
                    local_address=local_address,
                    local_asn=self.__local_asn,
                    peer_asn=router.getAsn(),
                    static_block=static_block,
                )
            )

        node.setFile(
            "/etc/exabgp/exabgp.conf",
            ExaBgpFileTemplates["config"].format(
                neighbor_blocks="\n".join(neighbor_blocks),
            ),
        )
        node.appendStartCommand(
            "mkdir -p /var/log/exabgp /opt/exabgp && "
            "touch /var/log/exabgp/events.jsonl /var/log/exabgp/exabgp.log "
            "/var/log/exabgp/live-control.log && "
            "chmod 755 /var/log/exabgp && "
            "chmod 666 /var/log/exabgp/events.jsonl /var/log/exabgp/exabgp.log "
            "/var/log/exabgp/live-control.log"
        )
        node.appendStartCommand(
            "mkdir -p /run/exabgp /var/run/exabgp && rm -f /run/exabgp/live.in"
        )
        node.appendStartCommand("chmod +x /opt/exabgp/event_sink.py /opt/exabgp/live_control.py /opt/exabgp/dashboard.py")
        if self.__enable_dashboard:
            node.appendStartCommand(
                f"EXABGP_EVENT_LOG=/var/log/exabgp/events.jsonl EXABGP_DASHBOARD_PORT={self.__dashboard_port} "
                f"EXABGP_DASHBOARD_TITLE={json.dumps(f'ExaBGP Looking Glass as{node.getAsn()}/{node.getName()}')} "
                "python3 /opt/exabgp/dashboard.py",
                True,
            )
        node.appendStartCommand(
            "EXABGP_EVENT_LOG=/var/log/exabgp/events.jsonl "
            "env exabgp.api.cli=false "
            "exabgp /etc/exabgp/exabgp.conf >/var/log/exabgp/exabgp.log 2>&1",
            True,
        )


class ExaBgpService(Service):
    __emulator: Optional[Emulator]

    def __init__(self):
        super().__init__()
        self.__emulator = None
        self.addDependency("Routing", False, False)
        self.addDependency("Ebgp", False, True)

    def _createServer(self) -> Server:
        return ExaBgpServer()

    def _doConfigure(self, node: Node, server: ExaBgpServer):
        assert self.__emulator is not None
        server.bind(self.__emulator)
        server.configureOnNode(node)
        super()._doConfigure(node, server)

    def configure(self, emulator: Emulator):
        self.__emulator = emulator
        return super().configure(emulator)

    def getName(self) -> str:
        return "ExaBgpService"
