const apis = [
	{
		name: "Get Accounts",
		description: "Returns the list of ethereum accounts in the container.",
		command: "getAccounts",
		parameters: []
	},
	{
		name: "Get Balance",
		description: "Returns the balance of the account specified as parameter.",
		command: "getBalance",
		parameters: [{el: "input", name: "Account index", required: true}]
	},
	{
		name: "Set Etherbase",
		description: "Sets the account which will be receiving ether when mining.",
		command: "setEtherBase",
		parameters: [{el: "input", name: "Account index", required: true}]
	},
	{
		name: "Get Coinbase",
		description: "Returns the address of the account collecting ether when mining",
		command: "getCoinBase",
	},
	{
		name: "Start Mining",
		description: "Starts the mining process on the coinbase account.",
		command: "startMiner",
		parameters: [{el: "input", name: "Number of threads", required: false}]
	},
	{
		name: "Stop Mining",
		description: "Stop the mining process.",
		command: "stopMiner",
		parameters: []
	},
	{
		name: "Send Transaction",
		description: "Send ether from one account to the other.",
		command: "sendTransaction",
		parameters: [{el: "input", name:"From address", required: true},{el: "input", name: "To address", required: true},{el: "input", name: "Value in ether", required: true}]
	},
	{
		name: "View Pending Transactions",
		description: "View a list of pending transactions in the network.",
		command: "viewPendingTransactions",
		parameters: []
	}
]

module.exports = apis;
