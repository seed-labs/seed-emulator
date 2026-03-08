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
        routing = Routing()
        ospf = Ospf()
        ibgp = Ibgp()

        emulator.addLayer(base)
        emulator.addLayer(routing)
        emulator.addLayer(ospf)
        emulator.addLayer(ibgp)

        return emulator, base, ibgp

    def _render_three_router_as(self, enable_rr: bool = False):
        emulator, base, ibgp = self._new_emulator()

        asn = 150
        asobj = base.createAutonomousSystem(asn)
        asobj.createNetwork("net0")

        routers = {}
        for name in ("r0", "r1", "r2"):
            routers[name] = asobj.createRouter(name).joinNetwork("net0")

        if enable_rr:
            routers["r0"].makeRouteReflector(True)

        emulator.render()
        return emulator, base, ibgp, asn

    def _render_multi_rr_as(self):
        emulator, base, ibgp = self._new_emulator()

        asn = 151
        asobj = base.createAutonomousSystem(asn)
        asobj.createNetwork("net0")

        routers = {}
        for name in ("r0", "r1", "r2", "r3"):
            routers[name] = asobj.createRouter(name).joinNetwork("net0")

        routers["r0"].makeRouteReflector(True)
        routers["r1"].makeRouteReflector(True)

        emulator.render()
        return emulator, base, ibgp, asn

    def _render_component_mixed_as(self):
        emulator, base, ibgp = self._new_emulator()

        asn = 152
        asobj = base.createAutonomousSystem(asn)
        asobj.createNetwork("net_a")
        asobj.createNetwork("net_b")

        r0 = asobj.createRouter("r0").joinNetwork("net_a")
        asobj.createRouter("r1").joinNetwork("net_a")
        asobj.createRouter("r2").joinNetwork("net_b")
        asobj.createRouter("r3").joinNetwork("net_b")
        r0.makeRouteReflector(True)

        emulator.render()
        return emulator, base, ibgp, asn

    def _render_clustered_rr_as(self, reflection_mode: str):
        emulator, base, ibgp = self._new_emulator()

        asn = 153
        cluster_id = "10.10.10.10"
        asobj = base.createAutonomousSystem(asn)
        asobj.createNetwork("net0")
        asobj.createCluster(cluster_id)

        routers = {}
        for name in ("r0", "r1", "r2"):
            routers[name] = asobj.createRouter(name).joinNetwork("net0").joinBgpCluster(cluster_id)

        routers["r0"].makeRouteReflector(True)
        ibgp.setReflectionMode(reflection_mode)

        emulator.render()
        return emulator, base, ibgp, asn, cluster_id

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
        _, base, _, asn = self._render_three_router_as(enable_rr=False)

        for router_name in ("r0", "r1", "r2"):
            conf = self._bird_conf(base, asn, router_name)
            self.assertEqual(_count_neighbors(conf, asn), 2)
            self.assertEqual(_count_rr_client(conf), 0)

    def test_with_single_rr_clients_only_peer_rr(self):
        emulator, base, ibgp, asn = self._render_three_router_as(enable_rr=True)

        rr_conf = self._bird_conf(base, asn, "r0")
        self.assertEqual(_count_neighbors(rr_conf, asn), 2)
        self.assertEqual(_count_rr_client(rr_conf), 2)

        for router_name in ("r1", "r2"):
            conf = self._bird_conf(base, asn, router_name)
            self.assertEqual(_count_neighbors(conf, asn), 1)
            self.assertEqual(_count_rr_client(conf), 0)

        self.assertEqual(
            self._graph_edges(emulator, ibgp, asn),
            {
                frozenset(("Router: r0", "Router: r1")),
                frozenset(("Router: r0", "Router: r2")),
            },
        )

    def test_with_multiple_rrs_clients_peer_all_route_reflectors(self):
        _, base, _, asn = self._render_multi_rr_as()

        for router_name in ("r0", "r1"):
            conf = self._bird_conf(base, asn, router_name)
            self.assertEqual(_count_neighbors(conf, asn), 3)
            self.assertEqual(_count_rr_client(conf), 2)

        for router_name in ("r2", "r3"):
            conf = self._bird_conf(base, asn, router_name)
            self.assertEqual(_count_neighbors(conf, asn), 2)
            self.assertEqual(_count_rr_client(conf), 0)

    def test_graph_keeps_full_mesh_for_non_rr_component(self):
        emulator, _, ibgp, asn = self._render_component_mixed_as()

        self.assertEqual(
            self._graph_edges(emulator, ibgp, asn),
            {
                frozenset(("Router: r0", "Router: r1")),
                frozenset(("Router: r2", "Router: r3")),
            },
        )

    def test_cluster_ids_are_ignored_in_simple_mode(self):
        _, base, _, asn, cluster_id = self._render_clustered_rr_as("simple")

        rr_conf = self._bird_conf(base, asn, "r0")
        self.assertEqual(_count_neighbors(rr_conf, asn), 2)
        self.assertEqual(_count_rr_client(rr_conf), 2)
        self.assertEqual(_count_rr_cluster_id(rr_conf, cluster_id), 0)

    def test_clustered_mode_uses_cluster_ids(self):
        emulator, base, ibgp, asn, cluster_id = self._render_clustered_rr_as("clustered")

        rr_conf = self._bird_conf(base, asn, "r0")
        self.assertEqual(_count_neighbors(rr_conf, asn), 2)
        self.assertEqual(_count_rr_client(rr_conf), 2)
        self.assertEqual(_count_rr_cluster_id(rr_conf, cluster_id), 2)

        for router_name in ("r1", "r2"):
            conf = self._bird_conf(base, asn, router_name)
            self.assertEqual(_count_neighbors(conf, asn), 1)
            self.assertEqual(_count_rr_client(conf), 0)

        self.assertEqual(
            self._graph_edges(emulator, ibgp, asn),
            {
                frozenset(("Router: r0", "Router: r1")),
                frozenset(("Router: r0", "Router: r2")),
            },
        )


if __name__ == "__main__":
    unittest.main()
