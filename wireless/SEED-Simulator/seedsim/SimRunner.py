#!/bin/env python3 

from .SeedSimLogger import *
import json
import os
import docker
from datetime import datetime
from .NodeInfo import *

SIMULATION_INFO_PATH = '/tmp/node_info/simulation_info.json'
NODE_INFO_PATH = '/tmp/node_info/node_pos.json'

TC_CMD = 'tc qdisc replace dev {dev} parent 1:1{id} handle 1{id}: netem delay {delay}us loss {loss}%\n'

LABEL_PREFIX = "org.seedsecuritylabs.seedemu.meta"
CLASS      = LABEL_PREFIX + ".class"
NODENAME   = LABEL_PREFIX + ".nodename"
WIRELESS   = "Wireless"

NETNAME = LABEL_PREFIX + ".net.{}.name"
NETADDR = LABEL_PREFIX + ".net.{}.address"
NET0    = 'net-wireless'

TC_CMD = 'tc qdisc replace dev {dev} parent 1:1{id} handle 1{id}: netem delay {delay}us loss {loss}%\n'
TC_QUEUE_DEL = 'tc qdisc del dev {dev} root;'
TC_QUEUE_ADD = 'tc qdisc add dev {dev} root handle 1: htb default 30;'

TC_EGRESS_CLASS_INIT = \
'''tc class add dev net-wireless parent 1:0 classid 1:1{id} htb rate 1000000000000;
tc qdisc add dev net-wireless parent 1:1{id} handle 1{id}:0 netem delay 0ms loss 0%;'''

TC_INGRESS_CLASS_INIT = \
'''tc class add dev ifb0 parent 1:0 classid 1:1{id} htb rate 1000000000000;
tc qdisc add dev ifb0 parent 1:1{id} handle 1{id}:0 netem delay 0ms loss 0%;
'''

class SimRunner():
    '''
    Run simulation info obtained from Simulator class on Emulator code.
    '''
    def __init__(self) -> None:
        self.simulation_info = json.load(open(SIMULATION_INFO_PATH))

        # Get all the containers
        client = docker.from_env()
        all_containers = client.containers.list()
        
        self.router_infos = self.__get_router_infos(all_containers)
        self.cur_iter = 0
        self.node_total = self.simulation_info['node_count']

    def __get_router_infos(self, containers):
        router_container_ids = {}
        for container in containers:
            if CLASS in container.labels and WIRELESS in container.labels[CLASS]:
                router_id = int(container.labels[NODENAME].split("_")[1])
                router_container_ids[router_id] = {
                                                    'container_id': container.short_id,
                                                    'ipaddr': self.__find_net0(container)
                                                }
        
        return router_container_ids
    
    def __find_net0(self, container):
        for i in range(10): # Assume no more than 10 interfaces 
            netname = NETNAME.format(i)
            if netname in container.labels and NET0 in container.labels[netname]:
                ipaddrwithmask = container.labels[NETADDR.format(i)]
                ipaddr = ipaddrwithmask.split('/')[0]
                return ipaddr
            
    def update_loss_and_delay_on_containers(self, iter=None):
        '''
        @brief Update loss on containers.

        @return self, for chaining api calls.
        '''
        start = datetime.now()
        iteration = iter
        if iteration == None:
            iteration = self.cur_iter
            self.cur_iter += 1

        self.__update_node_info_file(iteration)

        for router_id in range(self.node_total): 
            tc_start = datetime.now()
            cmd = self.__get_tc_cmd(iteration, router_id) 
            
            SeedSimLogger.debug(clsname=__name__, msg=cmd)

            self.__run_docker_exec(self.router_infos[router_id]['container_id'], cmd)
            tc_end = datetime.now()
            time_diff = (tc_end - tc_start)
            execution_time = time_diff.total_seconds() * 1000

            SeedSimLogger.debug(__name__, "iteration {} - router id {} - tc execution time elasped : {} milliseconds".format(iteration, router_id, execution_time))


        end = datetime.now()
        time_diff = (end - start)
        execution_time = time_diff.total_seconds() * 1000
        SeedSimLogger.debug(__name__, "iteration {} - time elasped : {} milliseconds".format(iteration, execution_time))
        return self

    def __update_on_node_info(self, iteration):
        for router_id in range(self.node_total):
            self.simulation_info['simulation_info'][iteration]['node_info'][router_id]['container_id'] = self.router_infos[router_id]['container_id']
            self.simulation_info['simulation_info'][iteration]['node_info'][router_id]['ipaddress'] = self.router_infos[router_id]['ipaddr']

    def __update_node_info_file(self, iteration):
        '''
        @brief update node info file for visualizing node positions 
        
        @return self, for chainging api calls
        '''
        self.__update_on_node_info(iteration)

        node_info = { 
                    "node_count": self.node_total,
                    "node_info": self.simulation_info['simulation_info'][iteration]['node_info'],
                    "building_info": self.simulation_info['building_info']
                    }
        json_object = json.dumps(node_info, indent=4, cls=NodeInfoEncoder)
        
        # Writing to sample.json
        with open(NODE_INFO_PATH, "w") as outfile:
            outfile.write(json_object)

    def __run_docker_exec (self, dockerID, cmd):
        '''
        @brief run command inside docker container.

        @param dockerID docker container id to run command
        @param cmd command to run 
        '''

        dockercmd = "docker exec {} bash -c \"{}\" ".format(dockerID, cmd)
        SeedSimLogger.debug(clsname=__name__, msg=dockercmd)
        
        os.system(dockercmd)

    def __get_tc_cmd(self, iteration, router_id):
        '''
        @brief craft tc command with the given loss.

        @param loss to set

        returns tc command
        '''
        node_info = self.simulation_info['simulation_info'][iteration]['node_info'][router_id]
        # SeedSimLogger.info(clsname=__name__, msg="given node id: "+str(router_id)+", printed node id: "+str(node_info['id']))
        cmd = ''
        for conn in node_info['connectivity']:
            cmd += TC_CMD.format(id=conn['id'], dev="ifb0", delay=conn['delay'], loss=conn['loss'])
        return cmd