const fs = require('fs');

const DockerOdeWrapper = {
	docker: {
		listContainers(dockerInstance) {
                	return new Promise((resolve, reject) => {
                        	dockerInstance.listContainers((error, containers) => {
                                	if(error) {
                                        	reject(error);
                               		} else {
                                        	resolve(containers);
                                	}
                        	});
                	})
        	},
        	getContainer(dockerInstance, id) {
                	return new Promise((resolve) => {
                        	resolve(dockerInstance.getContainer(id));
                	});
       		},
	},
	container: {
		exec(dockerInstance, container, command) {
			return new Promise((resolve, reject) => {
				container.exec({ Cmd: command.split(" "), AttachStdIn: true, AttachStdout: true}, (error, exec) => {
					exec.start({hijack: true, stdin: false}, (err, stream) => {
						if (error) {
							console.log(`Command \"${command}\" failed to run`);
							reject(err);
						} else {
							console.log(`Command \"${command}\" executed successfully`);
							//option 1
							//dockerInstance.modem.demuxStream(stream, process.stdout, process.stderr);
							//option 2
							//stream.setEncoding('utf8');
							//stream.pipe(process.stdout);
							const chunks = []
							stream.on('data', chunk => chunks.push(Buffer.from(chunk)))
							stream.on('error', err => reject(err))
							stream.on('end', () => resolve(Buffer.concat(chunks).toString('utf8')))
						}
					})
				})
			})
		} 
	}
}

module.exports = DockerOdeWrapper;
