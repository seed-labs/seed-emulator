from __future__ import annotations

import random
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple, Union


try:
    import networkx as nx
except ImportError:  # pragma: no cover - exercised only when dependency is absent.
    nx = None


GraphModel = Union[str, Callable[..., Any]]


class TopologyGenerationError(Exception):
    """Raised when an autonomous-system topology cannot be generated or validated."""


def _require_networkx():
    if nx is None:
        raise TopologyGenerationError("Autonomous-system topology generation requires networkx")
    return nx


def _call_graph_model(model: GraphModel, n: int, params: Dict[str, Any], seed: Optional[int]):
    nx_mod = _require_networkx()
    params = dict(params or {})

    if callable(model):
        return model(n=n, seed=seed, **params)

    model_name = str(model).strip().lower()
    registry: Dict[str, Callable[[], Any]] = {
        "cycle": lambda: nx_mod.cycle_graph(n),
        "path": lambda: nx_mod.path_graph(n),
        "complete": lambda: nx_mod.complete_graph(n),
        "random": lambda: nx_mod.erdos_renyi_graph(n=n, seed=seed, **params),
        "erdos_renyi": lambda: nx_mod.erdos_renyi_graph(n=n, seed=seed, **params),
        "gnp_random": lambda: nx_mod.gnp_random_graph(n=n, seed=seed, **params),
        "regular": lambda: nx_mod.random_regular_graph(n=n, seed=seed, **params),
        "random_regular": lambda: nx_mod.random_regular_graph(n=n, seed=seed, **params),
        "small_world": lambda: nx_mod.connected_watts_strogatz_graph(n=n, seed=seed, **params),
        "watts_strogatz": lambda: nx_mod.watts_strogatz_graph(n=n, seed=seed, **params),
        "connected_watts_strogatz": lambda: nx_mod.connected_watts_strogatz_graph(n=n, seed=seed, **params),
        "scale_free": lambda: nx_mod.barabasi_albert_graph(n=n, seed=seed, **params),
        "barabasi_albert": lambda: nx_mod.barabasi_albert_graph(n=n, seed=seed, **params),
        "powerlaw_cluster": lambda: nx_mod.powerlaw_cluster_graph(n=n, seed=seed, **params),
    }

    if model_name not in registry:
        raise TopologyGenerationError("unsupported NetworkX graph model: {}".format(model))

    try:
        return registry[model_name]()
    except TypeError as exc:
        raise TopologyGenerationError("invalid parameters for graph model {}: {}".format(model, exc)) from exc


class AutonomousSystemTopology:
    """A generated autonomous-system topology independent from any ASN or IX mapping."""

    def __init__(
        self,
        graph: Any,
        ebgp_routers: List[str],
        ebgp_to_internal: Dict[str, str],
        seed: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        _require_networkx()
        self._graph = graph.copy()
        self._ebgp_routers = [str(router) for router in ebgp_routers]
        self._ebgp_to_internal = {str(router): str(internal) for router, internal in ebgp_to_internal.items()}
        self.seed = seed
        self.metadata = dict(metadata or {})

    @classmethod
    def from_networkx(
        cls,
        internal_graph: Any,
        ebgp_router_count: int,
        ebgp_attach_policy: str = "spread",
        ebgp_to_internal: Optional[Dict[str, str]] = None,
        ebgp_router_prefix: str = "r",
        seed: Optional[int] = None,
    ) -> "AutonomousSystemTopology":
        generator = AutonomousSystemTopologyGenerator(
            ebgp_router_count=ebgp_router_count,
            internal_graph=internal_graph,
            ebgp_attach_policy=ebgp_attach_policy,
            ebgp_to_internal=ebgp_to_internal,
            ebgp_router_prefix=ebgp_router_prefix,
            seed=seed,
        )
        return generator.generate()

    def graph(self):
        return self._graph.copy()

    def to_networkx(self):
        return self.graph()

    def internal_graph(self):
        nx_mod = _require_networkx()
        return self._graph.subgraph(self.internal_routers()).copy()

    def routers(self) -> List[str]:
        return sorted(str(node) for node in self._graph.nodes)

    def ebgp_routers(self) -> List[str]:
        return list(self._ebgp_routers)

    def internal_routers(self) -> List[str]:
        return sorted(str(node) for node, data in self._graph.nodes(data=True) if data.get("role") == "internal")

    def links(self) -> List[Tuple[str, str]]:
        return sorted((str(a), str(b)) for a, b in self._graph.edges)

    def link_networks(self) -> List[Tuple[str, str, str]]:
        return [(a, b, self.network_name_for_link(a, b)) for a, b in self.links()]

    def network_name_for_link(self, a: str, b: str) -> str:
        return self._network_name(str(a), str(b))

    def ebgp_to_internal(self) -> Dict[str, str]:
        return dict(self._ebgp_to_internal)

    def validate(self) -> None:
        nx_mod = _require_networkx()

        if len(self._graph.nodes) == 0:
            raise TopologyGenerationError("autonomous-system topology has no routers")

        if not nx_mod.is_connected(self._graph):
            raise TopologyGenerationError("autonomous-system topology is not connected")

        if list(nx_mod.selfloop_edges(self._graph)):
            raise TopologyGenerationError("autonomous-system topology contains self loops")

        router_names = self.routers()
        if len(router_names) != len(set(router_names)):
            raise TopologyGenerationError("autonomous-system topology contains duplicate router names")

        internal = set(self.internal_routers())
        ebgp_routers = set(self.ebgp_routers())
        if not internal:
            raise TopologyGenerationError("autonomous-system topology has no internal routers")
        if not ebgp_routers:
            raise TopologyGenerationError("autonomous-system topology has no eBGP routers")

        for ebgp_router in ebgp_routers:
            if ebgp_router not in self._ebgp_to_internal:
                raise TopologyGenerationError("eBGP router {} is not attached to an internal router".format(ebgp_router))
            internal_router = self._ebgp_to_internal[ebgp_router]
            if internal_router not in internal:
                raise TopologyGenerationError(
                    "eBGP router {} attaches to unknown internal router {}".format(ebgp_router, internal_router)
                )
            if not self._graph.has_edge(ebgp_router, internal_router):
                raise TopologyGenerationError(
                    "eBGP router {} is missing graph link to {}".format(ebgp_router, internal_router)
                )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "seed": self.seed,
            "metadata": dict(self.metadata),
            "ebgp_routers": self.ebgp_routers(),
            "internal_routers": self.internal_routers(),
            "ebgp_to_internal": self.ebgp_to_internal(),
            "links": [list(link) for link in self.links()],
            "link_networks": [
                {"endpoints": [a, b], "network": network}
                for a, b, network in self.link_networks()
            ],
        }

    def to_yaml(self, path: Union[str, Path]) -> None:
        import yaml

        with open(path, "w", encoding="utf-8") as file:
            yaml.safe_dump(self.to_dict(), file, sort_keys=False)

    def to_dot(self, path: Union[str, Path]) -> None:
        nx_mod = _require_networkx()
        nx_mod.drawing.nx_pydot.write_dot(self._graph, path)

    def summary(self) -> str:
        return "{} eBGP routers, {} internal routers, {} links".format(
            len(self.ebgp_routers()),
            len(self.internal_routers()),
            len(self.links()),
        )

    def _network_name(self, a: str, b: str) -> str:
        left, right = sorted([a, b])
        name = "n_{}_{}".format(self._short_router_name(left), self._short_router_name(right))
        assert len(name) <= 15, "generated network name is too long for a Linux interface: {}".format(name)
        return name

    def _short_router_name(self, name: str) -> str:
        if name.startswith("core"):
            return "c{}".format(name[4:])
        return name.replace("-", "_")


class AutonomousSystemTopologyGenerator:
    """Generate autonomous-system topologies using NetworkX internal graph models."""

    def __init__(
        self,
        ebgp_router_count: int,
        internal_router_count: int = 4,
        graph_model: GraphModel = "small_world",
        graph_params: Optional[Dict[str, Any]] = None,
        internal_graph: Any = None,
        seed: Optional[int] = None,
        ebgp_attach_policy: str = "spread",
        ebgp_to_internal: Optional[Dict[str, str]] = None,
        ebgp_router_prefix: str = "r",
        internal_router_prefix: str = "core",
        require_connected: bool = True,
        max_attempts: int = 100,
    ):
        self.ebgp_router_count = int(ebgp_router_count)
        self.internal_router_count = int(internal_router_count)
        self.graph_model = graph_model
        self.graph_params = dict(graph_params or self._default_graph_params(graph_model))
        self.internal_graph = internal_graph
        self.seed = seed
        self.ebgp_attach_policy = str(ebgp_attach_policy)
        self.ebgp_to_internal = {str(router): str(internal) for router, internal in ebgp_to_internal.items()} if ebgp_to_internal else None
        self.ebgp_router_prefix = str(ebgp_router_prefix)
        self.internal_router_prefix = str(internal_router_prefix)
        self.require_connected = bool(require_connected)
        self.max_attempts = int(max_attempts)

    @classmethod
    def from_graph(
        cls,
        graph: Any,
        ebgp_router_count: int,
        **kwargs,
    ) -> "AutonomousSystemTopologyGenerator":
        return cls(ebgp_router_count=ebgp_router_count, internal_graph=graph, **kwargs)

    def generate(self) -> AutonomousSystemTopology:
        nx_mod = _require_networkx()
        self._validate_inputs()

        ebgp_routers = self._build_ebgp_routers()
        internal_graph = self._generate_internal_graph()
        internal_graph = self._relabel_internal_graph(internal_graph)
        internal_routers = sorted(str(node) for node in internal_graph.nodes)
        ebgp_to_internal = self.ebgp_to_internal or self._select_ebgp_attachments(ebgp_routers, internal_graph)

        graph = nx_mod.Graph()
        for router in internal_routers:
            graph.add_node(router, role="internal")
        for a, b in internal_graph.edges:
            graph.add_edge(str(a), str(b))

        for ebgp_router in ebgp_routers:
            graph.add_node(ebgp_router, role="ebgp")
            internal_router = ebgp_to_internal[ebgp_router]
            graph.add_edge(ebgp_router, internal_router)

        topology = AutonomousSystemTopology(
            graph=graph,
            ebgp_routers=ebgp_routers,
            ebgp_to_internal=ebgp_to_internal,
            seed=self.seed,
            metadata={
                "graph_model": self.graph_model if isinstance(self.graph_model, str) else getattr(self.graph_model, "__name__", "callable"),
                "graph_params": dict(self.graph_params),
                "ebgp_attach_policy": self.ebgp_attach_policy,
            },
        )
        topology.validate()
        return topology

    def _validate_inputs(self) -> None:
        if self.ebgp_router_count <= 0:
            raise TopologyGenerationError("ebgp_router_count must be positive")
        if self.internal_graph is None and self.internal_router_count <= 0:
            raise TopologyGenerationError("internal_router_count must be positive")
        if self.max_attempts <= 0:
            raise TopologyGenerationError("max_attempts must be positive")

    def _build_ebgp_routers(self) -> List[str]:
        return ["{}{}".format(self.ebgp_router_prefix, index) for index in range(self.ebgp_router_count)]

    def _generate_internal_graph(self):
        nx_mod = _require_networkx()
        if self.internal_graph is not None:
            graph = nx_mod.Graph(self.internal_graph)
            if self.require_connected and not nx_mod.is_connected(graph):
                raise TopologyGenerationError("provided internal graph is not connected")
            return graph

        last_error = None
        for attempt in range(self.max_attempts):
            attempt_seed = None if self.seed is None else self.seed + attempt
            try:
                graph = nx_mod.Graph(
                    _call_graph_model(self.graph_model, self.internal_router_count, self.graph_params, attempt_seed)
                )
            except TopologyGenerationError as exc:
                last_error = exc
                break

            if not self.require_connected or nx_mod.is_connected(graph):
                return graph

        if last_error is not None:
            raise last_error
        raise TopologyGenerationError(
            "could not generate a connected internal graph after {} attempts".format(self.max_attempts)
        )

    def _relabel_internal_graph(self, graph):
        nx_mod = _require_networkx()
        mapping = {}
        for index, node in enumerate(sorted(graph.nodes, key=str)):
            name = str(node)
            if not name.startswith(self.internal_router_prefix):
                name = "{}{}".format(self.internal_router_prefix, index)
            mapping[node] = name
        return nx_mod.relabel_nodes(graph, mapping, copy=True)

    def _select_ebgp_attachments(self, ebgp_routers: List[str], internal_graph) -> Dict[str, str]:
        internal_routers = sorted(str(node) for node in internal_graph.nodes)
        if not internal_routers:
            raise TopologyGenerationError("cannot attach eBGP routers without internal routers")

        policy = self.ebgp_attach_policy.lower()
        if policy == "manual":
            raise TopologyGenerationError("ebgp_attach_policy=manual requires ebgp_to_internal")

        sorted_ebgp_routers = sorted(ebgp_routers)
        if policy in {"spread", "round_robin"}:
            return {router: internal_routers[index % len(internal_routers)] for index, router in enumerate(sorted_ebgp_routers)}

        if policy == "random":
            rng = random.Random(self.seed)
            return {router: rng.choice(internal_routers) for router in sorted_ebgp_routers}

        if policy == "degree":
            ranked = sorted(internal_graph.degree, key=lambda item: (-item[1], str(item[0])))
            ranked_nodes = [str(node) for node, _degree in ranked]
            return {router: ranked_nodes[index % len(ranked_nodes)] for index, router in enumerate(sorted_ebgp_routers)}

        raise TopologyGenerationError("unsupported eBGP attachment policy: {}".format(self.ebgp_attach_policy))

    def _default_graph_params(self, graph_model: GraphModel) -> Dict[str, Any]:
        if not isinstance(graph_model, str):
            return {}

        model = graph_model.strip().lower()
        if model in {"random", "erdos_renyi", "gnp_random"}:
            return {"p": 0.4}
        if model in {"regular", "random_regular"}:
            return {"d": 2}
        if model in {"small_world", "connected_watts_strogatz", "watts_strogatz"}:
            return {"k": 2, "p": 0.25}
        if model in {"scale_free", "barabasi_albert"}:
            return {"m": 1}
        if model == "powerlaw_cluster":
            return {"m": 1, "p": 0.25}
        return {}
