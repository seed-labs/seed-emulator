import { EdgeOptions, NodeOptions } from 'vis-network';
import { BgpPeer, EmulatorNetwork, EmulatorNode } from '../common/types';


export type DataEvent = 'packet' | 'dead';

export interface Vertex extends NodeOptions {
    id: string;
    fixed: boolean;
    label: string;
    group?: string;
    shape?: string;
    x?: number;
    y?: number;
    type: 'node' | 'network';
    object: EmulatorNode | EmulatorNetwork;
}

export interface Edge extends EdgeOptions {
    id?: undefined;
    from: string;
    to: string;
    label?: string;
}

export interface ApiRespond<ResultType> {
    ok: boolean;
    result: ResultType;
}

export interface ConnResult {
    loss: string;
    routes?: string;
}
export interface FilterRespond {
    currentFilter: string;
}

export interface NodeInfo {
    node_count: number;
    node_info: {
        id: number;
        container_id: string;
        ipaddress: string;
        x: number;
        y: number;
        connectivity: {
            id: number;
            container_id: string;
            loss: number;
        }[]; 
    }[];
}

export class DataSource {
    private _apiBase: string;
    private _nodes: EmulatorNode[];
    private _nets: EmulatorNetwork[];

    private _node_info: NodeInfo;

    private _wsProtocol: string;
    private _socket: WebSocket;

    private _connected: boolean;

    private _packetEventHandler: (nodeId: string) => void;
    private _errorHandler: (error: any) => void;

    /**
     * construct new data provider.
     * 
     * @param apiBase api base url.
     * @param wsProtocol websocket protocol (ws/wss), default to ws.
     */
    constructor(apiBase: string, wsProtocol: string = 'ws') {
        this._apiBase = apiBase;
        this._wsProtocol = wsProtocol;
        this._nodes = [];
        this._nets = [];
        this._connected = false;
    }

    /**
     * load data from api.
     * 
     * @param method http method.
     * @param url target url.
     * @param body (optional) request body.
     * @returns api respond object.
     */
    private async _load<ResultType>(method: string, url: string, body: string = undefined): Promise<ApiRespond<ResultType>> {
        let xhr = new XMLHttpRequest();

        xhr.open(method, url);

        if (method == 'POST') {
            xhr.setRequestHeader('Content-Type', 'application/json;charset=UTF-8');
        }

        return new Promise((resolve, reject) => {
            xhr.onload = function () {
                if (this.status != 200) {
                    reject({
                        ok: false,
                        result: 'non-200 response from API.'
                    });

                    return;
                }

                var res = JSON.parse(xhr.response);
                
                if (res.ok) {
                    resolve(res);
                } else {
                    reject(res);
                }
            };

            xhr.onerror = function () {
                reject({
                    ok: false,
                    result: 'xhr failed.'
                });
            }

            xhr.send(body);
        })
    }

    /**
     * get a random color.
     * 
     * @returns hsl color string.
     */
    private _randomColor(): string {
        return `hsl(${Math.random() * 360}, 100%, 75%)`;
    }

    /**
     * connect to api: start listening sniffer socket, load nodes/nets list.
     * call again when connected to reload nodes/nets.
     */
    async get_position() {
        this._node_info = (await this._load<NodeInfo>('GET', `${this._apiBase}/position`)).result;
    }
    // async get_position(path: string) {
    //     this._node_info = (await this._load<NodeInfo>('POST', `${this._apiBase}/position`,
    //                                                         JSON.stringify({path: path}))).result;
    // }


    async connect() {
        this._nodes = (await this._load<EmulatorNode[]>('GET', `${this._apiBase}/container`)).result;
        this._nets = (await this._load<EmulatorNetwork[]>('GET', `${this._apiBase}/network`)).result;

        if (this._connected) {
            return;
        }

        this._socket = new WebSocket(`${this._wsProtocol}://${location.host}${this._apiBase}/sniff`);
        this._socket.addEventListener('message', (ev) => {
            let msg = ev.data.toString();

            let object = JSON.parse(msg);
            if (this._packetEventHandler) {
                this._packetEventHandler(object);
            }
        });

        this._socket.addEventListener('error', (ev) => {
            if (this._errorHandler) {
                this._errorHandler(ev);
            }
        });

        this._socket.addEventListener('close', (ev) => {
            if (this._errorHandler) {
                this._errorHandler(ev);
            }
        });

        this._connected = true;
    }

    /**
     * disconnect sniff socket.
     */
    disconnect() {
        this._connected = false;
        this._socket.close();
    }

    /**
     * get current sniff filter expression.
     * 
     * @returns filter expression.
     */
    async getSniffFilter(): Promise<string> {
        return (await this._load<FilterRespond>('GET', `${this._apiBase}/sniff`)).result.currentFilter;
    }

    /**
     * set sniff filter expression.
     * 
     * @param filter filter expression.
     * @returns updated filter expression.
     */
    async setSniffFilter(filter: string): Promise<string> {
        return (await this._load<FilterRespond>('POST', `${this._apiBase}/sniff`, JSON.stringify({ filter }))).result.currentFilter;
    }

    /**
     * get list of bgp peers of the given node.
     * 
     * @param node node id. must be node with router role.
     * @returns list of peers.
     */
    async getBgpPeers(node: string): Promise<BgpPeer[]> {
        return (await this._load<BgpPeer[]>('GET', `${this._apiBase}/container/${node}/bgp`)).result;
    }

    /**
     * set bgp peer state.
     * 
     * @param node node id. must be node with router role.
     * @param peer peer name.
     * @param up protocol state, true = up, false = down.
     */
    async setBgpPeers(node: string, peer: string, up: boolean) {
        await this._load('POST', `${this._apiBase}/container/${node}/bgp/${peer}`, JSON.stringify({ status: up }));
    }

    /**
     * get network state of the given node.
     * 
     * @param node node id.
     * @returns true if up, false if down.
     */
    async getNetworkStatus(node: string): Promise<boolean> {
        return (await this._load<boolean>('GET', `${this._apiBase}/container/${node}/net`)).result;
    }

    /**
     * set network state of the given node.
     * 
     * @param node node id.
     * @param up true if up, false if down.
     */
    async setNetworkStatus(node: string, up: boolean) {
        await this._load('POST', `${this._apiBase}/container/${node}/net`, JSON.stringify({ status: up }));
    }

    /**
     * set network state of the given node.
     * 
     * @param node node id.
     * @param ip true if up, false if down.
     */
    async setMobileConnect(node: string, ip: string) {
        return (await this._load<boolean>('GET', `${this._apiBase}/container/${node}/connect/${ip}`)).result;
    }

    /**
     * set network state of the given node.
     * 
     * @param node node id.
     * @param ip true if up, false if down.
     */
    async setTrafficControl(node: string, dst_ip: string, distance:string) {
        return (await this._load<boolean>('GET', `${this._apiBase}/container/${node}/tc/${dst_ip}/${distance}`)).result;
    }

    /**
     * start network connectivity test from the given node to the given dst ip.
     * 
     * @param node node id.
     * @param dst_ip true if up, false if down.
     */
    async startConnTest(node: string, dst_ip: string) {
        return (await this._load<ConnResult>('GET', `${this._apiBase}/container/${node}/connectivity/${dst_ip}`)).result;
    }

    /**
     * event handler register.
     * 
     * @param eventName event to listen.
     * @param callback callback.
     */
    on(eventName: DataEvent, callback?: (data: any) => void) {
        switch(eventName) {
            case 'packet':
                this._packetEventHandler = callback;
                break;
            case 'dead':
                this._errorHandler = callback;
        }
    }

    get edges(): Edge[] {
        var edges: Edge[] = [];

        this._nodes.forEach(node => {
            let nets = node.NetworkSettings.Networks;
            Object.keys(nets).forEach(key => {
                let net = nets[key];
                var label = '';

                node.meta.emulatorInfo.nets.forEach(emunet => {
                    // fixme
                    if (key.includes(emunet.name)) {
                        label = emunet.address;
                    }
                });
                edges.push({
                    from: node.Id,
                    to: net.NetworkID,
                    label
                });
            })
        })

        return edges;
    }
    
    nodeIdByIp(ip:string): string {
        console.log("search keyword", ip);
        var found = "";
        this._node_info.node_info.forEach(node=>{
            console.log("searching", node.ipaddress);
            if(node.ipaddress.split(".")[3] == ip.split(".")[3]){
                found = node.container_id;
            }
        })
        return found;
    }
    get mEdges(): Edge[] {
        var edges: Edge[] = [];

        this._node_info.node_info.forEach(node=>{
            node.connectivity.forEach(connection=>{
                var connectivity=0;
                if (connection.loss==0){
                    connectivity = 5
                }else if (connection.loss==20){
                    connectivity = 4
                }else if (connection.loss==40) {
                    connectivity = 3
                } else if (connection.loss==60) {
                    connectivity = 2
                } else if (connection.loss==80) {
                    connectivity = 1
                } else {
                    return
                }
                edges.push({
                    from: node.container_id,
                    to: connection.container_id,
                    width: connectivity,
                    label: connection.loss + "% loss"
                })
            })
            
        })

        this._nodes.forEach(node => {
            let nets = node.NetworkSettings.Networks;
            Object.keys(nets).forEach(key => {
                let net = nets[key];
                var label = '';

                node.meta.emulatorInfo.nets.forEach(emunet => {
                    // fixme
                    if (key.includes(emunet.name)) {
                        label = emunet.address;
                    }
                });
                edges.push({
                    from: node.Id,
                    to: net.NetworkID,
                    label
                });
            })
        })

        return edges;
    }

    get vertices(): Vertex[] {
        var vertices: Vertex[] = [];

        this._nodes.forEach(node => {
            var nodeInfo = node.meta.emulatorInfo;
            var vertex: Vertex = {
                id: node.Id,
                fixed: true,
                label: nodeInfo.displayname ?? `${nodeInfo.asn}/${nodeInfo.name}`,
                type: 'node',
                shape: nodeInfo.role == 'Router' ? 'dot' : 'hexagon',
                object: node
            };
            this._node_info.node_info.find(node=>{
                if(node.ipaddress == nodeInfo.nets[0].address.split('/')[0]){
                    vertex.x = node.x * 2;
                    vertex.y = node.y * 2;
                }
            })
            
            if (nodeInfo.role == 'Router') {
                vertices.push(vertex);
            }

            
        });

        return vertices;
    }

    get groups(): Set<string> {
        var groups = new Set<string>();

        this._nets.forEach(net => {
            groups.add(net.meta.emulatorInfo.scope);
        });

        this._nodes.forEach(node => {
            groups.add(node.meta.emulatorInfo.asn.toString());
        })

        return groups;
    }
}