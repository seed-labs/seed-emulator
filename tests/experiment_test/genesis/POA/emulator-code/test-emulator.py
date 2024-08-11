#!/usr/bin/env python3
# encoding: utf-8

from seedemu import *
from examples.blockchain.D00_ethereum_poa import ethereum_poa
from seedemu.services.EthereumService import *
from experiments.blockchain.D23_deploy_contract.lib.services.EthereumService.EthUtil import CustomGenesis
from experiments.blockchain.D23_deploy_contract.lib.services.EthereumService.EthereumService import CustomBlockchain
import platform
from web3 import Web3
import random


def run(dumpfile=None):
    ###############################################################################
    emu = Emulator()

    # Run and load the pre-built ethereum component; it is used as the base blockchain
    local_dump_path = "./blockchain-poa.bin"
    ethereum_poa.run(
        dumpfile=local_dump_path,
        hosts_per_as=1,
        total_eth_nodes=10,
        total_accounts_per_node=1,
    )
    emu.load(local_dump_path)

    # Get the blockchain information
    eth: EthereumService = emu.getLayer("EthereumService")
    blockchain: Blockchain = eth.getBlockchainByName(eth.getBlockchainNames()[0])
    eth_nodes   = blockchain.getEthServerNames()
    blockchain.__class__ = CustomBlockchain

    with open("./Contracts/Contract.bin-runtime", "r") as f:
        runtime_bytecode = Web3.toHex(hexstr=f.read().strip())

    # This account has been generated from the mnemonic phrase: "gentle always fun glass foster produce north tail security list example gain"
    # We will use this as a contract address for the contract deployment using genesis block
    contract_address = "0xA08Ae0519125194cB516d72402a00A76d0126Af8"
    blockchain.addLocalAccount(contract_address, balance=0)

    # Add the runtime bytecode with the contract address in the genesis block
    blockchain.addCode(contract_address, runtime_bytecode)
    
    # Set initial storage for the contract
    # This will assign the total supply of 1,000,000 tokens to the contract address using the slot 0 which is __balanceOf for the contract
    blockchain.addStorage(contract_address=contract_address, slot=0, value=1000000)
    
    # Add the initial balance for the custom address using storage and function slot 0
    custom_address = "0x2e2e3a61daC1A2056d9304F79C168cD16aAa88e9"
    blockchain.addStorage(contract_address=contract_address, slot=0, value=50000)

    # Generate the emulator files
    if dumpfile is not None:
        emu.dump(dumpfile)
    else:
        emu.render()
        data = {}
        data['rpc_url'] = str(emu.getBindingFor(random.choice(eth_nodes)).getInterfaces()[0].getAddress())
        # Save the data to a file
        with open("./../rpc_info.json", "w") as f:
            json.dump(data, f)

        if platform.machine() == "aarch64" or platform.machine() == "arm64":
            current_platform = Platform.ARM64
        else:
            current_platform = Platform.AMD64

        docker = Docker(etherViewEnabled=True, platform=current_platform, internetMapEnabled=False)
        emu.compile(docker, "./output", override=True)


if __name__ == "__main__":
    run()
