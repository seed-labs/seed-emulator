#!/bin/env python3 

import docker
import os, json
import numpy as np
from .NodeInfo import *
from .propagationModel.PropagationLossModel import *
from .propagationModel.PropagationDelayModel import *
from .propagationModel import *
import csv
from .SeedSimLogger import *
import copy

LABEL_PREFIX = "org.seedsecuritylabs.seedemu.meta"
JSON_PATH = "/tmp/node_info/node_pos.json"
JSON_FOLDER = "/tmp/node_info"

CLASS      = LABEL_PREFIX + ".class"
NODENAME   = LABEL_PREFIX + ".nodename"
WIRELESS   = "Wireless"

NETNAME = LABEL_PREFIX + ".net.{}.name"
NETADDR = LABEL_PREFIX + ".net.{}.address"
NET0    = 'net-wireless'

ROUTERID = LABEL_PREFIX + ".routerid"

IPTABLES_FLUSH = 'ip6tables -F;'
IPTABLES_CMD   = 'ip6tables -A INPUT  -s {} -j DROP;'

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

TC_FILTER = 'tc filter add dev {dev} protocol {proto} parent 1:0 prio {prio} u32 match {addr_type} {src_dst} {addr} flowid 1:1{id};'

def get_mac_addr(ipv4):
    ipv4a = ipv4.split('.')
    mac  =  "02:42:0a:" 
    mac += "{:02x}:{:02x}:{:02x}".format(int(ipv4a[1]), int(ipv4a[2]), int(ipv4a[3]))

    return mac

def get_ipv6_addr(ipv4):
        ipv4a = ipv4.split('.')
        ipv6  =  "fe80::42:aff:fe" 
        ipv6 += "{:02x}:{:02x}{:02x}".format(int(ipv4a[1]), int(ipv4a[2]), int(ipv4a[3]))

        return ipv6

class Simulation():
    total:int
    routers:list
    node_info:dict
    simulation_info:dict
    moved:int
    override:bool
    buildings:list
    loss_topology:list
    delay_topology:list
    loss_model:PropagationLossModel
    delay_model:ConstantSpeedPropagationDelayModel
    iteration:int

    def __init__(self, override=False) -> None:
        # Get all the containers
        client = docker.from_env()
        all_containers = client.containers.list()

        # Get all the wireless routers information
        routers_dict = self.__get_wireless_router_info(all_containers)

        # Convert the dictionary to array
        self.routers = [None] * len(routers_dict)
        for key in routers_dict:
            router_id = int(key.split('_')[1])
            self.routers[router_id] = routers_dict[key]

        self.total = len(self.routers)
        self.loss_topology = [[0 for col in range(self.total)] for row in range(self.total)]
        self.delay_topology = [[0.0 for col in range(self.total)] for row in range(self.total)]
        self.override = override
        self.simulation_info = {
            "node_count": self.total,
            "total_iter": 0,
            "simulation_info": []
        }
        self.__init_node_info()
        self.loss_model = PropagationLossModel()
        self.delay_model = None
        self._moved = 0
        self.iteration = 0
        self.csvInit()
        pass

    def __init_node_info(self):
        self.node_info = {
                    "node_count": self.total, 
                    "node_info": [],
                    "building_info": []
                }
        
        if (os.path.exists(JSON_PATH) and not self.override):
            f = open(JSON_PATH)
            nodes = json.load(f)['node_info']
            f.close()
            for id, router in enumerate(self.routers):
                node_info = NodeInfo(id, container_id=router['container'].id, ipaddress=router['ipv4'],
                                     x = nodes[id]["x"], y = nodes[id]["y"],
                                      distance = nodes[id]["distance"],
                                       connectivity = nodes[id]["connectivity"],
                                       direction= nodes[id]["direction"])
                # ToDo =================================
                mobility = ConstantVelocityMobilityModel()
                mobility.setPosition(Vector(node_info.x, node_info.y, 1.5))
                mobility.setVelocity(Vector(node_info.direction[0], node_info.direction[1], 0))
                node_info.setMobility(mobility)
                # ======================================
                self.node_info["node_info"].append(node_info)
            return
        

        for id, router in enumerate(self.routers):
            node_info = NodeInfo(id, container_id=router['container'].id, ipaddress=router['ipv4'])   
            self.node_info["node_info"].append(node_info)

        for i in range(self.total):
            x1, y1 = self.node_info["node_info"][i].x, self.node_info["node_info"][i].y
            self.node_info["node_info"][i].connectivity = []
            for j in range(i+1, self.total):
                x2, y2 = self.node_info["node_info"][j].x, self.node_info["node_info"][j].y
                dist = self.__get_distance(x1, y1, x2, y2)
                self.node_info["node_info"][i].distance[str(j)] = dist
                self.node_info["node_info"][i].connectivity.append({
                    "id":j,
                    "container_id":self.node_info["node_info"][j].container_id,
                    "loss":self.__get_loss(dist)
                })

        self.get_buildings()
        json_object = json.dumps(self.node_info, indent=4, cls=NodeInfoEncoder)
        node_info = copy.deepcopy(self.node_info['node_info'])
        # Writing to sample.json
        if not os.path.exists(JSON_FOLDER):
            os.mkdir(JSON_FOLDER)
        
        self.simulation_info['simulation_info'].append({'iter': iter,
                                                            'node_info': node_info})
        
        with open(JSON_PATH, "w") as outfile:
            outfile.write(json_object)
            

    def record_simulation_info(self, iteration):
        self.simulation_info['total_iter'] = iteration
        self.simulation_info["building_info"] = self.buildings
        # SeedSimLogger.info(__name__, "position_x"+str((self.simulation_info['simulation_info'][0]['node_info'][0]['x'])))
        json_object = json.dumps(self.simulation_info, indent=4, cls=NodeInfoEncoder)

        with open('/tmp/node_info/simulation_info.json', "w") as outfile:
            outfile.write(json_object)

    def get_buildings(self):
        self.buildings = BuildingList.getBuildings()
        self.node_info["building_info"] = self.buildings

    def __get_distance(self, x1, y1, x2, y2):
        a = np.array((x1, y1))
        b = np.array((x2, y2))

        dist = np.sqrt(np.sum(np.square(a-b)))
        return dist
    
    def __get_loss(self, dist):
        loss = 100
        if dist <= 10:
            loss = 0
        elif dist <= 20:
            loss = 20    
        elif dist <= 30:
            loss = 40
        elif dist <= 40:
            loss = 60
        # elif dist <= 500:
        #     loss = 80
        return loss

    def __set_loss_and_delay_topology_from_data(self, node_info):
        for node in node_info:
            for connection in node.connectivity:
                self.loss_topology[node.id][connection['id']] = connection['loss']
                self.delay_topology[node.id][connection['id']] = connection['delay']

    def __find_net0(self, container):
        for i in range(10): # Assume no more than 10 interfaces 
            netname = NETNAME.format(i)
            if netname in container.labels and NET0 in container.labels[netname]:
                ipaddrwithmask = container.labels[NETADDR.format(i)]
                ipaddr = ipaddrwithmask.split('/')[0]
                return ipaddr

    def __get_wireless_router_info(self, containers):
        routers = {}
        for container in containers:
            if CLASS in container.labels and WIRELESS in container.labels[CLASS]:
                router_name = container.labels[NODENAME]
                info = {}
                info['container'] = container
                info['dockerID'] = container.short_id
                ipaddr = self.__find_net0(container)
                info['ipv4'] = ipaddr 
                if ipaddr is not None:
                    info['ipv6'] = get_ipv6_addr(ipaddr)
                
                routers[router_name] = info
        
        return routers

    def __get_next_hop(self, router):
        _, output = router.exec_run('ip -j route')
        output = json.loads(output.decode('utf-8'))
        next_hop = [None] * 30
        for route in output:
            if route['dst'].startswith("10.0.0.1"):
                src_router_id = int(route['dst'].split('.')[3])-100
                dst_router_id = src_router_id
                if route.get('gateway'):
                    dst_router_id = int(route['gateway'].split('.')[3].split('/')[0]) - 100
                next_hop[src_router_id] = dst_router_id

        return next_hop
        
    def __get_all_next_hop(self):
        size = self.total
        all_next_hop = [[0 for col in range(size)] for row in range(size)]
        for i in range(size):
            all_next_hop[i] = self.__get_next_hop(self.routers[i]['container'])
        
        return all_next_hop
    
    def __get_tc_cmd(self, loss, delay):
        '''
        @brief craft tc command with the given loss.

        @param loss to set

        returns tc command
        '''
        cmd = ''
        for i in range(len(loss)):
            cmd += TC_CMD.format(id=i, dev="ifb0", delay=delay[i], loss=loss[i])
        return cmd
    
    def __run_docker_exec (self, dockerID, cmd):
        '''
        @brief run command inside docker container.

        @param dockerID docker container id to run command
        @param cmd command to run 
        '''
        dockercmd = "docker exec {} bash -c \"{}\" ".format(dockerID, cmd)
        # print(dockercmd)
        SeedSimLogger.debug(clsname=__name__, msg=dockercmd)
        os.system(dockercmd)
    
    def getNodeList(self):
        return self.node_info['node_info']
    
    def setNodeList(self, nodes):
        self.node_info['node_info'] = nodes

    def appendPropagationLossModel(self, lossModel:PropagationLossModel):
        self.loss_model.appendLossModel(lossModel)
        return self
    
    def getPropagationLossModel(self):
        return self.loss_model.getPropagationLossModelByIndex()
    
    def setPropagationDelayModel(self, delayModel:PropagationDelayModel):
        '''
        @brief Set Propagation Delay Model.

        @param delayModel Propagation Delay Model to set.

        @return self, for chaining api calls.
        '''
        self.delay_model = delayModel
        return self

    def __update_loss_and_delay(self):
        # update loss and delay
        lossModel:ThreeGppPropagationLossModel = self.getPropagationLossModel()
        conditionModel = lossModel.getChannelConditionModel()
        for i in range(self.total):
            node_a = self.node_info["node_info"][i]
            x1, y1 = self.node_info["node_info"][i].x, self.node_info["node_info"][i].y
            self.node_info["node_info"][i].connectivity = []
            for j in range(i+1, self.total):
                node_b = self.node_info["node_info"][j]
                x2, y2 = self.node_info["node_info"][j].x, self.node_info["node_info"][j].y
                dist = self.__get_distance(x1, y1, x2, y2)
                self.node_info["node_info"][i].distance[str(j)] = dist
                loss_rate = self.loss_model.calcLossRate(node_a, node_b)
                SeedSimLogger.debug(clsname=__name__, msg="node {} - node {} loss_rate: {}".format(i, j, loss_rate))
                self.node_info["node_info"][i].connectivity.append({
                    "id":j,
                    "container_id":self.routers[j]['container'].id,
                    "loss":loss_rate,
                    "delay":self.delay_model.getDelay(dist=dist) if self.delay_model else 0,
                    "los_condition": conditionModel.getChannelCondition(node_a, node_b).getLosCondition().value
                })
                self.csvWrite([self.iteration, i, j, x1, y1, x2, y2, dist, conditionModel.getChannelCondition(node_a, node_b).getLosCondition().value, loss_rate])
        
        self.iteration += 1
        self.__set_loss_and_delay_topology_from_data(self.node_info["node_info"])

        # Serializing json
        self.get_buildings()
        json_object = json.dumps(self.node_info, indent=4, cls=NodeInfoEncoder)
        node_info = copy.deepcopy(self.node_info['node_info'])
        iter = len(self.simulation_info['simulation_info'])
        self.simulation_info['simulation_info'].append({'iter': iter,
                                                            'node_info': node_info})
        
        # Writing to sample.json
        with open(JSON_PATH, "w") as outfile:
            outfile.write(json_object)
            

    def csvWrite(self, row):
        with open('/tmp/seedsim/siminfo/siminfo.csv', 'a', newline='') as csvfile:
            writer = csv.writer(csvfile, delimiter=' ')
            writer.writerow(row)
    
    def csvInit(self):
        with open('/tmp/seedsim/siminfo/siminfo.csv', 'w', newline='') as csvfile:
            writer = csv.writer(csvfile, delimiter=' ')
            columns = "Iter tx_node_id rx_node_id TxPosX[m] TxPosY[m] RxPosX[m] RxPosY[m] Distance[m] ChannelState PathlossRate[%]"
            writer.writerow(columns.split())

    # automove
    def move_nodes(self):
        '''
        @brief move nodes by its direction at a time. 
               Each NodeInfo object has dx and dy information. 
               At each move, the position of a node will be changed by dx and dy.
        '''
        self._moved += 1
        # move all nodes' positions
        for i in range(self.total):
            self.node_info["node_info"][i].move()
            
        # update loss and delay
        self.__update_loss_and_delay()
    
    #manual move
    def move_nodes_by_manual(self, nodes):
        '''
        @brief move nodes to the given position. 

        @param nodes indicates positions of all nodes. A list of tuples.[(node_id:int, x_position:float, y_position:float)]

        @return self, for chaining api calls.
        '''
        for id, x, y in nodes:
            self.node_info["node_info"][id].x, self.node_info["node_info"][id].y = x, y

        # update loss and delay
        self.__update_loss_and_delay()

    def calc_routes_and_loss(self):
        '''
        @brief get routes from containers using `ip route` command 
               and calculate loss from the routes and self.topology        
        '''
        size = self.total
        all_next_hop = self.__get_all_next_hop()
        route_info = [[{'routes':[], 'loss':0} for col in range(size)] for row in range(size)]
        for src in range(size):
            for dst in range(size):
                prev = next = src
                connectivity = 1
                routes = [src]
                while True:
                    next = all_next_hop[next][dst]
                    if len(routes)>2 and routes[-2]==next:
                        return False
                    if next == None:
                        # print("no route")
                        SeedSimLogger.debug(clsname=__name__, msg="no route")
                        break
                    routes.append(next)
                    loss = self.loss_topology[prev][next]
                    if prev > next:
                        loss = self.loss_topology[next][prev]
                        
                    connectivity = connectivity * ((1 - (loss / 100)))
                    if next == dst:
                        break
                    prev = next
                route_info[src][dst]['routes'] = routes
                route_info[src][dst]['loss'] = int((1-connectivity)*100)

        self.route_info = route_info
        return route_info

    def print_route_info(self, src=0, dst="all"):
        str_format = "{:^5}|{:^30}|{:^20}"
        SeedSimLogger.debug(clsname=__name__, msg="======================[ Route Info ]======================")
        SeedSimLogger.debug(clsname=__name__, msg="SRC: {}".format(src))
        SeedSimLogger.debug(clsname=__name__, msg=str_format.format("DST", "Route", "Loss"))
        for i in range(self.total):
            routes = ", ".join(str(e) for e in self.route_info[src][i]['routes'])
            loss = str(self.route_info[src][i]['loss'])
            SeedSimLogger.debug(clsname=__name__, msg=str_format.format(str(i), routes, loss))

    # def update_loss_on_topology_all(self, threshold = 0.50):
    #     '''!
    #     @brief Update loss on self.topology (symmetric matrix)
    #            size the total number of router nodes (self.total)
    #     @param threshold the percentage of loss 100% (disconnection) 
    #     '''
    #     size = self.total
        
    #     for i in range(size):
    #         self.loss_topology[i][i] = 0
    #         for j in range(i+1, size): 
    #             rand = random.randint(0, 100)
    #             if rand > threshold*100:
    #                 loss = random.randint(0, 5)*10
    #                 self.loss_topology[i][j] = loss
    #             else:
    #                 self.loss_topology[i][j] = 100
                
    #         # for j in range(i): 
    #         #     self.topology[i][j] = self.topology[j][i] 
    #     # self.loss_topology = self.loss_topology

    #     return self.loss_topology
    
    def update_loss_topology(self, src, dst, loss):
        '''
        @brief Update one loss information from the given src to dst
               on self.loss_topology by manual.

        @param src source node id.
        @param dst destination node id.
        @param loss to set.

        @return self, for chaining api calls.
        '''
        
        self.loss_topology[src][dst] = loss
        #self.topology[dst][src] = loss
        return self
    
    def set_loss_topology(self, topo):
        '''
        @brief Set loss topology.

        @param topo topology to set.

        @return self, for chaining api calls.
        '''
        self.loss_topology = topo
        return self
    
    def update_loss_and_delay_on_containers(self):
        '''
        @brief Update loss on containers.

        @return self, for chaining api calls.
        '''
        for k in range(self.total):   
            cmd = self.__get_tc_cmd(self.loss_topology[k], self.delay_topology[k]) 
            SeedSimLogger.debug(clsname=__name__, msg=cmd)
            SeedSimLogger.debug(clsname=__name__, msg="Node {:2d}: ".format(k))
            for i in range(self.total):
                SeedSimLogger.debug(clsname=__name__, msg="{:3f}/{:3f}".format(self.loss_topology[k][i], self.delay_topology[k][i]))
            SeedSimLogger.debug(clsname=__name__, msg="")
            self.__run_docker_exec(self.routers[k]['dockerID'], cmd)

        return self

    def print_loss_topology(self):
        """
        @brief print topology containing loss values.
        """
        total = self.total
        topology = self.loss_topology

        print("         ", end='')
        for i in range(total):
            print("{:3d} ".format(i), end='')
        print("")
        for k in range(total):   
            print("Node {:2d}: ".format(k), end='')
            for loss in topology[k]:
                print("{:3d} ".format(loss), end='')
        print("")

    def init_tc(self):
        '''
        @brief reset all tc filter and set to initial state.

        @return self, for chaining api calls.
        '''
        cmd = ''
        cmd += TC_QUEUE_DEL.format(dev="net-wireless")
        cmd += TC_QUEUE_DEL.format(dev="ifb0")
        cmd += TC_QUEUE_ADD.format(dev="net-wireless")
        cmd += TC_QUEUE_ADD.format(dev="ifb0")

        for i in range(self.total):            
            cmd += TC_EGRESS_CLASS_INIT.format(id=i)
            cmd += TC_INGRESS_CLASS_INIT.format(id=i)
            
        for i in range(self.total):
            self.__run_docker_exec(self.routers[i]['dockerID'], cmd)

    def add_filter(self, direction="ingress", proto="ip", addr_type="ether", priority=1):
        '''
        @brief add filter to each container.

        @param direction    "egress"|"ingress" (default: "ingress")
        @param proto        protocol to filter "ip|ipv6|icmp|all" (default: "ip")
        @param addr_type    address type to use "ether|ip|ip6" (default: "ether") 

        @return self, for chaining api calls.
        '''
        dev = "ifb0" if direction == "ingress" else "net-wireless"
        src_dst = "src" if direction == "ingress" else "dst"
        cmd = ""

        for i in range(self.total):
            addr = "10.9.0.{}".format(100+i)
            filter_addr = addr
            if addr_type == "ether":
                filter_addr = get_mac_addr(addr)
            elif addr_type == "ip6":
                filter_addr = get_ipv6_addr(addr)
            cmd += TC_FILTER.format(id=i, dev=dev, proto=proto, prio=priority, addr_type=addr_type, src_dst=src_dst, addr=filter_addr)
            
        for i in range(self.total):
            self.__run_docker_exec(self.routers[i]['dockerID'], cmd)

        return self
    
    def get_route_and_loss_from_ping(self, router_id):
        '''
        @brief get routes and loss running `ping` inside containers.
        '''

        str_format = "{:^5}|{:^30}|{:^20}"
        print("==================[ Route Info From Ping ]==================")
        print ("SRC: ", router_id)
        print(str_format.format("DST", "Route", "Loss"))
        for i in range(self.total):
            _, output = self.routers[router_id]['container'].exec_run('ping -i 0.01 -c 100 10.0.0.{id} -R'.format(id=100+i))
            # route
            output = output.decode('utf-8')
            loss = output.split("\n")[-3].split(",")[-2]
            route_list=""
            if loss.split("%")[0].strip() != "100":
                route_list = []
                route = output.split("\n\n")[0].split("RR:")[1].replace("\t", "").strip().split()
                for r in route:
                    route_list.append(int(r.split('.')[-1])-100)
                route_list = ", ".join(str(e) for e in route_list)
            print (str_format.format(str(i), route_list, loss))
