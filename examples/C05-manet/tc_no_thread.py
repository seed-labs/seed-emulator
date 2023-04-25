#!/usr/bin/env python3
# encoding: utf-8

import docker
import json
import time

def cal_loss_latency(dist):
    loss = dist//100 * 10
    latency = dist&100

    return loss, latency

client = docker.from_env()
containers = {}
client.containers.list()

for container in client.containers.list():
    labels = container.attrs['Config']['Labels']
    addr = labels.get("org.seedsecuritylabs.seedemu.meta.net.0.address").split("/")[0]
    containers[addr] = container

start = time.time()

f = open("/home/won/master/seed-emulator/examples/C05-manet/command/node_pos.json")

data = json.load(f)
tc_command = 'tc qdisc change dev eth1 parent 1:1{id} handle 1{id} netem loss {loss}% latency {latency}ms'

worker = []
for node in data["node_info"]:
    container = containers[node["ipaddress"]]

    for node2, dist in node["dist"].items():
        loss, latency = cal_loss_latency(int(dist))
        container.exec_run(tc_command.format(id=node2, loss=loss, latency=latency), detach=True)
        print(container.name, node2)

end = time.time()
print(end-start)
