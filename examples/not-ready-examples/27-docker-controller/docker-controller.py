import docker
import tarfile
import io
from seedemu import *

client = docker.from_env()

# Get containers by service name. (web, dhcp, dns ...)
containers = client.containers.list()
web_containers = []
for container in containers:
    print(container.attrs['Config']['Labels'].keys())
    if 'org.seedsecuritylabs.seedemu.meta.service' in container.attrs['Config']['Labels'].keys():
        if container.attrs['Config']['Labels']['org.seedsecuritylabs.seedemu.meta.service'] == "Web Service":
            web_containers.append(container)

for web in web_containers:
    print(web.name)
    # Execute Commands
    print(web.exec_run('ls').output.decode())

    # Get file from containers
    bits, stat = web.get_archive('/seedemu_sniffer') 
    for chunk in bits:
        tar = tarfile.TarFile(fileobj=io.BytesIO(chunk))
        for member in tar:
            print(tar.extractfile(member.name).read().decode())


# create Dockerfile for a dynamic-node
emu = Emulator()

emu.load('./base-component.bin')

base:Base = emu.getLayer('Base')
as151 = base.getAutonomousSystem(151)
as151.createHost('dynamic-node').joinNetwork('net0', address='10.151.0.99')

emu.render()
obj = emu.getRegistry().get(type='hnode', scope='151', name='dynamic-node')
docker = Docker()
#a = docker._compileNode(obj)
#print(a)

# create dynamic-node image
img = client.images.build(path="/home/seed/seed-emulator/hnode_151_dynamic-node", tag='dynamic-node')
a = client.containers.get('as151h-host2')
a.stop()
client.containers.prune()
# run dynamic-node container
client.containers.run('dynamic-node', cap_add=["ALL"], name='as151h-host2', detach=True, network='output_net_151_net0')

#net_151 = client.networks.get('output_net_151_net0')
#net_151.disconnect(a, force=True)
#net_151.connect(a, ipv4_address='10.151.0.99')
    