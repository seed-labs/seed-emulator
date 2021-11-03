const express = require('express');
const handlebars = require('express-handlebars');
const Docker = require('dockerode');
const path = require('path');
const bodyParser = require('body-parser');
const DockerOdeWrapper = require('./DockerOdeWrapper.ts');
const apis = require('./apis.ts')
const getCommand = require('./commands.ts')

const docker = new Docker()

const app = express();
const port = process.env.PORT || 3000;

app.engine('handlebars', handlebars());
app.set('view engine', 'handlebars');

app.use(express.static(path.join(__dirname, "/public")));
app.use(bodyParser.urlencoded({extended: false}))
app.use(bodyParser.json())

app.get('/', async (req, res) => {
	try {
		const containers = await DockerOdeWrapper.docker.listContainers(docker)
		res.render('home', {
			apis,
			containers: containers.filter(container => container.Names[0].includes('Ethereum')) 
		})
	} catch(e) {
		console.log(e)
	}
})

app.post('/', async (req, res) => {
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

app.listen(port, () => {
	console.log(`server started at http://localhost:${port}`)
})
