#!/usr/bin/env python3
# encoding: utf-8

from seedemu import *

CustomGenesisFileContent = '''\
{
        "nonce":"0x0",
        "timestamp":"0x621549f1",
        "parentHash":"0x0000000000000000000000000000000000000000000000000000000000000000",
        "extraData":"0x",
        "gasLimit":"0x80000000",
        "difficulty":"0x0",
        "mixhash":"0x0000000000000000000000000000000000000000000000000000000000000000",
        "coinbase":"0x0000000000000000000000000000000000000000",
        "number": "0x0",
        "gasUsed": "0x0",
        "baseFeePerGas": null,
        "config": {
            "chainId": 11,
            "homesteadBlock": 0,
            "eip150Block": 0,
            "eip150Hash": "0x0000000000000000000000000000000000000000000000000000000000000000",
            "eip155Block": 0,
            "eip158Block": 0,
            "byzantiumBlock": 0,
            "constantinopleBlock": 0,
            "petersburgBlock": 0,
            "istanbulBlock": 0,
            "ethash": {
            }
        },
        "alloc": {
        }
}
'''

emu = Emulator()

# Create the Ethereum layer
# saveState=True: will set the blockchain folder using `volumes`, 
# so the blockchain data will be preserved when containers are deleted.
eth = EthereumService(saveState = True, override=True)


# Create POW Ethereum nodes (nodes in this layer are virtual)
# Default consensus mechanism is POW. 
e1 = eth.install("eth1").setConsensusMechanism(ConsensusMechanism.POW)
e2 = eth.install("eth2")
e3 = eth.install("eth3")
e4 = eth.install("eth4")

# Create POA Ethereum nodes
e5 = eth.install("eth5").setConsensusMechanism(ConsensusMechanism.POA)
e6 = eth.install("eth6").setConsensusMechanism(ConsensusMechanism.POA)
e7 = eth.install("eth7").setConsensusMechanism(ConsensusMechanism.POA)
e8 = eth.install("eth8").setConsensusMechanism(ConsensusMechanism.POA)

# Set bootnodes on e1 and e5. The other nodes can use these bootnodes to find peers.
# Start mining on e1,e2 and e5,e6
# To start mine(seal) in POA consensus, the account should be unlocked first. 
e1.setBootNode(True).setBootNodeHttpPort(8090).startMiner()
e2.startMiner()
e5.setBootNode(True).unlockAccounts().startMiner()
e6.unlockAccounts().startMiner()

# Create more accounts with Balance on e3 and e7
# Create one account with createAccount() method
# Create multiple accounts with createAccounts() method
e3.createAccount(balance= 32 * pow(10,18), password="admin").unlockAccounts()
e7.createAccounts(3, balance = 32*pow(10,18), password="admin")

# Import account with balance 0 on e2
e2.importAccount(keyfilePath='./resources/keyfile_to_import', password="admin", balance=0)

# Enable http connection on e3 
# Set geth http port to 8540 (Default : 8545)
e3.enableGethHttp().setGethHttpPort(8540)

# Set custom genesis on e4 geth
e4.setGenesis(CustomGenesisFileContent)

# Set custom geth command option on e4
# Possible to enable geth http using setCustomGethCommandOption() method 
# instead of using enableGethHttp() method
e4.setCustomGethCommandOption("--http --http.addr 0.0.0.0")

# Enable ws connection on e5 geth
# Set geth ws port to 8541 (Default : 8546)
e5.enableGethWs().setGethWsPort(8541)

# Set nodiscover option on e8 geth
e8.setNoDiscover()

# Set custom geth binary file instead of installing an original file.
e3.setCustomGeth("./resources/custom_geth")

# Customizing the display names (for visualization purpose)
emu.getVirtualNode('eth1').setDisplayName('Ethereum-POW-1')
emu.getVirtualNode('eth2').setDisplayName('Ethereum-POW-2')
emu.getVirtualNode('eth3').setDisplayName('Ethereum-POW-3').addPortForwarding(8545, 8540)
emu.getVirtualNode('eth4').setDisplayName('Ethereum-POW-4')
emu.getVirtualNode('eth5').setDisplayName('Ethereum-POA-5')
emu.getVirtualNode('eth6').setDisplayName('Ethereum-POA-6')
emu.getVirtualNode('eth7').setDisplayName('Ethereum-POA-7')
emu.getVirtualNode('eth8').setDisplayName('Ethereum-POA-8')

# Add the layer and save the component to a file
emu.addLayer(eth)
emu.dump('component-blockchain.bin')
