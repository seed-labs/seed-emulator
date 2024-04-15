sudo ovs-vsctl add-br br1 \
-- set bridge br1 other-config:datapath-id=0000000000000001 \
-- set bridge br1 other-config:disable-in-band=true \
-- set bridge br1 fail_mode=secure \
-- set-controller br1 tcp:127.0.0.1:6653

sudo ovs-docker add-port br1 eth0 host-a1 --ipaddress=10.9.1.1/24 --gateway=10.9.1.254 
sudo ovs-docker add-port br1 eth0 host-a2 --ipaddress=10.9.2.1/24 --gateway=10.9.2.254