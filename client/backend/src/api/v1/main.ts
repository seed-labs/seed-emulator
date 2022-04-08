import express from 'express';
import { SocketHandler } from '../../utils/socket-handler';
import dockerode from 'dockerode';
import { SeedContainerInfo, Emulator, SeedNetInfo } from '../../utils/seedemu-meta';
import { Sniffer } from '../../utils/sniffer';
import WebSocket from 'ws';
import { Controller } from '../../utils/controller';
import BasePlugin from '../../plugin/BasePlugin'

const router = express.Router();
const docker = new dockerode();
const socketHandler = new SocketHandler(docker);
const sniffer = new Sniffer(docker);
const controller = new Controller(docker);

const getContainers: () => Promise<SeedContainerInfo[]> = async function() {
    var containers: dockerode.ContainerInfo[] = await docker.listContainers();

    var _containers: SeedContainerInfo[] = containers.map(c => {
        var withMeta = c as SeedContainerInfo;

        withMeta.meta = {
            hasSession: socketHandler.getSessionManager().hasSession(c.Id),
            emulatorInfo: Emulator.ParseNodeMeta(c.Labels)
        };

        return withMeta;
    });

    // filter out undefine (not our nodes)
    return _containers.filter(c => c.meta.emulatorInfo.name);;
} 

socketHandler.getLoggers().forEach(logger => logger.setSettings({
    minLevel: 'warn'
}));

sniffer.getLoggers().forEach(logger => logger.setSettings({
    minLevel: 'warn'
}));

controller.getLoggers().forEach(logger => logger.setSettings({
    minLevel: 'warn'
}));

// used to be able to run many plugins simultaneously
const instantiated_types: number[] = [];
const instantiated_plugins: {[key: number]: BasePlugin} = {};


router.post('/plugin/:type/init', async (req, res, next) => {
	const type = parseInt(req.params.type);
	if(instantiated_types.includes(type)) {
		console.log(`Plugin of type ${type} is already running`);
		next();
		res.json({
        		ok: true
   		});
		return;
	}
	instantiated_types.push(type);
	instantiated_plugins[type] = new BasePlugin(type);
	console.log(`Done creating plugin of type ${type}`)	
	res.json({
        	ok: true
    	});
	next();
})

// Used to be able to run many plugins simultaneously
const running_listeners: number[] = []
const running_ws: {[key: number]: WebSocket} = {};

router.ws('/plugin/:type/command/', async (ws, req, next) => {
	
	const type = parseInt(req.params.type);
	if(running_ws[type]) {
		console.log(`Clearing previous socket for type ${type}`)
		running_ws[type].close();
	}
	running_ws[type] = ws

	if(!instantiated_types.includes(type)) {
		console.log(`Cannot run command with uninitialized plugin of type ${type}`)
		next();
		return;
	}


	// triggered when the user enters a command in the map
	running_ws[type].on('message', (message) => {
		const data = message.toString()
		// Need to handle json.parse with try and catch!	
		const [command, subscription, params] =  JSON.parse(data).command.split(" ");
	
		switch(command) {
   			case "start": {
      				instantiated_plugins[type].attach(subscription, params)
      				break;
   			}
   			case "stop": {
      				instantiated_plugins[type].detach(subscription)
      				break;
   			}
   			default: {
      				break;
			}
		}
	})

	 if(!running_listeners.includes(type)) {
                instantiated_plugins[type].onMessage(function(data) {
                        // readyState 1 means open
                        // Sending data to client
                        if(running_ws[type].readyState == 1) {
                                running_ws[type].send(JSON.stringify(data))
                        }
                })
                instantiated_plugins[type].run(await getContainers())
                running_listeners.push(type)
          }

	next()
})


router.get('/network', async function(req, res, next) {
    var networks = await docker.listNetworks();

    var _networks: SeedNetInfo[] = networks.map(n => {
        var withMeta = n as SeedNetInfo;

        withMeta.meta = {
            emulatorInfo: Emulator.ParseNetMeta(n.Labels)
        };

        return withMeta;
    });
    
    _networks = _networks.filter(n => n.meta.emulatorInfo.name);

    res.json({
        ok: true,
        result: _networks
    });

    next();
});

router.get('/container', async function(req, res, next) {
    try {
        let containers = await getContainers();

        res.json({
            ok: true,
            result: containers
        });
    } catch (e) {
        res.json({
            ok: false,
            result: e.toString()
        });
    }

    next();
});

router.get('/container/:id', async function(req, res, next) {
    var id = req.params.id;

    var candidates = (await docker.listContainers())
        .filter(c => c.Id.startsWith(id));

    if (candidates.length != 1) {
        res.json({
            ok: false,
            result: `no match or multiple match for container ID ${id}.`
        });
    } else {
        var result: any = candidates[0];
        result.meta = {
            hasSession: socketHandler.getSessionManager().hasSession(result.Id),
            emulatorInfo: Emulator.ParseNodeMeta(result.Labels)
        };
        res.json({
            ok: true, result
        });
    }

    next();
});

router.get('/container/:id/net', async function(req, res, next) {
    let id = req.params.id;

    var candidates = (await docker.listContainers())
        .filter(c => c.Id.startsWith(id));

    if (candidates.length != 1) {
        res.json({
            ok: false,
            result: `no match or multiple match for container ID ${id}.`
        });
        next();
        return;
    }

    let node = candidates[0];

    res.json({
        ok: true,
        result: await controller.isNetworkConnected(node.Id)
    });

    next();
});

router.post('/container/:id/net', express.json(), async function(req, res, next) {
    let id = req.params.id;

    var candidates = (await docker.listContainers())
        .filter(c => c.Id.startsWith(id));

    if (candidates.length != 1) {
        res.json({
            ok: false,
            result: `no match or multiple match for container ID ${id}.`
        });
        next();
        return;
    }
    
    let node = candidates[0];

    controller.setNetworkConnected(node.Id, req.body.status);
    
    res.json({
        ok: true
    });

    next();
});

router.ws('/console/:id', async function(ws, req, next) {
    try {
        await socketHandler.handleSession(ws, req.params.id);
    } catch (e) {
        if (ws.readyState == 1) {
            ws.send(`error creating session: ${e}\r\n`);
            ws.close();
        }
    }
    
    next();
});

var snifferSubscribers: WebSocket[] = [];
var currentSnifferFilter: string = '';

router.post('/sniff', express.json(), async function(req, res, next) {
    sniffer.setListener((nodeId, data) => {
        var deadSockets: WebSocket[] = [];

        snifferSubscribers.forEach(socket => {
            if (socket.readyState == 1) {
                socket.send(JSON.stringify({
                    source: nodeId, data: data.toString('utf8')
                }));
            }

            if (socket.readyState > 1) {
                deadSockets.push(socket);
            }
        });

        deadSockets.forEach(socket => snifferSubscribers.splice(snifferSubscribers.indexOf(socket), 1));
    });

    currentSnifferFilter = req.body.filter ?? '';

    await sniffer.sniff((await getContainers()).map(c => c.Id), currentSnifferFilter);

    res.json({
        ok: true,
        result: {
            currentFilter: currentSnifferFilter
        }
    });

    next();
});

router.get('/sniff', function(req, res, next) {
    res.json({
        ok: true,
        result: {
            currentFilter: currentSnifferFilter
        }
    });

    next();
});

router.ws('/sniff', async function(ws, req, next) {
    snifferSubscribers.push(ws);
    next();
});

router.get('/container/:id/bgp', async function (req, res, next) {
    let id = req.params.id;

    var candidates = (await docker.listContainers())
        .filter(c => c.Id.startsWith(id));

    if (candidates.length != 1) {
        res.json({
            ok: false,
            result: `no match or multiple match for container ID ${id}.`
        });
        next();
        return;
    }

    let node = candidates[0];

    res.json({
        ok: true,
        result: await controller.listBgpPeers(node.Id)
    });

    next();
});

router.post('/container/:id/bgp/:peer', express.json(), async function (req, res, next) {
    let id = req.params.id;
    let peer = req.params.peer;

    var candidates = (await docker.listContainers())
        .filter(c => c.Id.startsWith(id));

    if (candidates.length != 1) {
        res.json({
            ok: false,
            result: `no match or multiple match for container ID ${id}.`
        });
        next();
        return;
    }

    let node = candidates[0];

    await controller.setBgpPeerState(node.Id, peer, req.body.status);

    res.json({
        ok: true
    });

    next();
});

export = router;
