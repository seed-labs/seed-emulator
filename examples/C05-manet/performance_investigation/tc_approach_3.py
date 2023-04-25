#!/usr/bin/env python3
# encoding: utf-8

from dockercontroller import * 
import time

container = get_container_by_ip("10.0.0.1")

elasped_time = 0
for test in range(100):
    start = time.time()

    container.exec_run("bash -c 'tc -b /tc_batch'")
    end = time.time()
    elasped_time += (end-start)

print("avg: ", elasped_time/100)
