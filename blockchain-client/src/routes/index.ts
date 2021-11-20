const express = require('express');
const docker = require('../docker/index.ts');
const DockerOdeWrapper = require('../DockerOdeWrapper.ts');
const apis = require('../apis.ts');
const getCommand = require('../commands.ts');

const router = express.Router();

router.get('/', async (req, res) => {
	try {
		const containers = await DockerOdeWrapper.docker.listContainers(docker)
		res.render('home', {
			port: process.env.PORT,
			apis,
			containers: containers.filter(container => container.Names[0].includes('Ethereum')) 
		})
	} catch(e) {
		console.log(e)
	}
})

router.post('/', async (req, res) => {
	try {
		const {containerId, command, params} = req.body;
		const container = await DockerOdeWrapper.docker.getContainer(docker, containerId)
		const output = await DockerOdeWrapper.container.exec(docker, container, getCommand(command, params))
		res.send(JSON.stringify({
			command,
			output
		}))
	} catch(e) {
		console.log(e)
	}
})

module.exports = router;
