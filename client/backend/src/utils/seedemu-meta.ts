import 'dockerode';
import Dockerode from 'dockerode';

function parseJsonArrayString(jsonArrayString: string): string[] {
    try {
        const jsonArray = JSON.parse(jsonArrayString);
        
        // Check if the parsed JSON is an array
        if (Array.isArray(jsonArray)) {
            // Check if each element in the array is a string
            if (jsonArray.every((element) => typeof element === 'string')) {
                return jsonArray;
            } else {
                throw new Error('Array elements must be strings.');
            }
        } else {
            throw new Error('Input is not a valid JSON array.');
        }
    } catch (error) {
        console.error(`Error parsing JSON array string: ${error.message}`);
        return [];
    }
}

const META_PREFIX = 'org.seedsecuritylabs.seedemu.meta.';

export interface VertexMeta {
    displayname?: string;
    description?: string;
}

export interface SeedEmulatorNode extends VertexMeta {
    name?: string;
    role?: string;
    asn?: number;
    nets: {
        name?: string;
        address?: string;
    }[];
    classes: string[];
}

export interface SeedEmulatorNet extends VertexMeta {
    name?: string;
    scope?: string;
    type?: string;
    prefix?: string;
}

export interface SeedEmulatorMetadata {
    hasSession: boolean;
    emulatorInfo: SeedEmulatorNode;
}

export interface SeedContainerInfo extends Dockerode.ContainerInfo {
    meta: SeedEmulatorMetadata;
}

export interface SeedNetInfo extends Dockerode.NetworkInspectInfo {
    meta: {
        emulatorInfo: SeedEmulatorNet;
    }
}

/**
 * Class with helpers to parse metadata labels.
 */
export class Emulator {

    /**
     * parse node metadata.
     * 
     * @param labels labels, where key is label, and value is value.
     * @returns parsed node metadata object.
     */
    static ParseNodeMeta(labels: {
        [key: string]: string
    }): SeedEmulatorNode {
        var node: SeedEmulatorNode = {
            nets: [],
            classes: [],
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
            if (key === 'displayname') node.displayname = value;
            if (key === 'description') node.description = value;
            if (key === 'class') node.classes = parseJsonArrayString(value);
        });

        return node;
    }

    /**
     * parse network metadata.
     * 
     * @param labels labels, where key is label, and value is value.
     * @returns parsed network metadata.
     */
    static ParseNetMeta(labels: {
        [key: string]: string
    }): SeedEmulatorNet {
        var net: SeedEmulatorNet = {};

        Object.keys(labels).forEach(label => {
            if (!label.startsWith(META_PREFIX)) return;
            var key = label.replace(META_PREFIX, '');
            var value = labels[label];

            if (key === 'type') net.type = value;
            if (key === 'scope') net.scope = value;
            if (key === 'name') net.name = value;
            if (key === 'prefix') net.prefix = value;
            if (key === 'displayname') net.displayname = value;
            if (key === 'description') net.description = value;
        });        

        return net;
    }

};