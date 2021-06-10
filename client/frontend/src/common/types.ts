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
            role: string
        };
    };
};

export interface EmulatorNetwork {
    Id: string;
    meta: {
        emulatorInfo: {
            type: string;
            scope: string;
            name: string;
            prefix: string;
        }
    }
};

export interface BgpPeer {
    name: string;
    protocolState: string;
    bgpState: string;
};