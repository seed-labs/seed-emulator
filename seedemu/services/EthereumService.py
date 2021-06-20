#!/usr/bin/env python
# encoding: utf-8
# __author__ = 'Demon'

from seedemu.core import Node, Service, Server
from typing import Dict, List

ETHServerFileTemplates: Dict[str, str] = {}

# genesis: the start of the chain
ETHServerFileTemplates['genesis'] = '''{
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
    "alloc":{}
}'''

# bootstraper: get enode urls from other eth nodes.
ETHServerFileTemplates['bootstrapper'] = '''
while read -r node; do {
    let count=0
    ok=true

    until curl -sHf http://$node:8888/eth-enode-url > /dev/null; do {
        echo "eth: node $node not ready, waiting..."
        sleep 3
        let count++
        [ $count -gt 20 ] && echo "eth: node $node failed too many times, skipping."
        ok=false
    }; done

    ($ok) && {
        echo "`curl -s http://$node:8888/eth-enode-url`," >> /tmp/eth-node-urls
    }
}; done < /tmp/eth-nodes
'''

class EthereumServer(Server):
    """!
    @brief The Ethereum Server
    """

    __serial_number: int

    def __init__(self, serial_number: int):
        """!
        @brief create new eth server.

        @param serial_number serial number of this server.
        """
        self.__serial_number = serial_number

    def configure(self, node: Node, eth: 'EthereumService'):
        """!
        @brief configure EthServer node, add all of Node IP in Service.

        @param node node to configure the server on.
        @param eth reference to eth service.
        """
        ifaces = node.getInterfaces()
        assert len(ifaces) > 0, 'EthereumServer configure(): node has not interfaces'
        addr = ifaces[0].getAddress()

        eth.addNodeIp(str(addr))

    def install(self, node: Node, eth: 'EthereumService'):
        """!
        @brief ETH server installation step.

        @param node node object
        @param eth reference to the eth service.
        """
        ifaces = node.getInterfaces()
        assert len(ifaces) > 0, 'EthereumServer#install(): node has not interfaces'
        addr = ifaces[0].getAddress()

        # get other nodes IP for the bootstrapper.
        enode_ips = eth.getNodeIps()[:]
        enode_ips.remove(str(addr))

        node.appendFile('/tmp/eth-genesis.json', ETHServerFileTemplates['genesis'])
        node.appendFile('/tmp/eth-nodes', '\n'.join(enode_ips))
        node.appendFile('/tmp/eth-bootstrapper', ETHServerFileTemplates['bootstrapper'])
        node.appendFile('/tmp/eth-password', 'admin') 

        node.addSoftware('software-properties-common')

        # tap the eth repo
        node.addBuildCommand('add-apt-repository ppa:ethereum/ethereum')

        # install geth and bootnode
        node.addBuildCommand('apt-get install --yes geth bootnode')

        # set the data directory
        datadir_option = "--datadir /root/.ethereum"

        # genesis
        node.appendStartCommand('geth {} init /tmp/eth-genesis.json'.format(datadir_option))

        # create account via pre-defined password
        node.appendStartCommand('geth {} --password /tmp/eth-password account new'.format(datadir_option))

        # generate enode url. other nodes will access this to bootstrap the network.
        node.appendStartCommand('echo "enode://$(bootnode --nodekey /root/.ethereum/geth/nodekey -writeaddress)@{}:30303" > /tmp/eth-enode-url'.format(addr))

        # host the eth-enode-url for other nodes.
        node.appendStartCommand('python3 -m http.server 8888 -d /tmp', True)

        # load enode urls from other nodes
        node.appendStartCommand('chmod +x /tmp/eth-bootstrapper')
        node.appendStartCommand('/tmp/eth-bootstrapper')

        # launch Ethereum process.
        node.appendStartCommand('geth {} --bootnodes "$(cat /tmp/eth-node-urls)" --identity="NODE_{}" --networkid=10 --verbosity=6 --mine --allow-insecure-unlock --rpc --rpcport=8549 --rpcaddr 0.0.0.0'.format(datadir_option, self.__serial_number), True)


class EthereumService(Service):
    """!
    @brief The Ethereum network service.

    """

    __serial: int
    __node_ips: List[str]

    def __init__(self):
        super().__init__()
        self.__serial = 0
        self.__node_ips = []

    def getName(self):
        return 'EthereumService'

    def addNodeIp(self, addr: str):
        """!
        @brief save node's IP.

        Node's IP need to be recorded so we we can let other nodes to bootstrap.
        """
        self.__node_ips.append(addr)

    def getNodeIps(self) -> List[str]:
        """
        @brief get node IPs.

        @returns list of IP addresses.
        """
        return self.__node_ips

    def _doConfigure(self, node: Node, server: EthereumServer):
        server.configure(node, self)

    def _doInstall(self, node: Node, server: EthereumServer):
        server.install(node, self)

    def _createServer(self) -> Server:
        self.__serial += 1
        return EthereumServer(self.__serial)
