#!/usr/bin/env python
# encoding: utf-8
# __author__ = 'Demon'

from seedsim.core import Node, Printable, Simulator, Service, Server
from seedsim.core.enums import NetworkType
from typing import List, Dict, Tuple, Set
import pkgutil

ETHServerFileTemplates: Dict[str, str] = {}

#This config file is used for initialing block
ETHServerFileTemplates['genesis'] = """{
   "nonce":"0x0000000000000042",
   "timestamp":"0x0",
   "parentHash":"0x0000000000000000000000000000000000000000000000000000000000000000",
   "extraData":"0x",
   "gasLimit":"0x80000000",
   "difficulty":"0x0",
   "mixhash":"0x0000000000000000000000000000000000000000000000000000000000000000",
   "coinbase":"0x3333333333333333333333333333333333333333",
   "config": {
    "chainId": 10,
    "homesteadBlock": 0,
    "eip150Block": 0,
    "eip150Hash": "0x0000000000000000000000000000000000000000000000000000000000000000",
    "eip155Block": 0,
    "eip158Block": 0,
    "byzantiumBlock": 0,
    "constantinopleBlock": 0,
    "petersburgBlock": 0,
    "istanbulBlock": 0,
    "ethash": {}
  },
 "alloc":{

   }
}"""

#This downloader is used for downloading enode info from other nodes. Then put them into --bootnodes option.
ETHServerFileTemplates["downloader"] = """
until $(curl --output /dev/null --silent --head --fail http://{node_addr}:8888); do
    echo "node not ready"
    sleep 3
done

FINGERPRINT=$(curl -s {node_addr}:8888/enode.txt)
echo "enode info ready"
echo $FINGERPRINT, >> /tmp/shared_enode

"""


class EthereumServer(Server):
    def __init__(self, serial_number):
        self.__serial_number = serial_number


    def configure(self, node: Node, eth):
        """!
        @brief configure EthServer node, add all of Node IP in Service.

        """
        ifaces = node.getInterfaces()
        assert len(ifaces) > 0, 'EthereumServer configure(): node has not interfaces'
        addr = ifaces[0].getAddress()

        eth.addNodeIp(str(addr))

    def install(self, node: Node, eth):
        """!
        @brief ETH server installation step.

        """
        ifaces = node.getInterfaces()
        assert len(ifaces) > 0, 'EthereumServer#install(): node has not interfaces'
        addr = ifaces[0].getAddress()

        #Get other nodes IP and generate the downloader in each of node, because we need download enode key from other nodes.
        enode_ips = eth.getNodeIps()[:]
        enode_ips.remove(str(addr))

        downloader_commands = ""
        for ip in enode_ips:
            downloader_commands += ETHServerFileTemplates["downloader"].format(node_addr = ip)

        node.appendFile("/tmp/genesis.json", ETHServerFileTemplates['genesis'])
        node.appendFile("/tmp/downloader.sh", downloader_commands)
        node.appendFile("/tmp/password", "admin") # ETH account password file
        node.addSoftware("software-properties-common")
        node.addBuildCommand("add-apt-repository ppa:ethereum/ethereum")

        #Install geth and bootnode
        node.addBuildCommand("apt-get install --yes geth bootnode")
        #Specify the data directory
        datadir_option = "--datadir /tmp/eth{}".format(self.__serial_number)
        #Initial block
        node.appendStartCommand("geth {} init /tmp/genesis.json".format(datadir_option))
        #Create account via pre-defined password
        node.appendStartCommand("geth {} --password /tmp/password account new &".format(datadir_option))
        node.appendStartCommand("sleep 3")
        #Generate enode URL. Used in --bootnodes option.
        node.appendStartCommand("echo \"enode://$(bootnode --nodekey /tmp/eth{}/geth/nodekey -writeaddress)@{}:30303\" > /tmp/enode.txt".format(self.__serial_number, addr))
        #Launch a webserver, provided for other nodes to download its enode info.
        node.appendStartCommand("python3 -m http.server 8888 -d /tmp &")
        #Execute downloader.
        node.appendStartCommand("bash /tmp/downloader.sh")
        node.appendStartCommand("sleep 2")
        #Launch Ethereum process.
        node.appendStartCommand('nohup geth {} --bootnodes "$(cat /tmp/shared_enode)" --identity="NODE_{}" --networkid=10 --verbosity=6 --mine --rpc --rpcport=8549 --rpcaddr 0.0.0.0 &'.format(datadir_option, self.__serial_number))



class EthereumService(Service):
    """!
    @brief The Ethereum network service.
    """

    def __init__(self):
        super().__init__()
        self.__serial = 0
        self.__node_ips = []

    def getName(self):
        return 'EthereumService'

    def addNodeIp(self, addr: str):
        self.__node_ips.append(addr)

    def getNodeIps(self):
        return self.__node_ips

    def _doConfigure(self, node: Node, server: EthereumServer):
        server.configure(node, self)

    def _doInstall(self, node: Node, server: EthereumServer):
        server.install(node, self)

    def _createServer(self) -> Server:
        self.__serial += 1
        return EthereumServer(self.__serial)