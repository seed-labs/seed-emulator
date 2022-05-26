#!/usr/bin/env python3
# encoding: utf-8

import docker
import tarfile
import io
import shutil
import os
from seedemu import *
import itertools, string
import yaml

client = docker.from_env()


# Get containers by service name. (web, dhcp, dns ...)
containers = client.containers.list()
web_containers = []
for container in containers:
    #print(container.attrs['Config']['Labels'].keys())
    if 'org.seedsecuritylabs.seedemu.meta.class' in container.attrs['Config']['Labels'].keys():
        print('hi')
        if container.attrs['Config']['Labels']['org.seedsecuritylabs.seedemu.meta.class'] == "WebService":
            web_containers.append(container)
            print('hi')

for web in web_containers:
    print(web.name)
    # Execute Commands
    result = web.exec_run('s')
    print(result.exit_code)
    print(result.output.decode())

    # Get file from containers
    bits, stat = web.get_archive('/seedemu_sniffer') 
    for chunk in bits:
        tar = tarfile.TarFile(fileobj=io.BytesIO(chunk))
        for member in tar:
            print(tar.extractfile(member.name).read().decode())

# create Dockerfile for a dynamic-node
emu = Emulator()
emu1 = Emulator()
emu1.load('./base-component.bin')
emu.load('./base-component.bin')

base:Base = emu.getLayer('Base')
as151 = base.getAutonomousSystem(151)
as151.createHost('dynamic-node').joinNetwork('net0', address='10.151.0.99')

emu.render()
emu1.render()
diff = emu.getRegistry().getAll().keys() - emu1.getRegistry().getAll().keys()
obj = emu.getRegistry().get(type='hnode', scope='151', name='dynamic-node')
docker = Docker()
if os.path.exists('./hnode_151_dynamic-node'):
    shutil.rmtree("./hnode_151_dynamic-node")
a = docker._compileNode(obj)
dct= yaml.load(a)
print(dct)


# create dynamic-node image
img = client.images.build(path="./hnode_151_dynamic-node", tag='dynamic-node')
a = client.containers.get('as151h-host2')
a.stop()
client.containers.prune()
# run dynamic-node container
c = client.containers.create('dynamic-node', cap_add=["ALL"], name='as151h-host2', detach=True, network='output_net_151_net0')
as151 = client.networks.get('output_net_151_net0')
as151.disconnect(c)
as151.connect(c, ipv4_address='10.151.0.99')
c.start()
print(diff)

