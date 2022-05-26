# Docker Controller
This example demonstrates the uses of DockerController class. DockerController class is the library for Runtime Interaction with the SEED Emulator. In this class, docker python sdk is used. The detailed manual of docker python sdk can be found in here: https://docker-py.readthedocs.io/en/stable/index.html

## Docker sdk summary
* Client
    * from_env() : 
    * DockerClient() : 
* Containers
    * 
    * 
    
* Container
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
* Networks
* Network

## DockerController Class

### Function List
- [x] works
- [x] works too
