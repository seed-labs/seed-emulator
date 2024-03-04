import dockerode from 'dockerode';
import { LogProducer , ILogObj } from '../interfaces/log-producer';
import { Logger } from 'tslog';
import { Session, SessionManager } from './session-manager';
import * as types from '../../../common/types';

interface ExecutionResult {
    id: number,
    return_value: number,
    output: string
}

/**
 * bgp peer.
 */
export interface BgpPeer {
    /** name of the protocol in bird of the peer. */
    name: string;

    /** state of the protocol itself (up/down/start, etc.) */
    protocolState: string;

    /** state of bgp (established/active/idle, etc.) */
    bgpState: string;
}

// only used to parse the output of seedemu_worker::mytraceroute function
interface TraceRouteResult {
    ttl: number,
    hop: string // an ip address
}

/**
 * controller class.
 * 
 * The controller class offers the ability to control a node with some common
 * operations. The operations are provided by the seedemu_worker script
 * installed to every node by the docker compiler. 
 */
export class Controller implements LogProducer {
    private _logger: Logger<ILogObj>;
    private _sessionManager: SessionManager;

    /** current task id. */
    private _taskId: number;

    /**
     * Callbacks for tasks. The key is task id, and the value is the callback.
     * All tasks are async: the requests need to be written to the container's
     * worker session, and the container will later reply the execution result
     * bound by '_BEGIN_RESULT_' and '_END_RESULT_'. 
     */
    private _unresolvedPromises: { [id: number]: ((result: ExecutionResult) => void)};

    /**
     * message buffers. The key is container id, and the value is buffer.
     * Container's execution results are marked by '_BEGIN_RESULT_' and
     * '_END_RESULT_'. One must wait till '_END_RESULT_' before parsing the
     * execution result. The buffers store to result received so far.
     */
    private _messageBuffer: { [nodeId: string]: string };

    /**
     * Only one task is allowed at a time. If the last task has not returned,
     * all future tasks must wait. This list stores the callbacks to wake
     * waiting tasks handler.
     */
    private _pendingTasks: (() => void)[];

    /**
     * construct controller.
     * 
     * @param docker dockerode object. 
     */
    constructor(docker: dockerode) {
        this._logger = new Logger({ name: 'Controller' });
        this._sessionManager = new SessionManager(docker, 'Controller');
        this._sessionManager.on('new_session', this._listenTo.bind(this));

        this._taskId = 0;
        this._unresolvedPromises = {};
        this._messageBuffer = {};
        this._pendingTasks = [];
    }

    /**
     * attach a listener to a newly created session.
     * 
     * @param nodeId node id.
     * @param session session.
     */
    private _listenTo(nodeId: string, session: Session) {
        this._logger.debug(`got new session for node ${nodeId}; attaching listener...`);

        session.stream.addListener('data', data => {
            var message: string = data.toString('utf-8');
            this._logger.debug(`message chunk from ${nodeId}: ${message}`);

            if (message.includes('_BEGIN_RESULT_')) {
                if (nodeId in this._messageBuffer && this._messageBuffer[nodeId] != '') {
                    this._logger.error(`${nodeId} sents another _BEGIN_RESULT_ while the last message was not finished.`);
                }

                this._messageBuffer[nodeId] = '';
            }

            if (!(nodeId in this._messageBuffer)) {
                this._messageBuffer[nodeId] = message;
            } else {
                this._messageBuffer[nodeId] += message;
            }
            
            if (!this._messageBuffer[nodeId].includes('_END_RESULT_')) {
                this._logger.debug(`message from ${nodeId} is not complete; push to buffer and wait...`);
                return;
            }

            let json = this._messageBuffer[nodeId]?.split('_BEGIN_RESULT_')[1]?.split('_END_RESULT_')[0];

            if (!json) {
                this._logger.warn(`end-of-message seen, but messsage incomplete for node ${nodeId}?`);
                return;
            }

            this._logger.debug(`message from ${nodeId}: "${json}"`);

            // message should be completed by now. parse and resolve.

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

    /**
     * run seedemu worker command on a node.
     * 
     * @param node id of node to run on.
     * @param command command.
     * TODO: maybe make arguments for the command explicit here. 
     *      currently they are a ';' separated field in 'command'
     * @returns execution result.
     */
    private async _run(node: string, command: string): Promise<ExecutionResult> {
        // wait for all pending tasks to finish.
        await this._wait();

        let task = ++this._taskId;

        this._logger.debug(`[task ${task}] running "${command}" on ${node}...`);
        let session = await this._sessionManager.getSession(node, ['/seedemu_worker']);

        session.stream.write(`${task};${command}\r`);

        // create a promise, push the resolve callback to unresolved promises for current id.
        let promise = new Promise<ExecutionResult>((resolve, reject) => {
            this._unresolvedPromises[task] = (result: ExecutionResult) => {
                resolve(result);

                // one or more tasks is waiting for us to finish, let the first in queue know we are done. 
                if (this._pendingTasks.length > 0) {
                    this._pendingTasks.shift()();
                }
            };
        });

        // wait for the listener to invoke the resolve callback.
        let result = await promise;

        this._logger.debug(`[task ${task}] task end:`, result);

        return result;
    }

    /**
     * wait for other tasks, if exist, to finish. return immediately if no
     * other tasks are running.
     */
    private async _wait(): Promise<void> {
        if (Object.keys(this._unresolvedPromises).length == 0) {
            return;
        }

        let promise = new Promise<void>((resolve, reject) => {
            this._pendingTasks.push(resolve);
        });

        return await promise;
    }

    /**
     * change the network connection state of a node.
     * 
     * @param node node id
     * @param connected true to re-connect, false to disconnect.
     */
    async setNetworkConnected(node: string, connected: boolean) {
        this._logger.debug(`setting network to ${connected ? 'connected' : 'disconnected'} on ${node}`);
        await this._run(node, connected ? 'net_up' : 'net_down');
    }

    /** 
     * resolve a coarse SCION interdomain path from 'node' to 'remote'
     * 
     * @param source is the --local IP address to listen on
     * @param sequence SCION hop predicate , what path to use i.e. '1-150#2 1-151#1,2 1-152#1'
     * @param remote SCION address, who to SCMP-ping i.e. 1-152,10.152.0.30 
     *
     */
    async getSCIONTraceroute(node: string, remote: string, sequence: string, source?: string): Promise<types.Path> {
        let path: types.Path;

        let command: string = `sciontraceroute; --sequence "${sequence}" ${remote} `;

        /*if (typeof source !== 'undefined') {
          // check that it is actually a valid ip address here
           command.concat(` --local ${source}`);               
            }       */

        let result = await this._run(node, command);

        if (result.return_value == 0) {
            let hops: types.Segment[] = JSON.parse(result.output);


            path = { segments: hops };

            // TODO: now the frontent datasource can loop over each segment and refine it with the intra-domain hops from getTraceroute()
            // with its address2nodeId() it can translate the addresses of Points to nodeIds which it can then use as a parameter to getTraceroute()
            // The getTraceroute() requests for each segment can run in parallel

            return path;
        } else {
            throw result.output;
        }
    }

    /**
     * @brief do Intra domain IP traceroute from source A to remote B 
     * (for SCION only within the same AS)
     * @param node node id
     * @param remote IP address that the node shall invoke traceroute with
     * @param interf  interface or net-name on which the ICMP echo requests shall be send
     * @param source   source-address that shall be used by the node
     * @returns a list of individual hops from the node to the remote 
     * TODO: maybe add optional ISD, AS parameters, if they are known
     */
    async getTraceroute(node: string, remote: string, source?: string, interf?: string ) : Promise<types.Point[]> {
        this._logger.debug(`to traceroute to remote ${remote} on node ${node}`);

        let points: types.Point[] = [];

        let command: string  =  `traceroute;${remote} `;
        if (typeof source !== 'undefined') {         
            command.concat(` --source ${source}`);
            // add the node itself with TTL of 0
            points.push({ip: source, id: node });
        } else {
            // TODO: find out the ip address through the node-id
            // add the node itself with TTL of 0
            points.push({ id: node });
        }

        if (typeof interf !== 'undefined') {
            command.concat(` --interface ${interf}`);
        }

        let result = await this._run(node,command);        
        let hops: TraceRouteResult[] = JSON.parse(result.output);
        
        // check that  ttl's are continous ( no omissions due to timeout i.e.)       

        // sort ascending by ttl (should be Noop but just to be sure)
        hops.sort((a, b) => { return a.ttl - b.ttl ; });

        let hop2point = function( hop: TraceRouteResult ){ return {ip: hop.hop };};

        points.concat( hops.map(hop2point) );
        
        // check if last hop is the remote, as expected. If not add it.        
        if( points[points.length -1 ].ip !== remote )
        {
            this._logger.debug(`traceroute of node ${node} to remote ${remote} didnt succeed`);
            points.push({ip: remote})
        }

        return points;
    }

    /**
     * get the network connection state of a node. 
     * 
     * @param node node id
     * @returns true if connected, false if not connected.
     */
    async isNetworkConnected(node: string): Promise<boolean> {
        this._logger.debug(`getting network status on ${node}`);

        let result = await this._run(node, 'net_status');

        return result.output.includes('up');
    }

    /**
     * list bgp peers.
     * 
     * @param node node id. this node must be a router node with bird running.
     * @returns list of bgp peers.
     */
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

    /**
     * set bgp peer state.
     * 
     * @param node node id.  this node must be a router node with bird running.
     * @param peer peer protocol name.
     * @param state new state. true to enable, false to disable.
     */
    async setBgpPeerState(node: string, peer: string, state: boolean) {
        this._logger.debug(`setting peer session with ${peer} on ${node} to ${state ? 'enabled' : 'disabled'}...`);

        await this._run(node, `bird_peer_${state ? 'up' : 'down'} ${peer}`);
    }

    getLoggers(): Logger<ILogObj>[] {
        return [this._logger, this._sessionManager.getLoggers()[0]];
    }
}