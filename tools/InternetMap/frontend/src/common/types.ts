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
};

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
};

export interface InstallType {
    Id: string,
    meta: {
        baseInfo: {
            name: string,
        }
    }
}

export interface BgpPeer {
    name: string;
    protocolState: string;
    bgpState: string;
}