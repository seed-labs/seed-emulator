# v1.1.5

- c65sdn 1.0.44
- frpc 0.22.55
- OVS 3.0.2
- pip/certifi
- grafana, prometheus, pytype

# v1.1.4

- c65sdn 1.0.43
- grpc 1.5.1
- OVS 3.0.1
- frpc 0.22.44
- docker 6.0.1
- grafana, prometheus, pytype

# v1.1.3

- Prometheus 2.29.0
- Grafana 9.1.7
- c65sdn 1.0.39
- frpc 0.22.42
 
# v1.1.2

- OVS 3.0.0
- golang 1.19
- grpc 1.4.9
- c65sdn 1.0.37
- logrus, grafana

# v1.1.1

- workarounds for missing OVS config/local port status.

# v1.1.0

- Updated faucetconfrpc, prometheus, grafana, faucet, gauge, openvswitch, and grpc
- Moved package to use pyproject.toml

# v1.0.10

- faucetconfrpc 0.22.35

# v1.0.9

- OVS 2.17.1
- c65sdn/faucet to 1.0.35
- golang 1.18
- libyaml 3.0
- grpc 1.46.2
- faucetconfrpc 0.22.34
- pylint, pytype, grafana, prometheus

# v1.0.8

- Update c65faucet to 1.0.29
- Update grpc to v1.45.0
- Update OVS to 2.17.0
- Update faucetconfrpc to 0.22.33
- Update prometheus, pytype, grafana

# v1.0.7

- Update c65faucet to 1.0.28
- Update containerd, image-spec (https://cve.mitre.org/cgi-bin/cvename.cgi?name=CVE-2022-23648)
- Update prometheus, pytype, grafana

# v1.0.6

- Update c65faucet to 1.0.27
- Update faucetconfrpc to 0.22.32
- Update ruamel.yaml to v0.17.21
- Update prometheus, pytype, grafana

# v1.0.5

- Update c65faucet to 1.0.23
- Update faucetconfrpc to 0.22.30
- Update containerd to 1.5.9
- Update OVS to 2.16.2
- Update grpc to 1.43.0
- Update docker to 2.3.2
- Update pylint, pytype, grafana

# v1.0.3

- Update to debian bullseye
- Update pytype, prometheus, grafana, faucet, gauge, faucetconfrpc

# v1.0.2

- Upgrade docker, ruamel.yaml, prometheus

# v1.0.1

- Fix packaging.

# v1.0.0

- Driver name has changed from ovs to dovesnap
- Add cleanup_dovesnap script
- Update faucet, gauge, grafana, pytype, pylint, faucetconfrpc, ovs

# v0.22.6

- Make Join() and CreateEndpoint() non blocking again, but retain the head start on OFPort provisioning in CreateEn
dpoint.

# v0.22.5 (2021-08-16)

- allocate OVS ports when endpoint is created, before container Join.
- allow preallocation of N FAUCET ports.
- trigger state reconcilation on webserver request for status
- upgrade pytype, prometheus, grpc

# v0.22.4 (2021-08-11)

- immediately allocate OVS port at container Join (faster networking setup)
- upgrade faucet, gauge, pytype, docker, grafana, grpc

# v0.22.3 (2021-07-28)

- reduce size of OVS and dovesnap containers (builders)
- upgrade to golang 1.16
- min TLS 1.3 version for faucetconfrpc
- pin more python dependencies (including graphviz, docker)

# v0.22.2 (2021-07-21)

- upgrade faucet, grafana, pytype
- docker as a systemd service

# v0.22.1 (2021-07-14)

- Use waitgroups to synchronize create/delete operations, including on exit.
- OVS 2.15.1
- Update faucet, gauge, pylint, grpc, grafana, docker, prometheus, faucetconfrpc

# v0.22.0 (2021-06-22)

- dovesnap plugin no longer needs privileged: true
- update prometheus, grafana, pytype.

# v0.21.0 (2021-06-17)

- restart/shutdown handling improvements, and network deletes now blocking to avoid leaked veths or other resources.
- Update pytype, docker, faucetconfrpc, prometheus, grafana, baseconv

# v0.20.0 (2021-05-04)

- Use c65sdn faucet/gauge docker images
- Upgrade pytype, docker, faucetconfrpc, prometheus, grafana
- Add routed mode

# v0.19.0 (2021-03-05)

- Use c65sdn faucet/gauge docker images
- Upgrade pytype, docker, faucetconfrpc

# v0.18.0 (2021-02-26)

- Fix mirror bridge may not be initialized correctly due to port number assignment
- Add network name specific mirror and ACL options
- Fix deadlock between Dovesnap and Docker when creating a lot of containers
- Delete all flows when creating a bridge to disable default switching
- Log all CLI arguments for debugging
- Upgrade OVS to 2.14.2
- Upgrade docker, grafana, grpc, logrus, prometheus, pytype

# v0.17.0 (2021-02-09)

- Dovesnap populates status server with DHCP addresses for containers
- graph script can generate a global view across multiple dovesnaps
- Upgrade docker, pytype

# v0.16.0 (2021-02-02)

- retry failed dump-ports-desc calls
- add VLAN output ACL
- upgrade OVS 2.14.1
- upgrade faucetconfrpc, certstrap

# v0.15.0 (2021-01-21)

- Add ovs.bridge.add_copro_ports
- Upgrade faucetconfrpc, certstrap, prometheus, grafana, grpc

# v0.14.0 (2021-01-14)

- Handle empty FAUCET config at startup
- Handle cold start of host with existing docker networks
- Handle ovs-ofctl returning an error temporarily, reconciling networks
- Upgrade prometheus, grpc, faucet, gauge, faucetconfrpc, certstrap, grafana

# v0.13.0 (2020-11-25)

- Updated grafana, faucetconfrpc, faucet-certstrap
- Fix stack test, for faucet

# v0.12.0 (2020-11-19)

- Updated prometheus, grafana, faucet, gauge, faucet-certstrap, faucetconfrpc
- Restructured tests

# v0.11.0 (2020-10-30)

- VLAN documentation
- Update faucet, gauge, certstrap, faucetconfrpc

# v0.10.0 (2020-10-22)

- Fix MANIFEST.in to include main.go
- Allow configuration of faucetconfrpc client key
- Upgrade grpc, grafana

# v0.9.0 (2020-10-21)

- Move non-error OVS debug to trace level
- Add support for setting container/NAT interface MAC prefixes.

# v0.8.0 (2020-10-09)

- add JSON endpoint to get dovesnap state
- log MAC address of containers
- Update faucet, faucetconfrpc, certstrap, grafana, grpc

# v0.7.0 (2020-09-30)

- allow ACL on NAT port
- tests check mirror flows are present
- mirror bridge should pass through packets with any VLAN tag
- fix viz crash when no ip command
- upgrade logrus, faucetconfrpc, grafana

# v0.6.0 (2020-09-22)

- fix race condition that could lead to multiple containers with same OFPort
- add NAT port mapping (-p) support via network gateway IP
- Remove OVS privilege when in userspace mode
- Move to go mod from dep ensure
- Viz script timeout/missing IP fixes
- update faucetconfrpc, OVS

# v0.5.0 (2020-09-04)

- update faucetconfrpc, certstrap
- graph_dovesnap vizualization script
- support OVS userspace mode

# v0.4.0 (2020-08-27)

- add/remove non-dovesnap managed ports to bridges to FAUCET
- ARM compatibility
- Updated grafana, faucetconfrpc

# v0.3.0 (2020-08-21)

- Add option for using DHCP
- Ability to restart dovesnap and have it recovering existing networks
- Updated grafana, faucet and gauge

# v0.2.0 (2020-08-14)

- Implement mirroring, stacking, FAUCET configuration via RPC.

# v0.1.1 (2020-05-21)

- Initial release (fork from https://github.com/gopher-net/docker-ovs-plugin).
- Can create both NAT and flat networks and can add existing ports to a bridge/network
- Does not yet support fixed OFPort allocations for containers.
