sudo ovs-vsctl show
sudo ovs-vsctl add-br brA
sudo ifconfig brA 10.9.1.0 netmask 255.255.255.0 up
sudo ovs-docker add-port brA eth0 host-a1 --ipaddress=10.9.1.1/24
sudo ovs-docker add-port brA eth0 host-a2 --ipaddress=10.9.1.2/24
sudo ovs-ofctl dump-flows brA

sudo ovs-vsctl set-fail-mode brB secure

sudo ovs-testcontroller ptcp:6653:127.0.0.1
sudo ovs-vsctl set-controller brB tcp:127.0.0.1:6653

