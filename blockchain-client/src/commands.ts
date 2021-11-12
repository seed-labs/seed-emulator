const helpers = require('./common/helpers.ts')

// @todo use the castGethParameters for all other commands
const commands = {
	getAccounts() {
		return "geth attach --exec eth.accounts"
	},
	getBalance(account) {
		account = account || 0;
		return `geth attach --exec eth.getBalance(eth.accounts[${account}])`
	},
	setDefaultAccount(account) {
		account = account || 0;
		// spaces matter here when writing the equality, remove the spaces.
		return `geth attach --exec eth.defaultAccount=eth.accounts[${account}]`
	},
	getDefaultAccount() {
		return `geth attach --exec eth.defaultAccount`
	},
	setEtherBase(account) {
		account = account || 0
		return `geth attach --exec miner.setEtherbase(eth.accounts[${account}])`
	},
	getCoinBase() {
		return `geth attach --exec eth.coinbase`
	},
	startMiner(threads) {
		threads = threads || 20;
		return `geth attach --exec miner.start(${threads})`
	},
	stopMiner() {
		return `geth attach --exec miner.stop()`
	},
	sendTransaction(sender, receiver, amount) {
		return `geth attach --exec eth.sendTransaction({from:"${sender}",to:"${receiver}",value:web3.toWei(${amount},\"ether\")})`
 	},
	viewPendingTransactions() {
		return `geth attach --exec eth.pendingTransactions`
	},
	deploySmartContract(account, abi, bytecode, params) {
		abi = abi.replace(" ", "\t")
		if(params.length) {
			//return `geth attach --exec eth.contract(${abi}).new(${params},{from :"${account}", data:bytecode, gas: 1000000})` 
		} else {
			return `geth attach --exec eth.contract(${abi}).new({from:"${account}",data:"${bytecode}",gas:1000000})`

		}
	},
	getTransactionReceipt(hash) {
		return `geth attach --exec eth.getTransactionReceipt("${hash}")` 
	},
	getContractByAddress(abi,address) {
		abi=abi.replace(" ", "\t")
		console.log('abi: ', abi)
		console.log('address: ', address)
		return `geth attach --exec eth.contract(${abi}).at("${address}")`
	},
	invokeContractFunction(funcName,defaultAccount ,params) {
		const [contractInfo, ...otherParams] = params;
		const abi = contractInfo.abi.replace(" ", "\t")
		let command = `geth attach --exec eth.defaultAccount=${helpers.castGethParameters(defaultAccount, 'address')};sc=eth.contract(${abi}).at(${helpers.castGethParameters(contractInfo.address, "address")});sc[${helpers.castGethParameters(funcName, 'string')}](`
		let i = 0;
		command += helpers.castGethParameters(otherParams[i].value, otherParams[i].type)
		for(i = 1; i < otherParams.length; i++) {
			command+="," + helpers.castGethParameters(otherParams[i].value, otherParams[i].type); 
		}
		command += ")"
		return command;
	}
	
}

function getCommand(name, params=[]) {
	if(commands[name]) {
		//console.log("spread params are: ", ...params)
		return commands[name](...params)
	}
}

module.exports = getCommand;
