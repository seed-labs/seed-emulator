const express = require('express')
const docker = require('../docker/index.ts');
const DockerOdeWrapper = require('../DockerOdeWrapper.ts');
const getCommand = require('../commands.ts');

const router = express.Router();

const getAccounts = 'getAccounts';

router.get('/', async (req, res) => {
	try {
		const containers = await DockerOdeWrapper.docker.listContainers(docker)
		const [openForConnectionContainer] = containers.filter(container => container.Names[0].includes(process.env.CONTAINER))
		const container = await DockerOdeWrapper.docker.getContainer(docker, openForConnectionContainer.Id)
		const accounts = await DockerOdeWrapper.container.exec(docker, container, getCommand(getAccounts));
		
		console.log('Accounts: ', accounts);

		res.render('smartcontract', {
			accounts: JSON.parse(accounts),
			port: process.env.PORT,
			container: openForConnectionContainer,
		})
	} catch(e) {
		console.log(e)
	}
})

module.exports = router;
