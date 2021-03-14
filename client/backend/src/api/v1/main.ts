import express from 'express';
import { SocketHandler } from '../../utils/socket-handler';
import dockerode from 'dockerode';
import { Simulator } from '../../utils/seedsim-meta';

const router = express.Router();
const docker = new dockerode();
const socketHandler = new SocketHandler(docker);

socketHandler.getLoggers().forEach(logger => logger.setSettings({
    minLevel: 'debug'
}));

router.get('/container', async function(req, res, next) {
    try {
        var containers: any[] = await docker.listContainers();

        containers.map(c => {
            c.meta = {
                hasSession: socketHandler.getSessionManager().hasSession(c.Id),
                nodeInfo: Simulator.ParseMeta(c.Labels)
            };
        });

        // filter out undefine (not our nodes)
        containers = containers.filter(c => c.nodeInfo.name);

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
            nodeInfo: Simulator.ParseMeta(result.Labels)
        };
        res.json({
            ok: true, result
        });
    }

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

export = router;