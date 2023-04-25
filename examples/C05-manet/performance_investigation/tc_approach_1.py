#!/usr/bin/env python3
# encoding: utf-8

#!/usr/bin/env python3
# encoding: utf-8

from dockercontroller import * 
import time

container = get_container_by_ip("10.0.0.1")
tc_command = 'tc qdisc change dev eth1 parent 1:1{id} handle 1{id} netem loss {loss}% latency {latency}ms'

elasped_time = 0
for test in range(10):
    start = time.time()

    for i in range(100):
        container.exec_run(tc_command.format(id=2,loss=0,latency=i), detach=True)

    end = time.time()
    elasped_time += (end-start)
    
print("avg: ", elasped_time/10)
