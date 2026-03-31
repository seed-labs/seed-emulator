import {DataSource as BaseDataSource, type Edge, META_CLASS, type Vertex} from '@/utils/map-datasource.ts';
import type {EmulatorNetwork, EmulatorNode, VisData} from "@/utils/types.ts";

export interface SimplifiedResult {
    simplifiedVertices: Vertex[];
    simplifiedEdges: Edge[];
    removedNodes: string[];
    simplifiedConnections: { from: string; to: string; path: string[]; label: string }[];
}

export class DataSource extends BaseDataSource {
    async connect() {
        if (this._nodes.length === 0 || this._nets.length === 0) {
            return
        }
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
        this._nodes.forEach((node: EmulatorNode) => {
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

        this._connected = true;
    }

    setVisData(data: VisData) {
        const {nodes, nets} = data
        this._nodes = nodes || []
        this._nets = nets || []
    }

    visDataSet(): { vertices: Vertex[], edges: Edge[] } {
        const allEdges: Edge[] = this.edges;
        const allVertices = this.vertices

        const result = this.simplifyNetworkGraph2(allVertices, allEdges);
        return {
            vertices: result.simplifiedVertices,
            edges: result.simplifiedEdges
        };
    }

    truncateLabel(label: string, maxLength: number = 15): { display: string; full: string } {
        if (!label) return {display: '', full: ''};

        if (label.length <= maxLength) {
            return {display: label, full: label};
        }

        const truncated = label.substring(0, maxLength - 3) + '...';
        return {display: truncated, full: label};
    }

    simplifyNetworkGraph1(nodes: Vertex[], edges: Edge[]): SimplifiedResult {
        const nodeMap = new Map<string, Vertex>();
        const adjacencyList = new Map<string, Set<string>>();
        const edgeLabels = new Map<string, string[]>();

        nodes.forEach(node => {
            nodeMap.set(node.id, node);
            adjacencyList.set(node.id, new Set());
        });

        edges.forEach(edge => {
            adjacencyList.get(edge.from)?.add(edge.to);
            adjacencyList.get(edge.to)?.add(edge.from);

            const key1 = `${edge.from}-${edge.to}`;
            const key2 = `${edge.to}-${edge.from}`;

            if (!edgeLabels.has(key1)) {
                edgeLabels.set(key1, []);
            }
            if (edge.label) {
                edgeLabels.get(key1)?.push(edge.label);
            }

            if (!edgeLabels.has(key2)) {
                edgeLabels.set(key2, []);
            }
            if (edge.label) {
                edgeLabels.get(key2)?.push(edge.label);
            }
        });

        const starNodes = nodes.filter(node => node.shape === "star").map(node => node.id);
        const starNodeSet = new Set(starNodes);
        starNodes.forEach(id => {
            const node = nodeMap.get(id);
            console.log(`  - ${node?.label} (${id})`);
        });

        const intermediateNodes = new Set<string>();
        nodes.forEach(node => {
            const degree = adjacencyList.get(node.id)?.size || 0;
            if (degree === 2 && !starNodeSet.has(node.id)) {
                intermediateNodes.add(node.id);
            }
        });

        const removedNodes = new Set<string>();
        const simplifiedConnections: SimplifiedResult['simplifiedConnections'] = [];

        const processedPairs = new Set<string>();

        starNodes.forEach(startId => {
            const stack: { nodeId: string; path: string[]; nodeLabels: string[] }[] = [];
            stack.push({nodeId: startId, path: [startId], nodeLabels: []});

            while (stack.length > 0) {
                const {nodeId, path, nodeLabels} = stack.pop()!;
                const neighbors = Array.from(adjacencyList.get(nodeId) || []);

                for (const neighbor of neighbors) {
                    if (path.includes(neighbor)) continue;

                    const neighborNode = nodeMap.get(neighbor);
                    const isStar = starNodeSet.has(neighbor);
                    const isIntermediate = intermediateNodes.has(neighbor);
                    const newPath = [...path, neighbor];
                    const newNodeLabels = [...nodeLabels];
                    if (neighborNode && !isStar) {
                        newNodeLabels.push(neighborNode.label);
                    }

                    if (isStar && neighbor !== startId) {
                        const pairKey = [startId, neighbor].sort().join('-');
                        if (newPath.length > 2 && !processedPairs.has(pairKey)) {
                            processedPairs.add(pairKey);
                            const middleNodes = newPath.slice(1, -1);
                            const allIntermediate = middleNodes.every(id => intermediateNodes.has(id));

                            if (allIntermediate && middleNodes.length > 0) {
                                const combinedLabel = newNodeLabels.join('/');
                                simplifiedConnections.push({
                                    from: startId,
                                    to: neighbor,
                                    path: middleNodes,
                                    label: combinedLabel
                                });
                                middleNodes.forEach(id => removedNodes.add(id));
                            }
                        }
                    }
                    else if (isIntermediate) {
                        stack.push({
                            nodeId: neighbor,
                            path: newPath,
                            nodeLabels: newNodeLabels
                        });
                    }
                }
            }
        });

        const simplifiedVertices: Vertex[] = [];
        nodes.forEach(node => {
            if (!removedNodes.has(node.id)) {
                simplifiedVertices.push({...node});
            }
        });

        const simplifiedEdges: Edge[] = [];
        const addedEdges = new Set<string>();
        edges.forEach(edge => {
            const fromRemoved = removedNodes.has(edge.from);
            const toRemoved = removedNodes.has(edge.to);

            if (!fromRemoved && !toRemoved) {
                const edgeKey = [edge.from, edge.to].sort().join('-');

                if (!addedEdges.has(edgeKey)) {
                    const {display, full} = this.truncateLabel(edge.label || '', 15);
                    simplifiedEdges.push({
                        ...edge,
                        label: display,
                        fullLabel: full
                    });
                    addedEdges.add(edgeKey);
                }
            }
        });

        simplifiedConnections.forEach(conn => {
            const edgeKey = [conn.from, conn.to].sort().join('-');
            if (!addedEdges.has(edgeKey)) {
                const {display, full} = this.truncateLabel(conn.label, 15);

                simplifiedEdges.push({
                    from: conn.from,
                    to: conn.to,
                    label: display,
                    fullLabel: full,
                    dashed: true,
                    simplified: true,
                    color: {color: '#ff6b6b'}
                });
                addedEdges.add(edgeKey);
            }
        });

        return {
            simplifiedVertices,
            simplifiedEdges,
            removedNodes: Array.from(removedNodes),
            simplifiedConnections
        };
    }

    simplifyNetworkGraph2(nodes: Vertex[], edges: Edge[]): SimplifiedResult {
        const nodeMap = new Map<string, Vertex>();
        const adjacencyList = new Map<string, Set<string>>();
        const edgeLabels = new Map<string, string[]>();

        nodes.forEach(node => {
            nodeMap.set(node.id, node);
            adjacencyList.set(node.id, new Set());
        });

        edges.forEach(edge => {
            adjacencyList.get(edge.from)?.add(edge.to);
            adjacencyList.get(edge.to)?.add(edge.from);

            const key1 = `${edge.from}-${edge.to}`;
            const key2 = `${edge.to}-${edge.from}`;

            if (!edgeLabels.has(key1)) {
                edgeLabels.set(key1, []);
            }
            if (edge.label) {
                edgeLabels.get(key1)?.push(edge.label);
            }

            if (!edgeLabels.has(key2)) {
                edgeLabels.set(key2, []);
            }
            if (edge.label) {
                edgeLabels.get(key2)?.push(edge.label);
            }
        });

        const starNodes = nodes.filter(node => node.shape === "star").map(node => node.id);
        const starNodeSet = new Set(starNodes);

        const diamondNodes = nodes.filter(node => node.shape === "diamond").map(node => node.id);
        const diamondNodeSet = new Set(diamondNodes);

        const dotNodes = new Set<string>();
        nodes.forEach(node => {
            if (node.shape === "dot") {
                dotNodes.add(node.id);
            }
        });

        const removedNodes = new Set<string>();
        const newEdgesToAdd: { from: string; to: string; label: string; path: string[]; type: string }[] = [];
        const processedPaths = new Set<string>();

        starNodes.forEach(startId => {
            const stack: {
                nodeId: string;
                path: string[];
                dotLabels: string[];
                lastNodeType: string;
            }[] = [];

            stack.push({
                nodeId: startId,
                path: [startId],
                dotLabels: [],
                lastNodeType: 'star'
            });

            while (stack.length > 0) {
                const {nodeId, path, dotLabels, lastNodeType} = stack.pop()!;
                const neighbors = Array.from(adjacencyList.get(nodeId) || []);

                for (const neighbor of neighbors) {
                    if (path.includes(neighbor)) continue;

                    const neighborNode = nodeMap.get(neighbor);
                    const isStar = starNodeSet.has(neighbor);
                    const isDiamond = diamondNodeSet.has(neighbor);
                    const isDot = dotNodes.has(neighbor);

                    const newPath = [...path, neighbor];
                    const newDotLabels = [...dotLabels];

                    if (isDot) {
                        newDotLabels.push(neighborNode?.label || '');
                    }

                    if (isStar && neighbor !== startId) {
                        const pathKey = [startId, neighbor].sort().join('-') + '-' + newDotLabels.join(',');
                        if (newDotLabels.length > 0 && !processedPaths.has(pathKey)) {
                            processedPaths.add(pathKey);
                            const pathNodes = newPath.filter(id => !dotNodes.has(id));
                            for (let i = 0; i < pathNodes.length - 1; i++) {
                                const currentNode = pathNodes[i];
                                const nextNode = pathNodes[i + 1];

                                const isCurrentStar = starNodeSet.has(currentNode);
                                const isCurrentDiamond = diamondNodeSet.has(currentNode);
                                const isNextStar = starNodeSet.has(nextNode);
                                const isNextDiamond = diamondNodeSet.has(nextNode);

                                const startIndex = newPath.indexOf(currentNode);
                                const endIndex = newPath.indexOf(nextNode);
                                const betweenDots = newPath.slice(startIndex + 1, endIndex).filter(id => dotNodes.has(id));

                                if (betweenDots.length > 0) {
                                    const betweenLabels = betweenDots.map(id => nodeMap.get(id)?.label || '').join('/');
                                    if (isCurrentStar && isNextStar) {
                                        newEdgesToAdd.push({
                                            from: currentNode,
                                            to: nextNode,
                                            label: betweenLabels,
                                            path: betweenDots,
                                            type: 'star-star'
                                        });
                                    } else if (isCurrentStar && isNextDiamond) {
                                        newEdgesToAdd.push({
                                            from: currentNode,
                                            to: nextNode,
                                            label: betweenLabels,
                                            path: betweenDots,
                                            type: 'star-diamond'
                                        });
                                    } else if (isCurrentDiamond && isNextStar) {
                                        newEdgesToAdd.push({
                                            from: currentNode,
                                            to: nextNode,
                                            label: betweenLabels,
                                            path: betweenDots,
                                            type: 'diamond-star'
                                        });
                                    } else if (isCurrentDiamond && isNextDiamond) {
                                        newEdgesToAdd.push({
                                            from: currentNode,
                                            to: nextNode,
                                            label: betweenLabels,
                                            path: betweenDots,
                                            type: 'diamond-diamond'
                                        });
                                    }

                                    betweenDots.forEach(id => removedNodes.add(id));
                                }
                            }
                        }
                    }

                    if (isDot || isDiamond) {
                        stack.push({
                            nodeId: neighbor,
                            path: newPath,
                            dotLabels: newDotLabels,
                            lastNodeType: isDot ? 'dot' : 'diamond'
                        });
                    }
                }
            }
        });

        dotNodes.forEach(dotId => {
            if (removedNodes.has(dotId)) return;

            const neighbors = Array.from(adjacencyList.get(dotId) || []);

            if (neighbors.length === 2) {
                const [nodeA, nodeB] = neighbors;
                if (!removedNodes.has(nodeA) && !removedNodes.has(nodeB)) {
                    const isAStar = starNodeSet.has(nodeA);
                    const isBStar = starNodeSet.has(nodeB);
                    const isADiamond = diamondNodeSet.has(nodeA);
                    const isBDiamond = diamondNodeSet.has(nodeB);

                    const dotLabel = nodeMap.get(dotId)?.label || '';
                    if (isAStar && isBStar) {
                        newEdgesToAdd.push({
                            from: nodeA,
                            to: nodeB,
                            label: dotLabel,
                            path: [dotId],
                            type: 'star-star'
                        });
                    } else if ((isAStar && isBDiamond) || (isADiamond && isBStar)) {
                        newEdgesToAdd.push({
                            from: isAStar ? nodeA : nodeB,
                            to: isAStar ? nodeB : nodeA,
                            label: dotLabel,
                            path: [dotId],
                            type: 'star-diamond'
                        });
                    } else if (isADiamond && isBDiamond) {
                        newEdgesToAdd.push({
                            from: nodeA,
                            to: nodeB,
                            label: dotLabel,
                            path: [dotId],
                            type: 'diamond-diamond'
                        });
                    }

                    removedNodes.add(dotId);
                }
            }
        });

        const simplifiedVertices: Vertex[] = [];
        nodes.forEach(node => {
            if (!removedNodes.has(node.id)) {
                simplifiedVertices.push({...node});
            }
        });

        const simplifiedEdges: Edge[] = [];
        const addedEdges = new Set<string>();

        edges.forEach(edge => {
            const fromRemoved = removedNodes.has(edge.from);
            const toRemoved = removedNodes.has(edge.to);

            if (!fromRemoved && !toRemoved) {
                const edgeKey = [edge.from, edge.to].sort().join('-');

                if (!addedEdges.has(edgeKey)) {
                    const {display, full} = this.truncateLabel(edge.label || '', 15);
                    simplifiedEdges.push({
                        ...edge,
                        label: display,
                        fullLabel: full
                    });
                    addedEdges.add(edgeKey);
                }
            }
        });

        newEdgesToAdd.forEach(newEdge => {
            const edgeKey = [newEdge.from, newEdge.to].sort().join('-');

            if (!addedEdges.has(edgeKey)) {
                const {display, full} = this.truncateLabel(newEdge.label, 15);

                let color = '#69c0ff';
                let dashed = false;
                let width = 2;

                if (newEdge.type === 'star-star') {
                    color = '#ff6b6b';
                    dashed = true;
                    width = 3;
                } else if (newEdge.type === 'star-diamond' || newEdge.type === 'diamond-star') {
                    color = '#ffa39e';
                    dashed = false;
                    width = 2.5;
                } else if (newEdge.type === 'diamond-diamond') {
                    color = '#69c0ff';
                    dashed = false;
                    width = 2;
                }

                simplifiedEdges.push({
                    from: newEdge.from,
                    to: newEdge.to,
                    label: display,
                    fullLabel: full,
                    dashed: dashed,
                    simplified: true,
                    // color: {color: color},
                    color: {color: "#000"},
                    // width: width,
                    // title: `${newEdge.path.map(id => nodeMap.get(id)?.label).join(' → ')}`
                });
                addedEdges.add(edgeKey);
            }
        });

        return {
            simplifiedVertices,
            simplifiedEdges,
            removedNodes: Array.from(removedNodes),
            simplifiedConnections: newEdgesToAdd.map(e => ({
                from: e.from,
                to: e.to,
                path: e.path,
                label: e.label
            }))
        };
    }
}