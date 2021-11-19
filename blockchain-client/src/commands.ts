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
	deploySmartContract(account, abi, bytecode, params, value) {
		abi = abi.replace(" ", "\t")
		let base = `{from:"${account}",data:"${bytecode}",gas:1000000`
		if(params.length) {
			base = params +',' + base;
		}
		if(value) {
			base += `,value:${value}`
		}
		base += '}'
		
		//if(params.length) {
		//	return `geth attach --exec eth.contract(${abi}).new(${params},{from:"${account}",data:"${bytecode}",gas:1000000})` 
		//} else {
		//	return `geth attach --exec eth.contract(${abi}).new()`
		//}
		return `geth attach --exec eth.contract(${abi}).new(${base})`
	},
	getTransactionReceipt(hash) {
		return `geth attach --exec eth.getTransactionReceipt("${hash}")` 
	},
	getContractByAddress(abi,address) {
		abi = abi.replace(" ", "\t")
		return `geth attach --exec eth.contract(${abi}).at("${address}")`
	},
	invokeContractFunction(funcInfo, parameters, additional=[]) {
		const {funcName, payable} = funcInfo
		const [defaultAccount, {abi, address}, value] = additional;
		const parameterString = this.generateCallString(parameters, {payable, value})
		const tail = this.options.call ? '.call' + parameterString : parameterString;

		sanitizedAbi = abi.replace(" ", "\t")
		
		return `geth attach --exec eth.defaultAccount="${defaultAccount}";` + 
			`sc=eth.contract(${sanitizedAbi}).at("${address}");` +
			`sc["${funcName}"]${tail}`
	},
	generateCallString(parameters=[], options={}) {
		let command = "("
		if(parameters.length) {
			let i = 0;
			command += `"${parameters[i].value}"`
			for(i = 1; i < parameters.length; i++) {
				command+=`,"${parameters[i].value}"`; 
			}
		}
		if(options.payable) {
			const stringObj = `{value:${options.value * Math.pow(10,18)}}`
			command += parameters.length ?`,${stringObj}` : stringObj
		}
		command += ")"
		return command;
	}
	
}

function getCommand(name, params=[], options={}) {
	if(commands[name]) {
		commands.options = options
		//console.log("spread params are: ", ...params)
		return commands[name](...params)
	}
}

module.exports = getCommand
