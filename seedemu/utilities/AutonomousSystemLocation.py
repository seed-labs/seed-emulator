from __future__ import annotations

import random
from typing import Any, Dict, Iterable, List, Optional, Tuple


try:
    import networkx as nx
except ImportError:  # pragma: no cover - exercised only when dependency is absent.
    nx = None


Location = Dict[str, Any]
FixedLocationInput = Dict[str, Any]


class LocationGenerationError(Exception):
    """Raised when router locations cannot be generated for an AS topology."""


def _require_networkx():
    if nx is None:
        raise LocationGenerationError("Autonomous-system location generation requires networkx")
    return nx


class AutonomousSystemLocationGenerator:
    """Generate router locations for an existing autonomous-system topology.

    This generator is intentionally separate from AutonomousSystemTopologyGenerator.
    The topology generator decides which routers and links exist; this class only
    assigns geographic coordinates after that topology has already been generated.

    Known router locations are fixed. Missing router locations are initialized in
    the bounding area of the fixed routers, then adjusted with NetworkX
    spring_layout while keeping the known locations unchanged.

    Fixed locations may use either:
      - {"lat": 40.7128, "lon": -74.0060}
      - {"latitude": 40.7128, "longitude": -74.0060}
      - {"y": 40.7128, "x": -74.0060}
      - (lat, lon)
    """

    def __init__(
        self,
        fixed_locations: Optional[Dict[str, FixedLocationInput]] = None,
        seed: Optional[int] = None,
        iterations: int = 100,
        default_span: float = 1.0,
        padding_ratio: float = 0.15,
        k: Optional[float] = None,
        weight: Optional[str] = "weight",
    ):
        self.fixed_locations = dict(fixed_locations or {})
        self.seed = seed
        self.iterations = int(iterations)
        self.default_span = float(default_span)
        self.padding_ratio = float(padding_ratio)
        self.k = k
        self.weight = weight

    def generate(
        self,
        topology_or_graph: Any,
        fixed_locations: Optional[Dict[str, FixedLocationInput]] = None,
    ) -> Dict[str, Location]:
        graph = self._get_graph(topology_or_graph)
        routers = sorted(str(node) for node in graph.nodes)
        if not routers:
            raise LocationGenerationError("cannot generate locations for an empty topology")

        merged_fixed = dict(self.fixed_locations)
        if fixed_locations:
            merged_fixed.update(fixed_locations)

        fixed_positions = self._normalize_fixed_locations(merged_fixed, routers)
        if fixed_positions:
            initial_positions = self._initial_positions(routers, fixed_positions)
            layout = _require_networkx().spring_layout(
                graph,
                pos=initial_positions,
                fixed=list(fixed_positions.keys()),
                iterations=self.iterations,
                seed=self.seed,
                k=self.k,
                weight=self.weight,
            )
        else:
            layout = _require_networkx().spring_layout(
                graph,
                iterations=self.iterations,
                seed=self.seed,
                k=self.k,
                weight=self.weight,
            )

        return self._format_locations(routers, layout, fixed_positions)

    def _get_graph(self, topology_or_graph: Any):
        nx_mod = _require_networkx()
        if hasattr(topology_or_graph, "graph") and callable(topology_or_graph.graph):
            return topology_or_graph.graph()
        return nx_mod.Graph(topology_or_graph)

    def _normalize_fixed_locations(
        self,
        fixed_locations: Dict[str, FixedLocationInput],
        routers: Iterable[str],
    ) -> Dict[str, Tuple[float, float]]:
        router_set = set(routers)
        positions: Dict[str, Tuple[float, float]] = {}

        for router, location in fixed_locations.items():
            router_name = str(router)
            if router_name not in router_set:
                raise LocationGenerationError(
                    "fixed location references unknown router: {}".format(router_name)
                )
            lat, lon = self._parse_location(location)
            positions[router_name] = (lon, lat)

        return positions

    def _parse_location(self, location: FixedLocationInput) -> Tuple[float, float]:
        if isinstance(location, dict):
            if "lat" in location and "lon" in location:
                return float(location["lat"]), float(location["lon"])
            if "latitude" in location and "longitude" in location:
                return float(location["latitude"]), float(location["longitude"])
            if "y" in location and "x" in location:
                return float(location["y"]), float(location["x"])
            raise LocationGenerationError(
                "fixed location dictionaries must contain lat/lon, latitude/longitude, or x/y"
            )

        if isinstance(location, (list, tuple)) and len(location) == 2:
            return float(location[0]), float(location[1])

        raise LocationGenerationError(
            "fixed locations must be dictionaries or two-item (lat, lon) sequences"
        )

    def _initial_positions(
        self,
        routers: List[str],
        fixed_positions: Dict[str, Tuple[float, float]],
    ) -> Dict[str, Tuple[float, float]]:
        rng = random.Random(self.seed)
        min_lon, max_lon, min_lat, max_lat = self._bounds(fixed_positions.values())
        positions = dict(fixed_positions)

        for router in routers:
            if router in positions:
                continue
            positions[router] = (
                rng.uniform(min_lon, max_lon),
                rng.uniform(min_lat, max_lat),
            )

        return positions

    def _bounds(self, positions: Iterable[Tuple[float, float]]) -> Tuple[float, float, float, float]:
        lon_values = [position[0] for position in positions]
        lat_values = [position[1] for position in positions]
        min_lon, max_lon = min(lon_values), max(lon_values)
        min_lat, max_lat = min(lat_values), max(lat_values)

        lon_span = max(max_lon - min_lon, self.default_span)
        lat_span = max(max_lat - min_lat, self.default_span)
        lon_padding = lon_span * self.padding_ratio
        lat_padding = lat_span * self.padding_ratio

        return (
            min_lon - lon_padding,
            max_lon + lon_padding,
            min_lat - lat_padding,
            max_lat + lat_padding,
        )

    def _format_locations(
        self,
        routers: List[str],
        layout: Dict[str, Tuple[float, float]],
        fixed_positions: Dict[str, Tuple[float, float]],
    ) -> Dict[str, Location]:
        locations: Dict[str, Location] = {}
        fixed_router_names = set(fixed_positions.keys())

        for router in routers:
            lon, lat = layout[router]
            locations[router] = {
                "lat": float(lat),
                "lon": float(lon),
                "source": "fixed" if router in fixed_router_names else "generated",
            }

        return locations
