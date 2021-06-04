import dockerode from 'dockerode';
import { LogProducer } from '../interfaces/log-producer';
import { Logger } from 'tslog';
import { SessionManager } from './session-manager';

export class Controller implements LogProducer {
    private _logger: Logger;
    private _sessionManager: SessionManager;
    private _netStatus: { [id: string]: boolean };

    constructor(docker: dockerode) {
        this._logger = new Logger({ name: 'Controller' });
        this._sessionManager = new SessionManager(docker, 'Controller');
        this._netStatus = {};
    }

    async setNetworkConnected(node: string, connected: boolean) {
        this._logger.debug(`setting network to ${connected ? 'connected' : 'disconnected'} on ${node}`);

        let session = this._sessionManager.getSession(node, ['/seedemu_worker']);

        (await session).stream.write(`${connected ? 'net_up' : 'net_down'}\r`);

        this._netStatus[node] = connected;
    }

    isNetworkConnected(node: string): boolean {
        return (node in this._netStatus) ? this._netStatus[node] : true;
    }

    getLoggers(): Logger[] {
        return [this._logger, this._sessionManager.getLoggers()[0]];
    }
}