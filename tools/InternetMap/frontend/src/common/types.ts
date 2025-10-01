export interface EmulatorNode {
    Id: string;
    NetworkSettings: {
        Networks: {
            [name: string]: {
                NetworkID: string,
                MacAddress: string
            }
        }
    };
    meta: {
        emulatorInfo: {
            nets: {
                name: string,
                address: string
            }[],
            asn: number,
            name: string,
            role: string,
            custom?: string,
            description?: string,
            displayname?: string
        };
        relation?: {
            parent: Set<string>,
        };
    };
}

export interface EmulatorNetwork {
    Id: string;
    meta: {
        emulatorInfo: {
            type: string,
            scope: string,
            name: string,
            prefix: string,
            description?: string,
            displayname?: string
        },
        relation?: {
            parent: Set<string>,
        },
    }
}

export interface IPlugin {
    id: string;
    name: string;
    version: string;
    entryPoint: string;
    description?: string;
    activate?: () => void;
    deactivate?: () => void;
}

export interface BgpPeer {
    name: string;
    protocolState: string;
    bgpState: string;
}