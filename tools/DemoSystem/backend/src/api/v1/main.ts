import express from 'express';
import {spawn} from "child_process"
import {getLocalIp} from '../../utils/tool';
import dockerRouter from './docker/index';

const router = express.Router();


router.get('/env.js', (req, res, next) => {
    const envVarsForFrontend = {
        CONSOLE: process.env.CONSOLE,
    };
    res.setHeader('Content-Type', 'application/javascript');
    res.send(`window.__ENV__ = ${JSON.stringify(envVarsForFrontend)}`);

    next();
});

router.get('/ip', async function (req, res, next) {
    const ip = getLocalIp()
    const ok = ip !== ''

    res.json({
        ok: ok,
        result: ok ? ip : "getIp failed"
    });

    next();
});

router.post('/run', async (req, res) => {
    const {cmd} = req.body;

    // 更严格的白名单检查
    // const whitelist = ['ls', 'cat', 'pwd', 'whoami', 'docker', 'docker-compose', 'cd', 'echo'];
    // const cmdParts = cmd.trim().split(/\s+/);
    // const cmdName = cmdParts[0];

    // // 检查命令是否在白名单中
    // if (!whitelist.includes(cmdName)) {
    //     return res.status(400).json({
    //         ok: false,
    //         result: `不允许的命令: ${cmdName}`
    //     });
    // }

    // // 安全检查：防止命令注入
    // const allowedDockerCommands = ['ps', 'images', 'version', 'info', 'compose'];
    // if (cmdName === 'docker' || cmdName === 'docker-compose') {
    //     const subCommand = cmdParts[1];
    //     if (!allowedDockerCommands.includes(subCommand) &&
    //         !subCommand?.startsWith('compose')) {
    //         return res.status(400).json({
    //             ok: false,
    //             result: `不允许的Docker子命令: ${subCommand}`
    //         });
    //     }
    // }

    try {
        // 使用 spawn 而不是 exec，支持长时间执行
        const childProcess = spawn('sh', ['-c', cmd], {
            cwd: process.cwd(),
            timeout: 5 * 60 * 1000, // 5分钟超时
            stdio: ['pipe', 'pipe', 'pipe'] // 标准输入、输出、错误
        });

        // 收集输出
        let stdout = '';
        let stderr = '';

        childProcess.stdout.on('data', (data) => {
            stdout += data.toString();
            // 可选：实时流式输出
            // 如果需要实时推送，可以在这里使用 WebSocket 或 Server-Sent Events
        });

        childProcess.stderr.on('data', (data) => {
            stderr += data.toString();
        });

        // 监听进程退出
        const exitCode = await new Promise<number>((resolve, reject) => {
            childProcess.on('close', (code) => {
                resolve(code || 0);
            });

            childProcess.on('error', (error) => {
                reject(error);
            });

            // 可选：设置超时
            setTimeout(() => {
                childProcess.kill('SIGTERM'); // 发送终止信号
                reject(new Error('命令执行超时'));
            }, 10 * 60 * 1000); // 10分钟超时
        });

        if (exitCode === 0) {
            return res.json({
                ok: true,
                result: stdout.trim(),
                // exitCode
            });
        } else {
            return res.status(500).json({
                ok: false,
                result: `命令执行失败: ${stderr.trim() || '未知错误'}`,
            });
        }

    } catch (error: any) {
        return res.status(500).json({
            ok: false,
            result: error.message || '命令执行异常'
        });
    }
});

router.post('/ssh/run', (req, res) => {
    const {host, port = 22, user, keyPath, remoteCmd} = req.body;
    // 示例白名单，仅允许 ls、cat、df 等安全命令
    const allowed = ['ls', 'cat', 'df', 'uptime'];
    const remoteCmdName = remoteCmd.split(' ')[0];
    if (!allowed.includes(remoteCmdName)) {
        return res.status(400).json({error: '不允许的远程命令'});
    }

    // 构造 ssh 参数
    const sshArgs = [
        '-i', keyPath,               // 私钥路径
        '-p', String(port),
        `${user}@${host}`,
        remoteCmd
    ];

    const ssh = spawn('ssh', sshArgs, {cwd: process.cwd()});

    let stdout = '';
    let stderr = '';

    ssh.stdout.on('data', data => (stdout += data.toString()));
    ssh.stderr.on('data', data => (stderr += data.toString()));

    ssh.on('close', code => {
        res.json({code, stdout, stderr});
    });

    ssh.on('error', err => {
        res.status(500).json({error: err.message});
    });
});

router.post('/stream', (req, res) => {
    const {cmd, args = []} = req.body;   // 例如：{ "cmd": "ping", "args": ["-c", "4", "8.8.8.8"] }

    const child = spawn(cmd, args, {cwd: process.cwd()});

    let stdout = '';
    let stderr = '';

    child.stdout.on('data', data => {
        stdout += data.toString();
        // 实时推送给前端（可使用 SSE / WebSocket）
    });

    child.stderr.on('data', data => {
        stderr += data.toString();
    });

    child.on('close', code => {
        res.json({code, stdout, stderr});
    });

    child.on('error', err => {
        res.status(500).json({error: err.message});
    });
});

router.use('/docker', dockerRouter);
export default router;
