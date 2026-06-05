from __future__ import annotations

from enum import Enum
from ipaddress import ip_address, ip_network
from typing import Iterable, List, Optional, TYPE_CHECKING, Tuple, Union

from .enums import NetworkType

if TYPE_CHECKING:
    from .Node import Interface, Node


class AddressFamily(Enum):
    """Address-family selector used by dual-stack aware services."""

    IPv4 = "ipv4"
    IPv6 = "ipv6"


def normalizeAddressFamily(family: Union[AddressFamily, str, int]) -> AddressFamily:
    """Normalize common address-family spellings to AddressFamily."""

    if isinstance(family, AddressFamily):
        return family

    value = str(family).strip().lower()
    if value in ("2", "4", "af_inet", "inet", "ip4", "ipv4", "v4"):
        return AddressFamily.IPv4
    if value in ("6", "10", "af_inet6", "inet6", "ip6", "ipv6", "v6"):
        return AddressFamily.IPv6

    raise ValueError("unsupported address family {}".format(family))


def _parseIpLiteral(value: Union[str, object]):
    candidate = str(value).strip()
    if candidate.startswith("[") and candidate.endswith("]"):
        candidate = candidate[1:-1].strip()
    return ip_address(candidate)


def normalizeAddressList(addrs: Iterable[Union[str, object]]) -> List[str]:
    """Normalize IPv4/IPv6 address literals while preserving list order."""

    return [str(_parseIpLiteral(addr)) for addr in addrs]


def normalizePrefix(prefix: Union[str, object], strict: bool = True) -> str:
    """Normalize an IPv4/IPv6 CIDR prefix literal."""

    value = str(prefix).strip()
    if "/" in value:
        addr, slash, prefix_len = value.partition("/")
        value = "{}{}{}".format(normalizeAddressList([addr])[0], slash, prefix_len.strip())
    return str(ip_network(value, strict=strict))


def normalizeAddressRecord(record: Union[str, object], trimNonAddressRecord: bool = False) -> str:
    """Normalize DNS-style A/AAAA record address literals.

    Non-address records are returned unchanged unless trimNonAddressRecord is
    set for callers whose historical API already trimmed those records.
    """

    value = str(record)
    parts = value.strip().split()
    if len(parts) >= 3 and parts[-2].upper() in ("A", "AAAA"):
        parts[-2] = parts[-2].upper()
        parsed = _parseIpLiteral(parts[-1])
        if parts[-2] == "A" and parsed.version != 4:
            raise ValueError("A record must use an IPv4 address: {}".format(record))
        if parts[-2] == "AAAA" and parsed.version != 6:
            raise ValueError("AAAA record must use an IPv6 address: {}".format(record))
        parts[-1] = str(parsed)
        return " ".join(parts)
    return value.strip() if trimNonAddressRecord else value


def _parseHostIpLiteral(host: Union[str, object]):
    try:
        return _parseIpLiteral(host)
    except ValueError:
        return None


def _formatBracketedIpv6Authority(value: str):
    if not value.startswith("["):
        return None

    end = value.find("]")
    if end < 0:
        raise ValueError("malformed bracketed IPv6 authority: {}".format(value))

    try:
        parsed = ip_address(value[1:end].strip())
    except ValueError:
        return None

    if parsed.version != 6:
        return None

    suffix = value[end + 1 :].strip()
    if suffix == "":
        return "[{}]".format(parsed)
    if suffix.startswith(":") and len(suffix) > 1 and suffix[1:].isdigit():
        return "[{}]{}".format(parsed, suffix)
    raise ValueError("malformed bracketed IPv6 authority: {}".format(value))


def _formatBracketedIpv6Host(value: str):
    if not value.startswith("["):
        return None

    end = value.find("]")
    if end < 0:
        raise ValueError("malformed bracketed IPv6 authority: {}".format(value))

    try:
        parsed = ip_address(value[1:end].strip())
    except ValueError:
        return None

    if parsed.version != 6:
        return None

    suffix = value[end + 1 :].strip()
    if suffix == "" or (suffix.startswith(":") and len(suffix) > 1 and suffix[1:].isdigit()):
        return "[{}]".format(parsed)
    raise ValueError("malformed bracketed IPv6 authority: {}".format(value))


def _formatHostWithExplicitPort(value: str):
    bracketed_host = _formatBracketedIpv6Host(value)
    if bracketed_host is not None:
        return bracketed_host

    if value.count(":") == 1:
        host, _old_port = value.rsplit(":", 1)
        if host.strip() and _old_port.strip():
            return formatHost(host)

    return formatHost(value)


def _formatTcpPort(port: Union[str, int]) -> str:
    value = str(port).strip()
    if value == "":
        raise ValueError("endpoint port must not be empty")
    if not value.isdigit():
        raise ValueError("endpoint port must be numeric: {}".format(port))
    return value


def getInterfaceAddress(iface: "Interface", family: Union[AddressFamily, str, int] = AddressFamily.IPv4):
    """Return an interface address for the requested address family."""

    selected = normalizeAddressFamily(family)
    if selected == AddressFamily.IPv4:
        return iface.getAddress()
    return iface.getIpv6Address() if iface.hasIpv6Address() else None


def hasInterfaceAddress(iface: "Interface", family: Union[AddressFamily, str, int] = AddressFamily.IPv4) -> bool:
    """Check if an interface has an address for the requested address family."""

    return getInterfaceAddress(iface, family) is not None


def nodeHasAddress(
    node: "Node",
    address: Union[str, object],
    family: Union[AddressFamily, str, int, None] = None,
) -> bool:
    """Check whether a node has an IPv4 or IPv6 address literal."""

    requested = _parseIpLiteral(address)
    if family is None:
        selected_family = AddressFamily.IPv4 if requested.version == 4 else AddressFamily.IPv6
    else:
        selected_family = normalizeAddressFamily(family)
        expected_version = 4 if selected_family == AddressFamily.IPv4 else 6
        if requested.version != expected_version:
            return False
    for iface in node.getInterfaces():
        iface_addr = getInterfaceAddress(iface, selected_family)
        if iface_addr is not None and str(iface_addr) == str(requested):
            return True
    return False


def nodeHasAddressInPrefix(
    node: "Node",
    prefix: Union[str, object],
    family: Union[AddressFamily, str, int, None] = None,
) -> bool:
    """Check whether any node address is inside an IPv4 or IPv6 prefix."""

    network = ip_network(normalizePrefix(prefix))
    if family is None:
        selected_family = AddressFamily.IPv4 if network.version == 4 else AddressFamily.IPv6
    else:
        selected_family = normalizeAddressFamily(family)
        expected_version = 4 if selected_family == AddressFamily.IPv4 else 6
        if network.version != expected_version:
            return False
    for iface in node.getInterfaces():
        iface_addr = getInterfaceAddress(iface, selected_family)
        if iface_addr is not None and iface_addr in network:
            return True
    return False


def _getNodeAddressCandidates(node: "Node"):
    ifaces = node.getInterfaces()
    assert len(ifaces) > 0, "Node {} has no IP address.".format(node.getName())

    local_ipv4 = None
    local_ipv6 = None
    fallback_ipv4 = None
    fallback_ipv6 = None

    for iface in ifaces:
        ipv4_addr = getInterfaceAddress(iface, AddressFamily.IPv4)
        ipv6_addr = getInterfaceAddress(iface, AddressFamily.IPv6)

        if fallback_ipv4 is None and ipv4_addr is not None:
            fallback_ipv4 = ipv4_addr
        if fallback_ipv6 is None and ipv6_addr is not None:
            fallback_ipv6 = ipv6_addr

        if iface.getNet().getType() == NetworkType.Local:
            if local_ipv4 is None and ipv4_addr is not None:
                local_ipv4 = ipv4_addr
            if local_ipv6 is None and ipv6_addr is not None:
                local_ipv6 = ipv6_addr

    return {
        "local": {
            AddressFamily.IPv4: local_ipv4,
            AddressFamily.IPv6: local_ipv6,
        },
        "fallback": {
            AddressFamily.IPv4: fallback_ipv4,
            AddressFamily.IPv6: fallback_ipv6,
        },
    }


def getNodeAddresses(node: "Node", preferLocal: bool = True) -> Tuple[object, object]:
    """Return preferred IPv4 and IPv6 addresses for a node.

    Local-network interfaces are preferred by default. When a requested family
    has no local address, the first address from any interface is returned.
    """

    candidates = _getNodeAddressCandidates(node)
    if not preferLocal:
        return (
            candidates["fallback"][AddressFamily.IPv4],
            candidates["fallback"][AddressFamily.IPv6],
        )

    local_ipv4 = candidates["local"][AddressFamily.IPv4]
    local_ipv6 = candidates["local"][AddressFamily.IPv6]
    fallback_ipv4 = candidates["fallback"][AddressFamily.IPv4]
    fallback_ipv6 = candidates["fallback"][AddressFamily.IPv6]
    return (local_ipv4 or fallback_ipv4, local_ipv6 or fallback_ipv6)


def getNodeAddress(
    node: "Node",
    family: Union[AddressFamily, str, int] = AddressFamily.IPv4,
    preferLocal: bool = True,
):
    """Return the node address for one address family."""

    selected = normalizeAddressFamily(family)
    candidates = _getNodeAddressCandidates(node)
    if not preferLocal:
        return candidates["fallback"][selected]
    return candidates["local"][selected] or candidates["fallback"][selected]


def getNodePreferredAddress(
    node: "Node",
    families: Iterable[Union[AddressFamily, str, int]] = (AddressFamily.IPv4, AddressFamily.IPv6),
    preferLocal: bool = True,
):
    """Return the first available node address in the requested family order."""

    selected_families = [normalizeAddressFamily(family) for family in families]
    candidates = _getNodeAddressCandidates(node)
    scopes = ("local", "fallback") if preferLocal else ("fallback",)
    for scope in scopes:
        for family in selected_families:
            address = candidates[scope][family]
            if address is not None:
                return address
    return None


def formatHost(host: Union[str, object]) -> str:
    """Format a host/address for endpoint strings, bracketing IPv6 literals."""

    value = str(host).strip()
    authority = _formatBracketedIpv6Authority(value)
    if authority is not None:
        return authority

    parsed = _parseHostIpLiteral(value)
    if parsed is None:
        return value

    if parsed.version == 6:
        return "[{}]".format(parsed)
    return str(parsed)


def formatHostPort(host: Union[str, object], port: Union[str, int]) -> str:
    """Format host:port with RFC 3986 brackets for IPv6 literals."""

    return "{}:{}".format(_formatHostWithExplicitPort(str(host).strip()), _formatTcpPort(port))


def formatUrl(
    scheme: str,
    host: Union[str, object],
    port: Optional[Union[str, int]] = None,
    path: str = "",
) -> str:
    """Format a URL from address-family neutral pieces."""

    authority = formatHost(host) if port is None else formatHostPort(host, port)
    if path and not path.startswith(("/", "?", "#")):
        path = "/" + path
    return "{}://{}{}".format(scheme, authority, path)


def formatMultiaddr(host: Union[str, object], tcpPort: Union[str, int], peerId: str = None) -> str:
    """Format an IPFS/libp2p style multiaddr for IPv4 or IPv6 literals."""

    parsed = _parseHostIpLiteral(host)
    if parsed is None:
        raise ValueError("multiaddr host must be an IPv4/IPv6 literal: {}".format(host))

    proto = "ip6" if parsed.version == 6 else "ip4"
    out = "/{}/{}/tcp/{}".format(proto, parsed, _formatTcpPort(tcpPort))
    if peerId is not None:
        out += "/p2p/{}".format(peerId)
    return out
