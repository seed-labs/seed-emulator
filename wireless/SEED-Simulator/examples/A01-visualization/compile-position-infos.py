#!/bin/env python3 

import pandas as pd
import docker
import json
import shutil

############################################
NODE_TOTAL  = 30
ITERATION   = 30
############################################

LABEL_PREFIX = "org.seedsecuritylabs.seedemu.meta"
CLASS      = LABEL_PREFIX + ".class"
NODENAME   = LABEL_PREFIX + ".nodename"
WIRELESS   = "Wireless"

NETNAME = LABEL_PREFIX + ".net.{}.name"
NETADDR = LABEL_PREFIX + ".net.{}.address"
NET0    = 'net-wireless'

def get_router_infos(containers):
    router_container_ids = {}
    for container in containers:
        if CLASS in container.labels and WIRELESS in container.labels[CLASS]:
            router_id = int(container.labels[NODENAME].split("_")[1])
            router_container_ids[router_id] = {
                                                'container_id': container.id,
                                                'ipaddress': find_net0(container)
                                            }
    
    return router_container_ids

def find_net0(container):
    for i in range(10): # Assume no more than 10 interfaces 
        netname = NETNAME.format(i)
        if netname in container.labels and NET0 in container.labels[netname]:
            ipaddrwithmask = container.labels[NETADDR.format(i)]
            ipaddr = ipaddrwithmask.split('/')[0]
            return ipaddr
        
iteration = ITERATION
node_total = NODE_TOTAL

# Get all the containers
client = docker.from_env()
all_containers = client.containers.list()

router_infos = get_router_infos(all_containers)
# print(router_infos)

json_file_path = '/tmp/node_info/node_pos.json'

# Read JSON data from the file
with open(json_file_path, 'r') as file:
    data = json.load(file)

df = pd.read_csv('/tmp/seedsim/siminfo/siminfo.csv', delimiter=' ')

for iter in range(iteration):
    node_info = {
        "current_iter" : iter,
        "node_count": node_total,
        "node_info": [],
        "building_info": data['building_info']
    }
    
    for node_id in range(node_total):
        if node_id == node_total-1:
            a = df[(df['Iter']==iter)&(df['tx_node_id']==node_id-1)]
            tmp_node_info = {
                "id": node_id,
                "container_id": router_infos[node_id]['container_id'],
                "ipaddress": router_infos[node_id]['ipaddress'],
                "x": a.at[a.index[0], 'RxPosX[m]'].tolist(),
                "y": a.at[a.index[0], 'RxPosY[m]'].tolist(),
                "connectivity": []
            }

        else:
            a = df[(df['Iter']==iter)&(df['tx_node_id']==node_id)]
            tmp_node_info = {
                "id": node_id,
                "container_id": router_infos[node_id]['container_id'],
                "ipaddress": router_infos[node_id]['ipaddress'],
                "x": a.at[a.index[0], 'TxPosX[m]'].tolist(),
                "y": a.at[a.index[0], 'TxPosY[m]'].tolist(),
                "connectivity": []
            }

            for i in a.index:
                rx_id = a.at[i, 'rx_node_id'].tolist()
                tmp_connectivity_info = {
                    "id": rx_id,
                    "container_id": router_infos[rx_id]['container_id'],
                    "loss": a.at[i, 'LossRate']
                }
                tmp_node_info['connectivity'].append(tmp_connectivity_info)
        
        node_info['node_info'].append(tmp_node_info)

    file_path = "/tmp/node_info/node_pos_{iter}.json".format(iter=iter)

    # Write the dictionary to a JSON file
    with open(file_path, 'w') as json_file:
        json.dump(node_info, json_file, indent=2)


shutil.copy("/tmp/node_info/node_pos_0.json", "/tmp/node_info/node_pos.json")
