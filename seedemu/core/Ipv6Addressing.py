from __future__ import annotations

from ipaddress import IPv6Network
from typing import Dict, Iterable, List, Set, Union

from .Addressing import normalizePrefix


DEFAULT_IPV6_ROOT_PREFIX = "2000::/12"
DEFAULT_IPV6_INFRA_PREFIX = "2000:ffff::/48"


class Ipv6Addressing:
    """Deterministic IPv6 prefix allocator for optional dual-stack emulations."""

    def __init__(self, rootPrefix: str = DEFAULT_IPV6_ROOT_PREFIX, reservedPrefixes: Iterable[str] = None):
        self.__root = IPv6Network(normalizePrefix(rootPrefix))
        assert self.__root.prefixlen <= 48, "IPv6 root prefix must be /48 or shorter"
        self.__used_as_indices: Set[int] = set()
        self.__as_prefixes: Dict[int, IPv6Network] = {}
        self.__as_net_indices: Dict[int, int] = {}
        self.__as_net_used: Dict[int, Set[int]] = {}
        self.__ix_prefixes: Dict[int, IPv6Network] = {}
        self.__ix_indices: Set[int] = set()
        self.__allocated_prefixes: Set[IPv6Network] = set()
        self.__as_prefix_bits = 48 - self.__root.prefixlen
        self.__network_bits = 16
        self.__ix_base = 1 << max(self.__as_prefix_bits - 1, 0)
        self.__reserved_prefixes: List[IPv6Network] = []

        if reservedPrefixes is None:
            reservedPrefixes = [DEFAULT_IPV6_INFRA_PREFIX]
        for prefix in reservedPrefixes:
            self.reservePrefix(prefix)

    def getRootPrefix(self) -> IPv6Network:
        return self.__root

    def getReservedPrefixes(self) -> List[IPv6Network]:
        return list(self.__reserved_prefixes)

    def __is_outside_root(self, prefix: IPv6Network) -> bool:
        if prefix.subnet_of(self.__root):
            return False
        assert not prefix.overlaps(self.__root), "IPv6 prefix {} overlaps root prefix {}".format(prefix, self.__root)
        return True

    def claimPrefix(self, prefix: Union[str, IPv6Network]) -> Ipv6Addressing:
        claimed = prefix if isinstance(prefix, IPv6Network) else IPv6Network(normalizePrefix(prefix))
        if self.__is_outside_root(claimed):
            return self
        assert self.__is_available(claimed), "IPv6 prefix {} overlaps an allocated prefix".format(claimed)
        self.__allocated_prefixes.add(claimed)
        return self

    def reservePrefix(self, prefix: Union[str, IPv6Network]) -> Ipv6Addressing:
        reserved = prefix if isinstance(prefix, IPv6Network) else IPv6Network(normalizePrefix(prefix))
        if self.__is_outside_root(reserved):
            return self
        self.claimPrefix(reserved)
        self.__reserved_prefixes.append(reserved)
        return self

    def reserveAsNetworkPrefix(self, asn: int, prefix: Union[str, IPv6Network]) -> Ipv6Addressing:
        network = prefix if isinstance(prefix, IPv6Network) else IPv6Network(normalizePrefix(prefix))
        if self.__is_outside_root(network):
            return self

        as_prefix = self.assignAsPrefix(asn)
        if network.subnet_of(as_prefix):
            self.__claim_as_network_prefix(asn, as_prefix, network)
            return self

        return self.claimPrefix(network)

    def __prefix_from_index(self, index: int, prefixlen: int) -> IPv6Network:
        child_bits = prefixlen - self.__root.prefixlen
        assert child_bits >= 0, "child prefix must be within IPv6 root"
        assert index >= 0 and index < (1 << child_bits), "IPv6 prefix index out of root range"
        base = int(self.__root.network_address)
        shift = 128 - prefixlen
        return IPv6Network((base + (index << shift), prefixlen))

    def __is_available(self, prefix: IPv6Network) -> bool:
        return all(not prefix.overlaps(used) for used in self.__allocated_prefixes)

    def __claim_as_network_prefix(self, asn: int, as_prefix: IPv6Network, prefix: IPv6Network) -> None:
        assert prefix.prefixlen >= 64, "AS IPv6 network prefix {} must be /64 or longer".format(prefix)
        base = int(as_prefix.network_address)
        first = (int(prefix.network_address) - base) >> 64
        last = (int(prefix.broadcast_address) - base) >> 64
        used = self.__as_net_used.setdefault(asn, set())
        for index in range(first, last + 1):
            assert index not in used, "IPv6 AS{} network prefix {} overlaps an allocated /64".format(asn, prefix)
        used.update(range(first, last + 1))

    def __claim_index(self, preferred: int, used: Set[int], limit: int, prefixlen: int) -> int:
        assert limit > 0, "IPv6 root prefix does not have enough allocation space"
        index = preferred % limit
        while index in used or not self.__is_available(self.__prefix_from_index(index, prefixlen)):
            index = (index + 1) % limit
            assert index != preferred % limit, "IPv6 prefix allocation exhausted"
        used.add(index)
        return index

    def assignAsPrefix(self, asn: int) -> IPv6Network:
        if asn not in self.__as_prefixes:
            limit = 1 << self.__as_prefix_bits
            preferred = int(asn)
            index = self.__claim_index(preferred, self.__used_as_indices, limit, 48)
            self.__as_prefixes[asn] = self.__prefix_from_index(index, 48)
            self.__allocated_prefixes.add(self.__as_prefixes[asn])
            self.__as_net_indices[asn] = 0
            self.__as_net_used.setdefault(asn, set())
        return self.__as_prefixes[asn]

    def nextAsNetworkPrefix(self, asn: int) -> IPv6Network:
        as_prefix = self.assignAsPrefix(asn)
        index = self.__as_net_indices.get(asn, 0)
        used = self.__as_net_used.setdefault(asn, set())
        while index in used:
            index += 1
            assert index < (1 << self.__network_bits), "IPv6 /64 network allocation exhausted for AS{}".format(asn)
        used.add(index)
        self.__as_net_indices[asn] = index + 1
        base = int(as_prefix.network_address)
        return IPv6Network((base + (index << 64), 64))

    def assignIxPrefix(self, ixid: int) -> IPv6Network:
        if ixid not in self.__ix_prefixes:
            child_bits = 64 - self.__root.prefixlen
            limit = 1 << child_bits
            preferred = (self.__ix_base + int(ixid)) % limit
            index = self.__claim_index(preferred, self.__ix_indices, limit, 64)
            self.__ix_prefixes[ixid] = self.__prefix_from_index(index, 64)
            self.__allocated_prefixes.add(self.__ix_prefixes[ixid])
        return self.__ix_prefixes[ixid]
