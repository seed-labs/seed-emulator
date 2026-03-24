import {DataSource} from './datasource.ts';
import {MapUi as BaseMapUi} from "@/utils/map-ui.ts";
import type {MapUiConfiguration} from "@/utils/map-ui.ts";
import {type Edge, type Vertex} from '@/utils/map-datasource.ts';
import {DataSet} from "vis-data";
import {dealTransitWeight} from "@/utils/tools.ts";

export interface UploadMapUiOtherConfiguration {

}

/**
 * map UI controller.
 */
export class MapUi extends BaseMapUi {
    public otherConfig: UploadMapUiOtherConfiguration

    constructor(config: MapUiConfiguration, otherConfig: UploadMapUiOtherConfiguration) {
        super(config)
        this.otherConfig = otherConfig;
        this._datasource = config.datasource as DataSource;
    }

    setVisData(data) {
        this._datasource.setVisData(data)
    }

    getIxs() {
        return this._datasource.ixs;
    }

    getTransits() {
        return this._datasource.transits;
    }

    setGraphEdgeEvent(tooltipContent, tooltipVisible, position) {
        const intervalHandle = setInterval(() => {
            if (!this._graph) {
                return
            }
            this._graph.on('hoverEdge', (params: any) => {
                const edgeId = params.edge;
                const edge = this._edges.get(edgeId) as any;

                if (edge && edge.fullLabel) {
                    position.value = DOMRect.fromRect({
                        x: params.pointer.DOM.x,
                        y: params.pointer.DOM.y,
                    })
                    tooltipContent.value = edge.fullLabel;
                    tooltipVisible.value = true;
                }
            });
            this._graph.on('blurEdge', () => {
                tooltipVisible.value = false;
            });
            clearInterval(intervalHandle)
        }, 1000)
    }

    filterGraphByIX(selectedStarLabels: string[]): { filteredNodes: Vertex[]; filteredEdges: Edge[] } {
        const nodes = this._datasource.vertices
        const edges = this._datasource.edges

        const nodeMap = new Map<string, Vertex>();
        nodes.forEach(node => nodeMap.set(node.id, node));

        const selectedStarIds = new Set<string>();
        const selectedStarLabelsSet = new Set(selectedStarLabels);

        const allStarIds = new Set<string>();
        const starIdToName = new Map<string, string>();

        nodes.forEach(node => {
            if (node.shape === 'star') {
                allStarIds.add(node.id);
                const starName = node.object?.meta?.emulatorInfo?.name;
                if (starName) {
                    starIdToName.set(node.id, starName);
                    if (selectedStarLabelsSet.has(starName)) {
                        selectedStarIds.add(node.id);
                    }
                }
            }
        });

        const adjacencyList = new Map<string, Set<string>>();
        nodes.forEach(node => adjacencyList.set(node.id, new Set()));
        edges.forEach(edge => {
            adjacencyList.get(edge.from)?.add(edge.to);
            adjacencyList.get(edge.to)?.add(edge.from);
        });

        const nodesToKeep = new Set<string>(selectedStarIds);
        const edgesToKeep = new Set<string>();
        const directlyConnectedStars = new Set<string>();

        selectedStarIds.forEach(starId => {
            const queue: { nodeId: string; path: string[]; fromStar: string }[] = [
                {nodeId: starId, path: [starId], fromStar: starId}
            ];

            const visited = new Set<string>([starId]);

            while (queue.length > 0) {
                const {nodeId, path, fromStar} = queue.shift()!;
                const neighbors = adjacencyList.get(nodeId) || new Set();

                for (const neighborId of neighbors) {
                    if (path.includes(neighborId)) continue;

                    const isStar = allStarIds.has(neighborId);
                    const neighborNode = nodeMap.get(neighborId);
                    const isDot = neighborNode?.shape === 'dot';
                    const isDiamond = neighborNode?.shape === 'diamond';

                    if (isStar && neighborId !== fromStar) {
                        if (!selectedStarIds.has(neighborId)) {
                            directlyConnectedStars.add(neighborId);
                            const fullPath = [...path, neighborId];
                            for (let i = 0; i < fullPath.length - 1; i++) {
                                const currentId = fullPath[i];
                                const nextId = fullPath[i + 1];
                                const edgeKey = [currentId, nextId].sort().join('-');
                                edgesToKeep.add(edgeKey);
                            }
                            fullPath.forEach(id => nodesToKeep.add(id));
                        }
                        continue;
                    }

                    if (isDot || isDiamond) {
                        if (!visited.has(neighborId)) {
                            visited.add(neighborId);
                            const edgeKey = [nodeId, neighborId].sort().join('-');
                            edgesToKeep.add(edgeKey);
                            nodesToKeep.add(neighborId);

                            queue.push({
                                nodeId: neighborId,
                                path: [...path, neighborId],
                                fromStar: fromStar
                            });
                        }
                    }
                    else if (!isStar) {
                        if (!visited.has(neighborId)) {
                            visited.add(neighborId);

                            const edgeKey = [nodeId, neighborId].sort().join('-');
                            edgesToKeep.add(edgeKey);
                            nodesToKeep.add(neighborId);

                            queue.push({
                                nodeId: neighborId,
                                path: [...path, neighborId],
                                fromStar: fromStar
                            });
                        }
                    }
                }
            }
        });

        directlyConnectedStars.forEach(starId => {
            const neighbors = adjacencyList.get(starId) || new Set();
            neighbors.forEach(neighborId => {
                const neighborNode = nodeMap.get(neighborId);
                const isDot = neighborNode?.shape === 'dot';

                if (isDot) {
                    nodesToKeep.add(neighborId);
                    const edgeKey = [starId, neighborId].sort().join('-');
                    edgesToKeep.add(edgeKey);
                }
            });
        });

        selectedStarIds.forEach(id => nodesToKeep.add(id));
        const filteredNodes: Vertex[] = nodes.filter(node => nodesToKeep.has(node.id));
        const filteredEdges: Edge[] = [];
        const addedEdges = new Set<string>();

        edges.forEach(edge => {
            const edgeKey = [edge.from, edge.to].sort().join('-');

            if (edgesToKeep.has(edgeKey) && !addedEdges.has(edgeKey)) {
                const newEdge = {...edge};
                filteredEdges.push(newEdge);
                addedEdges.add(edgeKey);
            }
        });

        return {
            filteredNodes,
            filteredEdges,
        };
    }

    filterGraphByIXNum(ixNumber: number): { filteredNodes: Vertex[], filteredEdges: Edge[] } {
        const selectedStarLabels = this.getIxs().map(v => v.meta.emulatorInfo.name).slice(0, ixNumber)
        return this.filterGraphByIX(selectedStarLabels)
    }

    filterGraphByTransit(selectedGroups: string[]): { filteredNodes: Vertex[]; filteredEdges: Edge[] } {
        const nodes = this._datasource.vertices;
        const edges = this._datasource.edges;
        if (selectedGroups.length === 0) {
            return {
                filteredNodes: [],
                filteredEdges: []
            };
        }

        const nodeMap = new Map<string, Vertex>();
        nodes.forEach(node => nodeMap.set(node.id, node));

        const adjacencyList = new Map<string, Set<string>>();
        nodes.forEach(node => adjacencyList.set(node.id, new Set()));
        edges.forEach(edge => {
            adjacencyList.get(edge.from)?.add(edge.to);
            adjacencyList.get(edge.to)?.add(edge.from);
        });

        const selectedGroupNodeIds = new Set<string>();
        nodes.forEach(node => {
            if (selectedGroups.includes(node.group as string)) {
                selectedGroupNodeIds.add(node.id);
            }
        });

        const nodesToKeep = new Set<string>();
        const edgesToKeep = new Set<string>();

        selectedGroupNodeIds.forEach(nodeId => {
            nodesToKeep.add(nodeId);
            const neighbors = adjacencyList.get(nodeId) || new Set();
            neighbors.forEach(neighborId => {
                nodesToKeep.add(neighborId);
                const edgeKey = [nodeId, neighborId].sort().join('-');
                edgesToKeep.add(edgeKey);
            });
        });

        const starNodesInKeep = Array.from(nodesToKeep).filter(id => {
            const node = nodeMap.get(id);
            return node?.shape === 'star';
        });

        starNodesInKeep.forEach(starId => {
            const neighbors = adjacencyList.get(starId) || new Set();

            neighbors.forEach(neighborId => {
                const neighborNode = nodeMap.get(neighborId);
                if (neighborNode?.shape === 'dot') {
                    nodesToKeep.add(neighborId);
                    const edgeKey = [starId, neighborId].sort().join('-');
                    edgesToKeep.add(edgeKey);
                }
            });
        });

        selectedGroupNodeIds.forEach(nodeId1 => {
            selectedGroupNodeIds.forEach(nodeId2 => {
                if (nodeId1 < nodeId2) {
                    const edgeKey = [nodeId1, nodeId2].sort().join('-');
                    if (adjacencyList.get(nodeId1)?.has(nodeId2)) {
                        edgesToKeep.add(edgeKey);
                    }
                }
            });
        });

        const filteredNodes: Vertex[] = nodes.filter(node => nodesToKeep.has(node.id));
        const filteredEdges: Edge[] = [];
        const addedEdges = new Set<string>();

        edges.forEach(edge => {
            const edgeKey = [edge.from, edge.to].sort().join('-');

            if (edgesToKeep.has(edgeKey) && !addedEdges.has(edgeKey)) {
                const newEdge = {...edge};
                filteredEdges.push(newEdge);
                addedEdges.add(edgeKey);
            }
        });

        return {
            filteredNodes,
            filteredEdges,
        };
    }

    filterGraphByTransitNum(transitsNumber: number): { filteredNodes: Vertex[], filteredEdges: Edge[] } {
        let groups = new Set<string>()
        if (transitsNumber <= 0) {
            return {filteredNodes: this._datasource.vertices, filteredEdges: this._datasource.edges}
        }

        const transitsWithWeight = dealTransitWeight(this._datasource.vertices)
        for (const transit of transitsWithWeight) {
            if (groups.size >= transitsNumber) {
                break
            }
            groups.add(transit.group as string)
        }

        return this.filterGraphByTransit([...groups])
    }

    render(vertices: Vertex[], edges: Edge[]) {
        this._edges = new DataSet(edges);
        this._nodes = new DataSet(vertices);
        if (!this._graph) {
            this.createVisGraph()
        } else {
            this._graph?.setData({
                nodes: this._nodes,
                edges: this._edges
            });
            this._graph.on('stabilizationProgress', (params) => {
                const percent = Math.round((params.iterations / params.total) * 100)
                this.allLoadingInstance?.setText(`${percent}%`)
            })
            this._graph.once('stabilizationIterationsDone', () => {
                this.allLoadingInstance?.close()
            })
        }
    }
}