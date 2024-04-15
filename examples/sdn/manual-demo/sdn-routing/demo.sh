sudo ovs-vsctl add-br br1 \
-- set bridge br1 other-config:datapath-id=0000000000000001 \
-- set bridge br1 other-config:disable-in-band=true \
-- set bridge br1 fail_mode=secure \
-- set-controller br1 tcp:127.0.0.1:6653

# sudo ifconfig br1 10.9.1.254 netmask 255.255.255.0 up
sudo ovs-docker add-port br1 eth0 host-a1 --ipaddress=10.9.1.1/24 --gateway=10.9.1.254 
sudo ovs-docker add-port br1 eth0 host-a2 --ipaddress=10.9.1.2/24 --gateway=10.9.1.254

sudo ovs-vsctl add-br br2 \
-- set bridge br2 other-config:datapath-id=0000000000000002 \
-- set bridge br2 other-config:disable-in-band=true \
-- set bridge br2 fail_mode=secure \
-- set-controller br2 tcp:127.0.0.1:6653

# sudo ifconfig br2 10.9.2.254 netmask 255.255.255.0 up
sudo ovs-docker add-port br2 eth0 host-b1 --ipaddress=10.9.2.1/24 --gateway=10.9.2.254
sudo ovs-docker add-port br2 eth0 host-b2 --ipaddress=10.9.2.2/24 --gateway=10.9.2.254

sudo ovs-vsctl add-br br3 \
-- set bridge br3 other-config:datapath-id=0000000000000003 \
-- set bridge br3 other-config:disable-in-band=true \
-- set bridge br3 fail_mode=secure \
-- set-controller br3 tcp:127.0.0.1:6653

# sudo ifconfig br3 10.9.3.254 netmask 255.255.255.0 up
sudo ovs-docker add-port br3 eth0 host-c1 --ipaddress=10.9.3.1/24 --gateway=10.9.3.254
sudo ovs-docker add-port br3 eth0 host-c2 --ipaddress=10.9.3.2/24 --gateway=10.9.3.254