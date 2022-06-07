# Docker Controller
This example demonstrates the uses of DockerController class. DockerController class is the library for Runtime Interaction with the SEED Emulator. In this class, docker python sdk is used. The detailed manual of docker python sdk can be found in here: https://docker-py.readthedocs.io/en/stable/index.html

## Docker sdk summary
### Client Class
* from_env() : local connect
    ```python
    client = docker.from_env()
    ```

* DockerClient() : remote connect available
    * enable TCP connection for external connection to Docker
(https://gist.github.com/styblope/dc55e0ad2a9848f2cc3307d4819d819f)     
    
    ```python
    client = docker.DockerClient(base_url='https://127.0.0.1:1234')
    ```
### Containers Class
* create() : create a container without starting it
    * `docker create`
* run() : run a container
    * `docker run`
* get() : get a container by name or ID
* list() : list containers
    * `docker ps`
* prune() : delete stopped containers
    * `docker container prune`

    
### Container Class
* attrs
    <details>
    <summary> container.attrs details </summary>
    <div markdown="1">
    container.attrs 

        Id
        Created
        Path
        Args
        State
        Image
        ResolveConfPath
        HostnamePath
        HostsPath
        LogPath
        Name
        RestartCount
        Driver
        Platform
        MountLabel
        ProcessLabel
        AppArmorProfile
        ExecIDs
        HostConfig:Dict
            {'Binds': [], 'ContainerIDFile': '', 'LogConfig': {'Type': 'json-file', 'Config': {}}, 'NetworkMode': 'output_net_3_net0', 'PortBindings': {}, 'RestartPolicy': {'Name': '', 'MaximumRetryCount': 0}, 'AutoRemove': False, 'VolumeDriver': '', 'VolumesFrom': [], 'CapAdd': ['ALL'], 'CapDrop': None, 'CgroupnsMode': 'host', 'Dns': None, 'DnsOptions': None, 'DnsSearch': None, 'ExtraHosts': None, 'GroupAdd': None, 'IpcMode': 'private', 'Cgroup': '', 'Links': None, 'OomScoreAdj': 0, 'PidMode': '', 'Privileged': True, 'PublishAllPorts': False, 'ReadonlyRootfs': False, 'SecurityOpt': ['label=disable'], 'UTSMode': '', 'UsernsMode': '', 'ShmSize': 67108864, 'Sysctls': {'net.ipv4.conf.all.rp_filter': '0', 'net.ipv4.conf.default.rp_filter': '0', 'net.ipv4.ip_forward': '1'}, 'Runtime': 'runc', 'ConsoleSize': [0, 0], 'Isolation': '', 'CpuShares': 0, 'Memory': 0, 'NanoCpus': 0, 'CgroupParent': '', 'BlkioWeight': 0, 'BlkioWeightDevice': None, 'BlkioDeviceReadBps': None, 'BlkioDeviceWriteBps': None, 'BlkioDeviceReadIOps': None, 'BlkioDeviceWriteIOps': None, 'CpuPeriod': 0, 'CpuQuota': 0, 'CpuRealtimePeriod': 0, 'CpuRealtimeRuntime': 0, 'CpusetCpus': '', 'CpusetMems': '', 'Devices': None, 'DeviceCgroupRules': None, 'DeviceRequests': None, 'KernelMemory': 0, 'KernelMemoryTCP': 0, 'MemoryReservation': 0, 'MemorySwap': 0, 'MemorySwappiness': None, 'OomKillDisable': False, 'PidsLimit': None, 'Ulimits': None, 'CpuCount': 0, 'CpuPercent': 0, 'IOMaximumIOps': 0, 'IOMaximumBandwidth': 0, 'MaskedPaths': None, 'ReadonlyPaths': None}
        GraphDriver
        Mounts
        Config:Dict
            {'Hostname': 'c1428b060d3b', 'Domainname': '', 'User': '', 'AttachStdin': False, 'AttachStdout': False, 'AttachStderr': False, 'Tty': False, 'OpenStdin': False, 'StdinOnce': False, 'Env': ['PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin'], 'Cmd': ['/start.sh'], 'Image': 'output_rnode_3_r1', 'Volumes': None, 'WorkingDir': '', 'Entrypoint': None, 'OnBuild': None, 'Labels': {'com.docker.compose.config-hash': '0e9bdf025c7d402e73f7cc5897d88461c6f771442b1d8aec1e5bbeda26e1a86e', 'com.docker.compose.container-number': '1', 'com.docker.compose.oneoff': 'False', 'com.docker.compose.project': 'output', 'com.docker.compose.project.config_files': 'docker-compose.yml', 'com.docker.compose.project.working_dir': '/home/seed/seed-emulator/examples/A20-nano-internet/output', 'com.docker.compose.service': 'rnode_3_r1', 'com.docker.compose.version': '1.27.4', 'org.seedsecuritylabs.seedemu.meta.asn': '3', 'org.seedsecuritylabs.seedemu.meta.net.0.address': '10.3.0.254/24', 'org.seedsecuritylabs.seedemu.meta.net.0.name': 'net0', 'org.seedsecuritylabs.seedemu.meta.net.1.address': '10.100.0.3/24', 'org.seedsecuritylabs.seedemu.meta.net.1.name': 'ix100', 'org.seedsecuritylabs.seedemu.meta.nodename': 'r1', 'org.seedsecuritylabs.seedemu.meta.role': 'Router'}}
        NetworkSettings
            {'Bridge': '', 'SandboxID': '21d98c8f2f1b4c07c2ee77d2673aa69c8bb219a783e3fc93387c2dd454e4c49a', 'HairpinMode': False, 'LinkLocalIPv6Address': '', 'LinkLocalIPv6PrefixLen': 0, 'Ports': {}, 'SandboxKey': '/var/run/docker/netns/21d98c8f2f1b', 'SecondaryIPAddresses': None, 'SecondaryIPv6Addresses': None, 'EndpointID': '', 'Gateway': '', 'GlobalIPv6Address': '', 'GlobalIPv6PrefixLen': 0, 'IPAddress': '', 'IPPrefixLen': 0, 'IPv6Gateway': '', 'MacAddress': '', 'Networks': {'output_net_3_net0': {'IPAMConfig': {'IPv4Address': '10.3.0.254'}, 'Links': None, 'Aliases': ['rnode_3_r1', 'c1428b060d3b'], 'NetworkID': '20f3fbcf8721058455f42e4d89ccdba25d0ccf451f8289d85ec7b15c860846fa', 'EndpointID': 'efa8ac5e602ffe7643c5e1cce5225a15733a74b9cceedb746b5aefafe1f92470', 'Gateway': '10.3.0.1', 'IPAddress': '10.3.0.254', 'IPPrefixLen': 24, 'IPv6Gateway': '', 'GlobalIPv6Address': '', 'GlobalIPv6PrefixLen': 0, 'MacAddress': '02:42:0a:03:00:fe', 'DriverOpts': None}, 'output_net_ix_ix100': {'IPAMConfig': {'IPv4Address': '10.100.0.3'}, 'Links': None, 'Aliases': ['rnode_3_r1', 'c1428b060d3b'], 'NetworkID': 'e3844f2eaaa04bf8d8264f6625983c1a86cfc4ce1c23f541110ded17505f3537', 'EndpointID': '87430634d4194c7af825188e16d027e08e8e8bae2c674892e0b63ed7e1b40254', 'Gateway': '10.100.0.1', 'IPAddress': '10.100.0.3', 'IPPrefixLen': 24, 'IPv6Gateway': '', 'GlobalIPv6Address': '', 'GlobalIPv6PrefixLen': 0, 'MacAddress': '02:42:0a:64:00:03', 'DriverOpts': None}}}


    </div>
    </details>
* exec_run() : execute command in the container
    * `docker exec`
* get_archive() : retrieve a file or folder from the container in the form of a tar archive
* put_archive() : insert a file or folder in the container using a tar archive as source
* start() : start the container
    * `docker start`
* stop() : stop the container
    * `docker stop`
    
### Networks Class
* create() : create a network
    * `docker network create`
* get() : get a network by its ID
* list() : list networks 
    * `docker network ls`
* prune() : delete unused networks
    * `docker networks prune`

### Network Class
* connect() : connect a container to this network
* disconnect() : disconnect a container from this network

## DockerController Class
### Function List

- [ ] support docker demon connection from remote
- [x] get containers
    - [getContainerById](#getcontainerbyid--get-container-by-id)
    - [getContainersByClass](#getcontainersbyclass--get-container-list-by-classname)
- [x] get network information; get 'ip addr' result from the container
    - [getNetworkInfo()](#getnetworkinfo--get-ip-addr-result-from-the-container)
- [ ] other useful Info : Think about it
- [x] execute command inside the container and retrieve the result
    - [execContainer()](#execcontainer-execcontainers--execute-command-inside-the-container-and-retrieve-the-result)
    - [execContainers()](#execcontainer-execcontainers--execute-command-inside-the-container-and-retrieve-the-result)
- [ ] install software dynamically inside a container
- [ ] set file to a container
- [x] get file from a container
    - [readFile()](#readfile--get-file-from-a-container)
- [x] add new nodes
    - [addNodes()](#addnodes--dynamically-add-new-nodes)
- [ ] add new networks
- [ ] delete nodes
- [ ] start/stop nodes

#### `getContainerById()` : get container by Id
```python
# Get container by container name
container = controller.getContainerById("as151r-router0-10.151.0.254")
```

#### `getContainersByClass()` : get container list by classname
```python
# Get containers by classname 
# returns container list with classname
# classname is assigned using Label:org.seedsecuritylabs.seedemu.meta.class
webContainers = controller.getContainersByClassName("WebService")
```

#### `getNetworkInfo()` : get 'ip addr' result from the container
```python
# Get networkInfo
# get result of 'ip addr' inside the container 
networkInfo = controller.getNetworkInfo(container)
print("networkInfo: \n", networkInfo)
```

#### `execContainer()`, `execContainers()` : execute command inside the container and retrieve the result
```python
# Execute command on containers
# returns a result
ls_result = controller.execContainers(webContainers, 'id')
print("ls_result: \n",ls_result)
```

#### `readFile()` : get file from a container
```python
# Read file from container
# It just print a file yet.
controller.readFile(webContainers[0], fileName='/seedemu_worker')
```
#### `addNodes()` : dynamically add new nodes
```python
####################################################################
# Add new node
# create a new node to a existing base-componenet.
emu = Emulator()

emu.load('./base-component.bin')

base:Base = emu.getLayer('Base')
as151 = base.getAutonomousSystem(151)
as151.createHost('dynamic-node').joinNetwork('net0', address='10.151.0.99')

# Run a new container based on the added node info. 
controller.addNode(emu, scope='151', name='dynamic-node', type='hnode')
```