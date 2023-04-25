#!/usr/bin/env python3
# encoding: utf-8

import docker
import json
from threading import Thread, Lock
from multiprocessing import Process
import time

def cal_loss_latency(dist):
    loss = dist//100 * 10
    latency = dist&100

    return loss, latency

def work(container, container_lock, tc_cmd):    
    with container_lock:
        container.exec_run("bash -c 'echo {}'".format("'{}' > test.sh".format("hihi\;hihi")), detach=True)#.format(tc_cmd), detach=True)

client = docker.from_env()
containers = {}
containers_lock = {}
client.containers.list()
for container in client.containers.list():
    labels = container.attrs['Config']['Labels']
    addr = labels.get("org.seedsecuritylabs.seedemu.meta.net.0.address").split("/")[0]
    containers[addr] = container
    containers_lock[addr] = Lock()

start = time.time()

f = open("/home/won/master/seed-emulator/examples/C05-manet/command/node_pos.json")

data = json.load(f)
tc = 'tc qdisc change dev eth1 parent 1:1{id} handle 1{id} netem loss {loss}% latency {latency}ms; '

worker = []
for node in data["node_info"]:
    container = containers[node["ipaddress"]]
    container_lock = containers_lock[node["ipaddress"]]
    tc_cmd = ""
    for node2, dist in node["dist"].items():
        loss, latency = cal_loss_latency(int(dist))
        tc_cmd += tc.format(id=node2, loss=loss, latency=latency)
    # _, output = container.exec_run("bash -c '{}'".format(tc_cmd), detach=True)
    # print(str(output))
        
    th = Thread(target=work, args=(container, container_lock, tc_cmd))
    th.start()
    worker.append(th)

for th in worker:
    th.join()

end = time.time()
print(end-start)
