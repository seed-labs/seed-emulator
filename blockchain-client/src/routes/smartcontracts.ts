const express = require('express')
const docker = require('../docker/index.ts');
const DockerOdeWrapper = require('../DockerOdeWrapper.ts');
const getCommand = require('../commands.ts');
const helpers = require('../common/helpers.ts')


const router = express.Router();

const sanitizeOutputForAction = {
	deploySmartContract(output) {
		return  JSON.parse(helpers.stringToJsonString(helpers.sanitizeGethStreamString(output))).transactionHash;
	},
	getTransactionReceipt(output) {
		const res = JSON.parse(helpers.stringToJsonString(helpers.sanitizeGethStreamString(output)))
		if(!res) {
			return res
		}
		return res.contractAddress
	},
	getContractByAddress(output) {
		return helpers.stringToJsonString(helpers.sanitizeGethStreamString(output))
	},
	invokeContractFunction(output) {
		return output
	}
}


router.get('/', async (req, res) => {
	try {
		const containers = await DockerOdeWrapper.docker.listContainers(docker)
		const [openForConnectionContainer] = containers.filter(container => container.Names[0].includes(process.env.CONTAINER))
		const container = await DockerOdeWrapper.docker.getContainer(docker, openForConnectionContainer.Id)
		const accounts = await DockerOdeWrapper.container.exec(docker, container, getCommand("getAccounts"));
	
		res.render('smartcontract', {
			accounts: JSON.parse(accounts),
			port: process.env.PORT,
			containerId: container.id,
		})
	} catch(e) {
		console.log(e)
	}
})

router.post('/', async(req, res) => {
	try {
		const {params, action, containerId} = req.body;
		const container = await DockerOdeWrapper.docker.getContainer(docker, containerId);
		let output = await DockerOdeWrapper.container.exec(docker, container, getCommand(action, params))
		
		if(action === 'invokeContractFunction') {
			// giving some time for the network to mine the actual transaction
			output = JSON.stringify({
				output: await DockerOdeWrapper.container.exec(docker, container, getCommand(action, params, {call:true})),
				funcName: params[0].funcName,
				abiIndex: params[0].abiIndex
			})
		}
		
		res.send({
			action,
			response: sanitizeOutputForAction[action](output)
		})	
	} catch(e) {
		console.log(e)
	}

})

module.exports = router;
