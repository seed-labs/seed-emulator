import path from "path"
import express from 'express';
import {DockerOperation} from '../../../utils/docker-operation';
import {getBaseDir} from '../../../utils/tool';

const router = express.Router();
const dockerOperation = new DockerOperation()
const basePath = getBaseDir()
router.post('/connect', async function (req, res, next) {
    const {host, port} = req.body as { host: string; port: string };

    const docker = await dockerOperation.getDocker()

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

    const docker = await dockerOperation.getDocker();
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
        res.json({ok: false, result: `容器未找到 ${containerNames}`})
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
router.post('/host/exec', async (req, res) => {
    let {cmd} = req.body as { cmd: string }
    const result = await dockerOperation.execOnHost(cmd)
    if (result.ok) {
        res.json({ok: true, result: result.stdout});
    } else {
        res.json({ok: false, result: result.stderr});
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

    const docker = await dockerOperation.getDocker();
    if (!docker) {
        res.json({ok: false, result: "getDocker failed"});
        return
    }
    const containers = await docker.listContainers({all: true})
    const srcId = srcName ? await dockerOperation.getContainerIdByName(docker, containers, srcName) : ''
    const dstId = dstName ? await dockerOperation.getContainerIdByName(docker, containers, dstName) : ''
    let cpRet
    if (srcPath.startsWith("./")) {
        srcPath = path.join(path.resolve(basePath), srcPath);
    }
    if (dstPath.startsWith("./")) {
        srcPath = path.resolve(path.resolve(basePath), dstPath);
    }
    if (srcPath.endsWith("/")) {
        if (!srcName) {
            cpRet = await dockerOperation.copyDirectoryToContainer(docker, dstId, srcPath, dstPath)
        } else if (!dstName) {
            cpRet = await dockerOperation.copyDirectoryFromContainer(docker, srcId, srcPath, dstPath)
        }
    } else {
        if (!srcName) {
            cpRet = await dockerOperation.copyToContainer(docker, dstId, srcPath, dstPath)
        } else if (!dstName) {
            cpRet = await dockerOperation.copyFromContainer(docker, srcId, srcPath, dstPath)
        } else {
            cpRet = await dockerOperation.copyBetweenContainers(docker, srcId, srcPath, dstId, dstPath)
        }
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

    const docker = await dockerOperation.getDocker();
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
export = router;
