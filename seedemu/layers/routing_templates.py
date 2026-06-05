from __future__ import annotations

from typing import Dict


BirdFileTemplates: Dict[str, str] = {}

BirdFileTemplates["rs_base"] = """\
router id {routerId};
ipv4 table t_direct;
protocol device {{
}}
"""

BirdFileTemplates["router_direct_interface"] = """
    interface "{interfaceName}";
"""

BirdFileTemplates["router_base"] = """\
router id {routerId};
ipv4 table t_direct;
protocol device {{
}}
protocol kernel {{
    ipv4 {{
        import all;
        export all;
    }};
    learn;
}}
"""

BirdFileTemplates["direct_protocol"] = """
    ipv4 {{
        table t_direct;
        import all;
    }};
{interfaces}
"""

BirdFileTemplates["ospf_body"] = """
    ipv4 {{
        table t_ospf;
        import all;
        export all;
    }};
    area 0 {{
{interfaces}
    }};
"""

BirdFileTemplates["ospf_interface"] = """\
        interface "{interfaceName}" {{ hello 1; dead count 2; }};
"""

BirdFileTemplates["ospf_stub_interface"] = """\
        interface "{interfaceName}" {{ stub; }};
"""

BirdFileTemplates["bgp_commons"] = """\
define LOCAL_COMM = ({localAsn}, 0, 0);
define CUSTOMER_COMM = ({localAsn}, 1, 0);
define PEER_COMM = ({localAsn}, 2, 0);
define PROVIDER_COMM = ({localAsn}, 3, 0);
"""

BirdFileTemplates["rs_peer"] = """\
    ipv4 {{
        import all;
        export all;
    }};
    rs client;
    local {localAddress} as {localAsn};
    neighbor {peerAddress} as {peerAsn};
"""

BirdFileTemplates["router_peer"] = """\
    ipv4 {{
        table t_bgp;
        import {importClause};
        export {exportClause};
{nextHopSelfClause}    }};
    local {localAddress} as {localAsn};
    neighbor {peerAddress} as {peerAsn};
"""

BirdFileTemplates["ibgp_peer"] = """\
    ipv4 {{
        table t_bgp;
        import all;
        export all;
        igp table {igpTable};
    }};
    local {localAddress} as {localAsn};
    neighbor {peerAddress} as {peerAsn};
"""

BirdFileTemplates["connected_export_filter"] = (
    "filter { bgp_large_community.add(LOCAL_COMM); bgp_local_pref = 40; accept; }"
)


FrrFileTemplates: Dict[str, str] = {}

FrrFileTemplates["managed_block"] = """\
! ===== seedemu-routing-frr begin =====
frr defaults traditional
service integrated-vtysh-config
hostname {hostname}
!
{body}
! ===== seedemu-routing-frr end =====
"""

FrrFileTemplates["start_script"] = """\
#!/bin/bash
set -e
sed -i 's/bgpd=no/bgpd=yes/' /etc/frr/daemons
sed -i 's/zebra=no/zebra=yes/' /etc/frr/daemons
sed -i 's/staticd=no/staticd=yes/' /etc/frr/daemons
sed -i 's/ospfd=no/ospfd=yes/' /etc/frr/daemons
service frr start
"""

FrrFileTemplates["route_map_connected"] = """\
route-map RM_CONNECTED_TO_BGP permit 10
 set large-community {local_comm} additive
 set local-preference 40
!
"""

FrrFileTemplates["community_lists"] = """\
bgp large-community-list standard LC_LOCAL permit {local_comm}
bgp large-community-list standard LC_CUSTOMER permit {customer_comm}
bgp large-community-list standard LC_LOCAL_OR_CUSTOMER permit {local_comm}
bgp large-community-list standard LC_LOCAL_OR_CUSTOMER permit {customer_comm}
!
"""

FrrFileTemplates["import_route_map"] = """\
route-map {name} permit 10
 set large-community {community} additive
 set local-preference {local_pref}
!
"""

FrrFileTemplates["export_route_map_local_customer"] = """\
route-map {name} permit 10
 match large-community LC_LOCAL_OR_CUSTOMER
!
route-map {name} deny 100
!
"""

FrrFileTemplates["export_route_map_all"] = """\
route-map {name} permit 10
!
"""

FrrFileTemplates["ospf_interface_active"] = """\
interface {interface}
 ip ospf area 0
 ip ospf hello-interval 1
 ip ospf dead-interval 2
!
"""

FrrFileTemplates["ospf_interface_passive"] = """\
interface {interface}
 ip ospf area 0
 ip ospf passive
!
"""

FrrFileTemplates["ospf_router"] = """\
router ospf
 ospf router-id {router_id}
!
"""
