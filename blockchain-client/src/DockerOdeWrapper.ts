const fs = require('fs');
const helpers = require('./common/helpers.ts')

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
							return helpers.demuxStream(stream)
								.then((output) => {	
									return resolve(output)
								})

						}
					})
				})
			})
		} 
	}
}

module.exports = DockerOdeWrapper;
