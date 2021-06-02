import 'dockerode';
import Dockerode from 'dockerode';

const META_PREFIX = 'org.seedsecuritylabs.seedemu.meta.';

export interface SeedEmulatorNode {
    name?: string;
    role?: string;
    asn?: number;
    nets: {
        name?: string;
        address?: string;
    }[];
};

export interface SeedEmulatorMetadata {
    hasSession: boolean;
    nodeInfo: SeedEmulatorNode;
}

export interface SeedContainerInfo extends Dockerode.ContainerInfo {
    meta: SeedEmulatorMetadata;
}

export class Emulator {

    static ParseMeta(labels: {
        [key: string]: string
    }): SeedEmulatorNode {
        var node: SeedEmulatorNode = {
            nets: []
        };

        Object.keys(labels).forEach(label => {
            if (!label.startsWith(META_PREFIX)) return;
            var key = label.replace(META_PREFIX, '');
            var value = labels[label];

            if (key === 'asn') node.asn = Number.parseInt(value);
            if (key === 'nodename') node.name = value;
            if (key === 'role') node.role = value;
            if (key.startsWith('net.')) {
                var [_, i, item] = key.match(/net\.(\d+)\.(\S+)/);
                var ifindex = Number.parseInt(i);
                if (!node.nets[ifindex]) node.nets[ifindex] = {};
                if (item != 'name' && item != 'address') return;
                node.nets[ifindex][item] = value;
            }
        });

        return node;
    }

};