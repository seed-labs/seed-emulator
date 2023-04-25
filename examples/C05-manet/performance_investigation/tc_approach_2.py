#!/usr/bin/env python3
# encoding: utf-8

from dockercontroller import * 
import time



container = get_container_by_ip("10.0.0.1")
tc_command = 'tc qdisc change dev eth1 parent 1:1{id} handle 1{id} netem loss {loss}% latency {latency}ms; '

elasped_time = 0
for test in range(10):
    start = time.time()
    tc_script = ''

    for i in range(100):
        tc_script += tc_command.format(id=2,loss=i,latency=0)

    container.exec_run("bash -c '{}'".format(tc_script))
    end = time.time()
    elasped_time += (end-start)
    
print("avg: ", elasped_time/10)
