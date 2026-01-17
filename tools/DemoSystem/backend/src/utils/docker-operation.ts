import dockerode from 'dockerode';
import {LogProducer} from '../interfaces/log-producer';
import {Logger} from 'tslog';
import {PassThrough, Readable} from 'stream';
import path from 'path';
import fs from 'fs';
import tar from 'tar-stream';
import tarFs from 'tar-fs';
import {exec} from 'child_process';
import {promisify} from 'util';
import yaml from 'js-yaml';
import {replaceRelativePath} from "./tool";

const execAsync = promisify(exec);
const docker = new dockerode();
const HOST_PID = 1;
const SEEDEMU_CONF_FILE_PATH = '/etc/seedemu/seedemu.conf'

interface ExecResult {
    ok: boolean;
    exitCode?: number;
    stdout: string;    // 标准输出（带换行）
    stderr?: string;    // 标准错误（带换行）
    combined?: string;  // 合并的输出（stdout + stderr，带换行）
    error?: string;    // 执行错误信息
}

export interface SeedemuConf {
    condaPath: string;
    demoSystem: {
        hostProjectPath: string
    }
}

export class DockerOperation implements LogProducer {
    private readonly _logger: Logger;
    public seedemuConf: SeedemuConf | null = null;

    constructor() {
        this._logger = new Logger({name: 'Docker'});
    }

    async getDocker() {
        return docker
    }

    async getContainerIdByName(docker: dockerode, containers: dockerode.ContainerInfo[], containerName: string): Promise<string> {
        try {
            if (!containers.length) {
                containers = await docker.listContainers({all: true})
            }

            const containerInfo = containers.find(container =>
                // 注意：容器名称前面会带有 "/" 前缀
                container.Names.some(name => name === `/${containerName}` || name === containerName)
            )

            if (!containerInfo) {
                throw new Error(`容器 "${containerName}" 未找到`)
            }

            // 使用容器ID获取容器对象
            return containerInfo!.Id

        } catch (error) {
            this._logger.error('查找容器失败:', error)
            this._logger.error(`查找容器失败: ${error}`,)
            return ''
        }
    }

    async copyBetweenContainers(
        docker: dockerode,
        sourceContainerId: string,
        sourcePath: string,
        targetContainerId: string,
        targetPath: string
    ): Promise<boolean> {
        let ret = true
        const srcContainer = docker.getContainer(sourceContainerId);
        const targetContainer = docker.getContainer(targetContainerId);
        const targetDir = path.posix.dirname(targetPath);   // 目标目录（容器内部使用 POSIX 路径）
        const targetFile = path.posix.basename(targetPath);
        try {
            // 1. 创建目标目录
            await this.ensureDirectoryExists(targetContainer, targetDir);

            // 2. 从源容器获取文件/目录的 tar 归档
            const archiveStream = await srcContainer.getArchive({
                path: sourcePath
            });

            // 3. 上传归档到目标容器并解压
            await targetContainer.putArchive(archiveStream, {
                path: targetDir,
                noOverwriteDirNonDir: false
            });

            // 4. 如果目标路径与解压后的路径不同，需要重命名
            const sourceFileName = path.posix.basename(sourcePath);
            if (targetPath !== `${targetDir}/${sourceFileName}`) {
                await this.renameFileInContainer(
                    docker,
                    targetContainerId,
                    `${targetDir}/${sourceFileName}`,
                    targetPath
                );
            }

        } catch (error) {
            this._logger.error('copy failed:', error);
            ret = false
        }
        return ret
    }

    /**
     * 确保容器中目录存在
     */
    async ensureDirectoryExists(
        container: dockerode.Container,
        dirPath: string
    ): Promise<void> {
        try {
            const exec = await container.exec({
                Cmd: ['mkdir', '-p', dirPath],
                AttachStdout: true,
                AttachStderr: true
            });

            const stream = await exec.start({});

            await new Promise<void>((resolve, reject) => {
                stream.on('end', resolve);
                stream.on('error', reject);
                // 消耗流数据
                stream.on('data', () => {
                });
            });

            const inspect = await exec.inspect();
            if (inspect.ExitCode !== 0) {
                throw new Error(`创建目录失败: ${dirPath}`);
            }
        } catch (error) {
            this._logger.error(`确保目录存在失败 ${dirPath}:`, error);
            throw error;
        }
    }

    async renameFileInContainer(
        docker: dockerode, containerId: string,
        oldPath: string,
        newPath: string
    ): Promise<boolean> {
        const {ok} = await this.execCmdInContainer(docker, containerId, `test -e ${oldPath}`)
        if (!ok) {
            return false
        }
        const ret = await this.execCmdInContainer(docker, containerId, `mv ${oldPath} ${newPath}`)
        return ret.ok
    }

    async appendToFileWithMarker(
        docker: dockerode, containerId: string,
        filePath: string,
        markedConfig: string,
        signature: string,
    ): Promise<boolean> {
        const appendToCmd = `cat >> "${filePath}" << 'APPEND_EOF'
${markedConfig}
APPEND_EOF`
        let result = await this.checkConfigExists(docker, containerId, filePath, signature)
        if (result) {
            return true
        }
        const {ok} = await this.execCmdInContainer(docker, containerId, appendToCmd)
        return ok
    }

    async checkConfigExists(
        docker: dockerode, containerId: string,
        filePath: string,
        signature: string
    ): Promise<boolean> {
        const checkCmd = `grep -q ${signature} "${filePath}"`;
        const {ok} = await this.execCmdInContainer(docker, containerId, checkCmd)
        return ok
    }

    /**
     * 在容器内复制文件
     */
    async copyFileInContainer(
        container: dockerode.Container,
        sourcePath: string,
        destPath: string
    ): Promise<void> {
        const exec = await container.exec({
            Cmd: ['cp', '-r', sourcePath, destPath],
            AttachStdout: true,
            AttachStderr: true
        });

        const stream = await exec.start({});
        await new Promise<void>((resolve, reject) => {
            stream.on('end', resolve);
            stream.on('error', reject);
            stream.resume();
        });

        const inspect = await exec.inspect();
        if (inspect.ExitCode !== 0) {
            throw new Error(`复制文件失败 ${sourcePath} -> ${destPath}`);
        }
    }

    async processStreamWithOutput(
        docker: dockerode,
        stream: Readable
    ): Promise<{ stdout: string; stderr: string }> {
        return new Promise<{ stdout: string; stderr: string }>((resolve, reject) => {
            // 创建缓冲区
            const stdoutChunks: Buffer[] = [];
            const stderrChunks: Buffer[] = [];

            // 创建分离流
            const stdoutStream = new PassThrough();
            const stderrStream = new PassThrough();

            // 收集数据
            stdoutStream.on('data', (chunk: Buffer) => {
                stdoutChunks.push(chunk);
            });

            stderrStream.on('data', (chunk: Buffer) => {
                stderrChunks.push(chunk);
            });

            // 分离流
            (docker.modem as any).demuxStream(stream, stdoutStream, stderrStream);

            // 同时输出到控制台（可选）
            const outputToConsole = true;
            if (outputToConsole) {
                (docker.modem as any).demuxStream(stream, process.stdout, process.stderr);
            }

            // 监听结束事件
            const onEnd = () => {
                const stdout = Buffer.concat(stdoutChunks).toString('utf8');
                const stderr = Buffer.concat(stderrChunks).toString('utf8');
                resolve({stdout, stderr});
            };

            // 监听错误事件
            const onError = (err: Error) => {
                reject(err);
            };

            // 添加事件监听
            stream.on('end', onEnd);
            stream.on('error', onError);

            // 确保流被消费
            stream.resume();
        });
    }

    async execCmdInContainer(docker: dockerode, containerId: string, cmd: string, detach: boolean = false): Promise<ExecResult> {
        // detach=true 后台运行
        let ret: ExecResult = {ok: true, stdout: ''}
        try {
            const container = docker.getContainer(containerId);
            const exec = await container.exec({
                Cmd: ['sh', '-c', cmd],
                AttachStdout: true,
                AttachStderr: true,
            });
            // start execution
            const stream = await exec.start({hijack: true, stdin: false, Detach: detach});
            if (detach) {
                // 后台运行模式
                ret.ok = true;
                this._logger.info(`容器 ${containerId} 后台执行命令: (${cmd})`);
                return ret;
            }
            const output = await this.processStreamWithOutput(docker, stream);
            const inspectResult = await exec.inspect();
            if (inspectResult.ExitCode !== 0) {
                throw new Error(`执行命令失败: (${cmd}), 退出码: ${inspectResult.ExitCode}`);
            }
            ret.ok = true;
            ret.stdout = output.stdout;
            this._logger.info(`containerId: ${containerId} Successfully exec cmd: (${cmd}), detach: ${detach}`);
        } catch (error) {
            this._logger.warn(`Error exec cmd: (${cmd}), error: ${error}`);
            ret.ok = false
            ret.stderr = `${error}`
        }
        return ret
    }

    async execCmdInContainerWithTimeout(
        docker: dockerode,
        containerId: string,
        cmd: string[],
        timeoutMs: number = 5 * 60 * 1000  // 默认5分钟
    ): Promise<boolean> {
        try {
            const container = docker.getContainer(containerId);

            const exec = await container.exec({
                Cmd: cmd,
                AttachStdout: true,
                AttachStderr: true
            });

            const stream = await exec.start({hijack: true, stdin: false});

            // 收集输出
            let stdout = '';
            let stderr = '';

            const stdoutStream = new PassThrough();
            const stderrStream = new PassThrough();

            docker.modem.demuxStream(stream, stdoutStream, stderrStream);

            stdoutStream.on('data', (chunk: Buffer) => {
                stdout += chunk.toString();
            });

            stderrStream.on('data', (chunk: Buffer) => {
                stderr += chunk.toString();
            });

            // 设置超时
            const executionPromise = new Promise<void>((resolve, reject) => {
                stream.on('end', resolve);
                stream.on('error', reject);
            });

            const timeoutPromise = new Promise<void>((_, reject) => {
                setTimeout(() => reject(new Error('Execution timeout')), timeoutMs);
            });

            // 等待执行完成或超时
            await Promise.race([executionPromise, timeoutPromise]);

            // 检查结果
            const inspectResult = await exec.inspect();

            if (inspectResult.ExitCode !== 0) {
                this._logger.warn(
                    `Command failed in container ${containerId}, ` +
                    `exit code: ${inspectResult.ExitCode}, ` +
                    `stderr: ${stderr}`
                );
                return false;
            }

            this._logger.info(
                `Command executed successfully in container ${containerId}, ` +
                `stdout: ${stdout.substring(0, 200)}...`
            );

            return true;

        } catch (error) {
            this._logger.error(
                `Error executing command in container ${containerId}:`,
                error
            );
            return false;
        }
    }

    /**
     * 从主机复制文件/目录到容器
     */
    async copyToContainer(
        docker: dockerode,
        containerId: string,
        sourcePath: string,
        containerPath: string,
    ): Promise<boolean> {
        try {
            const container = docker.getContainer(containerId);

            // 检查主机路径是否存在
            if (!fs.existsSync(sourcePath)) {
                throw new Error(`路径不存在: ${sourcePath}`);
            }

            const containerDir = path.posix.dirname(containerPath);

            await this.ensureDirectoryExists(container, containerDir);

            // 如果是文件
            const stats = fs.statSync(sourcePath);
            if (stats.isFile()) {
                return await this.copyFileToContainer(docker, containerId, sourcePath, containerPath);
            } else if (stats.isDirectory()) {
                return await this.copyDirectoryToContainer(docker, containerId, sourcePath, containerPath);
            }

            throw new Error(`不支持的路径类型: ${sourcePath}`);

        } catch (error) {
            this._logger.error('复制到容器失败:', error);
            return false;
        }
    }

    /**
     * 复制文件到容器
     */
    async copyFileToContainer(
        docker: dockerode,
        containerId: string,
        hostFilePath: string,
        containerFilePath: string
    ): Promise<boolean> {
        try {
            const container = docker.getContainer(containerId);

            const fileContent = fs.readFileSync(hostFilePath);
            const containerDir = path.posix.dirname(containerFilePath);
            const fileName = path.posix.basename(containerFilePath);

            // 创建 tar 流
            const pack = tar.pack();

            pack.entry({
                name: fileName,
                size: fileContent.length
            }, fileContent);

            pack.finalize();

            // 上传到容器
            await container.putArchive(pack, {
                path: containerDir,
                noOverwriteDirNonDir: false
            });

            this._logger.info(`文件复制成功: ${hostFilePath} -> ${containerFilePath}`);
            return true;

        } catch (error) {
            this._logger.error('复制文件到容器失败:', error);
        }
    }

    async copyDirectoryToContainer(
        docker: dockerode,
        containerId: string,
        hostDirPath: string,
        containerDirPath: string
    ): Promise<boolean> {
        try {
            const container = docker.getContainer(containerId);
            // 使用 tar-fs 创建 tar 流
            const pack = tarFs.pack(hostDirPath, {
                map: (header) => {
                    // 保持相对路径
                    return header;
                }
            });

            // 上传到容器
            await container.putArchive(pack, {
                path: containerDirPath,
                noOverwriteDirNonDir: false
            });

            this._logger.info(`目录复制成功: ${hostDirPath} -> ${containerDirPath}`);
            return true;

        } catch (error) {
            this._logger.error('复制目录到容器失败:', error);
            return false;
        }
    }

    /**
     * 从容器复制文件/目录到主机
     */
    async copyFromContainer(
        docker: dockerode,
        containerId: string,
        containerPath: string,
        sourcePath: string,
    ): Promise<boolean> {
        try {
            // 检查主机目录是否存在，不存在则创建
            const hostDir = path.dirname(sourcePath);
            if (!fs.existsSync(hostDir)) {
                fs.mkdirSync(hostDir, {recursive: true});
            }

            // 获取容器文件信息
            const {ok} = await this.execCmdInContainer(docker, containerId, `test -e ${containerPath}`);
            if (!ok) {
                return false
            }

            const _ret = await this.execCmdInContainer(docker, containerId, `test -d ${containerPath}`);
            const isDir = _ret.ok
            if (isDir) {
                return await this.copyDirectoryFromContainer(docker, containerId, containerPath, sourcePath);
            } else {
                return await this.copyFileFromContainer(docker, containerId, containerPath, sourcePath);
            }

        } catch (error) {
            this._logger.error('从容器复制失败:', error);
            return false;
        }
    }

    /**
     * 从容器复制文件到主机
     */
    async copyFileFromContainer(
        docker: dockerode,
        containerId: string,
        containerFilePath: string,
        hostFilePath: string
    ): Promise<boolean> {
        try {
            const container = docker.getContainer(containerId);
            // 方法1: 使用 Docker API 的 getArchive
            const archiveStream = await container.getArchive({
                path: containerFilePath
            });

            // 提取文件内容
            const extract = tar.extract();
            let fileContent: Buffer | null = null;

            extract.on('entry', (header, stream, next) => {
                const chunks: Buffer[] = [];

                stream.on('data', (chunk) => {
                    chunks.push(chunk);
                });

                stream.on('end', () => {
                    fileContent = Buffer.concat(chunks);
                    next();
                });

                stream.resume();
            });

            extract.on('finish', () => {
                if (fileContent) {
                    fs.writeFileSync(hostFilePath, fileContent);
                }
            });

            // 管道传输
            archiveStream.pipe(extract);

            await new Promise<void>((resolve, reject) => {
                extract.on('finish', resolve);
                extract.on('error', reject);
                archiveStream.on('error', reject);
            });

            this._logger.info(`文件复制成功: ${containerFilePath} -> ${hostFilePath}`);
            return true;

        } catch (error) {
            this._logger.error('使用 getArchive 复制文件失败:', error);
        }
    }

    /**
     * 从容器复制目录到主机
     */
    async copyDirectoryFromContainer(
        docker: dockerode,
        containerId: string,
        containerDirPath: string,
        hostDirPath: string
    ): Promise<boolean> {
        try {
            const container = docker.getContainer(containerId);
            // 获取目录内容
            const archiveStream = await container.getArchive({
                path: containerDirPath
            });

            // 使用 tar-fs 解压
            await new Promise<void>((resolve, reject) => {
                const extract = tarFs.extract(hostDirPath, {
                    ignore: (name) => {
                        // 忽略不需要的文件
                        return false;
                    }
                });

                archiveStream.pipe(extract);

                extract.on('finish', resolve);
                extract.on('error', reject);
                archiveStream.on('error', reject);
            });

            this._logger.info(`目录复制成功: ${containerDirPath} -> ${hostDirPath}`);
            return true;

        } catch (error) {
            this._logger.error('复制目录从容器失败:', error);
        }
    }

    /**
     * 执行原生 Docker 命令（类似 docker ps）
     */
    async execDockerCommand(command: string): Promise<{ stdout: string; stderr: string }> {
        try {
            return await execAsync(`docker ${command}`);
        } catch (error: any) {
            if (error.stdout || error.stderr) {
                return {
                    stdout: error.stdout || '',
                    stderr: error.stderr || ''
                };
            }
            throw new Error(`执行 Docker 命令失败: ${error.message}`);
        }
    }

    /**
     * 执行 Docker Compose 命令
     */
    async execComposeCommand(
        composePath: string,
        command: string,
        serviceName?: string
    ): Promise<{ stdout: string; stderr: string }> {
        let cleanedStdout, cleanedStderr
        try {
            let cmd = `cd ${composePath} && ${command}`;
            if (serviceName) {
                cmd += ` ${serviceName}`;
            }
            const {stdout, stderr} = await execAsync(cmd, {
                timeout: 60000 * 30,
                maxBuffer: 1024 * 1024 * 10 // 10MB buffer
            });
            cleanedStdout = stdout.trim();
            cleanedStderr = stderr.trim();
        } catch (error: any) {
            if (error.stdout || error.stderr) {
                cleanedStdout = error.stdout || ''
                cleanedStderr = error.stderr || ''
            } else {
                throw new Error(`执行 Docker Compose 命令失败: ${error.message}`);
            }
        }
        if (!cleanedStderr.includes("level=warning")) {
            throw new Error(cleanedStderr)
        }
        return {stdout: cleanedStdout, stderr: ''}
    }

    /**
     * 启动指定路径的 Docker Compose 服务
     */
    async composeUp(composePath: string, serviceName?: string): Promise<string> {
        let command = "DOCKER_BUILDKIT=0 docker compose build && docker compose up -d"
        command = serviceName ? `${command} ${serviceName}` : command;
        const result = await this.execComposeCommand(composePath, command);

        if (result.stderr && !result.stderr.includes('Creating')) {
            throw new Error(result.stderr);
        }

        return result.stdout || '服务启动成功';
    }

    /**
     * 停止 Docker Compose 服务
     */
    async composeDown(composePath: string): Promise<string> {
        const command = "docker compose down"
        const result = await this.execComposeCommand(composePath, command);

        if (result.stderr) {
            throw new Error(result.stderr);
        }

        return result.stdout || '服务停止成功';
    }

    async execOnHost(command: string): Promise<ExecResult> {
        const seedemuConf = await this.getHostSeedemuConf()
        command = replaceRelativePath(
            command,
            seedemuConf.demoSystem.hostProjectPath,
            seedemuConf.condaPath,
        )
        command = `nsenter -t ${HOST_PID} -m -u -i -n -p /bin/sh -c "${command}"`;
        this._logger.info(`宿主机执行命令: ${command}`);
        try {
            const _ret = await execAsync(command, {timeout: 60000 * 30})
            return {..._ret, ok: true};
        } catch (error: any) {
            if (error.stdout || error.stderr) {
                return {
                    ok: false,
                    stdout: error.stdout || '',
                    stderr: error.stderr || ''
                };
            }
            return {
                ok: false,
                stdout: '',
                stderr: error.message || ''
            };
        }
    }

    async getHostSeedemuConf(): Promise<SeedemuConf> {
        if (this.seedemuConf === null) {
            const command = `nsenter -t ${HOST_PID} -m -u -i -n -p -- cat ${JSON.stringify(SEEDEMU_CONF_FILE_PATH)}`;
            const {stdout} = await execAsync(command, {timeout: 6000})
            this.seedemuConf = yaml.load(stdout) as SeedemuConf;
        }
        return this.seedemuConf;
    }

    getLoggers(): Logger[] {
        return [this._logger];
    }
}