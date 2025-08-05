import express from 'express';
import {SocketHandler} from '../../utils/socket-handler';
import dockerode from 'dockerode';
import {SeedContainerInfo, Emulator, SeedNetInfo} from '../../utils/seedemu-meta';
import {Sniffer} from '../../utils/sniffer';
import {SubmitEvent} from '../../utils/submit-event';
import WebSocket from 'ws';
import {Controller} from '../../utils/controller';
import {promises as fs} from 'fs';

const router = express.Router();
const docker = new dockerode();
const socketHandler = new SocketHandler(docker);
const sniffer = new Sniffer(docker);
const controller = new Controller(docker);
const submitEvent = new SubmitEvent(docker);

async function readJsonFile(filePath: string) {
    try {
        const data = await fs.readFile(filePath, 'utf-8');
        return JSON.parse(data);
    } catch (err) {
        console.error(`读取文件 ${fs.realpath(filePath)} 失败:`, err);
        throw err;
    }
}

const getContainers: () => Promise<SeedContainerInfo[]> = async function () {
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
    return _containers.filter(c => c.meta.emulatorInfo.name);
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

router.get('/network', async function (req, res, next) {
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

router.get('/container', async function (req, res, next) {
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

router.get('/install', async function (req, res, next) {
    readJsonFile('installs.json').then(installs => {
        res.json({
            ok: true,
            result: installs
        });
    }).catch(e => {
        res.json({
            ok: false,
            result: e.toString()
        });
    })
});

router.post('/install', express.json(), async function (req, res, next) {
    const address = `${req.socket.localAddress}:${req.socket.localPort}`
    let ret = await submitEvent.submitEvent(address, (await getContainers()).map(c => c.Id), 'install');
    if (ret) {
        ret = {
            ok: true,
            result: "install success"
        }
    } else {
        ret = {
            ok: true,
            result: "install error"
        }
    }
    res.json(ret);

    next();
});

router.post('/uninstall', express.json(), async function (req, res, next) {
    let ret = await submitEvent.submitEvent('', (await getContainers()).map(c => c.Id), 'uninstall');
    if (ret) {
        ret = {
            ok: true,
            result: "uninstall success"
        }
    } else {
        ret = {
            ok: true,
            result: "uninstall error"
        }
    }
    res.json(ret);

    next();
});

router.get('/container/:id', async function (req, res, next) {
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

router.get('/container/:id/net', async function (req, res, next) {
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

router.post('/container/:id/net', express.json(), async function (req, res, next) {
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

router.post('/container/:id/vis/set', express.json(), async function (req, res, next) {
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

    var deadSockets: WebSocket[] = [];

    visSubscribers.forEach(socket => {
        if (socket.readyState == 1) {
            socket.send(JSON.stringify({
                source: id, data: JSON.stringify(req.body)
            }));
        }

        if (socket.readyState > 1) {
            deadSockets.push(socket);
        }
    });

    deadSockets.forEach(socket => visSubscribers.splice(visSubscribers.indexOf(socket), 1));

    res.json({
        ok: true,
        result: {
            currentFilter: 'success'
        }
    });

    next();
});

router.ws('/console/:id', async function (ws, req, next) {
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
var visSubscribers: WebSocket[] = [];

router.post('/sniff', express.json(), async function (req, res, next) {
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

router.get('/sniff', function (req, res, next) {
    res.json({
        ok: true,
        result: {
            currentFilter: currentSnifferFilter
        }
    });

    next();
});

router.ws('/sniff', async function (ws, req, next) {
    snifferSubscribers.push(ws);
    next();
});

router.ws('/container/vis/set', async function (ws, req, next) {
    visSubscribers.push(ws);
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
