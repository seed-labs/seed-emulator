import dockerode from 'dockerode';
import {LogProducer} from '../interfaces/log-producer';
import {Logger} from 'tslog';
import * as os from 'os';
import * as path from 'path';
import fs from 'fs';
import tar from 'tar-fs';
import stream from 'stream';

export class SubmitEvent implements LogProducer {
    private _logger: Logger;
    private _docker: dockerode;

    constructor(docker: dockerode) {
        this._logger = new Logger({name: 'SubmitEvent'});
        this._docker = docker;
    }

    /**
     * 从当前容器复制文件到目标容器
     * @param sourcePath 源路径（当前容器内绝对路径）
     * @param targetContainerId 目标容器ID
     * @param targetPath 目标路径（目标容器内绝对路径）
     */
    async copyToContainerFromCurrentContainer(
        sourcePath: string,
        targetContainerId: string,
        targetPath: string
    ): Promise<void> {
        // 获取容器对象
        const targetContainer = this._docker.getContainer(targetContainerId);
        try {
            // 2. 检查文件夹是否存在
            if (!fs.existsSync(sourcePath)) {
                this._logger.error(`源容器文件夹 ${sourcePath} 不存在`);
                return
            }
            // 3. 创建tar流
            const uploadStream = tar.pack(sourcePath);
            // 上传到目标容器
            await targetContainer.putArchive(uploadStream, {
                path: targetPath,
                noOverwriteDirNonDir: false
            });
        } catch (error) {
            this._logger.error('复制过程中出错:', error);
            throw error
        }
    }

    /**
     * 将文件或文件夹从主机复制到容器
     * @param {string} containerId - 目标容器ID或名称
     * @param {string} hostPath - 主机上的文件/文件夹路径
     * @param {string} containerPath - 容器内的目标路径
     * @returns {Promise<void>}
     */
    async copyToContainerFromHost(
        hostPath: string,
        containerId: string,
        containerPath: string,
    ) {
        try {
            // 1. 获取容器实例
            const container = this._docker.getContainer(containerId);
            // 2. 检查文件夹是否存在
            if (!fs.existsSync(hostPath)) {
                this._logger.error(`主机文件夹 ${hostPath} 不存在`);
                return
            }
            // 3. 创建tar流
            const tarStream = tar.pack(hostPath);
            // 4. 上传到容器
            await container.putArchive(tarStream, {
                path: containerPath,
                noOverwriteDirNonDir: false
            });
        } catch (error) {
            this._logger.error('复制文件夹到容器失败:', error);
            throw error;
        }
    }

    /**
     * 删除容器中的指定文件
     * @param containerId 容器ID或名称
     * @param filePaths 容器内要删除的文件路径
     */
    async delFileInContainer(containerId: string, filePaths: string[]): Promise<void> {
        try {
            // 获取容器对象
            const container = this._docker.getContainer(containerId);
            // 执行删除命令 (使用 rm -f 强制删除)
            const exec = await container.exec({
                Cmd: ['rm', '-f', ...filePaths],
                AttachStdout: true,
                AttachStderr: true
            });

            // 启动执行
            const stream = await exec.start({hijack: true, stdin: false});

            // 处理输出结果
            await new Promise((resolve, reject) => {
                this._docker.modem.demuxStream(stream, process.stdout, process.stderr);

                stream.on('end', () => resolve(undefined));
                stream.on('error', (err) => reject(err));
            });

            // 检查执行结果
            const inspectResult = await exec.inspect();
            if (inspectResult.ExitCode !== 0) {
                throw new Error(`Failed to delete file, exit code: ${inspectResult.ExitCode}`);
            }

            this._logger.info(`containerId: ${containerId} Successfully deleted file: ${filePaths}`);
        } catch (error) {
            this._logger.error('Error deleting file:', error);
            throw error;
        }
    }

    async submitEvent(address: string, nodes: string[], type: 'install' | 'uninstall'): Promise<any> {
        let ret = false;
        switch (type) {
            case 'install':
                ret = await this._install(address, nodes);
                break
            case 'uninstall':
                ret = await this._uninstall(address, nodes);
                break
            default:
                this._logger.debug(`submit event type error: ${type}`);
                break
        }

        return ret;
    }

    async _install(address: string, nodes: string[]) {
        let ret = true;

        this._logger.debug(`submit event install on ${nodes}...`);
        // 创建临时文件夹
        const tempDir = path.join(os.tmpdir(), 'submit-event');
        await fs.promises.mkdir(tempDir, {recursive: true});

        // 3. 读取指定文件
        const sourceFilePath = '../module/submit_event.sh'
        if (!fs.existsSync(sourceFilePath)) {
            this._logger.info(`${fs.realpathSync(sourceFilePath)} 文件不存在`);
            return
        }
        const fileContent = fs.readFileSync(sourceFilePath, 'utf8');

        // 4. 修改地址 ip+port
        let modifiedContent = fileContent.replace('ADDRESS', address);

        try {
            await Promise.all(nodes.map(
                async node => {
                    const tempNodeDir = path.join(tempDir, node);
                    await fs.promises.mkdir(tempNodeDir, {recursive: true});
                    const tempFilePath1 = path.join(tempNodeDir, 'option.json');
                    const tempFilePath2 = path.join(tempNodeDir, 'submit_event.sh');
                    // 写入vis 配置模板文件
                    fs.writeFileSync(tempFilePath1, JSON.stringify({id: node, interval: 300, static: {}, dynamic: {}}));
                    // 写入vis 脚本文件
                    const _modifiedContent = modifiedContent.replace('ID', node);
                    fs.writeFileSync(tempFilePath2, _modifiedContent);
                    // await this.copyToContainerFromHost(tempNodeDir, node, '/')
                    await this.copyToContainerFromCurrentContainer(tempNodeDir, node, '/');
                }
            ));
        } catch (error) {
            this._logger.error('Error submit event install: ', error);
            ret = false
        } finally {
            await fs.promises.rm(tempDir, {recursive: true, force: true});
        }
        return ret;
    }

    async _uninstall(address: string, nodes: string[]) {
        let ret = true;
        this._logger.debug(`submit event uninstall on ${nodes}...`);

        try {
            await Promise.all(nodes.map(
                async node => {
                    await this.delFileInContainer(node, ['/option.json', '/submit_event.sh']);
                }
            ));
        } catch (error) {
            this._logger.error('Error submit event uninstall: ', error);
            ret = false
        }
        return ret;
    }

    getLoggers(): Logger[] {
        return [this._logger];
    }
}