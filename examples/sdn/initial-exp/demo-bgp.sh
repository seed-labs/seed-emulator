sudo ovs-vsctl del-br br1
sudo ip link del veth-faucet
# sudo ip link del veth-faucet-ovs

sudo ovs-vsctl add-br br1 \
-- set bridge br1 other-config:datapath-id=0000000000000001 \
-- set bridge br1 other-config:disable-in-band=true \
-- set bridge br1 fail_mode=secure \
-- set-controller br1 tcp:127.0.0.1:6653

sudo ovs-docker add-port br1 eth0 host-a1 --ipaddress=10.150.1.1/24 --gateway=10.150.1.252 
sudo ovs-docker add-port br1 eth0 host-a2 --ipaddress=10.150.1.2/24 --gateway=10.150.1.252
sudo ovs-docker add-port br1 eth0 host-b1 --ipaddress=10.150.2.1/24 --gateway=10.150.2.252
sudo ovs-docker add-port br1 eth0 host-b2 --ipaddress=10.150.2.2/24 --gateway=10.150.2.252
#sudo ovs-docker add-port br1 sdn0 host-c1 --ipaddress=10.150.3.1/24 --gateway=10.150.3.254
#sudo ovs-docker add-port br1 sdn0 host-c2 --ipaddress=10.150.3.2/24 --gateway=10.150.3.254


sudo ip link add veth-faucet type veth peer name veth-faucet-ovs
sudo ovs-vsctl add-port br1 veth-faucet-ovs
sudo ip addr add 10.150.1.253/24 dev veth-faucet
sudo ip link set veth-faucet up
sudo ip link set veth-faucet-ovs up

sudo ovs-docker add-port br1 sdn0 as150r-router0-10.150.0.254 --ipaddress=10.150.1.254/24

#docker cp ./bird.conf bgp-router:/etc/bird/bird.conf
#chmod +x run-bird.sh
#docker cp ./run-bird.sh bgp-router:/run-bird.sh
# docker exec -d bgp-router /run-bird.sh

sudo cp faucet-bgp.yaml /etc/faucet/faucet.yaml
sudo systemctl restart faucet
