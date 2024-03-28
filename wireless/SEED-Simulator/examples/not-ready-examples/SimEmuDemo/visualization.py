#!/bin/env python3 

import pandas as pd
# import numpy as np
import docker
import json
import time
import shutil
from datetime import datetime, timedelta

NODE_TOTAL  = 30
ITERDUATION = 1
ITERATION   = 30

file_path = "/tmp/seedsim/setting/info.txt"

with open(file_path, 'r') as file:
    # Read the entire content of the file
    file_content = file.read()

sim_info = file_content.split("-")

sleep_interval = float(sim_info[3])

# Given time in string format
time_str = sim_info[2]
desired_start_time = []
# Convert string to datetime object
datetime_obj = datetime.strptime(time_str, "%H:%M:%S")

# Add 10 seconds
time_interval = 1
for i in range(ITERATION):
    desired_start_time.append(datetime_obj.time())
    datetime_obj = datetime_obj + timedelta(seconds=ITERDUATION)

#Iter tx_node_id rx_node_id TxPosX[m] TxPosY[m] RxPosX[m] RxPosY[m] Distance[m] ChannelState LossRate Delay

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

df = pd.read_csv('/tmp/seedsim/siminfo/siminfo.csv', delimiter=' ')

for iter in range(iteration):
    node_info = {
        "current_iter" : iter,
        "node_count": node_total,
        "node_info": [],
        "building_info": []
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

    while True:
        if iter == 0:
            break
        elif datetime.utcnow().time() >= desired_start_time[iter]:
            print(desired_start_time[iter])
            break
        else:
            print("sleep")
            time.sleep(sleep_interval)
    file_path = "/tmp/node_info/node_pos_{iter}.json".format(iter=iter)

    # Write the dictionary to a JSON file
    with open(file_path, 'w') as json_file:
        json.dump(node_info, json_file, indent=2)

    shutil.copy(file_path, "/tmp/node_info/node_pos.json")