#!/bin/bash

source ./tests/lib_test.sh

init_dirs
conf_gauge
conf_keys

sudo rm -f $FAUCET_CONFIG
cat >$FAUCET_CONFIG <<EOFC || exit 1
meters:
  lossymeter:
    meter_id: 1
    entry:
        flags: "KBPS"
        bands: [{type: "DROP", rate: 100}]
acls:
  ratelimitit:
  - rule:
      actions:
        meter: lossymeter
        allow: 1
  allowall:
  - rule:
      actions:
        allow: 1
  denyall:
  - rule:
      actions:
        allow: 0
dps:
  odsrootsw:
    dp_id: 0x77
    hardware: Open vSwitch
    interfaces:
        1:
           native_vlan: 100
        88:
           output_only: true
  testnet:
    dp_id: 0x1
    hardware: Open vSwitch
    interfaces:
        0xfffffffe:
            native_vlan: 100
            opstatus_reconf: false
            # TODO: workaround for FAUCET bug handling change of pipeline upon ACL change with stacking.
            acls_in: [allowall]
    interface_ranges:
        2-10:
            native_vlan: 100
            acls_in: [denyall]
EOFC

docker compose build || exit 1
init_ovs

sudo ip link add odsrootswintp1 type veth peer name odsrootswextp1
sudo ip link set dev odsrootswintp1 up || exit 1
sudo ip link set dev odsrootswextp1 up || exit 1

docker exec -t $OVSID ovs-vsctl add-br odsrootsw || exit 1
docker exec -t $OVSID ovs-vsctl set-fail-mode odsrootsw secure
docker exec -t $OVSID ovs-vsctl set bridge odsrootsw other-config:datapath-id=0x77
docker exec -t $OVSID ovs-vsctl set-controller odsrootsw tcp:127.0.0.1:6653 tcp:127.0.0.1:6654
docker exec -t $OVSID ovs-vsctl add-port odsrootsw odsrootswintp1 -- set interface odsrootswintp1 ofport_request=7
docker exec -t $OVSID ovs-vsctl show

echo starting dovesnap infrastructure
FAUCET_PREFIX=$TMPDIR STACK_PRIORITY1=odsrootsw STACKING_INTERFACES=odsrootsw:7:odsrootswextp1 STACK_MIRROR_INTERFACE=odsrootsw:88 STACK_OFCONTROLLERS=tcp:127.0.0.1:6653,tcp:127.0.0.1:6654 docker compose -f docker-compose.yml -f docker-compose-standalone.yml up -d || exit 1
wait_faucet

docker ps -a
echo creating testnet
docker network create testnet -d dovesnap --internal -o ovs.bridge.mode=nat -o ovs.bridge.dpid=0x1 -o ovs.bridge.lbport=99 -o ovs.bridge.preallocate_ports=10 || exit 1
docker network ls
restart_wait_dovesnap
echo creating testcon
# github test runner can't use ping.
docker pull busybox
# TODO: wait for stack to come up before adding a tunnel. FAUCET can miss the mirror via tunnel request if it is made before the stack comes up.
wait_stack_state 3 4
docker run -d --label="dovesnap.faucet.portacl=ratelimitit" --label="dovesnap.faucet.mirror=true" --net=testnet --rm --name=testcon busybox sleep 1h
RET=$?
if [ "$RET" != "0" ] ; then
	echo testcon container creation returned: $RET
	exit 1
fi
wait_acl
wait_testcon
# mirror flow will be in table 1, because ACLs are applied.
wait_mirror 1
wait_stack_state 3 4
wait_push_vlan 0 99
wait_verify_internet
OVSID="$(docker ps -q --filter name=ovs)"
echo showing packets tunnelled: tunnel 356 is vlan 100 plus default offset 256
PACKETS=$(docker exec -t $OVSID ovs-ofctl dump-flows odsrootsw table=0,dl_vlan=356|grep -v n_packets=0)
echo $PACKETS
if [ "$PACKETS" == "" ] ; then
        echo no packets were tunnelled
        docker exec -t $OVSID ovs-ofctl dump-flows odsrootsw
        docker exec -t $OVSID ovs-ofctl dump-flows $BRIDGE
        exit 1
fi

clean_dirs
