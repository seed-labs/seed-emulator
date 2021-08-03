#!/usr/bin/env python
# encoding: utf-8
# __author__ = 'Demon'
import sys
import os
from seedemu.core import Node
from seedemu.services import EthereumService,EthereumServer


class EthereumConsoleManager():

	def getContent(self, file_name):
		file = open(file_name, "r")
		data = file.read()
		file.close()
		return data.replace("\n","")

	def generate_abi_bin(self, file_name):
		abiCommand = "solc --abi " + file_name + " | awk '/JSON ABI/{x=1}x' | sed 1d > contract.abi"
		binCommand = "solc --bin " + file_name + " | awk '/Binary:/{x=1;next}x' > contract.bin"

		os.system(abiCommand) #need to change api
		os.system(binCommand)

	def generateSmartContractCommand(self, file_name):
		self.generate_abi_bin(file_name)
		abi = "abi = {}".format(self.getContent("contract.abi"))
		byte_code = "byteCode = \"0x{}\"".format(self.getContent("contract.bin"))
		unlock_account = "personal.unlockAccount(eth.accounts[0], \"{}\")".format("admin")
		contract_command = "testContract = eth.contract(abi).new({ from: eth.accounts[0], data: byteCode, gas: 1000000})"
		display_contract_Info = "testContract"
		finalCommand = "{},{},{},{},{}".format(abi, byte_code, unlock_account, contract_command, display_contract_Info)

		SmartContractCommand = " sleep 30\n\
		geth --exec 'miner.start(5)' attach \n\
		sleep 600 \n\
		gethCommand=\'{}\'\n\
		finalCommand=\'geth --exec \"$gethCommand\" attach\'\n\
		result=$(eval \"$finalCommand\")\n\
		touch transaction.txt\n\
		echo \"transaction hash $result\" \n\
		echo \"$result\" >> transaction.txt\n\
		".format(finalCommand)
		return SmartContractCommand

	def deploySmartContractOn(self, ethereum_server:EthereumServer, ethereum_service: EthereumService, contract_file_name: str):
		for (server, node) in ethereum_service.getTargets():
			if(ethereum_server == server):
				print("akarsh=======>")
				print(node)
				smartContractCommand = self.generateSmartContractCommand(contract_file_name)
				node.appendStartCommand('(\n {})&'.format(smartContractCommand))
			
		
