import { EdgeOptions, NodeOptions } from 'vis-network';
import { EmulatorNetwork, EmulatorNode } from '../common/types';

export type DataEvent = 'packet';

export interface Vertex extends NodeOptions {
    id: string;
    label: string;
    group?: string;
    shape?: string;
    type: 'node' | 'network';
    object: EmulatorNode | EmulatorNetwork;
}

export interface Edge extends EdgeOptions {
    id?: undefined;
    from: string;
    to: string;
    label?: string;
}

export class DataSource {
    private _apiBase: string;
    private _nodes: EmulatorNode[];
    private _nets: EmulatorNetwork[];

    private _wsProtocol: string;
    private _socket: WebSocket;

    private _connected: boolean;

    private _packetEventHandler: (nodeId: string) => void;

    constructor(apiBase: string, wsProtocol: string = 'ws') {
        this._apiBase = apiBase;
        this._wsProtocol = wsProtocol;
        this._nodes = [];
        this._nets = [];
        this._connected = false;
    }

    private async _load(method: string, url: string, body: string = undefined): Promise<any> {
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
                
                if (res.ok) resolve(res);
                else reject(res);
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

    async connect() {
        this._nodes = (await this._load('GET', `${this._apiBase}/container`)).result;
        this._nets = (await this._load('GET', `${this._apiBase}/network`)).result;

        if (this._connected) {
            return;
        }

        this._socket = new WebSocket(`${this._wsProtocol}://${location.host}${this._apiBase}/sniff`);
        this._socket.addEventListener('message', (ev) => {
            let object = JSON.parse(ev.data.toString());
            if (this._packetEventHandler) {
                this._packetEventHandler(object);
            }
        });

        this._connected = true;
    }

    disconnect() {
        this._connected = false;
        this._socket.close();
    }

    async getSniffFilter(): Promise<string> {
        return (await this._load('GET', `${this._apiBase}/sniff`)).result.currentFilter;
    }

    async setSniffFilter(filter: string): Promise<string> {
        return (await this._load('POST', `${this._apiBase}/sniff`, JSON.stringify({ filter }))).result.currentFilter;
    }

    on(eventName: DataEvent, callback?: (data: any) => void) {
        switch(eventName) {
            case 'packet':
                this._packetEventHandler = callback;
                break;
        }
    }

    get edges(): Edge[] {
        var edges: Edge[] = [];

        this._nodes.forEach(node => {
            let nets = node.NetworkSettings.Networks;
            Object.keys(nets).forEach(key => {
                let net = nets[key];
                edges.push({
                    from: node.Id,
                    to: net.NetworkID
                });
            })
        })

        return edges;
    }

    get vertices(): Vertex[] {
        var vertices: Vertex[] = [];

        this._nets.forEach(net => {
            var netInfo = net.meta.emulatorInfo;
            var vertex: Vertex = {
                id: net.Id,
                label: `${netInfo.scope}/${netInfo.name}`,
                type: 'network',
                shape: 'star',
                object: net
            };

            if (netInfo.type == 'local') {
                vertex.group = netInfo.scope;
            }

            vertices.push(vertex);
        });

        this._nodes.forEach(node => {
            var nodeInfo = node.meta.emulatorInfo;
            var vertex: Vertex = {
                id: node.Id,
                label: `${nodeInfo.asn}/${nodeInfo.name}`,
                type: 'node',
                shape: 'box',
                shapeProperties: {
                    borderRadius: 0
                },
                object: node
            };

            if (nodeInfo.role != 'Route Server') {
                vertex.group = nodeInfo.asn.toString();
            }

            vertices.push(vertex);
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