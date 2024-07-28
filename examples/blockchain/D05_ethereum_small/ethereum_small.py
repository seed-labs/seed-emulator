#!/usr/bin/env python3
# encoding: utf-8

from seedemu import *
import os, sys

DOMAIN = ".net"

def buildBase(total:int):
    base = Base()
    as_ = base.createAutonomousSystem(150)

    as_.createNetwork('net0')

    for i in range(total):
        name = 'node-{}'.format(i)
        node = as_.createHost(name)
        node.joinNetwork('net0')

    return base

def buildEthComponent(total:int):
    eth = EthereumService()
    blockchain = eth.createBlockchain(chainName="POA", consensus=ConsensusMechanism.POA)

    blockchain.addLocalAccount(address='0x2e2e3a61daC1A2056d9304F79C168cD16aAa88e9',
                            balance=9999999)
    
    vnodes = []
    for i in range(total):
       vnode = 'eth-{}'.format(i)
       vnodes.append(vnode)
       e = blockchain.createNode(vnode)
       e.enableGethHttp().enableGethWs().unlockAccounts().startMiner()

       displayName = 'Ethereum-POA-%.2d'
       if i%3 == 0:
           e.setBootNode(True)
           displayName = displayName + '-BootNode'

       e.setDisplayName(displayName%(i))
       e.addHostName(vnode + DOMAIN) # Add this name to /etc/hosts

    # Create the Faucet server
    faucet:FaucetServer = blockchain.createFaucetServer(
               vnode='faucet',
               port=80,
               linked_eth_node='eth-0',
               balance=10000,
               max_fund_amount=10)
    faucet.setDisplayName('Faucet')
    faucet.addHostName('faucet' + DOMAIN) # Add this name to /etc/hosts
    vnodes.append('faucet')

    # Create the initialization and information server
    util:EthUtilityServer = blockchain.createEthUtilityServer(
               vnode='utility',
               port=5000,
               linked_eth_node='eth-0',
               linked_faucet_node='faucet')
    util.setDisplayName('UtilityServer')
    util.addHostName('utility' + DOMAIN)  # Add this name to /etc/hosts
    vnodes.append('utility')

    return eth, vnodes


def run(dumpfile = None, total_hosts=15, total_eth_nodes=10):
    ###############################################################################
    # Set the platform information
    if dumpfile is None:
        script_name = os.path.basename(__file__)

        if len(sys.argv) == 1:
            platform = Platform.AMD64
        elif len(sys.argv) == 2:
            if sys.argv[1].lower() == 'amd':
                platform = Platform.AMD64
            elif sys.argv[1].lower() == 'arm':
                platform = Platform.ARM64
            else:
                print(f"Usage:  {script_name} amd|arm")
                sys.exit(1)
        else:
            print(f"Usage:  {script_name} amd|arm")
            sys.exit(1)

    assert total_hosts >= total_eth_nodes+2, "Not enough hosts" 

    emu  = Emulator()

    base        = buildBase(total_hosts)
    eth, vnodes = buildEthComponent(total_eth_nodes)


    # Bind to physical nodes
    for vnode in vnodes:
        emu.addBinding(Binding(vnode, filter=Filter(nodeName='node*'),
                       action=Action.FIRST))

    emu.addLayer(base)
    emu.addLayer(eth)
    emu.addLayer(EtcHosts())

    # Generate output
    if dumpfile is not None:
        emu.dump(dumpfile)
    else:
        emu.render()
        docker = Docker(etherViewEnabled=True, platform=platform)
        emu.compile(docker, './output', override=True)

if __name__ == "__main__":
    run()
