import {DataSource as BaseDataSource, type Edge, type Vertex} from '@/utils/map-datasource.ts';
import type {EmulatorNetwork} from "@/utils/types.ts";
import {dealTransitWeight} from "@/utils/tools.ts";

export class DataSource extends BaseDataSource {
    visDataSet(ixsNumber: number): { vertices: Vertex[], edges: Edge[] } {
        const selectedStarLabels = this.ixs.map(v => v.meta.emulatorInfo.name).slice(0, ixsNumber)
        return this.visDataSetByIX([...selectedStarLabels])
    }

    visDataSetByIX(selectedStarLabels: string[]): { vertices: Vertex[]; edges: Edge[] } {
        const nodes = this.vertices
        const edges = this.edges

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
            vertices: filteredNodes,
            edges: filteredEdges,
        };
    }
}