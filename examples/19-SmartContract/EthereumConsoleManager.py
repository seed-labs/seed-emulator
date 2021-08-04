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

	def generateSmartContractCommand(self, contract_file_bin, contract_file_abi):
		abi = "abi = {}".format(self.getContent(contract_file_abi))
		byte_code = "byteCode = \"0x{}\"".format(self.getContent(contract_file_bin))
		unlock_account = "personal.unlockAccount(eth.accounts[0], \"{}\")".format("admin")
		contract_command = "testContract = eth.contract(abi).new({ from: eth.accounts[0], data: byteCode, gas: 1000000})"
		display_contract_Info = "testContract"
		finalCommand = "{},{},{},{},{}".format(abi, byte_code, unlock_account, contract_command, display_contract_Info)

		SmartContractCommand = "sleep 30 \n \
		while true \n\
		do \n\
		\t balanceCommand=\"geth --exec 'eth.getBalance(eth.accounts[0])' attach\" \n\
		\t balance=$(eval \"$balanceCommand\") \n\
		\t minimumBalance=1000000 \n\
		\t if [ $balance -lt $minimumBalance ] \n\
		\t then \n \
		\t \t sleep 60 \n \
		\t else \n \
		\t \t break \n \
		\t fi \n \
		done \n \
		echo \"Balance ========> $balance\" \n\
		gethCommand=\'{}\'\n\
		finalCommand=\'geth --exec \"$gethCommand\" attach\'\n\
		result=$(eval \"$finalCommand\")\n\
		touch transaction.txt\n\
		echo \"transaction hash $result\" \n\
		echo \"$result\" >> transaction.txt\n\
		".format(finalCommand)
		return SmartContractCommand

	def deploySmartContractOn(self, ethereum_server:EthereumServer, ethereum_service: EthereumService, contract_file_bin: str, contract_file_abi: str):
		for (server, node) in ethereum_service.getTargets():
			if(ethereum_server == server):
				smartContractCommand = self.generateSmartContractCommand(contract_file_bin, contract_file_abi)
				node.appendStartCommand('(\n {})&'.format(smartContractCommand))	

	def addMinerStartCommand(self, node: Node):	
		command = SmartContractCommand = " sleep 20\n\
		geth --exec 'eth.defaultAccount = eth.accounts[0]' attach \n\
		geth --exec 'miner.start(5)' attach \n\
		"
		node.appendStartCommand('(\n {})&'.format(command))

	def startMinerInAllNodes(self, ethereum_service: EthereumService):
		for (server, node) in ethereum_service.getTargets():
			self.addMinerStartCommand(node)

	def startMinerInNode(self, ethereum_server:EthereumServer, ethereum_service: EthereumService):
		for (server, node) in ethereum_service.getTargets():
			if(ethereum_server == server):
				self.addMinerStartCommand(node)

	def createNewAccountCommand(self, node: Node):
		command = SmartContractCommand = " sleep 20\n\
		geth --password /tmp/eth-password account new \n\
		"
		node.appendStartCommand('(\n {})&'.format(command))

	def createNewAccountInNode(self, ethereum_server:EthereumServer, ethereum_service: EthereumService):		
		for (server, node) in ethereum_service.getTargets():
			if(ethereum_server == server):
				self.createNewAccountCommand(node)