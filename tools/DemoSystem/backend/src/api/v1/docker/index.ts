import path from "path"
import express from 'express';
import {DockerOptions} from 'dockerode';
import {DockerOperation} from '../../../utils/docker-operation';
import {getBaseDir} from '../../../utils/tool';

const router = express.Router();
const dockerOperation = new DockerOperation()

const basePath = getBaseDir()

router.post('/connect', async function (req, res, next) {
    const {host, port} = req.body as { host: string; port: string };

    const docker = await dockerOperation.getDocker({
        host, port, protocol: 'http'
    } as DockerOptions)

    const ok = docker !== null

    res.json({
        ok: ok,
        result: ok ? "" : "connect failed"
    });

    next();
});

router.post('/exec', async (req, res) => {
    let {host, port, containerIds, containerNames, cmd, detach} = req.body as {
        host: string;
        port: string,
        containerIds: string[];
        containerNames: string[];
        cmd: string,
        detach: boolean
    };

    const docker = await dockerOperation.getDocker({host, port, protocol: 'http'} as DockerOptions);
    if (!docker) {
        res.json({ok: false, result: "getDocker failed"});
        return
    }
    const containers = await docker.listContainers({all: true})
    if (!containerIds.length) {
        containerIds = (await Promise.all(
            containerNames.map(async name => await dockerOperation.getContainerIdByName(docker, containers, name))
        )).filter(id => id !== "")
    }
    if (!containerIds.length) {
        dockerOperation.execDockerCommand(cmd).then(r => {
            res.json({ok: true, result: r.stdout})
        }).catch(err => {
            res.json({ok: false, result: err.message})
        })
        return
    }
    await Promise.all(
        containerIds.map(id =>
            dockerOperation.execCmdInContainer(docker, id, `pkill -f "${cmd}"`, false)
        )
    );

    const execPromises = containerIds.map(id =>
        dockerOperation.execCmdInContainer(docker, id, cmd, !!detach)
            .then(result => ({id, success: true, output: result.stdout}))
            .catch(err => ({id, success: false, output: err}))
    );

    const results = await Promise.all(execPromises);
    const succeeded = results.filter(r => r.success).map(r => ({
        id: r.id,
        output: r.output
    }));
    const failed = results.filter(r => !r.success).map(r => ({
        id: r.id,
        output: r.output
    }));
    if (failed.length) {
        res.json({ok: false, result: JSON.stringify({succeeded, failed})});
        return
    }
    res.json({ok: true, result: JSON.stringify({succeeded, failed})});
});

router.post('/compose/exec', async (req, res) => {
    let {host, port, composePath, cmd, pythonFile} = req.body as {
        host: string;
        port: string,
        composePath: string,
        cmd: string,
        pythonFile: string,
    };

    const docker = await dockerOperation.getDocker({host, port, protocol: 'http'} as DockerOptions);
    if (!docker) {
        res.json({ok: false, result: "getDocker failed"});
        return
    }
    try {
        composePath = path.join(basePath, composePath)
        switch (cmd) {
            case "composeUp":
                await dockerOperation.composeUp(composePath, pythonFile)
                break
            case "composeDown":
                await dockerOperation.composeDown(composePath)
                break
            default:
                throw new Error(`暂不支持的命令: ${cmd}`)
        }
        res.json({ok: true, result: ''});
    } catch (e) {
        res.json({ok: false, result: e.message as string})
    }
});

router.post('/exec/cp', async (req, res) => {
    let {host, port, srcName, dstName, srcPath, dstPath} = req.body as {
        host: string;
        port: string,
        srcName: string,
        dstName: string,
        srcPath: string,
        dstPath: string,
    };

    const docker = await dockerOperation.getDocker({host, port, protocol: 'http'} as DockerOptions);
    if (!docker) {
        res.json({ok: false, result: "getDocker failed"});
        return
    }
    const containers = await docker.listContainers({all: true})
    const srcId = srcName === '' ? '' : await dockerOperation.getContainerIdByName(docker, containers, srcName)
    const dstId = dstName === '' ? '' : await dockerOperation.getContainerIdByName(docker, containers, dstName)
    let cpRet
    if (srcPath.startsWith("./")) {
        srcPath = path.join(path.resolve(basePath), srcPath);
    }
    if (dstPath.startsWith("./")) {
        srcPath = path.resolve(path.resolve(basePath), dstPath);
    }
    if (srcName === '') {
        cpRet = await dockerOperation.copyToContainer(docker, dstId, srcPath, dstPath)
    } else if (dstName === '') {
        cpRet = await dockerOperation.copyFromContainer(docker, srcId, srcPath, dstPath)
    } else {
        cpRet = await dockerOperation.copyBetweenContainers(docker, srcId, srcPath, dstId, dstPath)
    }
    if (cpRet) {
        res.json({ok: true, result: ''});
    } else {
        res.json({ok: false, result: 'cp failed'});
    }
});

router.post('/exec/append', async (req, res) => {
    let {host, port, containerIds, containerNames, filepath, content, signature} = req.body as {
        host: string;
        port: string,
        containerIds: string[];
        containerNames: string[];
        filepath: string,
        content: string,
        signature: string,
    };

    const docker = await dockerOperation.getDocker({host, port, protocol: 'http'} as DockerOptions);
    if (!docker) {
        res.json({ok: false, result: "getDocker failed"});
        return
    }
    const containers = await docker.listContainers({all: true})
    if (!containerIds.length) {
        containerIds = (await Promise.all(
            containerNames.map(async name => await dockerOperation.getContainerIdByName(docker, containers, name))
        )).filter(id => id !== "")
    }

    const execPromises = containerIds.map(id =>
        dockerOperation.appendToFileWithMarker(docker, id, filepath, content, signature)
            .then(result => ({id, success: result}))
            .catch(err => ({id, success: false, error: err}))
    );

    const results = await Promise.all(execPromises);
    const succeeded = results.filter(r => r.success).map(r => r.id);
    const failed = results.filter(r => !r.success).map(r => ({
        id: r.id,
        error: (r as any).error
    }));
    if (failed.length) {
        res.json({ok: false, result: JSON.stringify({succeeded, failed})});
        return
    }
    res.json({ok: true, result: JSON.stringify({succeeded, failed})});
});

router.post('/exec/rename', async (req, res) => {
    let {host, port, containerIds, containerNames, oldPath, newPath} = req.body as {
        host: string;
        port: string,
        containerIds: string[];
        containerNames: string[];
        oldPath: string,
        newPath: string
    };

    const docker = await dockerOperation.getDocker({host, port, protocol: 'http'} as DockerOptions);
    if (!docker) {
        res.json({ok: false, result: "getDocker failed"});
        return
    }
    const containers = await docker.listContainers({all: true})
    if (!containerIds.length) {
        containerIds = (await Promise.all(
            containerNames.map(async name => await dockerOperation.getContainerIdByName(docker, containers, name))
        )).filter(id => id !== "")
    }

    const execPromises = containerIds.map(id =>
        dockerOperation.renameFileInContainer(docker, id, oldPath, newPath)
            .then(result => ({id, success: result}))
            .catch(err => ({id, success: false, error: err}))
    );

    const results = await Promise.all(execPromises);
    const succeeded = results.filter(r => r.success).map(r => r.id);
    const failed = results.filter(r => !r.success).map(r => ({
        id: r.id,
        error: (r as any).error
    }));
    if (failed.length) {
        res.json({ok: false, result: JSON.stringify({succeeded, failed})});
        return
    }
    res.json({ok: true, result: JSON.stringify({succeeded, failed})});
});
export = router;
