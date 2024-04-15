#!/bin/bash

source ./tests/lib_test.sh

sudo ip link add odsmirrori type veth peer name odsmirroro
sudo ip link set dev odsmirrori up || exit 1
sudo ip link set dev odsmirroro up || exit 1

init_dirs
conf_faucet
conf_gauge
conf_keys

echo starting dovesnap infrastructure
docker compose build || exit 1
init_ovs

FAUCET_PREFIX=$TMPDIR MIRROR_BRIDGE_OUT=odsmirrori docker compose -f docker-compose.yml -f docker-compose-standalone.yml up -d || exit 1
wait_faucet

docker ps -a
echo creating testnet
docker network create testnet -d dovesnap --internal -o ovs.bridge.mode=nat -o ovs.bridge.dpid=0x1 -o ovs.bridge.controller=tcp:127.0.0.1:6653,tcp:127.0.0.1:6654 -o ovs.bridge.preallocate_ports=10 || exit 1
docker network ls
restart_wait_dovesnap
echo creating testcon
# github test runner can't use ping.
docker pull busybox
docker run -d --label="dovesnap.faucet.portacl=ratelimitit" --label="dovesnap.faucet.mirror=testnet:true" --mac-address=0e:99:00:00:00:07 --net=testnet --rm --name=testcon busybox sleep 1h
RET=$?
if [ "$RET" != "0" ] ; then
	echo testcon container creation returned: $RET
	exit 1
fi
wait_acl
wait_mirror 1
wait_testcon
timeout 30s sudo tcpdump -n -c 1 -U -i odsmirroro -w $MIRROR_PCAP tcp &
sleep 3
wait_verify_internet
docker exec -t testcon ifconfig eth0 |grep -iq 0e:99:00:00:00:07 || exit 1
PCAPMATCH=TCP
wait_for_pcap_match
clean_dirs
