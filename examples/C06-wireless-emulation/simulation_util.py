#!/bin/env python3 

import docker
import os, json
import random
import numpy as np
from typing import Tuple
from json import JSONEncoder

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

TC_CMD = 'tc qdisc replace dev {dev} parent 1:1{id} handle 1{id}: netem delay 0ms loss {loss}%\n'
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

class NodeInfoEncoder(JSONEncoder):
        def default(self, o):
            return o.__dict__ 
        
class NodeInfo:
    id:int
    # position : (x, y)
    x:int
    y:int
    # direction : (dx, dy)
    direction:Tuple[int, int]
    container_id:str
    ipaddress:str
    distance:dict
    connectivity:list

    def __init__(self, node_id:int, container_id:str, ipaddress:str,
                 x:int=None, y:int=None, distance:dict={}, connectivity:list=[],
                 direction:list=None) -> None:
        self.id = node_id
        self.ipaddress = ipaddress
        self.container_id = container_id
        self.distance = distance
        self.connectivity = connectivity

        self.x = x if x else int(node_id%6) * 100
        self.y = y if y else int(node_id//6) * 100
        if direction: self.direction = direction
        else: self.__setDirection()

    def __setDirection(self):
        dx = random.randint(-100, 100)
        dy = random.randint(-100, 100)
        self.direction = (dx, dy)

    def move(self):
        x, y = self.x, self.y
        dx, dy = self.direction

        if x+dx > 1000 or x+dx < 0:
            dx *= (-1)

        if y+dy > 1000 or y+dy < 0:
            dy *= (-1)

        self.x, self.y = (x+dx, y+dy)
        self.direction = (dx, dy)

        return self

class Simulation:
    total:int
    routers:list
    topology:list
    node_info:dict
    moved:int
    override:bool

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
        self.topology = [[0 for col in range(self.total)] for row in range(self.total)]
        self.override = override
        self.__init_node_info()

        self._moved = 0
        pass

    def __init_node_info(self):
        self.node_info = {
                    "node_count": self.total, 
                    "node_info": []
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

        json_object = json.dumps(self.node_info, indent=4, cls=NodeInfoEncoder)
    
        # Writing to sample.json
        if not os.path.exists(JSON_FOLDER):
            os.mkdir(JSON_FOLDER)
        
        with open(JSON_PATH, "w") as outfile:
            outfile.write(json_object)

    def __get_distance(self, x1, y1, x2, y2):
        a = np.array((x1, y1))
        b = np.array((x2, y2))

        dist = np.sqrt(np.sum(np.square(a-b)))
        return dist
    
    def __get_loss(self, dist):
        loss = 100
        if dist <= 100:
            loss = 0
        elif dist <= 200:
            loss = 20    
        elif dist <= 300:
            loss = 40
        elif dist <= 400:
            loss = 60
        # elif dist <= 500:
        #     loss = 80
        return loss

    def __set_topology_from_data(self, node_info):
        for node in node_info:
            for connection in node.connectivity:
                self.topology[node.id][connection['id']] = connection['loss']

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
    
    def __get_tc_cmd(self, loss):
        '''
        @brief craft tc command with the given loss.

        @param loss to set

        returns tc command
        '''
        cmd = ''
        for i in range(len(loss)):
            cmd += TC_CMD.format(id=i, dev="ifb0", loss=loss[i])
        return cmd
    
    def __run_docker_exec (self, dockerID, cmd):
        '''
        @brief run command inside docker container.

        @param dockerID docker container id to run command
        @param cmd command to run 
        '''
        dockercmd = "docker exec {} bash -c \"{}\" ".format(dockerID, cmd)
        os.system(dockercmd)

    def move_and_update_loss(self):
        self._moved += 1
        print(self._moved)
        # move all nodes' positions
        for i in range(self.total):
            self.node_info["node_info"][i].move()
            
        # update loss
        for i in range(self.total):
            x1, y1 = self.node_info["node_info"][i].x, self.node_info["node_info"][i].y
            self.node_info["node_info"][i].connectivity = []
            for j in range(i+1, self.total):
                x2, y2 = self.node_info["node_info"][j].x, self.node_info["node_info"][j].y
                dist = self.__get_distance(x1, y1, x2, y2)
                self.node_info["node_info"][i].distance[str(j)] = dist
                self.node_info["node_info"][i].connectivity.append({
                    "id":j,
                    "container_id":self.routers[j]['container'].id,
                    "loss":self.__get_loss(dist)
                })
                
        self.__set_topology_from_data(self.node_info["node_info"])

        # Serializing json
        json_object = json.dumps(self.node_info, indent=4, cls=NodeInfoEncoder)

        # Writing to sample.json
        with open(JSON_PATH, "w") as outfile:
            outfile.write(json_object)

    def move_nodes(self, nodes):

        node_total = self.total
        for id, x, y in nodes:
            self.node_info["node_info"][id].x, self.node_info["node_info"][id].y = x, y

        # update loss
        for i in range(node_total):
            x1, y1 = self.node_info["node_info"][i].x, self.node_info["node_info"][i].y
            self.node_info["node_info"][i].connectivity = []
            for j in range(i+1, node_total):
                x2, y2 = self.node_info["node_info"][j].y, self.node_info["node_info"][j].y
                dist = self.__get_distance(x1, y1, x2, y2)
                self.node_info["node_info"][i].distance[str(j)] = dist
                self.node_info["node_info"][i].connectivity.append({
                    "id":j,
                    "container_id":self.routers[j]['container'].id,
                    "loss":self.__get_loss(dist)
                })
                
        self.__set_topology_from_data(self.node_info["node_info"])

        # Serializing json
        json_object = json.dumps(self.node_info, indent=4, cls=NodeInfoEncoder)
        
        # Writing to sample.json
        with open(JSON_PATH, "w") as outfile:
            outfile.write(json_object)

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
                        print("no route")
                        break
                    routes.append(next)
                    loss = self.topology[prev][next]
                    if prev > next:
                        loss = self.topology[next][prev]
                        
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
        print("======================[ Route Info ]======================")
        print("SRC: ", src)
        print(str_format.format("DST", "Route", "Loss"))
        for i in range(self.total):
            routes = ", ".join(str(e) for e in self.route_info[src][i]['routes'])
            loss = str(self.route_info[src][i]['loss'])
            print(str_format.format(str(i), routes, loss))

    def update_loss_on_topology_all(self, threshold = 0.50):
        '''!
        @brief Update loss on self.topology (symmetric matrix)
               size the total number of router nodes (self.total)
        @param threshold the percentage of loss 100% (disconnection) 
        '''
        size = self.total
        
        for i in range(size):
            self.topology[i][i] = 0
            for j in range(i+1, size): 
                rand = random.randint(0, 100)
                if rand > threshold*100:
                    loss = random.randint(0, 5)*10
                    self.topology[i][j] = loss
                else:
                    self.topology[i][j] = 100
                
            # for j in range(i): 
            #     self.topology[i][j] = self.topology[j][i] 
        self.topology = self.topology
        return self.topology
    
    def update_loss_on_topology(self, src, dst, loss):
        '''
        @brief Update loss on self.topology by manual.

        @param src source node id
        @param dst destination node id
        @param loss to set
        '''
        
        self.topology[src][dst] = loss
        #self.topology[dst][src] = loss
        return self
    
    def set_topology(self, topo):
        self.topology = topo
        return self
    
    def update_loss_on_containers(self):
        '''
        @brief Update loss on containers.
        '''
        for k in range(self.total):   
            cmd = self.__get_tc_cmd(self.topology[k]) 
            print("Node {:2d}: ".format(k), end='')
            for loss in self.topology[k]:
                print("{:3d} ".format(loss), end='')
            print("")
            self.__run_docker_exec(self.routers[k]['dockerID'], cmd)

    def print_topology(self):
        """
        @brief print topology containing loss values.
        """
        total = self.total
        topology = self.topology

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
