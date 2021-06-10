import dockerode from 'dockerode';
import { LogProducer } from '../interfaces/log-producer';
import { Logger } from 'tslog';
import { Session, SessionManager } from './session-manager';

interface ExecutionResult {
    id: number,
    return_value: number,
    output: string
}

export interface BgpPeer {
    name: string;
    protocolState: string;
    bgpState: string;
}

export class Controller implements LogProducer {
    private _logger: Logger;
    private _sessionManager: SessionManager;

    private _taskId: number;
    private _unresolvedPromises: { [id: number]: ((result: ExecutionResult) => void)};
    private _messageBuffer: { [nodeId: string]: string };

    constructor(docker: dockerode) {
        this._logger = new Logger({ name: 'Controller' });
        this._sessionManager = new SessionManager(docker, 'Controller');
        this._sessionManager.on('new_session', this._listenTo.bind(this));

        this._taskId = 0;
        this._unresolvedPromises = {};
        this._messageBuffer = {};
    }

    private _listenTo(nodeId: string, session: Session) {
        this._logger.debug(`got new session for node ${nodeId}; attaching listener...`);

        session.stream.addListener('data', data => {
            var message: string = data.toString('utf-8');
            this._logger.debug(`message chunk from ${nodeId}: ${message}`);
            if (!(nodeId in this._messageBuffer)) {
                this._messageBuffer[nodeId] = message;
            } else {
                this._messageBuffer[nodeId] += message;
            }
            
            if (!this._messageBuffer[nodeId].includes('_END_RESULT_')) {
                this._logger.debug(`message from ${nodeId} is not complete; push to buffer and wait...`);
                return;
            }

            let json = this._messageBuffer[nodeId].split('_BEGIN_RESULT_')[1].split('_END_RESULT_')[0];

            this._logger.debug(`message from ${nodeId}: "${json}"`);

            try {
                let result = JSON.parse(json) as ExecutionResult;

                if (result.id in this._unresolvedPromises) {
                    this._unresolvedPromises[result.id](result);
                    delete this._unresolvedPromises[result.id];
                } else {
                    this._logger.warn(`unknow task id ${result.id} from node ${nodeId}: `, result);
                }
            } catch (e) {
                this._logger.warn(`error decoding message from ${nodeId}: `, e);
            }

            this._messageBuffer[nodeId] = '';
        });
    }

    private async _run(node: string, command: string): Promise<ExecutionResult> {
        let task = ++this._taskId;

        this._logger.debug(`[task ${task}] running "${command}" on ${node}...`);
        let session = await this._sessionManager.getSession(node, ['/seedemu_worker']);

        session.stream.write(`${task};${command}\r`);

        let promise = new Promise<ExecutionResult>((resolve, reject) => {
            this._unresolvedPromises[task] = resolve;
        });

        let result = await promise;

        this._logger.debug(`[task ${task}] task end:`, result);

        return result;
    }

    async setNetworkConnected(node: string, connected: boolean) {
        this._logger.debug(`setting network to ${connected ? 'connected' : 'disconnected'} on ${node}`);
        await this._run(node, connected ? 'net_up' : 'net_down');
    }

    async isNetworkConnected(node: string): Promise<boolean> {
        this._logger.debug(`getting network status on ${node}`);

        let result = await this._run(node, 'net_status');

        return result.output.includes('up');
    }

    async listBgpPeers(node: string): Promise<BgpPeer[]> {
        // potential crash when running on non-router node?

        this._logger.debug(`getting bgp peers on ${node}...`);

        let result = await this._run(node, 'bird_list_peer');

        let lines = result.output.split('\n').map(s => s.split(/\s+/));

        var peers: BgpPeer[] = [];

        lines.forEach(line => {
            if (line.length < 6) {
                return;
            }
            peers.push({
                name: line[0],
                protocolState: line[3],
                bgpState: line[5]
            });
        });

        this._logger.debug(`parsed bird output: `, lines, peers);

        return peers;
    }

    async setBgpPeerState(node: string, peer: string, state: boolean) {
        this._logger.debug(`setting peer session with ${peer} on ${node} to ${state ? 'enabled' : 'disabled'}...`);

        await this._run(node, `bird_peer_${state ? 'up' : 'down'} ${peer}`);
    }

    getLoggers(): Logger[] {
        return [this._logger, this._sessionManager.getLoggers()[0]];
    }
}