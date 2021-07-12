#!/usr/bin/env python
# encoding: utf-8
# __author__ = 'Demon'

from __future__ import annotations
from seedemu.core import Node, Emulator, Service, Server
from typing import List, Dict, Set
from enum import Enum

TorServerFileTemplates: Dict[str, str] = {}

# tor general configuration file
TorServerFileTemplates['torrc'] = '''\
# Run Tor as a regular user (do not change this)
#User debian-tor

TestingTorNetwork 1

## Comprehensive Bootstrap Testing Options ##
# These typically launch a working minimal Tor network in 25s-30s,
# and a working HS Tor network in 40-45s.
# See authority.tmpl for a partial explanation
#AssumeReachable 0
#Default PathsNeededToBuildCircuits 0.6
#Disable TestingDirAuthVoteExit
#Disable TestingDirAuthVoteHSDir
#Default V3AuthNIntervalsValid 3

## Rapid Bootstrap Testing Options ##
# These typically launch a working minimal Tor network in 6s-10s
# These parameters make tor networks bootstrap fast,
# but can cause consensus instability and network unreliability
# (Some are also bad for security.)
AssumeReachable 1
PathsNeededToBuildCircuits 0.25
TestingDirAuthVoteExit *
TestingDirAuthVoteHSDir *
V3AuthNIntervalsValid 2

## Always On Testing Options ##
# We enable TestingDirAuthVoteGuard to avoid Guard stability requirements
TestingDirAuthVoteGuard *
# We set TestingMinExitFlagThreshold to 0 to avoid Exit bandwidth requirements
TestingMinExitFlagThreshold 0
# VoteOnHidServDirectoriesV2 needs to be set for HSDirs to get the HSDir flag
#Default VoteOnHidServDirectoriesV2 1

## Options that we always want to test ##
Sandbox 1

# Private tor network configuration
RunAsDaemon 0
ConnLimit 60
ShutdownWaitLength 0
#PidFile /var/lib/tor/pid
Log info stdout
ProtocolWarnings 1
SafeLogging 0
DisableDebuggerAttachment 0

DirPortFrontPage /usr/share/doc/tor/tor-exit-notice.html
'''

# tor DirServer(DA) configuration file
TorServerFileTemplates['torrc.da'] = '''\
AuthoritativeDirectory 1
V3AuthoritativeDirectory 1

# Speed up the consensus cycle as fast as it will go
# Voting Interval can be:
#   10, 12, 15, 18, 20, 24, 25, 30, 36, 40, 45, 50, 60, ...
# Testing Initial Voting Interval can be:
#    5,  6,  8,  9, or any of the possible values for Voting Interval,
# as they both need to evenly divide 30 minutes.
# If clock desynchronisation is an issue, use an interval of at least:
#   18 * drift in seconds, to allow for a clock slop factor
TestingV3AuthInitialVotingInterval 300
#V3AuthVotingInterval 15
# VoteDelay + DistDelay must be less than VotingInterval
TestingV3AuthInitialVoteDelay 5
V3AuthVoteDelay 5
TestingV3AuthInitialDistDelay 5
V3AuthDistDelay 5
# This is autoconfigured by chutney, so you probably don't want to use it
#TestingV3AuthVotingStartOffset 0

# Work around situations where the Exit, Guard and HSDir flags aren't being set
# These flags are all set eventually, but it takes Guard up to ~30 minutes
# We could be more precise here, but it's easiest just to vote everything
# Clients are sensible enough to filter out Exits without any exit ports,
# and Guards and HSDirs without ORPorts
# If your tor doesn't recognise TestingDirAuthVoteExit/HSDir,
# either update your chutney to a 2015 version,
# or update your tor to a later version, most likely 0.2.6.2-final

# These are all set in common.i in the Comprehensive/Rapid sections
# Work around Exit requirements
#TestingDirAuthVoteExit *
# Work around bandwidth thresholds for exits
#TestingMinExitFlagThreshold 0
# Work around Guard uptime requirements
#TestingDirAuthVoteGuard *
# Work around HSDir uptime and ORPort connectivity requirements
#TestingDirAuthVoteHSDir *
'''

# DirServer fingerprint fetch script
TorServerFileTemplates["da_fingerprint"] = '''\
#!/bin/sh
# version 2
TOR_NICK=$(grep "^Nick" /etc/tor/torrc | awk -F ' ' '{print $2}')
AUTH=$(grep "fingerprint" $TOR_DIR/$TOR_NICK/keys/* | awk -F " " '{print $2}')
NICK=$(cat $TOR_DIR/$TOR_NICK/fingerprint| awk -F " " '{print $1}')
RELAY=$(cat $TOR_DIR/$TOR_NICK/fingerprint|awk -F " " '{print $2}')
SERVICE=$(grep "dir-address" $TOR_DIR/$TOR_NICK/keys/* | awk -F " " '{print $2}')
IPADDR=$(ip addr | grep 'state UP' -A2 | tail -n1 | awk '{print $2}' | cut -f1  -d'/')

TORRC="DirAuthority $TOR_NICK orport=${TOR_ORPORT} no-v2 v3ident=$AUTH $SERVICE  $RELAY"

echo $TORRC
'''

# tor setup script
TorServerFileTemplates["tor-entrypoint"] = '''\
#!/bin/bash
set -o errexit

# Fudge the sleep to try and keep the consensus
#FUDGE=$(( ( RANDOM % 100) + 20 ))
FUDGE=3

echo -e "\n========================================================"

if [ ! -e /tor-config-done ]; then
    touch /tor-config-done   # only run this once

    # Generate a random name
    RPW=$(pwgen -0A 10)
    export TOR_NICKNAME=${{ROLE}}${{RPW}}
    echo "Setting random Nickname: ${{TOR_NICKNAME}}"
    echo -e "\nNickname ${{TOR_NICKNAME}}" >> /etc/tor/torrc

    # Host specific modifications to the torrc file
    echo -e "DataDirectory ${{TOR_DIR}}/${{TOR_NICKNAME}}" >> /etc/tor/torrc
    # Updated to handle docker stack/swarm network overlays
    TOR_IP={TOR_IP} #$(ip addr show eth1 | grep "inet" | grep -v '\/32'| awk '{{print $2}}' | cut -f1 -d'/')
    NICS=$(ip addr | grep 'state UP' | awk '{{print $2}}' | cut -f1 -d':')

    echo "Address ${{TOR_IP}}" >> /etc/tor/torrc
    echo -e "ControlPort 0.0.0.0:9051" >> /etc/tor/torrc
    if [  -z "${{TOR_CONTROL_PWD}}" ]; then
       TOR_CONTROL_PWD="16:6971539E06A0F94C6011414768D85A25949AE1E201BDFE10B27F3B3EBA"
    fi
    echo -e "HashedControlPassword ${{TOR_CONTROL_PWD}}" >> /etc/tor/torrc

    # Changes to the torrc file based on the desired role
    case ${{ROLE}} in
      DA)
        echo "Setting role to DA"
	cat /etc/tor/torrc.da >> /etc/tor/torrc
	echo -e "OrPort ${{TOR_ORPORT}}" >> /etc/tor/torrc
	echo -e "Dirport ${{TOR_DIRPORT}}" >> /etc/tor/torrc
	echo -e "ExitPolicy accept *:*" >> /etc/tor/torrc
	KEYPATH=${{TOR_DIR}}/${{TOR_NICKNAME}}/keys
	mkdir -p ${{KEYPATH}}
	echo "password" | tor-gencert --create-identity-key -m 12 -a ${{TOR_IP}}:${{TOR_DIRPORT}} \
            -i ${{KEYPATH}}/authority_identity_key \
            -s ${{KEYPATH}}/authority_signing_key \
            -c ${{KEYPATH}}/authority_certificate \
	    --passphrase-fd 0
	tor --list-fingerprint --orport 1 \
    	    --dirserver "x 127.0.0.1:1 ffffffffffffffffffffffffffffffffffffffff" \
	    --datadirectory ${{TOR_DIR}}/${{TOR_NICKNAME}}
	echo "Saving DA fingerprint to shared path"
	da_fingerprint >> ${{TOR_DIR}}/torrc.da
	echo "Waiting for other DA's to come up..."
        ;;
      RELAY)
        echo "Setting role to RELAY"
 	echo -e "OrPort ${{TOR_ORPORT}}" >> /etc/tor/torrc
        echo -e "Dirport ${{TOR_DIRPORT}}" >> /etc/tor/torrc
        echo -e "ExitPolicy accept private:*" >> /etc/tor/torrc

        echo "Waiting for other DA's to come up..."
	;;
      EXIT)
        echo "Setting role to EXIT"
        echo -e "OrPort ${{TOR_ORPORT}}" >> /etc/tor/torrc
        echo -e "Dirport ${{TOR_DIRPORT}}" >> /etc/tor/torrc
        echo -e "ExitPolicy accept *:*" >> /etc/tor/torrc
	echo "Waiting for other DA's to come up..."
        ;;
      CLIENT)
        echo "Setting role to CLIENT"
	echo -e "SOCKSPort 0.0.0.0:9050" >> /etc/tor/torrc
        ;;
      HS)
	# NOTE By default the HS role will point to a service running on port 80
	#  but there is no service running on port 80. You can either attach to
	#  the container and start one, or better yet, point to another docker
	#  container on the network by setting the TOR_HS_ADDR to its IP
	echo "Setting role to HIDDENSERVICE"
	echo -e "HiddenServiceDir ${{TOR_DIR}}/${{TOR_NICKNAME}}/hs" >> /etc/tor/torrc
	if [  -z "${{TOR_HS_PORT}}" ]; then
	  TOR_HS_PORT=80
	fi
	if [ -z "${{TOR_HS_ADDR}}" ]; then
	  TOR_HS_ADDR=127.0.0.1
	fi
	echo -e "HiddenServicePort ${{TOR_HS_PORT}} ${{TOR_HS_ADDR}}:${{TOR_HS_PORT}}" >> /etc/tor/torrc
	;;
      *)
        echo "Role variable missing"
        exit 1
        ;;
    esac

    # Buffer to let the directory authority list be built
    sleep $FUDGE
    #cat ${{TOR_DIR}}/torrc.da >> /etc/tor/torrc
    {downloader}

fi

echo -e "\n========================================================"
# display Tor version & torrc in log
tor --version
cat /etc/tor/torrc
echo -e "========================================================\n"

# else default to run whatever the user wanted like "bash"
exec "$@"
'''

#Used for download DA fingerprints from DA servers.
TorServerFileTemplates["downloader"] = """
    until $(curl --output /dev/null --silent --head --fail http://{da_addr}:8888); do
        echo "DA server not ready"
        sleep 3
    done
    sleep 3
    FINGERPRINT=$(curl -s {da_addr}:8888/torrc.da)

    while ! echo $FINGERPRINT | grep DirAuthority
    do
        echo " fingerprint not ready"
        sleep 2
    done
    echo "fingerprint ready"
    echo $FINGERPRINT >> /etc/tor/torrc
"""

BUILD_COMMANDS = """build_temps="build-essential automake" && \
    build_deps="libssl-dev zlib1g-dev libevent-dev ca-certificates\
        dh-apparmor libseccomp-dev dh-systemd \
        git" && \
    DEBIAN_FRONTEND=noninteractive apt-get -y --no-install-recommends install $build_deps $build_temps \
        init-system-helpers \
        pwgen && \
    mkdir /src && \
    cd /src && \
    git clone https://git.torproject.org/tor.git && \
    cd tor && \
    git checkout ${TOR_VER} && \
    ./autogen.sh && \
    ./configure --disable-asciidoc && \
    make && \
    make install && \
    apt-get -y purge --auto-remove $build_temps && \
    apt-get clean && rm -r /var/lib/apt/lists/* && \
    rm -rf /src/*
"""


class TorNodeType(Enum):
    """!
    @brief Tor node types.
    """

    ## directory authority
    DA = "DA"

    ## non-exit relay
    RELAY = "RELAY"

    ## exit relay
    EXIT = "EXIT"

    ## client
    CLIENT = "CLIENT"

    ## hidden service
    HS = "HS"


class TorServer(Server):
    """!
    @brief The Tor server.
    """

    __role: TorNodeType
    __hs_link: Set

    def __init__(self):
        """!
        @brief TorServer constructor.
        """
        self.__role = TorNodeType.RELAY.value
        self.__hs_link = ()

    def setRole(self, role: TorNodeType) -> TorServer:
        """!
        @brief User need to set a role of tor server, by default, it's relay node.

        @param role specify what type of role in this tor server

        @returns self, for chaining API calls.
        """
        self.__role = role.value

        return self

    def getRole(self) -> str:
        """!
        @brief Get role info of this tor server.

        @returns role.
        """
        return self.__role

    def getLink(self) -> str:
        """!
        @brief Get the link of HS server, only HS role node has this feature.

        @returns hidden service dest.
        """
        return self.__hs_link

    def setLink(self, addr: str, port: int) -> TorServer:
        """!
        @brief set IP link of HS server, only be invoked by __resolveHSLink()

        @param addr address
        @param port port.

        @returns self, for chaining API calls.
        """
        self.__hs_link = (addr, port)

        return self

    def linkByVnode(self, vname: str, port: int) -> TorServer:
        """!
        @brief set Vnode link of HS server.
        
        If a tor server is HS role, it's able to link to another virtual node
        as an onion service. In /tor/HS[random]/hs/hostname file at HS node, it
        contains the onion address name.

        @param vname virtual node name.
        @param port port.

        @returns self, for chaining API calls.
        """
        assert self.getRole() == "HS", "linkByVnode(): only HS type node can bind a host."
        assert len(self.__hs_link) == 0, "linkByVnode(): TorServer already has linked a host."
        self.__hs_link = (vname, port)

        return self

    def configure(self, node: Node, tor: 'TorService'):
        """!
        @brief configure TorServer node

        @param node target node.
        @param tor tor service.
        """
        ifaces = node.getInterfaces()
        assert len(ifaces) > 0, 'TorNode configure(): node has not interfaces'
        addr = ifaces[0].getAddress()

        if self.getRole() == "DA":
            # Save DA address in tor service, other type of node will download fingerprint from these DA.
            tor.addDirAuthority(addr)

        if self.getRole() == "HS" and len(self.getLink()) != 0:
            # take out link in HS server and set it to env variable, they would mapping to tor config file.
            addr, port = self.getLink()
            node.appendStartCommand("export TOR_HS_ADDR={}".format(addr))
            node.appendStartCommand("export TOR_HS_PORT={}".format(port))

    def install(self, node: Node, tor: 'TorService'):
        """!
        @brief Tor server installation step.

        @param node target node.
        @param tor tor service.
        """
        ifaces = node.getInterfaces()
        assert len(ifaces) > 0, 'node has not interfaces'
        addr = ifaces[0].getAddress()
        download_commands = ""
        for dir in tor.getDirAuthority():
            download_commands += TorServerFileTemplates["downloader"].format(da_addr=dir)

        node.addSoftware("git python3")
        node.addBuildCommand(BUILD_COMMANDS)

        node.setFile("/etc/tor/torrc", TorServerFileTemplates["torrc"])
        node.setFile("/etc/tor/torrc.da", TorServerFileTemplates["torrc.da"])
        node.setFile("/usr/local/bin/da_fingerprint", TorServerFileTemplates["da_fingerprint"])
        node.setFile("/usr/local/bin/tor-entrypoint", TorServerFileTemplates["tor-entrypoint"].format(TOR_IP=addr, downloader = download_commands))
        
        node.appendStartCommand("export TOR_ORPORT=7000")
        node.appendStartCommand("export TOR_DIRPORT=9030")
        node.appendStartCommand("export TOR_DIR=/tor")
        node.appendStartCommand("export ROLE={}".format(self.__role))
        node.appendStartCommand("chmod +x /usr/local/bin/tor-entrypoint /usr/local/bin/da_fingerprint")
        node.appendStartCommand("mkdir /tor")
       
        # If node role is DA, launch a python webserver for other node to download fingerprints.
        if self.getRole() == "DA":
            node.appendStartCommand("python3 -m http.server 8888 -d /tor", True)
        
        node.appendStartCommand("tor-entrypoint")
        node.appendStartCommand("tor -f /etc/tor/torrc")

    def print(self, indent: int) -> str:
        out = ' ' * indent
        out += 'TorServer'

        return out

class TorService(Service):
    """!
    @brief The Tor network service.
    """

    def __init__(self):
        super().__init__()
        self.__da_nodes = []

    def getName(self):
        return 'TorService'

    def _doConfigure(self, node: Node, server: TorServer):
        server.configure(node, self)

    def addDirAuthority(self, addr: str) -> TorService:
        """!
        @brief add DA.

        @param addr address of DA.

        @returns self, for chaining API calls.
        """
        self.__da_nodes.append(addr)

        return self

    def getDirAuthority(self) -> List[str]:
        """!
        @brief get DAs.

        @returns list of DA addresses.
        """

        return self.__da_nodes

    def __resolveHSLink(self, emulator: Emulator):
        """!
        @brief Transfer vnode link to physical node IP address.

        """
        for server in self.getPendingTargets().values():
            if server.getRole() == "HS" and len(server.getLink()) != 0:
                vname, port = server.getLink()
                pnode = emulator.resolvVnode(vname)
                ifaces = pnode.getInterfaces()
                assert len(ifaces) > 0, '__resolveHSLink(): node as{}/{} has no interfaces'.format(pnode.getAsn(), pnode.getName())
                addr = ifaces[0].getAddress()
                server.setLink(addr, port)

    def configure(self, emulator: Emulator):
        self.__resolveHSLink(emulator)
        return super().configure(emulator)

    def _doInstall(self, node: Node, server: TorServer):
        server.install(node, self)

    def _createServer(self) -> Server:
        return TorServer()