
apt-get install curl gnupg apt-transport-https lsb-release
mkdir -p /etc/apt/keyrings/
curl -1sLf https://packagecloud.io/faucetsdn/faucet/gpgkey | sudo gpg --dearmor -o /etc/apt/keyrings/faucet.gpg
echo "deb [signed-by=/etc/apt/keyrings/faucet.gpg] https://packagecloud.io/faucetsdn/faucet/$(lsb_release -si | awk '{print tolower($0)}')/ $(lsb_release -sc) main" | sudo tee /etc/apt/sources.list.d/faucet.list
sudo apt-get update
sudo apt-get install faucet-all-in-one
sudo apt-get install openvswitch-switch

systemctl start ovs-vswitchd.service
systemctl start ovsdb-server.service

#preparing br container
apt-get update
apt-get upgrade
apt-get install systemctl
apt-get install openvswitch-switch
systemctl start ovsdb-server.service
systemctl start ovs-vswitchd.service

#preparing controller container
apt-get update
apt-get upgrade
apt-get install systemctl
apt-get install curl gnupg apt-transport-https lsb-release
mkdir -p /etc/apt/keyrings/
curl -1sLf https://packagecloud.io/faucetsdn/faucet/gpgkey | gpg --dearmor -o /etc/apt/keyrings/faucet.gpg
echo "deb [signed-by=/etc/apt/keyrings/faucet.gpg] https://packagecloud.io/faucetsdn/faucet/$(lsb_release -si | awk '{print tolower($0)}')/ $(lsb_release -sc) main" | tee /etc/apt/sources.list.d/faucet.list
apt-get update
apt-get install faucet-all-in-one
systemctl start faucet.service
