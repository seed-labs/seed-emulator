import {DataSource as BaseDataSource, type Edge, type Vertex} from '@/utils/map-datasource.ts';
import {dealTransitWeight} from "@/utils/tools.ts";

export class DataSource extends BaseDataSource {
    visDataSet(transitsNumber: number): { vertices: Vertex[], edges: Edge[] } {
        let groups = new Set<string>()
        if (transitsNumber <= 0) {
            return {vertices: this.vertices, edges: this.edges}
        }

        const transitsWithWeight = dealTransitWeight(this.vertices)
        for (const transit of transitsWithWeight) {
            if (groups.size >= transitsNumber) {
                break
            }
            groups.add(transit.group as string)
        }

        return this.visDataSetByAsn([...groups])
    }

    visDataSetByAsn(selectedGroups: number[] | string[]): { vertices: Vertex[], edges: Edge[] } {
        const nodes = this.vertices;
        const edges = this.edges;
        if (selectedGroups.length === 0) {
            return {
                vertices: nodes,
                edges: edges
            };
        }
        const _selectedGroups = selectedGroups.map(item => item.toString())
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
            if (_selectedGroups.includes(node.group as string)) {
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

        const filteredNodes: Vertex[] = nodes.filter((node: Vertex) => nodesToKeep.has(node.id));
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
            vertices: filteredNodes,
            edges: filteredEdges,
        };
    }
}