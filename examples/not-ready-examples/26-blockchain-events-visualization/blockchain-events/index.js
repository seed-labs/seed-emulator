import Web3 from 'web3';
import Docker from 'dockerode'
import DockerOdeWrapper from './DockerOdeWrapper.js'


const docker = new Docker()

const web3_eth1 = new Web3(new Web3.providers.WebsocketProvider("ws://localhost:8544"));
const web3_eth2 = new Web3(new Web3.providers.WebsocketProvider("ws://localhost:8545"));
const web3_eth3 = new Web3(new Web3.providers.WebsocketProvider("ws://localhost:8546"));
const web3_eth4 = new Web3(new Web3.providers.WebsocketProvider("ws://localhost:8547"));
const web3_eth5 = new Web3(new Web3.providers.WebsocketProvider("ws://localhost:8548"));
const web3_eth6 = new Web3(new Web3.providers.WebsocketProvider("ws://localhost:8549"));


const accountsToContainerMap = {}

async function driver() {
	const eth1_accounts = await web3_eth1.eth.getAccounts()
	const eth2_accounts = await web3_eth2.eth.getAccounts()
	const eth3_accounts = await web3_eth3.eth.getAccounts()
	const eth4_accounts = await web3_eth4.eth.getAccounts()
	const eth5_accounts = await web3_eth5.eth.getAccounts()
	const eth6_accounts = await web3_eth6.eth.getAccounts()
	
	const totalNumberOfAccounts = eth1_accounts.length + eth2_accounts.length + eth3_accounts.length + eth4_accounts.length + eth5_accounts.length + eth6_accounts.length;

	eth1_accounts.forEach(account => accountsToContainerMap[account.toLowerCase()] = '')
	eth2_accounts.forEach(account => accountsToContainerMap[account.toLowerCase()] = '')
	eth3_accounts.forEach(account => accountsToContainerMap[account.toLowerCase()] = '')
	eth4_accounts.forEach(account => accountsToContainerMap[account.toLowerCase()] = '')
	eth5_accounts.forEach(account => accountsToContainerMap[account.toLowerCase()] = '')
	eth6_accounts.forEach(account => accountsToContainerMap[account.toLowerCase()] = '')

	const containers = (await DockerOdeWrapper.docker.listContainers(docker)).filter(container => container.Names[0].includes('Ethereum'))
	
	let matchingAccounts = 0;

	containers.forEach(async (container) =>{
		const c = await DockerOdeWrapper.docker.getContainer(docker, container.Id)
		const output = await DockerOdeWrapper.container.exec(docker, c, 'geth attach --exec eth.accounts')
		const accounts = JSON.parse(output)
		accounts.forEach((account) => {
			if(accountsToContainerMap.hasOwnProperty(account)) {
				matchingAccounts++
				accountsToContainerMap[account] = container.Id
			}
		})
	})
	setTimeout(() => {
		if(matchingAccounts === totalNumberOfAccounts) {
			console.log(accountsToContainerMap)
			attachSubscriptions(web3_eth1, "Ethererum_1", "pendingTransactions");
			attachSubscriptions(web3_eth2, "Ethererum_2", "newBlockHeaders");
		}
	},3000)
	
}

function attachSubscriptions(web3, containerName, subscription) {
	if(attachSubscriptions[subscription]) {
		attachSubscriptions[subscription](web3, containerName)
	}
}

attachSubscriptions.newBlockHeaders = (web3, containerName) => {
	web3.eth.subscribe('newBlockHeaders', (error, result)=>{
		handleSubscriptionResults('newBlockHeaders', [web3, containerName, error, result])
	})
}

attachSubscriptions.pendingTransactions = (web3, containerName) => {
	web3.eth.subscribe('pendingTransactions', (error, result) => {
		handleSubscriptionResults('pendingTransactions', [web3, containerName, error, result])
	})
}

function handleSubscriptionResults(subscription, data = []) {
	if(!Array.isArray(data)) return;
	if(handleSubscriptionResults[subscription]) {
		handleSubscriptionResults[subscription](...data)
	}
}

handleSubscriptionResults.newBlockHeaders = (web3, containerName, error,  result) => {
	if(error) {
		console.log(`==== ${containerName} ==== New block header error\n\tMessage: ${error}\n`);
		return;
	}
	console.log(`==== ${containerName} ==== New block header result\n\tSource container: ${accountsToContainerMap[result.miner.toLowerCase()]}\n\tBlock number: ${result.number}\n\tBlock hash: ${result.hash}\n\tBlock miner: ${result.miner}\n`)

}

handleSubscriptionResults.pendingTransactions = (web3, containerName, error, result) => {
	if(error) {
		console.log(`==== ${containerName} ==== Pending transaction error\n\tMessage: ${error}\n`);
		return;
	}
	
	getTransactionReceipt(web3, containerName, result)
}

function getTransactionReceipt(web3, containerName, transactionHash) {
	web3.eth.getTransactionReceipt(transactionHash, (error, receipt) => {
		if(error) {
			console.log(`==== ${containerName} ==== Transaction receipt error\n\tMessage: ${error}\n`)
			return
		}
		if(receipt !== null) {
			console.log(`==== ${containerName}  ==== Transaction receipt result\n\tSource container: ${accountsToContainerMap[receipt.from.toLowerCase()]}\n\tDestination container: ${accountsToContainerMap[receipt.to ? receipt.to.toLowerCase() : '']}\n\tContract address: ${receipt.contractAddress}\n`)
		} else {
			setTimeout(() => {
				getTransactionReceipt(web3, containerName, transactionHash)
			},1000)
		}
	})
}

driver()


