#!/usr/bin/env python3

import re
import unittest

from seedemu.core import Emulator
from seedemu.layers import Base, Ibgp, Ospf, Routing


def _count_neighbors(conf: str, asn: int) -> int:
    pattern = rf"^\s*neighbor\s+[0-9\.]+\s+as\s+{asn};\s*$"
    return len(re.findall(pattern, conf, flags=re.MULTILINE))


def _count_rr_client(conf: str) -> int:
    return len(re.findall(r"^\s*rr client;\s*$", conf, flags=re.MULTILINE))


def _count_rr_cluster_id(conf: str, cluster_id: str) -> int:
    pattern = rf"^\s*rr cluster id\s+{re.escape(cluster_id)};\s*$"
    return len(re.findall(pattern, conf, flags=re.MULTILINE))


class IbgpRouteReflectorTest(unittest.TestCase):
    def _new_emulator(self):
        emulator = Emulator()
        base = Base()
        emulator.addLayer(base)
        emulator.addLayer(Routing())
        emulator.addLayer(Ospf())
        ibgp = Ibgp()
        emulator.addLayer(ibgp)
        return emulator, base, ibgp

    def _bird_conf(self, base: Base, asn: int, router_name: str) -> str:
        router = base.getAutonomousSystem(asn).getRouter(router_name)
        return router.getFile("/etc/bird/bird.conf").get()[1]

    def _graph_edges(self, emulator: Emulator, ibgp: Ibgp, asn: int):
        ibgp.createGraphs(emulator)
        graph = ibgp.getGraph(f"AS{asn}: iBGP sessions")
        vertices = graph.vertices
        return {
            frozenset((vertices[edge.a].name, vertices[edge.b].name))
            for edge in graph.edges
            if edge.style == "solid"
        }

    def test_without_rr_keeps_full_mesh(self):
        emulator, base, _ = self._new_emulator()
        asobj = base.createAutonomousSystem(150)
        asobj.createNetwork("net0")
        for name in ("r0", "r1", "r2"):
            asobj.createRouter(name).joinNetwork("net0")

        emulator.render()

        for router_name in ("r0", "r1", "r2"):
            conf = self._bird_conf(base, 150, router_name)
            self.assertEqual(_count_neighbors(conf, 150), 2)
            self.assertEqual(_count_rr_client(conf), 0)

    def test_without_rr_graph_keeps_full_mesh(self):
        emulator, base, ibgp = self._new_emulator()
        asobj = base.createAutonomousSystem(154)
        asobj.createNetwork("net0")
        for name in ("r0", "r1", "r2"):
            asobj.createRouter(name).joinNetwork("net0")

        emulator.render()

        self.assertEqual(
            self._graph_edges(emulator, ibgp, 154),
            {
                frozenset(("Router: r0", "Router: r1")),
                frozenset(("Router: r0", "Router: r2")),
                frozenset(("Router: r1", "Router: r2")),
            },
        )

    def test_single_rr_clients_only_peer_route_reflector(self):
        emulator, base, ibgp = self._new_emulator()
        asobj = base.createAutonomousSystem(151)
        asobj.createNetwork("net0")
        routers = {}
        for name in ("r0", "r1", "r2"):
            routers[name] = asobj.createRouter(name).joinNetwork("net0")
        routers["r0"].makeRouteReflector(True)

        emulator.render()

        rr_conf = self._bird_conf(base, 151, "r0")
        self.assertEqual(_count_neighbors(rr_conf, 151), 2)
        self.assertEqual(_count_rr_client(rr_conf), 2)

        for router_name in ("r1", "r2"):
            conf = self._bird_conf(base, 151, router_name)
            self.assertEqual(_count_neighbors(conf, 151), 1)
            self.assertEqual(_count_rr_client(conf), 0)

        self.assertEqual(
            self._graph_edges(emulator, ibgp, 151),
            {
                frozenset(("Router: r0", "Router: r1")),
                frozenset(("Router: r0", "Router: r2")),
            },
        )


    def test_multiple_rrs_mesh_and_reflect_clients(self):
        emulator, base, _ = self._new_emulator()
        asobj = base.createAutonomousSystem(152)
        asobj.createNetwork("net0")
        routers = {}
        for name in ("r0", "r1", "r2", "r3"):
            routers[name] = asobj.createRouter(name).joinNetwork("net0")
        routers["r0"].makeRouteReflector(True)
        routers["r1"].makeRouteReflector(True)

        emulator.render()

        for router_name in ("r0", "r1"):
            conf = self._bird_conf(base, 152, router_name)
            self.assertEqual(_count_neighbors(conf, 152), 3)
            self.assertEqual(_count_rr_client(conf), 2)

        for router_name in ("r2", "r3"):
            conf = self._bird_conf(base, 152, router_name)
            self.assertEqual(_count_neighbors(conf, 152), 2)
            self.assertEqual(_count_rr_client(conf), 0)

    def test_explicit_cluster_id_is_written_to_rr_sessions(self):
        emulator, base, _ = self._new_emulator()
        cluster_id = "10.10.10.10"
        asobj = base.createAutonomousSystem(153)
        asobj.createNetwork("net0")
        asobj.createCluster(cluster_id)

        r0 = asobj.createRouter("r0").joinNetwork("net0").joinBgpCluster(cluster_id)
        r1 = asobj.createRouter("r1").joinNetwork("net0").joinBgpCluster(cluster_id)
        r2 = asobj.createRouter("r2").joinNetwork("net0").joinBgpCluster(cluster_id)
        r0.makeRouteReflector(True)

        emulator.render()

        rr_conf = self._bird_conf(base, 153, "r0")
        self.assertEqual(_count_neighbors(rr_conf, 153), 2)
        self.assertEqual(_count_rr_client(rr_conf), 2)
        self.assertEqual(_count_rr_cluster_id(rr_conf, cluster_id), 2)

        for router_name in ("r1", "r2"):
            conf = self._bird_conf(base, 153, router_name)
            self.assertEqual(_count_neighbors(conf, 153), 1)
            self.assertEqual(_count_rr_client(conf), 0)


if __name__ == "__main__":
    unittest.main()
