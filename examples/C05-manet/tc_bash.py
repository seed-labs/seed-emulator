#!/usr/bin/env python3
# encoding: utf-8

import docker
import json
from threading import Thread, Lock
from multiprocessing import Process
import time
import subprocess
import os

def cal_loss_latency(dist):
    loss = dist//200 * 10
    latency = dist%200

    return loss, latency

def work(container, node2, dist):
    loss, latency = cal_loss_latency(int(dist))
    command = "docker container exec {container} {cmd}".format(
        container = container,
        cmd = tc_command.format(id=node2, loss=loss, latency=latency)
    ).split()

    subprocess.Popen(command,start_new_session=True)

client = docker.from_env()
containers = {}
client.containers.list()
for container in client.containers.list():
    labels = container.attrs['Config']['Labels']
    addr = labels.get("org.seedsecuritylabs.seedemu.meta.net.0.address").split("/")[0]
    containers[addr] = container.name

start = time.time()

f = open("/home/won/master/seed-emulator/examples/C05-manet/command/node_pos.json")

data = json.load(f)
tc_command = 'tc qdisc change dev eth1 parent 1:1{id} handle 1{id} netem loss {loss}% latency {latency}ms'

worker = []
for node in data["node_info"]:
    container = containers[node["ipaddress"]]

    for node2, dist in node["dist"].items():
        th = Thread(target=work, args=(container, node2, dist))
        th.start()
        worker.append(th)

for th in worker:
    th.join()

end = time.time()
print(end-start)