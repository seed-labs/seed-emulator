import express from 'express';
import { SocketHandler } from '../../utils/socket-handler';
import dockerode from 'dockerode';
import { SeedContainerInfo, Emulator, SeedNetInfo } from '../../utils/seedemu-meta';
import { Sniffer } from '../../utils/sniffer';
import WebSocket from 'ws';
import { Controller } from '../../utils/controller';
import {SCIONAddress} from '../../../../common/scion';
import { IPv4 ,IPv6} from "ip-num/IPNumber";
import * as types from '../../../../common/types';
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

socketHandler.getLoggers().forEach(logger => logger.settings.minLevel=4 );

sniffer.getLoggers().forEach(logger => logger.settings.minLevel=4);

controller.getLoggers().forEach(logger => logger.settings.minLevel=4);

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

/*
Example for scion/S03-bandwidth-test 
    curl -H "Accept: application/json"
    http://localhost:8080/api/v1/traceroute/abafb9f7c4b1/scion/?path=1-150%232%201-151%231%2C2%201-152%231\&remote=1-152%2C10.152.0.30
Response Body:
{"ok":true,
  "result":
  {"segments":
  [ {"from": {"id": abafb9f7c4b1}, "to": {"isd":1,"asn":150,"ip":"10.0.0.1"} },
    {"from": {"isd":1,"asn":150,"ip":"10.0.0.1"},"to": {"isd":1,"asn":151,"ip":"10.0.0.2"} },
    {"from": {"isd":1,"asn":151,"ip":"10.0.0.2"},"to": {"isd":1,"asn":151,"ip":"10.0.0.2"} },
    {"from": {"isd":1,"asn":151,"ip":"10.0.0.2"},"to": {"isd":1,"asn":152,"ip":"10.0.0.3"} },
    {"from": {"isd":1,"asn":152,"ip":"10.0.0.3"},"to": {"isd":1,"asn":152,"ip":"10.152.0.30"} }
  ]
  }
}   
    ?remote=1-152%2C10.152.0.30 -> 1-152,10.152.0.30  // who to SCMP-ping
    ?sequence ?path=1-150%232%201-151%231%2C2%201-152%231  -> [1-150#2 1-151#1,2 1-152#1 ] // on what SCION-path
*/
router.get('/traceroute/:id/scion/', async function (req, res, next) {
    let id = req.params.id;
    let remote : any;
    let scion_remote: SCIONAddress | undefined;
    let path: any;

    if("path" in req.query )
    {
        path = req.query.path;
    }
    if("remote" in req.query )
    {
        remote = req.query.remote;
    }
    // check if remote is a valid SCION address, and return error if not
    try {       
        scion_remote =  SCIONAddress.fromStr(remote);
    } catch (err) {
        res.json({
            ok: false,
            result: `invalid traceroute parameter: ${err}`
        });
        next();
        return;
    }

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
   

    try {
        let p: types.Path = await controller.getSCIONTraceroute(node.Id, remote ,path );

        //TODO:  add source ip here if given
        //       parse ASN from first hop in path
        p.segments.unshift({from: {id: id }, to: p.segments[0].from } );
    
        p.segments.push( {from: p.segments[p.segments.length-1].to , to: {ip: scion_remote.getIP().toString(), isd: scion_remote.getIA()[0], asn: scion_remote.getIA()[1] } } );
        res.json({
            ok: true,
            result: p
        });
    
        next();
     

    } catch (err) {
        res.json({
            ok: false,
            result: `Error: ${err}`
        });
        next();
        return;
    }

    
});

/*
Example from scion/S03-bandwidth-test: Host 10.150.0.30 (container 'abafb9f7c4b1' ) resolving the hops to its ControlService 10.150.0.71
curl -H "Accept: application/json" http://localhost:8080/api/v1/traceroute/abafb9f7c4b1/v4/10.150.0.71?source=10.150.0.30

Response Body:
{"ok":true,
"result":[ {"ip":"10.150.0.30"},
           {"ip":"10.150.0.71"}
        ]
}
// -> single hop, since they both are on the same net
*/
router.get('/traceroute/:id/v4/:remote', async function (req, res, next) {
    let id = req.params.id;
    let remote = req.params.remote;
    let source: any;
    // check if remote is a valid IPv4 address, and return error if not
    try {
        let ip4: IPv4 = IPv4.fromDecimalDottedString(remote);
    } catch (err) {
        res.json({
            ok: false,
            result: `invalid traceroute parameter: ${err}`
        });
        next();
        return;
    }
    if( "source" in req.query)
    {       
        source = req.query.source;     
    }

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
        result: await controller.getTraceroute(node.Id, remote,source)
    });

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