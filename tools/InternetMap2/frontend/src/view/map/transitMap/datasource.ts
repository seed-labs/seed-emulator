import {DataSource as BaseDataSource, type Edge, type Vertex} from '@/utils/map-datasource.ts';
import type {EmulatorNetwork, EmulatorNode} from "@/utils/types.ts";

export class DataSource extends BaseDataSource {
    visDataSet(transitsNumber: number): { vertices: Vertex[], edges: Edge[] } {
        const allEdges: Edge[] = this.edges;
        const allVertices = this.vertices

        let newVerticeIds = new Set<string>()
        let newVertices: Vertex[] = []
        let newEdges: Edge[] = []
        let groups = new Set<string>()
        if (transitsNumber <= 0) {
            return {vertices: newVertices, edges: newEdges}
        }

        const {_nets, _nodes} = this.getter()
        const transitsWithWeight = this.dealTransitWeight(allVertices)
        for (const transit of transitsWithWeight) {
            groups.add(transit.group as string)
            if (groups.size > transitsNumber) {
                break
            }

            for (let i = allEdges.length - 1; i >= 0; i--) {
                const edge = allEdges[i] as Edge;
                if (edge.from !== transit.id) {
                    continue
                }
                const from = _nodes.find(item => item.Id === edge!.from) as EmulatorNode
                const to = _nets.find(item => item.Id === edge!.to) as EmulatorNetwork

                if (!from || !to) continue

                let nodeInfo = from.meta.emulatorInfo;
                let netInfo = to!.meta.emulatorInfo;
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
                    id: to!.Id,
                    label: netInfo.displayname ?? `${netInfo.scope}/${netInfo.name}`,
                    type: 'network',
                    shape: netInfo.type == 'global' ? 'star' : 'diamond',
                    object: to!,
                    collapsed: _netVertex!.collapsed,
                    borderWidth: _netVertex!.borderWidth
                };
                if (!newVerticeIds.has(to!.Id)) {
                    if (netInfo.type == 'local') {
                        netVertex.group = netInfo.scope;
                    }
                    newVerticeIds.add(to!.Id)
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

    visDataSetByAsn(AsnArray: number[]): { vertices: Vertex[], edges: Edge[] } {
        const allEdges: Edge[] = this.edges;
        const allVertices = this.vertices

        let newVerticeIds = new Set<string>()
        let newVertices: Vertex[] = []
        let newEdges: Edge[] = []
        if (AsnArray.length <= 0) {
            return {vertices: newVertices, edges: newEdges}
        }

        const {_nets, _nodes} = this.getter()
        const transitsWithWeight = this.dealTransitWeight(allVertices)
        for (const transit of transitsWithWeight) {
            const obj = transit.object as EmulatorNode
            if (!AsnArray.includes(obj.meta.emulatorInfo.asn)) {
                break
            }

            for (let i = allEdges.length - 1; i >= 0; i--) {
                const edge = allEdges[i] as Edge;
                if (edge.from !== transit.id) {
                    continue
                }
                const from = _nodes.find(item => item.Id === edge!.from) as EmulatorNode
                const to = _nets.find(item => item.Id === edge!.to) as EmulatorNetwork

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
                    id: to!.Id,
                    label: netInfo.displayname ?? `${netInfo.scope}/${netInfo.name}`,
                    type: 'network',
                    shape: netInfo.type == 'global' ? 'star' : 'diamond',
                    object: to!,
                    collapsed: _netVertex!.collapsed,
                    borderWidth: _netVertex!.borderWidth
                };
                if (!newVerticeIds.has(to!.Id)) {
                    if (netInfo.type == 'local') {
                        netVertex.group = netInfo.scope;
                    }
                    newVerticeIds.add(to!.Id)
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

        dataList.forEach(item => {
            if (item.shape === 'dot') {
                dotItems.push(item);
                groupCount[item.group as string] = (groupCount[item.group as string] || 0) + 1;
            }
        });

        return dotItems
            .map(item => ({...item, weight: groupCount[item.group as string]}))
            .sort((a, b) => {
                if (b.weight !== a.weight) {
                    return b.weight! - a.weight!;
                }
                return a.group!.localeCompare(b.group as string);
            });
    }
}