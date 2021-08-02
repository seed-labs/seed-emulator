import sys
import os

def getContent(file_name):
	file = open(file_name, "r")
	data = file.read()
	file.close()
	return data.replace("\n","")

def generate_abi_bin(file_name):
	abiCommand = "solc --abi " + file_name + " | awk '/JSON ABI/{x=1}x' | sed 1d > contract.abi"
	binCommand = "solc --bin " + file_name + " | awk '/Binary:/{x=1;next}x' > contract.bin"

	os.system(abiCommand) #need to change api
	os.system(binCommand)

def generateSmartContractCommand(file_name):
	generate_abi_bin(file_name)
	abi = "abi = {}".format(getContent("contract.abi"))
	byte_code = "byteCode = \"0x{}\"".format(getContent("contract.bin"))
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