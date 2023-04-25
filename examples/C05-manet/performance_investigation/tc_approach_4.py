#!/usr/bin/env python3
# encoding: utf-8

from dockercontroller import * 
import time
import os

container_pid = get_container_pid_by_ip("10.0.0.1")

elasped_time = 0
for test in range(100):
    start = time.time()
    os.system("sudo nsenter -t {pid} -n tc -b tc_batch".format(pid=container_pid))
    end = time.time()
    elasped_time += (end-start)

print("avg: ", elasped_time/100)
