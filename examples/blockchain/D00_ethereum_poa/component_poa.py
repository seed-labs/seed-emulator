#!/usr/bin/env python3
# encoding: utf-8

from seedemu import *
from examples.internet.B03_hybrid_internet import hybrid_internet

def run(dumpfile=None, total_eth_nodes=20, total_accounts_per_node=2): 
    # Create the Ethereum layer

    emu = Emulator()

    eth = EthereumService()
    blockchain = eth.createBlockchain(chainName="POA", consensus=ConsensusMechanism.POA)

    # Change the default account balance to 1000
    mnemonic, _, _= blockchain.getEmuAccountParameters()
    blockchain.setEmuAccountParameters(mnemonic=mnemonic, balance=1000, \
            total_per_node = total_accounts_per_node)

    # Some number of pre-funded accounts (called local accounts) will be created
    # automatically based on a default set of parameters. 
    # We can change the default parameters like the following (the specified
    # phrase in this example is actually the same as the default phrase):  
    words = "great amazing fun seed lab protect network system security prevent attack future"
    blockchain.setLocalAccountParameters(mnemonic=words, total=10, balance=100) 

    # Other than the accounts automatically created by the emulator, we can
    # also add arbitrary accounts. 
    # The 3 accounts in this example are generated from the following phrase:
    # "gentle always fun glass foster produce north tail security list example gain"
    # We can recreate them and their private keys using the same phrase
    blockchain.addLocalAccount(address='0xF5406927254d2dA7F7c28A61191e3Ff1f2400fe9',
                            balance=30)
    blockchain.addLocalAccount(address='0x2e2e3a61daC1A2056d9304F79C168cD16aAa88e9', 
                            balance=9999999)
    blockchain.addLocalAccount(address='0xCBF1e330F0abD5c1ac979CF2B2B874cfD4902E24', 
                            balance=10)


    # Create the Ethereum servers. 
    signers  = []
    for i in range(total_eth_nodes):
       vnode = 'eth{}'.format(i)
       e = blockchain.createNode(vnode) 
       e.enableGethHttp()    # Enable HTTP on all nodes
       e.enableGethWs()      # Enable WebSocket on all nodes
       e.unlockAccounts()

       displayName = 'Ethereum-POA-%.2d'
       if i%2  == 0:
           e.startMiner()
           signers.append(vnode)
           displayName = displayName + '-Signer'
           e.appendClassName("Signer")
       if i%3 == 0:
           e.setBootNode(True)
           displayName = displayName + '-BootNode'
           e.appendClassName("BootNode")
       e.setDisplayName(displayName%(i))
                
    # Create the Faucet server
    faucet:FaucetServer = blockchain.createFaucetServer(
               vnode='faucet', 
               port=80, 
               linked_eth_node='eth5',
               balance=10000,
               max_fund_amount=10)
    faucet.setDisplayName('Faucet')

    # Add the Ethereum layer
    emu.addLayer(eth)

    # Generate output
    if dumpfile is not None:
        emu.dump(dumpfile)
    else:
        emu.dump("component_poa.bin")

if __name__ == "__main__":
    run()
