import express from 'express';
import { SocketHandler } from '../../utils/socket-handler';
import dockerode from 'dockerode';
import { SeedContainerInfo, Emulator, SeedNetInfo, NodeInfo } from '../../utils/seedemu-meta';
import { Sniffer } from '../../utils/sniffer';
import WebSocket from 'ws';
import { Controller } from '../../utils/controller';
import fs from 'fs';
import { execSync } from 'child_process';
import { stringify } from 'querystring';

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
    //const _node_info = fs.readFileSync(filepath, 'utf-8');
    try {
        const _node_info = fs.readFileSync('/tmp/node_info/node_pos.json', 'utf-8');
        const node_info = JSON.parse(_node_info) as NodeInfo;
        return node_info;;
      } catch (error) {
        if (error.code === 'ENOENT') {
          // Handle the case where the file does not exist
          console.error('File does not exist.');
          return null
        } else {
          // Handle other potential errors
          console.error('Error reading the file:', error.message);
        }
      }
}

// const getSimulationInfo: () => Promise<NodeInfo> = aync function() {
//     const _simulation_info = fs.readFileSync('/tmp/node_info/simulation_info.json', 'utf-8')
//     const simulation_info = JSON.parse(_simulation_info) as SimulationInfo;
//     return simulation_info;;
// }

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
        if (containers!==null){
            res.json({
                ok: true,
                result: containers
            });
        }
        else{
            res.json({
                ok:false,
                result: "no position file found."
            });
        }
    } catch (e) {
        res.json({
            ok: false,
            result: e.toString()
        });
    }

    next();
});

// router.post('/position', express.json(), async function(req, res, next) {
//     let filepath = req.body.path;
//     try {
//         let containers = await getNodePosition(filepath);
//         res.json({
//             ok: true,
//             result: containers
//         });
//     } catch (e) {
//         res.json({
//             ok: false,
//             result: e.toString()
//         });
//     }

//     next();
// });

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


router.get('/container/:id/connectivity/:ip', express.json(), async function (req, res, next) {
    let id = req.params.id;
    let dst_ip = req.params.ip;
    
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

    let result = await controller.startConnTest(node.Id, dst_ip);

    let splitted_result = result.output.split('\n')
    console.log(splitted_result)
    let loss = "100"
    let routes = 'no routes'
    
    if (splitted_result.length>2){

        let result_summary = splitted_result[splitted_result.length-2]
        if (result_summary.startsWith('---')){
            result_summary = splitted_result[splitted_result.length-1]
        }
        let splitted_result_summary = result_summary.split(",")
        console.log(result_summary)
        loss = splitted_result_summary[splitted_result_summary.length-2]
        routes = 'no routes';
        console.log(loss);

        if (loss.split("%")[0].trim() != "100"){
            let routes_list: string[] = [];
            result.output.split("\n\n")[0].split("RR:")[1].split('\n').forEach(route=>{
                console.log(route)
                routes_list.push(route.replace('\t','').trim());
            });

            routes = routes_list.join('\n')
        }
        console.log(routes);
    }
    
    res.json({
        ok: true,
        result: {
            loss: loss,
            routes: routes
        }
    });

    next();
});

// ${this._apiBase}/container/${node}/nexthop/${dst_ip}
router.get('/container/:id/nexthop/:ip', express.json(), async function (req, res, next) {
    let id = req.params.id;
    let dst_ip = req.params.ip;
    
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

    let result = await controller.getNextHop(node.Id, dst_ip);
    let next_hop = result.output.split(' ')[2].trim()
    console.log(`container output result : ${next_hop}`);
    res.json({
        ok: true,
        result: {
            nextHop: `${next_hop}`
        }
    });

    next();
});

// ${this._apiBase}/container/${node}/iter/${iter}
router.get('/container/:id/iter/:iter', express.json(), async function (req, res, next) {
    let id = req.params.id;
    let iter = req.params.iter;
    
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

    await controller.moveNodePositionAtIter(node.Id, iter);
    
    res.json({
        ok: true
    });

    next();
});

router.get('/position/iter/:iter', express.json(), async function (req, res, next) {
    let iter = req.params.iter;
    let sourceFilePath = `/tmp/node_info/node_pos_${iter}.json`;
    let dstFilePath = "/tmp/node_info/node_pos.json";
    fs.copyFileSync(sourceFilePath, dstFilePath);
    
    res.json({
        ok: true
    });

    next();
});

export = router;