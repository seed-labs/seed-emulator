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
	}
}

function getCommand(name, params=[]) {
	if(commands[name]) {
		console.log("spread params are: ", ...params)
		return commands[name](...params)
	}
}

module.exports = getCommand;
