"""Internet Simulator Constants."""

# Define constant strings and templates


class SimConstants:
    OUTDIR = "./output/{}"
    TEMPLATE_HOSTDIR = "./template/host"
    TEMPLATE_ROUTERDIR = "./template/router"
    ASNAME = 'as{}'
    IXNAME = 'ix{}'
    ASNETNAME = 'net_as{}'
    IXNETNAME = 'net_ix{}'
    BGPRouterNAME = 'rt_as{}_ix{}'
    RSNAME = 'rs_ix{}'
    HOSTNAME = 'host_{}_{}'


class FileTemplate():
    hostStartScript =  \
        """#!/bin/bash
  
ip route change default via {} dev eth0
service nginx start
tail -f /dev/null
"""

    routerStartScript =  \
        """#!/bin/bash
  
[ ! -d /run/bird ] && mkdir /run/bird
bird -d
"""

    birdConf_common =  \
        """protocol kernel {
    import none;
    export all;
}

protocol device {
}

protocol direct {
    interface "eth0";
}

"""

    birdConf_BGP = \
        """protocol bgp {{
    import all;
    export all;

    local    {} as {};
    neighbor {} as {};
}}

"""

    birdConf_BGP_RS = \
        """protocol bgp {{
    import all;
    export all;

    rs client;

    local    {} as {};
    neighbor {} as {};
}}

"""

    birdConf_IBGP = \
        """protocol bgp {{
    import all;
    export all;

    igp table t_ospf;

    local    {} as {};
    neighbor {} as {};
}}

"""

    birdConf_OSPF = \
        """table t_ospf;

protocol ospf {
    table t_ospf;

    import all;
    export all;

    area 0.0.0.0 {
        interface "eth0" {};
        interface "eth1" { stub; };
    };
}

"""

    docker_compose_host_entry = \
        """    {0}:
        build: {1}
        cap_add:
                - ALL
        networks:
            {2}:
                ipv4_address: {3}
"""

    docker_compose_router_entry = \
        """    {0}:
        build: {1}
        cap_add:
                - ALL
        sysctls:
                - net.ipv4.ip_forward=1
        networks:
{2}
"""

    docker_compose_interface_entry = \
        """            {}:
                ipv4_address: {}
"""

    docker_compose_network_entry = \
        """    {0}:
        ipam:
            config:
                - subnet: {1}/{2}
"""

    docker_compose_header = \
        """version: "3"

services:

    iib_base_router:
        build: ./base_router
        image: iib_base_router

    iib_base_host:
        build: ./base_host
        image: iib_base_host

"""
