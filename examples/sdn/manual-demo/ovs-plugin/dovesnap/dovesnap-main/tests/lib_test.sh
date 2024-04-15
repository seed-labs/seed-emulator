#!/bin/bash

reset_ovsid ()
{
        OVSID="$(docker ps -q --filter name=ovs)"
}

reset_bridgename ()
{
        BRIDGE=""
        while [ "$BRIDGE" == "" ] ; do
                echo refreshing bridge name
                BRIDGE=$(wget -q -O- http://0.0.0.0:9401/networks|jq -r '.[] | select(."NetworkName" == "testnet").BridgeName')
                sleep 1
        done
}

restart_container ()
{
        containerid=$1
        echo restarting $containerid
        CID=$(docker ps -q --filter name=$containerid)
        docker logs $CID
        docker restart $CID
        docker logs $CID
}

restart_dovesnap ()
{
        restart_container dovesnap-plugin
}

restart_ovs ()
{
        restart_container ovs
}

restart_wait_dovesnap ()
{
        echo waiting for FAUCET config to have testnet mirror port
        TESTNETCOUNT=0
        while [ "$TESTNETCOUNT" != "1" ] ; do
                TESTNETCOUNT=$(sudo grep -c 99: $FAUCET_CONFIG)
                sleep 1
        done
        restart_dovesnap
}

init_dirs()
{
        export TMPDIR=$(mktemp -d)
        export FAUCET_CONFIG=$TMPDIR/etc/faucet/faucet.yaml
        export GAUGE_CONFIG=$TMPDIR/etc/faucet/gauge.yaml
        if [ ! -d "$TMPDIR" ] ; then
                exit 1
        fi
        mkdir -p $TMPDIR/etc/faucet
        MIRROR_PCAP=$TMPDIR/mirror.cap
        sed -i -E 's/version = "([0-9\.]+)"/version = "\1.dev"/g' main.go || exit 1
        cd release && ./update_docker_compose.py && cd .. || exit 1
}

clean_dirs()
{
        wget -q -O- localhost:9401/networks || exit 1
        py=$(which python3)
        echo using: $py
        sudo "${py}" ./src/dovesnap/graph_dovesnap.py -o /tmp/dovesnapviz || exit 1
        ./src/dovesnap/cleanup_dovesnap
        rm -rf $TMPDIR
        VETHS="$(ip link | grep -E ':( ovs-veth|ovp)')"
        if [ "$VETHS" != "" ] ; then
                echo veths leaked: $VETHS
                exit 1
        fi
        DIEC=$(docker system events --since=15m --until=0m --filter="container=dovesnap-plugin-1" --filter="event=die" | grep -v exitCode=0)
        if [ "$DIEC" != "" ] ; then
               echo dovesnap exited unexpectedly: $DIEC
               exit 1
        fi
}

conf_faucet()
{
        echo configuring faucet
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
  testnet:
    dp_id: 0x1
    hardware: Open vSwitch
    interfaces:
        0xfffffffe:
            native_vlan: 100
            opstatus_reconf: false
EOFC
}

conf_gauge()
{
        echo configuring gauge
cat >$GAUGE_CONFIG <<EOGC || exit 1
faucet_configs:
    - '/etc/faucet/faucet.yaml'
watchers:
    port_status_poller:
        type: 'port_state'
        all_dps: True
        db: 'prometheus'
    port_stats_poller:
        type: 'port_stats'
        all_dps: True
        interval: 30
        db: 'prometheus'
dbs:
    prometheus:
        type: 'prometheus'
        prometheus_addr: '0.0.0.0'
        prometheus_port: 9303
EOGC
}

conf_keys ()
{
        echo creating keys
        mkdir -p /opt/faucetconfrpc || exit 1
        FAUCET_PREFIX=$TMPDIR docker compose -f docker-compose.yml -f docker-compose-standalone.yml up faucet_certstrap || exit 1
        ls -al /opt/faucetconfrpc/faucetconfrpc.key || exit 1
}

wait_faucet ()
{
        for p in 6653 6654 9302 59999 ; do
                PORTCOUNT=""
                while [ "$PORTCOUNT" = "0" ] ; do
                        echo waiting for $p
                        PORTCOUNT=$(ss -tHl sport = :$p|grep -c $p)
                        sleep 1
                done
        done
        echo waiting for frpc
        OUTPUT=""
        while [ "$OUTPUT" == "" ] ; do
                OUTPUT=$(docker ps -q --filter health=healthy --filter name=faucetconfrpc)
                sleep 1
        done
}

wait_acl ()
{
        echo waiting for ACL to be applied
        DOVESNAPID="$(docker ps -q --filter name=dovesnap-plugin)"
        ACLCOUNT=0
        while [ "$ACLCOUNT" != "2" ] ; do
                docker logs $DOVESNAPID
                sudo cat $FAUCET_CONFIG
                ACLCOUNT=$(sudo grep -c ratelimitit $FAUCET_CONFIG)
                sleep 1
        done
        reset_ovsid
        reset_bridgename
        OUTPUT=""
        while [ "$OUTPUT" != "meter" ] ; do
                OUTPUT=$(docker exec -t $OVSID ovs-ofctl dump-flows -OOpenFlow13 $BRIDGE table=0|grep -o meter|cat)
                echo -n waiting for meter flow in table 0:
                docker exec -t $OVSID ovs-ofctl dump-flows -OOpenFlow13 $BRIDGE table=0
                sleep 1
        done
}


wait_testcon ()
{
	DOVESNAPID="$(docker ps -q --filter name=dovesnap-plugin)"
	OUTPUT=""
	while [ "$OUTPUT" == "" ] ; do
		OUTPUT=$(sudo grep "description: /testcon" $FAUCET_CONFIG)
		echo waiting for /testcon in $FAUCET_CONFIG
		sleep 1
		docker logs $DOVESNAPID
	done
}


wait_verify_internet ()
{
	gwip=$(docker exec -t testcon ip route |grep default|grep -Eo "[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+")
	echo testcon gateway: $gwip
	dockerip=$(ip address show docker0 |grep -Eo "inet [0-9]+\.[0-9]+\.[0-9]+\.[0-9]+"|sed "s/inet //g")
	echo docker0 gateway: $dockerip
	docker exec -t testcon ping -c3 $gwip
	docker exec -t testcon ping -c3 $dockerip
	docker network inspect testnet
	sudo iptables -t nat -L
	testurl=http://azure.archive.ubuntu.com/ubuntu
	docker exec -t testcon wget -O/dev/null $testurl || exit 1
}


wait_stack_state ()
{
        state=$1
        count=$2
        FIP=$(docker inspect -f '{{range.NetworkSettings.Networks}}{{.IPAddress}}{{end}}' dovesnap-faucet-1)
        STACKUPCOUNT=0
        echo waiting for $count stack ports to be state $state
        while [ "$STACKUPCOUNT" != "$count" ] ; do
                STACKUPCOUNT=$(wget -q -O- $FIP:9302|grep -Ec "^port_stack_state.+$state.0$")
                sleep 1
        done
        sleep 5
}

wait_push_vlan ()
{
        table=$1
        inport=$2
        reset_ovsid
        reset_bridgename
        OUTPUT=""
        while [ "$OUTPUT" != "push_vlan:" ] ; do
                OUTPUT=$(docker exec -t $OVSID ovs-ofctl dump-flows -OOpenFlow13 $BRIDGE in_port=$inport,table=$table|grep -o push_vlan:|cat)
                docker exec -t $OVSID ovs-ofctl dump-flows -OOpenFlow13 $BRIDGE table=$table
                echo waiting for push vlan rule for port $inport in table $table
                sleep 1
        done
}

wait_mirror ()
{
        table=$1
        if [ "$table" == "" ] ; then
                table=0
        fi
        echo waiting for mirror to be applied to config
        DOVESNAPID="$(docker ps -q --filter name=dovesnap-plugin)"
        MIRRORCOUNT=0
        while [ "$MIRRORCOUNT" != "1" ] ; do
                docker logs $DOVESNAPID
                sudo cat $FAUCET_CONFIG
                MIRRORCOUNT=$(sudo grep -c mirror: $FAUCET_CONFIG)
                sleep 1
        done
        reset_bridgename
        OUTPUT=""
        while [ "$OUTPUT" != "output:" ] ; do
                OUTPUT=$(docker exec -t $OVSID ovs-ofctl dump-flows -OOpenFlow13 $BRIDGE table=$table|grep -o output:|cat)
                echo waiting for mirror flow in table $table
                sleep 1
        done
}

init_ovs ()
{
        docker compose -f docker-compose.yml up -d ovs || exit 1
        reset_ovsid
        while ! docker exec -t $OVSID ovs-vsctl show ; do
                echo waiting for OVS
                sleep 1
        done
        docker exec -t $OVSID /bin/sh -c 'for i in `ovs-vsctl list-br` ; do ovs-vsctl del-br $i ; done' || exit 1
}

wait_for_container_ip ()
{
        i=0
        IP=$1
        OUT=""
        while [ "$OUT" == "" ] && [ "$i" != 30 ] ; do
                echo waiting for container IP: $i 
                OUT=$(docker exec -t testcon ifconfig|grep "inet addr:$IP"|cat)
                ((i=i+1))
                sleep 1
        done
        if [ "$OUT" == "" ] ; then
                echo No IP
                DOVESNAPID="$(docker ps -q --filter name=dovesnap-plugin)"
                docker logs $DOVESNAPID
                exit 1
        fi
        echo $OUT
}

wait_for_status_container_ip ()
{
        i=0
        IP=$1
        OUT=""
        STATUS=""
        while [ "$OUT" == "" ] && [ "$i" != 30 ] ; do
                echo waiting for status container IP: $i
                STATUS=$(wget -q -O- localhost:9401/networks|jq -c)
                OUT=$(echo $STATUS|grep HostIP|grep $IP|cat)
                ((i=i+1))
                sleep 1
        done
        if [ "$OUT" == "" ] ; then
                echo No IP
                echo $STATUS
                exit 1
        fi
        echo $OUT
}

wait_for_pcap_match ()
{
        i=0
        OUT=""
        sudo chmod go+rx $TMPDIR
        while [ "$OUT" == "" ] && [ "$i" != 30 ] ; do
                echo waiting for pcap match $PCAPMATCH: $i
                sudo chown root $MIRROR_PCAP
                OUT=$(sudo tcpdump -n -r $MIRROR_PCAP -v | grep $PCAPMATCH)
                ((i=i+1))
                sleep 1
        done
        if [ "$OUT" == "" ] ; then
                echo $PCAPMATCH not found in pcap
                exit 1
        fi
        echo $PCAPMATCH
}
