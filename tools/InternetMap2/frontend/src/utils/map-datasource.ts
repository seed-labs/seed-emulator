import {DataSet} from 'vis-data';
import type {FullItem} from 'vis-data/declarations/data-interface';
import type {EdgeOptions, NodeOptions} from 'vis-network';
import request from '@/utils/request';
import type {AxiosRequestConfig, AxiosResponse} from 'axios';
import type {
    BgpPeer,
    EmulatorNetwork,
    EmulatorNode,
    EmulatorNodeInfo,
    TransitsEmulatorNodeInfo,
} from './types';

export const META_CLASS = 'org.seedsecuritylabs.seedemu.meta.class';

export type DataEvent = 'packet' | 'dead' | 'vis';

export interface Vertex extends NodeOptions {
    id: string;
    label: string;
    group?: string;
    shape?: string;
    type: 'node' | 'network';
    object: EmulatorNode | EmulatorNetwork;
    collapsed?: boolean,
    custom?: string,
    hidden?: boolean,
    borderWidth?: number,
    weight?: string
}

export interface Edge extends EdgeOptions {
    id?: string | undefined;
    from: string;
    to: string;
    label?: string;
}

export type NodesType = DataSet<Vertex, 'id'>
export type EdgesType = DataSet<Edge, 'id'>

export interface ApiRespond<ResultType> {
    ok: boolean;
    result: ResultType;
}

export interface FilterRespond {
    currentFilter: string;
}

export class DataSource {
    public services: Set<string>;
    protected _nodes: EmulatorNode[];
    protected _nets: EmulatorNetwork[];
    private readonly _wsProtocol: string;
    private _socket!: WebSocket;
    private _socketVis!: WebSocket;
    protected _connected: boolean;
    private _packetEventHandler!: (nodeId: string) => void;
    private _errorHandler!: (error: any) => void;
    private _visEventHandler!: (params: any) => void;

    /**
     * construct new data provider.
     *
     * @param wsProtocol websocket protocol (ws/wss), default to ws.
     */
    constructor(wsProtocol: string = 'ws') {
        this._wsProtocol = wsProtocol;
        this.services = new Set<string>();
        this._nodes = [];
        this._nets = [];
        this._connected = false;
    }

    getter() {
        return {_nodes: this._nodes, _nets: this._nets}
    }

    /**
     * load data from api.
     *
     * @param method http method.
     * @param url target url.
     * @param body (optional) request body.
     * @returns api respond object.
     */
    private async _load<ResultType>(
        method: 'GET' | 'POST' | 'PUT' | 'DELETE',
        url: string,
        body?: any
    ): Promise<AxiosResponse<ApiRespond<ResultType>>> {
        // 组装 axios 配置
        const config: AxiosRequestConfig = {
            method,
            url,
            // 对于 POST/PUT 自动设置 JSON 头并序列化 body
            ...(method === 'POST' || method === 'PUT'
                ? {
                    headers: {'Content-Type': 'application/json;charset=UTF-8'},
                    data: body,
                }
                : {}),
        };

        try {
            const response: AxiosResponse<ApiRespond<ResultType>> = await request(config);

            // axios 默认只在 HTTP 状态码 2xx 时 resolve
            // 这里再检查业务层面的 ok 标记
            if (response.ok) {
                return response;
            } else {
                // 业务返回错误，直接抛出让调用方走 catch 分支
                throw response;
            }
        } catch (error: any) {
            // 统一错误结构，保持与原实现的 reject 参数一致
            if (error?.response) {
                // 服务器有响应但状态码非 2xx
                return Promise.reject({
                    ok: false,
                    result: `non-200 response from API`,
                });
            } else if (error?.request) {
                // 请求已发出，但没有收到响应
                return Promise.reject({
                    ok: false,
                    result: 'axios request failed.',
                });
            } else {
                // 其它错误（例如代码错误、JSON 解析错误等）
                return Promise.reject({
                    ok: false,
                    result: error?.message ?? 'unknown error',
                });
            }
        }
    }

    /**
     * connect to api: start listening sniffer socket, load nodes/nets list.
     * call again when connected to reload nodes/nets.
     */
    async connect() {
        this._nodes = (await this._load<EmulatorNode[]>('GET', `/container`)).result;
        this._nets = (await this._load<EmulatorNetwork[]>('GET', `/network`)).result;

        if (this._connected) {
            return;
        }

        this._nets.forEach((net: EmulatorNetwork) => {
            net.meta.relation = {parent: new Set<string>()}
            if (META_CLASS in net['Labels'] && net['Labels'][META_CLASS] !== '') {
                let services = JSON.parse(net['Labels'][META_CLASS]);
                for (const service of services) {
                    if (service.endsWith("Service")) {
                        this.services.add(service);
                    }
                }
            }
        })
        this._nodes.forEach(node => {
            node.meta.relation = {parent: new Set<string>()};
            if (META_CLASS in node['Labels'] && node['Labels'][META_CLASS] !== '') {
                let services = JSON.parse(node['Labels'][META_CLASS]);
                for (const service of services) {
                    if (service.endsWith("Service")) {
                        this.services.add(service);
                    }
                }
            }
        })
        const host = import.meta.env.MODE === 'development' ? import.meta.env.VITE_PROXY_ADDRESS.replace(/^https?:\/\//, '') : location.host
        this._socket = new WebSocket(`${this._wsProtocol}://${host}${import.meta.env.VITE_SERVER_URL_PREFIX}/sniff`);
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
        // vis set ws
        this._socketVis = new WebSocket(`${this._wsProtocol}://${host}${import.meta.env.VITE_SERVER_URL_PREFIX}/container/vis/set`);
        this._socketVis.addEventListener('message', (ev) => {
            let msg = ev.data.toString();

            let object = JSON.parse(msg);
            if (this._visEventHandler) {
                this._visEventHandler(object);
            }
        });

        this._socketVis.addEventListener('error', (ev) => {
            if (this._errorHandler) {
                this._errorHandler(ev);
            }
        });

        this._socketVis.addEventListener('close', (ev) => {
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
        this._socketVis.close();
    }

    getNodeInfoById(nodeId: string) {
        return this._nodes.find(n => n.Id === nodeId);
    }

    getNodeInfoByContainerName(name: string) {
        return this._nodes.find(node => node.Names.includes(name));
    }

    getNodeInfoByIP(ip) {
        return this._nodes.find(node => {
            const net = node.NetworkSettings.Networks;
            for (const key of Object.keys(net)) {
                if (net[key]['IPAddress'] === ip) {
                    return true
                }
            }
        });
    }

    /**
     * get current sniff filter expression.
     *
     * @returns filter expression.
     */
    async getSniffFilter(): Promise<string> {
        return (await this._load<FilterRespond>('GET', `/sniff`)).result.currentFilter;
    }

    /**
     * set sniff filter expression.
     *
     * @param filter filter expression.
     * @returns updated filter expression.
     */
    async setSniffFilter(filter: string): Promise<string> {
        return (await this._load<FilterRespond>('POST', `/sniff`, JSON.stringify({filter}))).result.currentFilter;
    }

    /**
     * get list of bgp peers of the given node.
     *
     * @param node node id. must be node with router role.
     * @returns list of peers.
     */
    async getBgpPeers(node: string): Promise<BgpPeer[]> {
        return (await this._load<BgpPeer[]>('GET', `/container/${node}/bgp`)).result;
    }

    /**
     * set bgp peer state.
     *
     * @param node node id. must be node with router role.
     * @param peer peer name.
     * @param up protocol state, true = up, false = down.
     */
    async setBgpPeers(node: string, peer: string, up: boolean) {
        await this._load('POST', `/container/${node}/bgp/${peer}`, JSON.stringify({status: up}));
    }

    /**
     * get network state of the given node.
     *
     * @param node node id.
     * @returns true if up, false if down.
     */
    async getNetworkStatus(node: string): Promise<boolean> {
        return (await this._load<boolean>('GET', `/container/${node}/net`)).result;
    }

    /**
     * set network state of the given node.
     *
     * @param node node id.
     * @param up true if up, false if down.
     */
    async setNetworkStatus(node: string, up: boolean) {
        await this._load('POST', `/container/${node}/net`, JSON.stringify({status: up}));
    }

    /**
     * event handler register.
     *
     * @param eventName event to listen.
     * @param callback callback.
     */
    on(eventName: DataEvent, callback?: (data: any) => void) {
        switch (eventName) {
            case 'packet':
                this._packetEventHandler = callback;
                break;
            case 'dead':
                this._errorHandler = callback;
                break
            case 'vis':
                this._visEventHandler = callback;
        }
    }

    get edges(): Edge[] {
        let edges: Edge[] = [];

        this._nodes.forEach(node => {
            let nets = node.NetworkSettings.Networks;
            Object.keys(nets).forEach(key => {
                let net = nets[key];
                let label = '';

                node.meta.emulatorInfo.nets.forEach((item: { name: string, address: string }) => {
                    if (key.includes(item.name)) {
                        label = item.address;
                    }
                });

                edges.push({
                    from: node.Id,
                    to: net.NetworkID,
                    label
                });

                const nodeInfo = node.meta.emulatorInfo;
                if (['Router', 'BorderRouter'].includes(nodeInfo.role)) {
                    for (const item of this._nets) {
                        if (item.Id === net.NetworkID) {
                            if (item.meta.emulatorInfo.type === 'global') {
                                node.meta.relation.parent.add(item.Id);
                            } else {
                                item.meta.relation.parent.add(node.Id);
                            }
                            break;
                        }
                    }
                } else {
                    node.meta.relation.parent.add(net.NetworkID);
                }
            })
        })

        return edges
    }

    get vertices(): Vertex[] {
        let vertices: Vertex[] = [];
        let hiddenNodeNetworkIds = new Set<string>()

        // const IX_DB: IXLocation[] = [
        //     {id: 'HN', name: 'HaiNan-IX', lat: 20.04, lon: 110.19},
        //     {id: 'BJ', name: 'BeiJing-IX', lat: 39.9, lon: 116.4},
        //     {id: 'AMS', name: 'AMS-IX', lat: 52.37, lon: 4.9},
        //     {id: 'LON', name: 'LINX', lat: 51.5, lon: -0.12},
        //     {id: 'TYO', name: 'JP-IX', lat: 35.68, lon: 139.76},
        //     {id: 'NewYork', name: 'NewYork-IX', lat: 74.01, lon: 40.71}
        // ]

        this._nodes.forEach(node => {
            let nodeInfo = node.meta.emulatorInfo;
            let vertex: Vertex = {
                id: node.Id,
                label: nodeInfo.displayname ?? `${nodeInfo.asn}/${nodeInfo.name}`,
                type: 'node',
                shape: ['Router', 'BorderRouter'].includes(nodeInfo.role) ? 'dot' : 'hexagon',
                // hidden: !['Router', 'BorderRouter', 'Route Server'].includes(nodeInfo.role),
                object: node,
                collapsed: false,
                custom: node.meta.emulatorInfo.custom,
            };

            if (nodeInfo.role != 'Route Server') {
                vertex.group = nodeInfo.asn.toString();
            }
            if (vertex.hidden) {
                const nets = node.NetworkSettings.Networks;
                Object.keys(nets).forEach(key => {
                    hiddenNodeNetworkIds.add(nets[key].NetworkID)
                })
            } else {
                vertices.push(vertex);
            }
        });

        this._nets.forEach(net => {
            let netInfo = net.meta.emulatorInfo;
            let vertex: Vertex = {
                id: net.Id,
                label: netInfo.displayname ?? `${netInfo.scope}/${netInfo.name}`,
                type: 'network',
                shape: netInfo.type == 'global' ? 'star' : 'diamond',
                object: net,
                collapsed: hiddenNodeNetworkIds.has(net.Id),
                borderWidth: hiddenNodeNetworkIds.has(net.Id) ? 3 : 1
            };

            // if (netInfo.type === 'global') {
            //     const ix = IX_DB.pop()
            //     if (ix) {
            //         vertex.physics = false
            //         vertex.fixed = true
            //         vertex.label = ix.name
            //         const pos = geoToXY(ix!.lat, ix!.lon)
            //         console.log(pos)
            //         vertex.x = pos.x
            //         vertex.y = pos.y
            //         vertex.size = 30
            //         vertex.color = { background: '#2563eb', border: '#0f172a' }
            //         vertex.font = { size: 13, color: '#000' }
            //     }
            // }

            if (netInfo.type == 'local') {
                vertex.group = netInfo.scope;
            }

            vertices.push(vertex);
        });

        return vertices;
    }

    get ixs(): EmulatorNetwork[] {
        return this._nets.filter(net => net.meta.emulatorInfo.type === 'global')
    }

    get transits(): Array<TransitsEmulatorNodeInfo> {
        let asnSet = new Set<number>()
        let asnInfoMap = new Map<number, EmulatorNodeInfo[]>();
        this._nodes.forEach(node => {
            const asn = node.meta.emulatorInfo.asn
            if (!["Router", "BorderRouter"].includes(node.meta.emulatorInfo.role) || node.meta.emulatorInfo.name.startsWith("router")) {
                return
            }
            if (asnSet.has(asn)) {
                asnInfoMap.get(asn)!.push(node.meta.emulatorInfo)
            } else {
                asnSet.add(asn)
                asnInfoMap.set(asn, [node.meta.emulatorInfo])
            }
        })
        const asnInfoArray: TransitsEmulatorNodeInfo[] = Array.from(asnInfoMap, ([asn, info]): {
            asn: number,
            info: EmulatorNodeInfo[]
        } => ({asn, info}));

        return asnInfoArray.sort(
            (a, b) => {
                if (b.info.length !== a.info.length) {
                    return b.info.length - a.info.length
                }
                return a.asn - b.asn
            }
        )
    }

    get groups(): Set<string> {
        let groups = new Set<string>();

        this._nets.forEach(net => {
            groups.add(net.meta.emulatorInfo.scope);
        });

        this._nodes.forEach(node => {
            groups.add(node.meta.emulatorInfo.asn.toString());
        })

        return groups;
    }

    newVertices(currentNode: FullItem<Vertex, 'id'>[]): { vertices: Vertex[], edges: Edge[] } {
        let vertices: Vertex[] = [];
        let edges: Edge[] = [];
        if (currentNode["type"] !== "network") {
            return {vertices, edges};
        }
        this._nodes.forEach(node => {
            if (['Router', 'BorderRouter', 'Route Server'].includes(node.meta.emulatorInfo.role)) {
                return
            }
            let nets = node.NetworkSettings.Networks;
            Object.keys(nets).forEach(key => {
                let label = '';
                let net = nets[key]!;
                if (net.NetworkID !== currentNode['id']) {
                    return
                }

                node.meta.emulatorInfo.nets.forEach((item: { name: string, address: string }) => {
                    if (key.includes(item.name)) {
                        label = item.address;
                    }
                });
                edges.push({
                    from: node.Id,
                    to: net.NetworkID,
                    label
                });

                const nodeInfo = node.meta.emulatorInfo;
                let vertex: Vertex = {
                    id: node.Id,
                    label: nodeInfo.displayname ?? `${nodeInfo.asn}/${nodeInfo.name}`,
                    type: 'node',
                    shape: ['Router', 'BorderRouter'].includes(nodeInfo.role) ? 'dot' : 'hexagon',
                    object: node,
                    collapsed: false,
                    custom: node.meta.emulatorInfo.custom
                };

                if (nodeInfo.role != 'Route Server') {
                    vertex.group = nodeInfo.asn.toString();
                }
                vertices.push(vertex);
            })
        })

        return {vertices, edges};
    }

    connectExistingTopology(originalNodes: Vertex[], originalEdges: Edge[], currentNodes: Vertex[], currentEdges: Edge[]): Edge[] {
        // 生成边的唯一标识
        const getEdgeKey = (from: string, to: string): string => `${from}-${to}`;

        // 构建图的邻接表（双向）
        const buildGraph = (edges: Edge[]): Map<string, { node: string, edge: Edge }[]> => {
            const graph = new Map<string, { node: string, edge: Edge }[]>();

            edges.forEach(edge => {
                if (edge.from === edge.to) return;

                if (!graph.has(edge.from)) {
                    graph.set(edge.from, []);
                }
                if (!graph.has(edge.to)) {
                    graph.set(edge.to, []);
                }
                graph.get(edge.from)!.push({node: edge.to, edge});
                graph.get(edge.to)!.push({node: edge.from, edge});
            });

            return graph;
        };

        // 查找两个现有节点之间的最短路径（路径中间都是缺失节点）
        const findShortestPathBetweenExistingNodes = (
            graph: Map<string, { node: string, edge: Edge }[]>,
            start: string,
            end: string,
            existingNodes: Set<string>
        ): { path: string[], edges: Edge[] } | null => {
            if (start === end) return null;

            const visited = new Set<string>();
            const queue: { node: string; path: string[]; edges: Edge[] }[] = [
                {node: start, path: [start], edges: []}
            ];

            while (queue.length > 0) {
                const current = queue.shift()!;

                if (visited.has(current.node)) continue;
                visited.add(current.node);

                const neighbors = graph.get(current.node) || [];

                for (const neighbor of neighbors) {
                    // 跳过自环
                    if (neighbor.node === current.node) continue;

                    // 如果遇到终点，返回路径
                    if (neighbor.node === end) {
                        return {
                            path: [...current.path, end],
                            edges: [...current.edges, neighbor.edge]
                        };
                    }

                    // 只允许通过缺失节点（不在existingNodes中）
                    if (!visited.has(neighbor.node) && !existingNodes.has(neighbor.node)) {
                        queue.push({
                            node: neighbor.node,
                            path: [...current.path, neighbor.node],
                            edges: [...current.edges, neighbor.edge]
                        });
                    }
                }
            }

            return null;
        };

        // 根据节点类型确定边的方向
        const determineEdgeDirection = (node1: Vertex, node2: Vertex): { from: string, to: string } | null => {
            if (node1.id === node2.id) return null; // 同一个节点

            if (node1.type === 'node' && node2.type === 'network') {
                return {from: node1.id, to: node2.id};
            } else if (node1.type === 'network' && node2.type === 'node') {
                return {from: node2.id, to: node1.id};
            }
            // 如果都是同类型节点，根据ID排序确定方向以避免重复
            return node1.id < node2.id ? {from: node1.id, to: node2.id} : {from: node2.id, to: node1.id};
        };

        // 生成新边的标签
        const generateEdgeLabel = (originalEdges: Edge[]): string => {
            const labels = originalEdges.map(edge => edge.label).filter(Boolean);
            if (labels.length === 0) {
                return 'connected';
            }

            // 只有一个标签时，直接返回该标签（仍保持方括号的格式）
            if (labels.length === 1) {
                return `[${labels[0]}]`;
            }

            // // 多于一个标签时，取第一个和最后一个
            // const first = labels[0];
            // const last = labels[labels.length - 1];
            // return `${first}->${last}`;
            return ''
        };

        // 判断两个节点是否已经存在边
        const hasExistingEdge = (edges: Edge[], node1Id: string, node2Id: string): boolean => {
            return edges.some(edge =>
                (edge.from === node1Id && edge.to === node2Id) ||
                (edge.from === node2Id && edge.to === node1Id)
            );
        };

        // 主函数：连接现有节点
        if (currentNodes.length === 0) return [];

        const existingNodeIds = new Set(currentNodes.map(node => node.id));
        const graph = buildGraph(originalEdges);

        let newEdges: Edge[] = [...currentEdges];
        const processedPairs = new Set<string>();

        // 检查每对现有节点，寻找需要连接的路径
        for (let i = 0; i < currentNodes.length; i++) {
            for (let j = i + 1; j < currentNodes.length; j++) {
                const nodeA = currentNodes[i];
                const nodeB = currentNodes[j];

                if (nodeA.id === nodeB.id) continue; // 跳过同一个节点

                const pairKey = getEdgeKey(nodeA.id, nodeB.id);
                const reversePairKey = getEdgeKey(nodeB.id, nodeA.id);

                if (processedPairs.has(pairKey) || processedPairs.has(reversePairKey)) continue;
                processedPairs.add(pairKey);

                // 如果已经存在边，跳过
                if (hasExistingEdge(newEdges, nodeA.id, nodeB.id)) continue;

                // 确定边的方向
                const direction = determineEdgeDirection(nodeA, nodeB);
                if (!direction) continue;

                const {from, to} = direction;

                // 查找通过缺失节点的路径
                const pathResult = findShortestPathBetweenExistingNodes(
                    graph,
                    from,
                    to,
                    existingNodeIds
                );

                // 如果找到路径且路径中有缺失节点，创建新边
                if (pathResult && pathResult.path.length > 2) {
                    const newEdge: Edge = {
                        from,
                        to,
                        label: generateEdgeLabel(pathResult.edges)
                    };

                    // 检查是否已经添加了这条边
                    if (!hasExistingEdge(newEdges, from, to)) {
                        newEdges.push(newEdge);
                    }
                }
            }
        }

        return newEdges.filter(edge => originalNodes.find(item => item.id === edge.from)?.shape !== 'star' || originalNodes.find(item => item.id === edge.to)?.shape !== 'star');
    }
}