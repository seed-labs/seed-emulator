import docker
import json
import shutil

LABEL_PREFIX = "org.seedsecuritylabs.seedemu.meta"
JSON_PATH = "/tmp/node_info/node_pos.json"
JSON_FOLDER = "/tmp/node_info"

CLASS      = LABEL_PREFIX + ".class"
NODENAME   = LABEL_PREFIX + ".nodename"
WIRELESS   = "Wireless"

NETNAME = LABEL_PREFIX + ".net.{}.name"
NETADDR = LABEL_PREFIX + ".net.{}.address"
NET0    = 'net-wireless'

def get_ipv6_addr(ipv4):
        ipv4a = ipv4.split('.')
        ipv6  =  "fe80::42:aff:fe" 
        ipv6 += "{:02x}:{:02x}{:02x}".format(int(ipv4a[1]), int(ipv4a[2]), int(ipv4a[3]))

        return ipv6

class SimTool():
    
    
    def __init__(self):
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

        self.loss_topology = [[0 for col in range(self.node_total)] for row in range(self.node_total)]
        

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
        self.node_total = len(routers)
        return routers
    
    def __get_next_hop(self, router):
        _, output = router.exec_run('ip -j route')
        output = json.loads(output.decode('utf-8'))
        next_hop = [None] * 30
        id_list = []
        for route in output:
            if route['dst'].startswith("10.0.0.1"):
                src_router_id = int(route['dst'].split('.')[3])-100
                dst_router_id = src_router_id
                id_list.append(src_router_id)
                if route.get('gateway'):
                    dst_router_id = int(route['gateway'].split('.')[3].split('/')[0]) - 100
                next_hop[src_router_id] = dst_router_id
        for i in range(self.node_total):
            if i not in id_list:
                next_hop[i]=None


        return next_hop
    
    def __get_all_next_hop(self):
        size = self.node_total
        all_next_hop = [[0 for col in range(size)] for row in range(size)]
        for i in range(size):
            all_next_hop[i] = self.__get_next_hop(self.routers[i]['container'])
        
        return all_next_hop
    
    def calc_routes_and_loss(self):
        '''
        @brief get routes from containers using `ip route` command 
               and calculate loss from the routes and self.topology        
        '''
        size = self.node_total
        all_next_hop = self.__get_all_next_hop()
        route_info = [[{'routes':[], 'loss':0} for col in range(size)] for row in range(size)]
        for src in range(size):
            for dst in range(size):
                prev = next = src
                # connectivity = 1
                routes = [src]
                while True:
                    next = all_next_hop[next][dst]
                    if len(routes)>2 and routes[-2]==next:
                        routes = ['no routes']
                        break
                    if next == None:
                        # print("no route")
                        # print("no route")
                        routes = ['no routes']
                        break
                    elif next == dst:
                        routes.append(next)
                        break
                    else:
                        routes.append(next)
                    # if prev > next:
                    #     loss = self.loss_topology[next][prev]
                        
                    # connectivity = connectivity * ((1 - (loss / 100)))
                    if next == dst:
                        break
                    # prev = next
                # if next != dst :
                #     routes = ['no routes']
                route_info[src][dst]['routes'] = routes
                # route_info[src][dst]['loss'] = int((1-connectivity)*100)

        self.route_info = route_info
        return route_info
    
    def get_route_info(self, src, dst):
        assert dst < self.node_total and dst >=0, "input dst node id is out of range"
        routes = ", ".join(str(e) for e in self.route_info[src][dst]['routes'])
        # loss = str(self.route_info[src][dst]['loss'])
        return dst, routes #, loss
        
    def print_route_info(self, src=0, dst="all"):
        # str_format = "{:^5}|{:^30}|{:^20}"
        str_format = "{:^5}|{:^30}"

        print("======================[ Route Info ]======================")
        print("SRC: {}".format(src))
        print(str_format.format("DST", "Route", "Loss"))
        if dst=="all":
            for i in range(self.node_total):
                dst, routes = self.get_route_info(src=src, dst=i)
                print(str_format.format(dst, routes))
        else:
            dst, routes = self.get_route_info(src=src, dst=dst)
            print(str_format.format(dst, routes))
            
    def move_to_iter_at(self, iter):
        
        for router in self.routers:
            router['container'].exec_run('/tc_command/tc_command_{}'.format(iter))#, detach=True)

        shutil.copy("/tmp/node_info/node_pos_{}.json".format(iter), "/tmp/node_info/node_pos.json")
        
