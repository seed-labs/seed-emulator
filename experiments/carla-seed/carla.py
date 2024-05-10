#!/usr/bin/env python3
# encoding: utf-8


import os
import yaml
from seedemu import *


# Load environment variables
CARLA_IP = "128.230.114.88"
CARLA_PORT = 2000
ROLE_NAME_1 = "car1"
ROLE_NAME_2 = "car2"
ROLE_NAME_3 = "car3"
ROLE_NAME_4 = "car4"
ROLE_NAME_5 = "car5"
ROLE_NAME_6 = "car6"
CAMERA_1 = "on"
CAMERA_2 = "off"
CAMERA_3 = "off"
CAMERA_4 = "off"
CAMERA_5 = "off"
CAMERA_6 = "off"
AGENT_TYPE = "Behavior" # Choices:"Behavior", "Basic", "Constant"
AGENT_BEHAVIOR = "cautious" # Choices:"normal", "aggressive", "cautious"
TRAFFIC_VEHICLES_NO = 5
TRAFFIC_WALKERS_NO = 2
CARLAVIZ_LOGFILE_NAME = "carlaviz.log"
CARLAVIZ_EGO_VEHICHLE_NAME = "car1"
CARLAVIZ_RETRY_SECONDS = 300

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
seedcar1.appendStartCommand(f'( sleep 20; python3.7 -u /automatic_control/headless_automatic_control.py --ws_ip=websocket --ws_port=6789 --host={CARLA_IP} --port={CARLA_PORT} --agent={AGENT_TYPE} --behavior={AGENT_BEHAVIOR} --r_name={ROLE_NAME_1} --cam={CAMERA_1} --ws_enable on -l > /seed{ROLE_NAME_1}.log 2>&1 ) &')

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
seedcar2.appendStartCommand(f'( sleep 25; python3.7 -u /automatic_control/headless_automatic_control.py --ws_ip=websocket --ws_port=6789 --host={CARLA_IP} --port={CARLA_PORT} --agent={AGENT_TYPE} --behavior={AGENT_BEHAVIOR} --r_name={ROLE_NAME_2} --cam={CAMERA_2} --ws_enable on -l > /seed{ROLE_NAME_2}.log 2>&1 ) &')

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
seedcar3.appendStartCommand(f'( sleep 30; python3.7 -u /automatic_control/headless_automatic_control.py --ws_ip=websocket --ws_port=6789 --host={CARLA_IP} --port={CARLA_PORT} --agent={AGENT_TYPE} --behavior={AGENT_BEHAVIOR} --r_name={ROLE_NAME_3} --cam={CAMERA_3} --ws_enable on -l > /seed{ROLE_NAME_3}.log 2>&1 ) &')

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
seedcar4.appendStartCommand(f'( sleep 35; python3.7 -u /automatic_control/headless_automatic_control.py --ws_ip=websocket --ws_port=6789 --host={CARLA_IP} --port={CARLA_PORT} --agent={AGENT_TYPE} --behavior={AGENT_BEHAVIOR} --r_name={ROLE_NAME_4} --cam={CAMERA_4} --ws_enable on -l > /seed{ROLE_NAME_4}.log 2>&1 ) &')

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
seedcar5.appendStartCommand(f'( sleep 40; python3.7 -u /automatic_control/headless_automatic_control.py --ws_ip=websocket --ws_port=6789 --host={CARLA_IP} --port={CARLA_PORT} --agent={AGENT_TYPE} --behavior={AGENT_BEHAVIOR} --r_name={ROLE_NAME_5} --cam={CAMERA_5} --ws_enable on -l > /seed{ROLE_NAME_5}.log 2>&1 ) &')

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
seedcar6.appendStartCommand(f'( sleep 45; python3.7 -u /automatic_control/headless_automatic_control.py --ws_ip=websocket --ws_port=6789 --host={CARLA_IP} --port={CARLA_PORT} --agent={AGENT_TYPE} --behavior={AGENT_BEHAVIOR} --r_name={ROLE_NAME_6} --cam={CAMERA_6} --ws_enable on -l > /seed{ROLE_NAME_6}.log 2>&1 ) &')

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
traffic.appendStartCommand(f'( sleep 15 && python3.7 -u /traffic/generate_traffic.py --host={CARLA_IP} --port={CARLA_PORT} --asynch --safe --respawn --number-of-vehicles={TRAFFIC_VEHICLES_NO} --number-of-walkers={TRAFFIC_WALKERS_NO}  > /traffic.log 2>&1 ) &')

# Commented code
# as159 = base.createAutonomousSystem(159)
# as159.createNetwork('net0')
# as159.createRouter('router0').joinNetwork('net0').joinNetwork('ix100')
# carlaviz = emu.getLayer('Base').getAutonomousSystem(159).createHost('carlaviz')
# carlaviz.joinNetwork('net0').addHostName('carlaviz')

# Save it to a component file, so it can be used by other emulators
#emu.dump('base-component.bin')

# Function to append Carlaviz configuration to docker-compose.yml
def append_carlaviz_to_compose(output_dir):
    compose_file_path = os.path.join(output_dir, 'docker-compose.yml')
    
    # Read the current content of the Docker Compose file
    with open(compose_file_path, 'r') as file:
        data = yaml.safe_load(file)
    
    # Define the Carlaviz configuration
    carlaviz_config = {
        'image': 'mjxu96/carlaviz:0.9.15',
        'network_mode': 'host',
        'command': [
        f"--simulator_host {CARLA_IP}", 
        f"--simulator_port {CARLA_PORT}",
        f"--log_filename {CARLAVIZ_LOGFILE_NAME}",
        f"--simulator_ego_vehicle_name seed{CARLAVIZ_EGO_VEHICHLE_NAME}",
        f"--simulator_retry_interval_seconds {CARLAVIZ_RETRY_SECONDS}", 
        f"--simulator_retry_times_after_disconnection {CARLAVIZ_RETRY_SECONDS}"
        ]
    }

    # Insert the Carlaviz configuration at the end of the services block
    if 'services' not in data:
        data['services'] = {}
    data['services']['carlaviz'] = carlaviz_config
    
    # Write back the modified content to the Docker Compose file
    with open(compose_file_path, 'w') as file:
        yaml.safe_dump(data, file, default_flow_style=False, sort_keys=False)


# Uncomment the following if you want to generate the final emulation files
emu.render()
#print(dns.getZone('.').getRecords())
docker = Docker(internetMapEnabled=True,internetMapPort=8090)
#carlaviz_image = 'mjxu96/carlaviz:0.9.15'
#image = DockerImage(name=carlaviz_image, local=False, software=[])
#docker.addImage(image)
#docker.setImageOverride(carlaviz, carlaviz_image)
emu.compile(docker, './output/', override = True)
append_carlaviz_to_compose('./output/')

