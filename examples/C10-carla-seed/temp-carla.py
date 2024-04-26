#!/usr/bin/env python3
# encoding: utf-8


import os
from seedemu import *

def import_directory(host, directory_path, container_base_path):
    """
    Traverse a directory and import each file into a Docker container using given method on a host object.
    
    Args:
        host: The host object with .importFile method.
        directory_path (str): Path to the directory on the host.
        container_base_path (str): Base path in the container where files will be stored.
    """
    relative_path = directory_path
    absolute_path = os.path.abspath(relative_path)

    # Normalize the container base path
    if not container_base_path.endswith('/'):
        container_base_path += '/'

    for root, dirs, files in os.walk(absolute_path):
        for file in files:
            host_path = os.path.join(root, file)
            relative_path = os.path.relpath(host_path, start=absolute_path)
            container_path = os.path.join(container_base_path, relative_path.replace('\\', '/'))  # replace for Windows paths

            # Call the .importFile method for each file
            host.importFile(hostpath=host_path, containerpath=container_path)


###############################################################################
emu     = Emulator()
base    = Base()
routing = Routing()
ebgp    = Ebgp()
ibgp    = Ibgp()
ospf    = Ospf()
web     = WebService()
ovpn    = OpenVpnRemoteAccessProvider()
etc_hosts = EtcHosts()


###############################################################################

ix100 = base.createInternetExchange(100)

# Customize names (for visualization purpose)
ix100.getPeeringLan().setDisplayName('CARLA-SEED')


as150 = base.createAutonomousSystem(150)
as150.createNetwork('net0')
as150.createRouter('router0').joinNetwork('net0').joinNetwork('ix100')
as150.createHost('websocket').joinNetwork('net0').addHostName('websocket')

as151 = base.createAutonomousSystem(151)
as151.createNetwork('net0')
as151.createRouter('router0').joinNetwork('net0').joinNetwork('ix100')
as151.createHost('controller').joinNetwork('net0').addHostName('controller')

as152 = base.createAutonomousSystem(152)
as152.createNetwork('net0')
as152.createRouter('router0').joinNetwork('net0').joinNetwork('ix100')
as152.createHost('seedcar1').joinNetwork('net0').addHostName('seedcar1')

as153 = base.createAutonomousSystem(153)
as153.createNetwork('net0')
as153.createRouter('router0').joinNetwork('net0').joinNetwork('ix100')
as153.createHost('seedcar2').joinNetwork('net0').addHostName('seedcar2')

as154 = base.createAutonomousSystem(154)
as154.createNetwork('net0')
as154.createRouter('router0').joinNetwork('net0').joinNetwork('ix100')
as154.createHost('seedcar3').joinNetwork('net0').addHostName('seedcar3')

as155 = base.createAutonomousSystem(155)
as155.createNetwork('net0')
as155.createRouter('router0').joinNetwork('net0').joinNetwork('ix100')
as155.createHost('seedcar4').joinNetwork('net0').addHostName('seedcar4')

as156 = base.createAutonomousSystem(156)
as156.createNetwork('net0')
as156.createRouter('router0').joinNetwork('net0').joinNetwork('ix100')
as156.createHost('seedcar5').joinNetwork('net0').addHostName('seedcar5')

as157 = base.createAutonomousSystem(157)
as157.createNetwork('net0')
as157.createRouter('router0').joinNetwork('net0').joinNetwork('ix100')
as157.createHost('seedcar6').joinNetwork('net0').addHostName('seedcar6')

as158 = base.createAutonomousSystem(158)
as158.createNetwork('net0')
as158.createRouter('router0').joinNetwork('net0').joinNetwork('ix100')
as158.createHost('traffic').joinNetwork('net0').addHostName('traffic')

# Create real-world AS.
# AS11872 is the Syracuse University's autonomous system

as11872 = base.createAutonomousSystem(11872)
as11872.createRealWorldRouter('rw-11872-syr').joinNetwork('ix100', '10.100.0.95')

###############################################################################
# Create hybrid AS.
# AS99999 is the emulator's autonomous system that routes the traffics to the real-world internet
as99999 = base.createAutonomousSystem(99999)
as99999.createRealWorldRouter('rw-real-world', prefixes=['0.0.0.0/1', '128.0.0.0/1']).joinNetwork('ix100', '10.100.0.99')
###############################################################################

ebgp.addRsPeer(100, 150)
ebgp.addRsPeer(100, 151)
ebgp.addRsPeer(100, 152)
ebgp.addRsPeer(100, 153)
ebgp.addRsPeer(100, 154)
ebgp.addRsPeer(100, 155)
ebgp.addRsPeer(100, 156)
ebgp.addRsPeer(100, 157)
ebgp.addRsPeer(100, 158)
ebgp.addRsPeer(100, 11872)
ebgp.addRsPeer(100, 99999)

###############################################################################

# Add layers to the emulator
emu.addLayer(base)
emu.addLayer(routing)
emu.addLayer(ebgp)
emu.addLayer(ibgp)
emu.addLayer(ospf)
emu.addLayer(web)
emu.addLayer(etc_hosts)


websocket = as150.getHost('websocket')
websocket.addBuildCommand(
    'apt-get update &&'
    'apt-get install -y software-properties-common &&'
    'add-apt-repository -y ppa:deadsnakes/ppa &&'
    'apt-get update && apt-get install -y python3.7 python3-pip python3.7-distutils &&'
    'update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.7 1 &&'
    'python3.7 -m pip install --upgrade pip'
)
import_directory(websocket, 'webserver', '/webserver')
websocket.addBuildCommand("pip3.7 install carla asyncio websockets")
websocket.addPortForwarding(6789, 6789)
websocket.appendStartCommand('( sleep 10; python3.7 -u /webserver/webserver.py --w_ip=0.0.0.0 --w_port=6789 > carla_webserver.log 2>&1 ) &')

controller = as151.getHost('controller')
controller.addBuildCommand(
    'apt-get update &&'
    'apt-get install -y software-properties-common &&'
    'add-apt-repository -y ppa:deadsnakes/ppa &&'
    'apt-get update && apt-get install -y python3.7 python3-pip python3.7-distutils &&'
    'update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.7 1 &&'
    'python3.7 -m pip install --upgrade pip'
)
import_directory(controller, 'controller', '/controller')
controller.addBuildCommand("pip3.7 install carla asyncio websockets numpy numpy==1.18.4 psutil py-cpuinfo python-tr")

seedcar1 = as152.getHost('seedcar1')
seedcar1.addBuildCommand(
    'apt-get update &&'
    'apt-get install -y software-properties-common &&'
    'add-apt-repository -y ppa:deadsnakes/ppa &&'
    'apt-get update && apt-get install -y python3.7 python3-pip python3.7-distutils &&'
    'update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.7 1 &&'
    'python3.7 -m pip install --upgrade pip'
)
import_directory(seedcar1, 'automatic_control', '/automatic_control')
seedcar1.addBuildCommand("pip3.7 install carla asyncio websockets datetime numpy numpy==1.18.4 networkx distro Shapely==1.6.4.post2")
seedcar1.appendStartCommand('( sleep 20; python3.7 -u /automatic_control/headless_automatic_control.py --ws_ip=10.150.0.71 --ws_port=6789 --host=128.230.114.88 --port=2000 --r_name=car1 --cam=on --ws_enable on -l > /seedcar1.log 2>&1 ) &')

seedcar2 = as153.getHost('seedcar2')
seedcar2.addBuildCommand(
    'apt-get update &&'
    'apt-get install -y software-properties-common &&'
    'add-apt-repository -y ppa:deadsnakes/ppa &&'
    'apt-get update && apt-get install -y python3.7 python3-pip python3.7-distutils &&'
    'update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.7 1 &&'
    'python3.7 -m pip install --upgrade pip'
)
import_directory(seedcar2, 'automatic_control', '/automatic_control')
seedcar2.addBuildCommand("pip3.7 install carla asyncio websockets datetime numpy numpy==1.18.4 networkx distro Shapely==1.6.4.post2")
seedcar2.appendStartCommand('( sleep 25; python3.7 -u /automatic_control/headless_automatic_control.py --ws_ip=10.150.0.71 --ws_port=6789 --host=128.230.114.88 --port=2000 --r_name=car2 --cam=off --ws_enable on -l > /seedcar2.log 2>&1 ) &')

seedcar3 = as154.getHost('seedcar3')
seedcar3.addBuildCommand(
    'apt-get update &&'
    'apt-get install -y software-properties-common &&'
    'add-apt-repository -y ppa:deadsnakes/ppa &&'
    'apt-get update && apt-get install -y python3.7 python3-pip python3.7-distutils &&'
    'update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.7 1 &&'
    'python3.7 -m pip install --upgrade pip'
)
import_directory(seedcar3, 'automatic_control', '/automatic_control')
seedcar3.addBuildCommand("pip3.7 install carla asyncio websockets datetime numpy numpy==1.18.4 networkx distro Shapely==1.6.4.post2")
seedcar3.appendStartCommand('( sleep 30; python3.7 -u /automatic_control/headless_automatic_control.py --ws_ip=10.150.0.71 --ws_port=6789 --host=128.230.114.88 --port=2000 --r_name=car3 --cam=off --ws_enable on -l > /seedcar3.log 2>&1 ) &')

seedcar4 = as155.getHost('seedcar4')
seedcar4.addBuildCommand(
    'apt-get update &&'
    'apt-get install -y software-properties-common &&'
    'add-apt-repository -y ppa:deadsnakes/ppa &&'
    'apt-get update && apt-get install -y python3.7 python3-pip python3.7-distutils &&'
    'update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.7 1 &&'
    'python3.7 -m pip install --upgrade pip'
)
import_directory(seedcar4, 'automatic_control', '/automatic_control')
seedcar4.addBuildCommand("pip3.7 install carla asyncio websockets datetime numpy numpy==1.18.4 networkx distro Shapely==1.6.4.post2")
seedcar4.appendStartCommand('( sleep 35; python3.7 -u /automatic_control/headless_automatic_control.py --ws_ip=10.150.0.71 --ws_port=6789 --host=128.230.114.88 --port=2000 --r_name=car4 --cam=off --ws_enable on -l > /seedcar4.log 2>&1 ) &')

seedcar5 = as156.getHost('seedcar5')
seedcar5.addBuildCommand(
    'apt-get update &&'
    'apt-get install -y software-properties-common &&'
    'add-apt-repository -y ppa:deadsnakes/ppa &&'
    'apt-get update && apt-get install -y python3.7 python3-pip python3.7-distutils &&'
    'update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.7 1 &&'
    'python3.7 -m pip install --upgrade pip'
)
import_directory(seedcar5, 'automatic_control', '/automatic_control')
seedcar5.addBuildCommand("pip3.7 install carla asyncio websockets datetime numpy numpy==1.18.4 networkx distro Shapely==1.6.4.post2")
seedcar5.appendStartCommand('( sleep 40; python3.7 -u /automatic_control/headless_automatic_control.py --ws_ip=10.150.0.71 --ws_port=6789 --host=128.230.114.88 --port=2000 --r_name=car5 --cam=off --ws_enable on -l > /seedcar5.log 2>&1 ) &')

seedcar6 = as157.getHost('seedcar6')
seedcar6.addBuildCommand(
    'apt-get update &&'
    'apt-get install -y software-properties-common &&'
    'add-apt-repository -y ppa:deadsnakes/ppa &&'
    'apt-get update && apt-get install -y python3.7 python3-pip python3.7-distutils &&'
    'update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.7 1 &&'
    'python3.7 -m pip install --upgrade pip'
)
import_directory(seedcar6, 'automatic_control', '/automatic_control')
seedcar6.addBuildCommand("pip3.7 install carla asyncio websockets datetime numpy numpy==1.18.4 networkx distro Shapely==1.6.4.post2")
seedcar6.appendStartCommand('( sleep 45; python3.7 -u /automatic_control/headless_automatic_control.py --ws_ip=10.150.0.71 --ws_port=6789 --host=128.230.114.88 --port=2000 --r_name=car6 --cam=off --ws_enable on -l > /seedcar6.log 2>&1 ) &')


traffic = as158.getHost('traffic')
traffic.addBuildCommand(
    'apt-get update &&'
    'apt-get install -y software-properties-common &&'
    'add-apt-repository -y ppa:deadsnakes/ppa &&'
    'apt-get update && apt-get install -y python3.7 python3-pip python3.7-distutils &&'
    'update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.7 1 &&'
    'python3.7 -m pip install --upgrade pip'
)
import_directory(traffic, 'traffic', '/traffic')
traffic.addBuildCommand("pip3.7 install carla datetime numpy numpy==1.18.4")
traffic.appendStartCommand('( sleep 15 && python3.7 -u /traffic/generate_traffic.py --host=128.230.114.88 --port=2000 --asynch --safe --respawn --number-of-vehicles 5 --number-of-walkers 2  > /traffic.log 2>&1 ) &')

# Commented code
# as159 = base.createAutonomousSystem(159)
# as159.createNetwork('net0')
# as159.createRouter('router0').joinNetwork('net0').joinNetwork('ix100')
# carlaviz = emu.getLayer('Base').getAutonomousSystem(159).createHost('carlaviz')
# carlaviz.joinNetwork('net0').addHostName('carlaviz')

# Save it to a component file, so it can be used by other emulators
#emu.dump('base-component.bin')

# Uncomment the following if you want to generate the final emulation files
emu.render()
#print(dns.getZone('.').getRecords())
docker = Docker(internetMapEnabled=True,internetMapPort=8090)
#carlaviz_image = 'mjxu96/carlaviz:0.9.15'
#image = DockerImage(name=carlaviz_image, local=False, software=[])
#docker.addImage(image)
#docker.setImageOverride(carlaviz, carlaviz_image)
emu.compile(docker, './output/', override = True)

