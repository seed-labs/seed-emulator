"""Internet Simulator."""

import os
import csv

from .constants import *
from .network import Network
from .as_ixp import AS, IXP
from .machine import *


####################################
# The Simulator class
####################################
class Simulator():
    def __init__(self, name):
        self.name = name
        self.networks = {}
        self.hosts = {}
        self.routers = {}
        self.ASes = {}
        self.IXPs = {}

    def addIX(self, name, asn, net_name):
        if name in self.IXPs.keys():
            # print('The key {} already exists, ignored.'.format(name))
            return self.IXPs[name]
        else:
            self.IXPs[name] = IXP(name, asn, net_name, self)
            return self.IXPs[name]

    def addAS(self, name, asn, as_type, net_name):
        if name in self.ASes.keys():
            # print('The key {} already exists, ignored.'.format(name))
            return self.ASes[name]
        else:
            self.ASes[name] = AS(name, asn, as_type, net_name, self)
            return self.ASes[name]

    # Can get both AS and IX

    def getASByName(self, name):
        if name.startswith(SimConstants.ASNAME[:2]):
            if name in self.ASes.keys():
                return self.ASes[name]
        if name.startswith(SimConstants.IXNAME[:2]):
            if name in self.IXPs.keys():
                return self.IXPs[name]

        return None

    def getASByASN(self, asn):
        name = SimConstants.ASNETNAME.format(asn)
        if name in self.ASes.keys():
            return self.ASes[name]
        else:
            return None

    def addNetwork(self, name, network, netmask, type):
        if name in self.networks.keys():
            #print('The key {} already exists, ignored.'.format(name))
            return self.networks[name]
        else:
            self.networks[name] = Network(name, network, netmask, type, self)
            return self.networks[name]

    def getNetwork(self, name):
        if name in self.networks.keys():
            return self.networks[name]
        else:
            return None

    def addBGPRouter(self, asn, ixp, type):
        if type == 'as':
            name = SimConstants.BGPRouterNAME.format(asn, ixp)
        else:
            name = SimConstants.RSNAME.format(ixp)

        if name in self.routers.keys():
            #print('The key {} already exists, ignored.'.format(name))
            return self.routers[name]

        if type == 'as':
            router = BGPRouter(name, asn, ixp, self)
            router.initializeNetwork()
            self.routers[name] = router
        else:  # for 'rs', route server
            router = RouteServer(name, ixp, self)
            router.initializeNetwork()
            self.routers[name] = router

        return self.routers[name]

    def getRouter(self, name):
        if name in self.routers.keys():
            return self.routers[name]
        else:
            return None

    def addHost(self, name, host):
        if name in self.hosts.keys():
            print('The key {} already exists, ignored.'.format(name))
        else:
            self.hosts[name] = host

    def getHost(self, name):
        if name in self.hosts.keys():
            return self.hosts[name]
        else:
            return None

    def listRouters(self):
        for k, (rt_name, router) in enumerate(self.routers.items()):
            router.printDetails()

    def listHosts(self):
        for k, (host_name, host) in enumerate(self.hosts.items()):
            host.printDetails()

    def listNetworks(self):
        for k, (net_name, network) in enumerate(self.networks.items()):
            network.printDetails()

    def listASes(self):
        for k, (as_name, as_obj) in enumerate(self.ASes.items()):
            as_obj.printDetails()

    def listIXPs(self):
        for k, (ix_name, is_obj) in enumerate(self.IXPs.items()):
            is_obj.printDetails()

    # Create the host list.
    # total: specify how many hosts to create for each network

    def generateHosts(self, total):
        for k, (net_name, network) in enumerate(self.networks.items()):
            if network.type == 'IX':
                continue  # need to generate hosts for the IX network

            for i in range(total):
                host_name = SimConstants.HOSTNAME.format(net_name, str(i+1))
                host = Host(host_name, net_name, network.getIP(), self)
                self.addHost(host_name, host)

    def createHostDockerFiles(self):
        for k, (hostname, host) in enumerate(self.hosts.items()):
            start_script = host.createStartScript()

            dirname = SimConstants.OUTDIR.format(hostname)
            os.system("mkdir -p {}".format(dirname))
            os.system(
                "cp -rf {}/* {}/".format(SimConstants.TEMPLATE_HOSTDIR, dirname))
            with open(dirname+"/start.sh", "w") as f:
                f.write(start_script)
            os.system("chmod a+x {}".format(dirname+"/start.sh"))

    def createRouterDockerFiles(self):
        for k, (routername, router) in enumerate(self.routers.items()):
            bird_conf = router.createBirdConf_BGP()
            if router.getType() == 'as':   # IBGP is meaningful for BGP router, not for router server
                bird_conf += router.createBirdConf_IBGP()

            dirname = SimConstants.OUTDIR.format(routername)
            os.system("mkdir -p {}".format(dirname))
            os.system(
                "cp -rf {}/* {}/".format(SimConstants.TEMPLATE_ROUTERDIR, dirname))
            with open(dirname+"/bird.conf", "w") as f:
                f.write(bird_conf)

    def createDockerComposeFile(self):
        f = open(SimConstants.OUTDIR.format("docker-compose.yml"), "w")
        f.write(FileTemplate.docker_compose_header)

        # Write the entry for each host
        for k, (name, host) in enumerate(self.hosts.items()):
            f.write(host.createDockerComposeEntry())
            f.write("\n")

        # Write the entry for each router
        for k, (name, router) in enumerate(self.routers.items()):
            f.write(router.createDockerComposeEntry())
            f.write("\n")

        # Write the entry for each network
        f.write("\n\n")
        f.write("networks:\n")
        for k, (name, network) in enumerate(self.networks.items()):
            f.write(network.createDockerComposeEntry())
            f.write("\n")
        f.close()

    # Read the AS data from CSV file

    def getASFromCSV(self, filename):
        with open(filename, newline='') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                asn = row['asn'].strip()
                type = row['type'].strip()
                cidr = row['network'].strip()

                if type == 'IX':
                    as_name = SimConstants.IXNAME.format(asn)
                    net_name = SimConstants.IXNETNAME.format(asn)
                else:
                    as_name = SimConstants.ASNAME.format(asn)
                    net_name = SimConstants.ASNETNAME.format(asn)

                (tmp, netmask) = cidr.split('/')
                net_ip = tmp.replace('@', str(asn))

                # Create Network and add it to simulator
                self.addNetwork(net_name, net_ip, netmask, type)

                if type == 'IX':
                    self.addIX(as_name, asn, net_name)
                else:
                    self.addAS(as_name, asn, type, net_name)

    def getPeeringsFromCSV(self, filename):
        with open(filename, newline='') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                peer1_asn = row['asn'].strip()
                peer1_name = SimConstants.ASNAME.format(peer1_asn)
                #print("Peer 1: {}".format(peer1_name))

                for i in range(10):
                    col = 'peer' + str(i+1)
                    if row[col]:
                        value = row[col].strip()
                        if '@' not in value:
                            continue   # empty, skip it

                        #print("    Peer 2: {}".format(value))
                        (peer2_asn, ixp_asn) = row[col].strip().split('@')
                        ixp_name = SimConstants.IXNAME.format(ixp_asn)
                        peer2_type = 'as'
                        peer2_name = SimConstants.ASNAME.format(peer2_asn)

                        if peer2_asn == 'rs':  # peer with router server
                            peer2_type = 'rs'
                            peer2_name = ixp_name
                            peer2_asn = ixp_asn

                        # Make sure the AS and IX exist
                        peer1 = self.getASByName(peer1_name)
                        peer2 = self.getASByName(peer2_name)
                        ixp = self.getASByName(ixp_name)

                        if not peer1 or not peer2 or not ixp:
                            print("AS or IXP does not exist! {} {} {}".format(
                                peer1_name, peer2_name, ixp_name))
                            print(peer1, peer2, ixp)
                            continue

                        # Create/Add BGP routers to Simulator (return them if already existing)
                        router1 = self.addBGPRouter(peer1_asn, ixp_asn, "as")
                        router2 = self.addBGPRouter(
                            peer2_asn, ixp_asn, peer2_type)

                        router1.addPeer(router2.getName())
                        router2.addPeer(router1.getName())

                        # Add BGP routers to AS/IX
                        as_obj = self.getASByName(peer1_name)
                        as_obj.addBGPRouter(router1.getName())

                        as_obj = self.getASByName(peer2_name)
                        as_obj.addBGPRouter(router2.getName())

                        # Later: add routers to IXP (not very necessary)
