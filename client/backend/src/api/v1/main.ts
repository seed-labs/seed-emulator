import express from 'express';
import { SocketHandler } from '../../utils/socket-handler';
import dockerode from 'dockerode';
import { SeedContainerInfo, Emulator, SeedNetInfo, NodeInfo } from '../../utils/seedemu-meta';
import { Sniffer } from '../../utils/sniffer';
import WebSocket from 'ws';
import { Controller } from '../../utils/controller';
import fs from 'fs';
import { execSync } from 'child_process';
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

const getNodePosition: () => Promise<NodeInfo> = async function() {
    const _node_info = fs.readFileSync('/home/won/seedblock/experiments/moving/info/node_pos.json', 'utf-8');
    const node_info = JSON.parse(_node_info) as NodeInfo;
    console.log(node_info);
    return node_info;;
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

router.get('/position', async function(req, res, next) {
    try {
        let containers = await getNodePosition();
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

router.get('/container/:id/connect/:ip', express.json(), async function (req, res, next) {
    let id = req.params.id;
    let peer_ip = req.params.ip;
    let peer1_ofport = execSync(`sudo ovs-vsctl find interface external_ids"{>}"container_id=${id}`,{ 'encoding': 'utf8' }).replaceAll(' ', '').split('ofport:')[1].split('\n')[0];
    let peer2_ofport = execSync(`sudo ovs-vsctl find interface external_ids"{>}"container_id=${peer_ip}`,{ 'encoding': 'utf8' }).replaceAll(' ', '').split('ofport:')[1].split('\n')[0];
    
    let current_flow_rules = execSync('sudo ovs-ofctl dump-flows sdn0', { 'encoding': 'utf8' }).split('\n')
    let peer1_current_flows: string[]= [];
    let peer2_current_flows: string[]= [];

    current_flow_rules.forEach(rule => {
        if (rule.includes(`in_port=${peer1_ofport}`)){
            let output = rule.split(' ').pop().replace('actions=', '').replaceAll('output:', '')
            if (output.includes(',')){
                peer1_current_flows = output.split(',')
            }else{
                peer1_current_flows = [output]
            }
        }
        if (rule.includes(`in_port=${peer2_ofport}`)){
            let output = rule.split(' ').pop().replace('actions=', '').replaceAll('output:', '')
            if (output.includes(',')){
                peer2_current_flows = output.split(',')
            }else{
                peer2_current_flows = [output]
            }
        }
    })
    if (peer1_current_flows.includes(peer2_ofport)==false){
        peer1_current_flows.push(peer2_ofport)
    } 
    if (peer2_current_flows.includes(peer1_ofport)==false){
        peer2_current_flows.push(peer1_ofport)
    }

    execSync(`sudo ovs-ofctl add-flow sdn0 in_port=${peer1_ofport},actions=output:${peer1_current_flows.join(',')}`, { 'encoding': 'utf8' })
    execSync(`sudo ovs-ofctl add-flow sdn0 in_port=${peer2_ofport},actions=output:${peer2_current_flows.join(',')}`, { 'encoding': 'utf8' })
    

    console.log(peer1_current_flows)
    console.log(peer2_current_flows)
    
    // var candidates = (await docker.listContainers())
    //     .filter(c => c.Id.startsWith(id));

    // if (candidates.length != 1) {
    //     res.json({
    //         ok: false,
    //         result: `no match or multiple match for container ID ${id}.`
    //     });
    //     next();
    //     return;
    // }

    // let node = candidates[0];

    // await controller.setBgpPeerState(node.Id, peer, req.body.status);

    res.json({
        ok: true
    });

    next();
});

router.get('/container/:id/tc/:ip/:distance', express.json(), async function (req, res, next) {
    let id = req.params.id;
    let peer_ip = req.params.ip;
    let distance = req.params.distance;
    
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

    await controller.setTrafficControl(node.Id, peer_ip, distance);

    res.json({
        ok: true
    });

    next();
});

export = router;