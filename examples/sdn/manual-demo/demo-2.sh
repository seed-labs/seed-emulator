sudo ovs-vsctl add-br br-A
sudo ifconfig br-A 10.9.1.254 netmask 255.255.255.0 up
sudo ovs-docker add-port br-A eth0 host-a1 --ipaddress=10.9.1.1/24 --gateway=10.9.1.254 
sudo ovs-docker add-port br-A eth0 host-a2 --ipaddress=10.9.1.2/24 --gateway=10.9.1.254
# sudo ovs-vsctl add-port br-A p-ab
# sudo ovs-vsctl add-port br-A p-ac

sudo ovs-vsctl add-br br-B
sudo ifconfig br-B 10.9.2.254 netmask 255.255.255.0 up
sudo ovs-docker add-port br-B eth0 host-b1 --ipaddress=10.9.2.1/24 --gateway=10.9.2.254
sudo ovs-docker add-port br-B eth0 host-b2 --ipaddress=10.9.2.2/24 --gateway=10.9.2.254
# sudo ovs-vsctl add-port br-B p-bc 
# sudo ovs-vsctl add-port br-B p-ba

sudo ovs-vsctl add-br br-C
sudo ifconfig br-C 10.9.3.254 netmask 255.255.255.0 up
sudo ovs-docker add-port br-C eth0 host-c1 --ipaddress=10.9.3.1/24 --gateway=10.9.3.254
sudo ovs-docker add-port br-C eth0 host-c2 --ipaddress=10.9.3.2/24 --gateway=10.9.3.254
sudo ovs-vsctl show
# sudo ovs-vsctl add-port br-C p-ca 
# sudo ovs-vsctl add-port br-C p-cb

# sudo ovs-vsctl set interface p-ab type=patch options:peer=p-ba
# sudo ovs-vsctl set interface p-ba type=patch options:peer=p-ab
# sudo ovs-vsctl set interface p-ac type=patch options:peer=p-ca
# sudo ovs-vsctl set interface p-ca type=patch options:peer=p-ac
# sudo ovs-vsctl set interface p-bc type=patch options:peer=p-cb
# sudo ovs-vsctl set interface p-cb type=patch options:peer=p-bc


sudo ovs-vsctl add-port br-A p-ac

sudo ovs-vsctl add-port brA 


sudo ovs-ofctl dump-flows br-A

sudo ovs-vsctl set-fail-mode br-B secure

sudo ovs-testcontroller ptcp:6653:127.0.0.1
sudo ovs-vsctl set-controller br-B tcp:127.0.0.1:6653

