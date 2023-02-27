import os
import getopt
import sys
import docker
import time

client = docker.from_env()
containers = client.containers.list()
            

for container in containers:
    if "10.150.0.71" in container.name:
        source_host = container
        break
        
exit_code, output = source_host.exec_run("ping -c 3 8.8.8.8")
print(exit_code)
print(output)
exit_code, output = source_host.exec_run("ping -c 3 10.151.0.99")
print(exit_code)
print(output)
        
    
