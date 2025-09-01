import dockerode from 'dockerode';
import {LogProducer} from '../interfaces/log-producer';
import {Logger} from 'tslog';
import * as os from 'os';
import * as path from 'path';
import fs from 'fs';
import tar from 'tar-fs';

export class SubmitEvent implements LogProducer {
    private _logger: Logger;
    private _docker: dockerode;

    constructor(docker: dockerode) {
        this._logger = new Logger({name: 'SubmitEvent'});
        this._docker = docker;
    }

    /**
     * Copy files from the current container to the target container
     * @param sourcePath
     * @param targetContainerId
     * @param targetPath
     */
    async copyToContainerFromCurrentContainer(
        sourcePath: string,
        targetContainerId: string,
        targetPath: string
    ): Promise<void> {
        const targetContainer = this._docker.getContainer(targetContainerId);
        try {
            if (!fs.existsSync(sourcePath)) {
                this._logger.error(`source path ${sourcePath} does not exist`);
                return
            }
            // create tar stream
            const uploadStream = tar.pack(sourcePath);
            // upload
            await targetContainer.putArchive(uploadStream, {
                path: targetPath,
                noOverwriteDirNonDir: false
            });
        } catch (error) {
            this._logger.error('copy failed:', error);
            throw error
        }
    }

    /**
     * Delete the specified file in the container
     * @param containerId
     * @param filePaths The file path to be deleted within the container
     */
    async delFileInContainer(containerId: string, filePaths: string[]): Promise<void> {
        try {
            const container = this._docker.getContainer(containerId);
            // execute the deletion command (use rm -f to force deletion)
            const exec = await container.exec({
                Cmd: ['rm', '-f', ...filePaths],
                AttachStdout: true,
                AttachStderr: true
            });
            // start execution
            const stream = await exec.start({hijack: true, stdin: false});
            // process the output result
            await new Promise((resolve, reject) => {
                this._docker.modem.demuxStream(stream, process.stdout, process.stderr);
                stream.on('end', () => resolve(undefined));
                stream.on('error', (err) => reject(err));
            });
            // check the execution result
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
        // create a temporary folder
        const tempDir = path.join(os.tmpdir(), 'submit-event');
        await fs.promises.mkdir(tempDir, {recursive: true});
        // read the file
        const sourceFilePath = '../module/submit_event.sh'
        if (!fs.existsSync(sourceFilePath)) {
            this._logger.info(`File ${fs.realpathSync(sourceFilePath)} does not exist`);
            return
        }
        const fileContent = fs.readFileSync(sourceFilePath, 'utf8');
        // modify the address (ip+port)
        let modifiedContent = fileContent.replace('ADDRESS', address);

        try {
            await Promise.all(nodes.map(
                async node => {
                    const tempNodeDir = path.join(tempDir, node);
                    await fs.promises.mkdir(tempNodeDir, {recursive: true});
                    // const tempFilePath1 = path.join(tempNodeDir, 'option.json');
                    const tempFilePath2 = path.join(tempNodeDir, 'submit_event.sh');
                    // write to the configuration template file
                    // fs.writeFileSync(tempFilePath1, JSON.stringify({id: node, interval: 300, static: {}, dynamic: {}}));
                    // write to the vis script file
                    const _modifiedContent = modifiedContent.replace('ID', node);
                    fs.writeFileSync(tempFilePath2, _modifiedContent);
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
                    // await this.delFileInContainer(node, ['/option.json', '/submit_event.sh']);
                    await this.delFileInContainer(node, ['/submit_event.sh']);
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