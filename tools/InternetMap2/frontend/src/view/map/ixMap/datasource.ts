import {DataSource as BaseDataSource, type Edge, type Vertex} from '@/utils/map-datasource.ts';

export class DataSource extends BaseDataSource {
    visDataSet(ixsNumber: number): { vertices: Vertex[], edges: Edge[] } {
        const allEdges: Edge[] = this.edges;
        const allVertices = this.vertices
        const ixs = this.ixs

        let newVertices: Vertex[] = []
        let newEdges: Edge[] = []
        if (ixsNumber <= 0) {
            return {vertices: newVertices, edges: newEdges}
        } else if (ixsNumber > ixs.length) {
            ixsNumber = ixs.length
        }

        const {_nets} = this.getter()

        let displayIxIds: string[]
        if (ixs.length > ixsNumber) {
            let values = Array.from(this.generateStarNodeAnalysisReport(allVertices, allEdges).values())
            values.sort((a, b) => b.allUniqueDotNodes.length - a.allUniqueDotNodes.length)
            displayIxIds = values.slice(0, ixsNumber).map(item => item.starNode)
        } else {
            displayIxIds = ixs.map(item => item.Id)
        }
        displayIxIds.forEach(id => {
            const net = _nets.find(item => item.Id === id)
            const netInfo = net.meta.emulatorInfo;

            let netVertex: Vertex = {
                id: id,
                label: netInfo.displayname ?? `${netInfo.scope}/${netInfo.name}`,
                type: 'network',
                shape: 'star',
                object: net,
            };
            netVertex.group = netInfo.scope;
            newVertices.push(netVertex)
        })

        const _newEdges = this.connectExistingTopology(allVertices, allEdges, newVertices, newEdges)

        return {vertices: newVertices, edges: _newEdges};
    }

    generateStarNodeAnalysisReport(originalNodes: Vertex[], originalEdges: Edge[]): Map<string, {
        starNode: string;
        directConnections: Map<string, { paths: string[][]; allDotNodes: string[]; pathCount: number }>;
        allUniqueDotNodes: string[]
    }> {
        // 构建图的邻接表（双向）
        const buildGraph = (edges: Edge[]): Map<string, string[]> => {
            const graph = new Map<string, string[]>();

            edges.forEach(edge => {
                if (edge.from === edge.to) return;

                if (!graph.has(edge.from)) {
                    graph.set(edge.from, []);
                }
                if (!graph.has(edge.to)) {
                    graph.set(edge.to, []);
                }
                graph.get(edge.from)!.push(edge.to);
                graph.get(edge.to)!.push(edge.from);
            });

            return graph;
        };

// 检查路径是否经过其他 star 节点（除了起点和终点）
        const pathPassesThroughOtherStar = (
            path: string[],
            startStar: string,
            endStar: string,
            nodeMap: Map<string, Vertex>
        ): boolean => {
            // 检查路径的中间节点（排除起点和终点）
            for (let i = 1; i < path.length - 1; i++) {
                const nodeId = path[i];
                const node = nodeMap.get(nodeId);
                if (node && node.shape === 'star') {
                    return true; // 路径中经过了其他 star 节点
                }
            }
            return false;
        };

// 查找两个节点之间的所有不重复路径，且不经过其他 star 节点
        const findAllDirectPathsBetweenStars = (
            graph: Map<string, string[]>,
            start: string,
            end: string,
            nodeMap: Map<string, Vertex>,
            maxDepth: number = 10
        ): string[][] => {
            if (start === end) return [];

            const paths: string[][] = [];
            const visited = new Set<string>();

            const dfs = (current: string, path: string[], depth: number) => {
                if (depth > maxDepth) return;

                // 如果当前节点是 star 节点但不是起点和终点，说明经过了其他 star 节点，停止搜索
                if (current !== start && current !== end) {
                    const node = nodeMap.get(current);
                    if (node && node.shape === 'star') {
                        return;
                    }
                }

                if (current === end) {
                    paths.push([...path]);
                    return;
                }

                visited.add(current);

                const neighbors = graph.get(current) || [];
                for (const neighbor of neighbors) {
                    if (!visited.has(neighbor)) {
                        path.push(neighbor);
                        dfs(neighbor, path, depth + 1);
                        path.pop();
                    }
                }

                visited.delete(current);
            };

            dfs(start, [start], 0);
            return paths;
        };

// 从路径中提取所有不同的 dot 节点
        const extractDotNodesFromPath = (path: string[], nodeMap: Map<string, Vertex>): string[] => {
            const dotNodes = new Set<string>();

            // 排除起点和终点（都是 star 节点），只检查中间节点
            for (let i = 1; i < path.length - 1; i++) {
                const nodeId = path[i];
                const node = nodeMap.get(nodeId);
                if (node && node.shape === 'dot') {
                    dotNodes.add(nodeId);
                }
            }

            return Array.from(dotNodes);
        };

// 分析单个 star 节点到其他直接可达 star 节点的所有路径
        const analyzeStarNodeDirectPaths = (
            starNode: string,
            allStarNodes: string[],
            graph: Map<string, string[]>,
            nodeMap: Map<string, Vertex>
        ): {
            starNode: string;
            directConnections: Map<string, {
                paths: string[][];
                allDotNodes: string[]; // 所有路径中出现的不同 dot 节点
                pathCount: number;
            }>;
            allUniqueDotNodes: string[]; // 该 star 节点到所有直接可达 star 节点经过的所有不同 dot 节点
        } => {
            const directConnections = new Map<string, {
                paths: string[][];
                allDotNodes: string[];
                pathCount: number;
            }>();

            const allDotNodesForThisStar = new Set<string>();

            // 分析到每个其他 star 节点的所有直接路径（不经过其他 star 节点）
            for (const targetStar of allStarNodes) {
                if (targetStar === starNode) continue;

                const allPaths = findAllDirectPathsBetweenStars(graph, starNode, targetStar, nodeMap);

                // 过滤掉经过其他 star 节点的路径（双重检查）
                const validPaths = allPaths.filter(path =>
                    !pathPassesThroughOtherStar(path, starNode, targetStar, nodeMap)
                );

                if (validPaths.length > 0) {
                    // 收集所有路径中的 dot 节点
                    const dotNodesForThisConnection = new Set<string>();

                    validPaths.forEach(path => {
                        const dotNodesInPath = extractDotNodesFromPath(path, nodeMap);
                        dotNodesInPath.forEach(dotNode => {
                            dotNodesForThisConnection.add(dotNode);
                            allDotNodesForThisStar.add(dotNode);
                        });
                    });

                    directConnections.set(targetStar, {
                        paths: validPaths,
                        allDotNodes: Array.from(dotNodesForThisConnection),
                        pathCount: validPaths.length
                    });
                }
            }

            return {
                starNode,
                directConnections,
                allUniqueDotNodes: Array.from(allDotNodesForThisStar)
            };
        };

// 主函数：分析所有 star 节点的直接可达路径
        const analyzeAllStarNodesDirectPaths = (
            originalNodes: Vertex[],
            originalEdges: Edge[]
        ): Map<string, {
            starNode: string;
            directConnections: Map<string, {
                paths: string[][];
                allDotNodes: string[];
                pathCount: number;
            }>;
            allUniqueDotNodes: string[];
        }> => {
            const nodeMap = new Map(originalNodes.map(node => [node.id, node]));
            const graph = buildGraph(originalEdges);

            // 找出所有 shape 为 'star' 的节点
            const starNodes = originalNodes
                .filter(node => node.shape === 'star')
                .map(node => node.id);

            const results = new Map<string, {
                starNode: string;
                directConnections: Map<string, {
                    paths: string[][];
                    allDotNodes: string[];
                    pathCount: number;
                }>;
                allUniqueDotNodes: string[];
            }>();

            // 分析每个 star 节点
            starNodes.forEach(starNode => {
                const analysis = analyzeStarNodeDirectPaths(
                    starNode,
                    starNodes,
                    graph,
                    nodeMap
                );

                results.set(starNode, analysis);
            });

            return results;
        };

// 生成详细的报告
        const generateDirectPathsAnalysisReport = (
            originalNodes: Vertex[],
            originalEdges: Edge[]
        ): Map<string, {
            starNode: string;
            directConnections: Map<string, { paths: string[][]; allDotNodes: string[]; pathCount: number }>;
            allUniqueDotNodes: string[]
        }> => {
            return analyzeAllStarNodesDirectPaths(originalNodes, originalEdges)
            // const nodeMap = new Map(originalNodes.map(node => [node.id, node]));
            // console.log('=== 每个 Star 节点到其他直接可达 Star 节点的路径分析报告 ===\n');

            // results.forEach((analysis, starNode) => {
            //     const nodeInfo = nodeMap.get(starNode);
            //     console.log(`⭐ Star 节点: ${starNode} (${nodeInfo?.label || '未知'})`);
            //     console.log(`   所有路径中经过的不同 Dot 节点: ${analysis.allUniqueDotNodes.length} 个`);
            // });
        };

        return generateDirectPathsAnalysisReport(originalNodes, originalEdges);
    }
}