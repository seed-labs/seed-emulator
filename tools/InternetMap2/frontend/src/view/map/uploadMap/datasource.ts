import {DataSource as BaseDataSource, type Edge, META_CLASS, type Vertex} from '@/utils/map-datasource.ts';
import type {EmulatorNetwork, EmulatorNode, VisData} from "@/utils/types.ts";

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
}