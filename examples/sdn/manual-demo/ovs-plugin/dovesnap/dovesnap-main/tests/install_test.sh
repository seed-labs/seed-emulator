#!/bin/sh

sudo modprobe openvswitch && \
  sudo modprobe 8021q && \
  export DEBIAN_FRONTEND=noninteractive && \
  echo 'debconf debconf/frontend select Noninteractive' | sudo debconf-set-selections && \
  sudo apt-get update && \
  sudo apt-get purge docker docker-engine docker.io containerd runc python3-yaml && \
  sudo apt-get install apt-transport-https ca-certificates curl gnupg-agent software-properties-common && \
  curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo apt-key add - && \
  sudo add-apt-repository "deb [arch=amd64] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" && \
  sudo apt-get update && sudo apt-get install docker-ce docker-ce-cli containerd.io && \
  sudo apt-get install graphviz wget udhcpd jq nftables && sudo nft flush ruleset && sudo apt-get purge nftables && sudo apt-get --reinstall install iptables && \
  sudo update-alternatives --set iptables /usr/sbin/iptables-legacy && \
  sudo /etc/init.d/docker restart && \
  cd openvswitch && docker build -f Dockerfile . -t iqtlabs/openvswitch:v3.2.1 && cd .. && \
  sudo ip link && sudo ip addr
