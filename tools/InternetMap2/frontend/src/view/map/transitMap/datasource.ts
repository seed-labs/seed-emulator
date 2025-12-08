import {DataSource as BaseDataSource, type Edge, type Vertex} from '@/utils/map-datasource.ts';

export class DataSource extends BaseDataSource {
    visDataSet(transitsNumber: number): { vertices: Vertex[], edges: Edge[] } {
        const allEdges: Edge[] = this.edges;
        const allVertices = this.vertices

        let newVerticeIds = new Set<string>()
        let newVertices = []
        let newEdges = []
        let groups = new Set<string>()
        if (transitsNumber <= 0) {
            return {vertices: newVertices, edges: newEdges}
        }

        const {_nets, _nodes} = this.getter()
        const transitsWithWeight = this.dealTransitWeight(allVertices)
        for (const transit of transitsWithWeight) {
            groups.add(transit.group)
            if (groups.size > transitsNumber) {
                break
            }

            for (let i = allEdges.length - 1; i >= 0; i--) {
                const edge = allEdges[i];
                if (edge.from !== transit.id) {
                    continue
                }
                const from = _nodes.find(item => item.Id === edge.from)
                const to = _nets.find(item => item.Id === edge.to)

                let nodeInfo = from.meta.emulatorInfo;
                let netInfo = to.meta.emulatorInfo;
                let nodeVertex: Vertex = {
                    id: from.Id,
                    label: nodeInfo.displayname ?? `${nodeInfo.asn}/${nodeInfo.name}`,
                    type: 'node',
                    shape: ['Router', 'BorderRouter'].includes(nodeInfo.role) ? 'dot' : 'hexagon',
                    object: from,
                    collapsed: false,
                    custom: nodeInfo.custom
                };
                if (!newVerticeIds.has(from.Id)) {
                    newVerticeIds.add(from.Id)
                    newVertices.push(nodeVertex)
                    nodeVertex.group = nodeInfo.asn.toString();
                }
                const _netVertex = allVertices.find(item => item.id === to.Id)
                let netVertex: Vertex = {
                    id: to.Id,
                    label: netInfo.displayname ?? `${netInfo.scope}/${netInfo.name}`,
                    type: 'network',
                    shape: netInfo.type == 'global' ? 'star' : 'diamond',
                    object: to,
                    collapsed: _netVertex!.collapsed,
                    borderWidth: _netVertex!.borderWidth
                };
                if (!newVerticeIds.has(to.Id)) {
                    if (netInfo.type == 'local') {
                        netVertex.group = netInfo.scope;
                    }
                    newVerticeIds.add(to.Id)
                    newVertices.push(netVertex)
                }
                newEdges.push(edge)
                allEdges.splice(i, 1);
            }
        }

        const _newEdges = this.connectExistingTopology(allVertices, allEdges, newVertices, newEdges)
        newVertices.push(...allVertices.filter(item => {
            if (item.shape !== 'star') {
                return false
            } else {
                return !newVertices.find(n => n.id === item.id);
            }
        }))

        return {vertices: newVertices, edges: _newEdges};
    }

    dealTransitWeight(dataList: Vertex[]) {
        const groupCount: { [key: string]: number } = {};
        const dotItems: Vertex[] = [];

        // 一次循环完成筛选和统计
        dataList.forEach(item => {
            if (item.shape === 'dot') {
                dotItems.push(item);
                groupCount[item.group] = (groupCount[item.group] || 0) + 1;
            }
        });

        // 更新 weight 并排序
        return dotItems
            .map(item => ({...item, weight: groupCount[item.group]}))
            .sort((a, b) => {
                // 首先按 weight 降序排列
                if (b.weight !== a.weight) {
                    return b.weight - a.weight;
                }
                // 如果 weight 相同，按 group 排序，确保同一 group 在一起
                return a.group.localeCompare(b.group);
            });
    }
}