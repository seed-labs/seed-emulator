import {useRouter} from "vue-router";
import {ElLoading} from "element-plus";
import type {RouteRecord, NewRouteRecord} from "@/types/index.ts";
import type {EmulatorNetwork, EmulatorNode} from "@/utils/types.ts";
import {type Vertex} from '@/utils/map-datasource.ts';

export const getRouteByPath = (path: string) => {
    const router = useRouter()
    const routes = router.getRoutes()
    return routes.find(route => route.path === path)
}

export const RouterToListItem = (routes: RouteRecord[]) => {
    const result: NewRouteRecord[] = [];

    const walk = (list: RouteRecord[]) => {
        for (const item of list) {
            result.push({
                title: item.meta?.title,
                name: item.path,
                content: item.meta?.componentName as string,
                icon: item.meta?.icon,
                type: 'element',
            });
            if (item.children && item.children.length > 0) {
                walk(item.children);
            }
        }
    };

    walk(routes);
    return result;
}
export const findRouteWithParents = (path: string, routes: RouteRecord[]): RouteRecord[] => {
    const result: RouteRecord[] = []

    const findRecursive = (currentRoutes: RouteRecord[], currentPath: string, parents: RouteRecord[] = []): boolean => {
        for (const route of currentRoutes) {
            const normalizedRoutePath = route.path.startsWith('/') ? route.path : `/${route.path}`
            const normalizedTargetPath = currentPath.startsWith('/') ? currentPath : `/${currentPath}`

            if (normalizedRoutePath === normalizedTargetPath) {
                result.push(...parents, route)
                return true
            }

            if (route.children && route.children.length > 0) {
                const found = findRecursive(route.children, currentPath, [...parents, route])
                if (found) return true
            }
        }
        return false
    }

    findRecursive(routes, path)
    return result
}

const proxyAddress = import.meta.env.MODE === 'development' ? import.meta.env.VITE_PROXY_ADDRESS : location.host
export const getImgUrl = (path: string | undefined) => {
    if (!path || import.meta.env.MODE !== "development") {
        return ''
    }
    if (path?.startsWith("http")) {
        return path
    } else {
        return `${proxyAddress}/${path}`
    }
}
export const allLoading = () => {
    return ElLoading.service({
        lock: true,
        text: 'Loading…',
        background: 'rgba(0,0,0,0.3)',
        fullscreen: true
    })
}
export const getSocket = (protocol: string = 'ws', uri: string = '/host'): WebSocket => {
    const host = import.meta.env.MODE === 'development' ? import.meta.env.VITE_PROXY_ADDRESS.replace(/^https?:\/\//, '') : location.host
    return new WebSocket(`${protocol}://${host}${import.meta.env.VITE_SERVER_URL_PREFIX}${uri}`);
}

export interface ComposeData {
    services?: Record<string, any>;
    networks?: Record<string, any>;

    [key: string]: any;
}

export function genVisData(composeData: ComposeData, projectName = "demo_output"): {
    nodes: EmulatorNode[];
    nets: EmulatorNetwork[]
} {

    interface SkippedNode {
        name: string;
        node_name?: string;
        reason: string;
    }

    interface NetworkNameToId {
        [key: string]: string;
    }

    /**
     * Generate a deterministic ID based on seed
     */
    function generateId(seed: string): string {
        let hash = 0;
        for (let i = 0; i < seed.length; i++) {
            const char = seed.charCodeAt(i);
            hash = ((hash << 5) - hash) + char;
            hash = hash & hash; // Convert to 32-bit integer
        }
        const hashHex = Math.abs(hash).toString(16).padStart(8, '0');
        return hashHex.repeat(8).substring(0, 64);
    }

    /**
     * Generate a random MAC address
     */
    function generateMacAddress(): string {
        const mac = [
            0x00, 0x16, 0x3e,
            Math.floor(Math.random() * 0x7f),
            Math.floor(Math.random() * 0xff),
            Math.floor(Math.random() * 0xff)
        ];
        return mac.map(x => x.toString(16).padStart(2, '0')).join(':');
    }

    /**
     * Create network entries from compose data
     */
    function createNetworks(composeData: ComposeData, project: string = "demo_output"): [EmulatorNetwork[], NetworkNameToId] {
        const networks: EmulatorNetwork[] = [];
        const networkNameToId: NetworkNameToId = {};

        if (!composeData.networks) {
            console.log("Warning: There is no network definition in the compose file.");
            return [networks, networkNameToId];
        }

        for (const [netName, netConfig] of Object.entries(composeData.networks)) {
            if (!netConfig.ipam?.config?.[0]?.subnet) {
                continue;
            }

            const subnet = netConfig.ipam.config[0].subnet;
            const fullNetName = `${project}_${netName}`;
            const netId = generateId(fullNetName);
            const labels = netConfig.labels || {};

            networkNameToId[fullNetName] = netId;

            // Extract emulator info from labels
            const emulatorInfo = {
                name: labels['org.seedsecuritylabs.seedemu.meta.name'] || '',
                prefix: labels['org.seedsecuritylabs.seedemu.meta.prefix'] || subnet,
                scope: labels['org.seedsecuritylabs.seedemu.meta.scope'] || '',
                type: labels['org.seedsecuritylabs.seedemu.meta.type'] || 'local',
                displayname: labels['org.seedsecuritylabs.seedemu.meta.displayname'] || '',
            };

            const network: EmulatorNetwork = {
                Name: fullNetName,
                Id: netId,
                Created: new Date().toISOString().replace('Z', '+08:00'),
                Scope: "local",
                Driver: "bridge",
                EnableIPv4: true,
                EnableIPv6: false,
                IPAM: {
                    Driver: "default",
                    Options: null,
                    Config: [{Subnet: subnet}]
                },
                Internal: false,
                Attachable: false,
                Ingress: false,
                ConfigFrom: {Network: ""},
                ConfigOnly: false,
                Containers: {},
                Options: {"com.docker.network.driver.mtu": "1500"},
                Labels: labels,
                meta: {
                    emulatorInfo: emulatorInfo,
                    relation: {parent: {}}
                }
            };

            networks.push(network);
        }

        return [networks, networkNameToId];
    }

    /**
     * Check whether the check node is valid
     * Requirement: The meta.emulatorInfo.name exists and is not an empty string
     */
    function isValidNode(labels: Record<string, any>): boolean {
        const nodeName = labels['org.seedsecuritylabs.seedemu.meta.nodename'];

        if (nodeName === undefined || nodeName === null) {
            return false;
        }

        if (typeof nodeName === 'string' && nodeName.trim() === '') {
            return false;
        }

        let hasNetwork = false;
        for (const key in labels) {
            if (key.startsWith('org.seedsecuritylabs.seedemu.meta.net.')) {
                hasNetwork = true;
                break;
            }
        }

        return Boolean(nodeName) && hasNetwork;
    }

    function getNodeName(labels: Record<string, any>): string {
        const nodeName = labels['org.seedsecuritylabs.seedemu.meta.nodename'] || '';
        if (typeof nodeName === 'string') {
            return nodeName.trim();
        }
        return String(nodeName);
    }

    function createNodes(
        composeData: ComposeData,
        networkNameToId: NetworkNameToId,
        project: string = "demo_output"
    ): [EmulatorNode[], SkippedNode[]] {
        const nodes: EmulatorNode[] = [];
        const skippedNodes: SkippedNode[] = [];

        if (!composeData.services) {
            console.log("Warning: There are no service definitions in the compose file.");
            return [nodes, skippedNodes];
        }

        for (const [svcName, svcConfig] of Object.entries(composeData.services)) {
            // Skip dummy services
            if (['39e016aa9e819f203ebc1809245a5818', '98a2693c996c2294358552f48373498d'].includes(svcName)) {
                skippedNodes.push({
                    name: svcName,
                    reason: 'dummy service'
                });
                continue;
            }

            const labels = svcConfig.labels || {};
            const nodeName = getNodeName(labels);
            const containerName = svcConfig.container_name || svcName;

            if (!isValidNode(labels)) {
                let skipReason = '';
                if (!nodeName) {
                    skipReason = 'meta.emulatorInfo.name is null ';
                } else if (nodeName.trim() === '') {
                    skipReason = 'meta.emulatorInfo.name is an empty string';
                } else {
                    skipReason = 'No network configuration';
                }
                skippedNodes.push({
                    name: containerName,
                    node_name: nodeName,
                    reason: skipReason
                });
                continue;
            }

            const nodeId = generateId(`${project}_${svcName}_${containerName}`);
            const image = svcConfig.image || svcName;
            const names: string[] = [];
            if (containerName) {
                names.push(`/${containerName}`);
            }

            const netSettings: { Networks: Record<string, any> } = {Networks: {}};
            let networkMode = "";

            if (svcConfig.networks) {
                for (const [netName, netCfg] of Object.entries(svcConfig.networks)) {
                    const fullNetName = `${project}_${netName}`;

                    let ip = '';
                    if (typeof netCfg === 'object' && netCfg !== null) {
                        ip = (netCfg as any).ipv4_address || '';
                    }

                    let networkId = networkNameToId[fullNetName];
                    if (!networkId) {
                        console.log(`Warning: The ID of the network ${fullNetName} could not be found. A new ID will be generated.`);
                        networkId = generateId(fullNetName);
                    }

                    if (!networkMode) {
                        networkMode = fullNetName;
                    }

                    let gateway = '';
                    if (ip) {
                        const ipParts = ip.split('.');
                        if (ipParts.length === 4) {
                            gateway = `${ipParts[0]}.${ipParts[1]}.${ipParts[2]}.1`;
                        }
                    }

                    netSettings.Networks[fullNetName] = {
                        IPAMConfig: ip ? {IPv4Address: ip} : null,
                        Links: null,
                        Aliases: null,
                        MacAddress: generateMacAddress(),
                        DriverOpts: null,
                        GwPriority: 0,
                        NetworkID: networkId,
                        EndpointID: generateId(`${nodeId}_${netName}_endpoint`),
                        Gateway: gateway,
                        IPAddress: ip,
                        IPPrefixLen: 24,
                        IPv6Gateway: "",
                        GlobalIPv6Address: "",
                        GlobalIPv6PrefixLen: 0,
                        DNSNames: null
                    };
                }
            }

            const netsInfo: Array<{ name: string; address: string }> = [];
            for (let i = 0; i < 10; i++) { // Check up to 10 networks
                const nameKey = `org.seedsecuritylabs.seedemu.meta.net.${i}.name`;
                const addrKey = `org.seedsecuritylabs.seedemu.meta.net.${i}.address`;
                if (nameKey in labels && addrKey in labels) {
                    netsInfo.push({
                        name: labels[nameKey],
                        address: labels[addrKey]
                    });
                }
            }

            const node: EmulatorNode = {
                Id: nodeId,
                Names: names,
                Image: image,
                ImageID: `sha256:${generateId(image)}`,
                Command: "/start.sh",
                Created: Math.floor(Date.now() / 1000) - Math.floor(Math.random() * 100000) - 100000,
                Ports: [],
                Labels: labels,
                State: "running",
                Status: `Up ${Math.floor(Math.random() * 30) + 20} hours`,
                HostConfig: {NetworkMode: networkMode},
                NetworkSettings: netSettings,
                Mounts: [],
                meta: {
                    emulatorInfo: {
                        nets: netsInfo,
                        asn: Number(labels['org.seedsecuritylabs.seedemu.meta.asn'] || 0),
                        name: nodeName,
                        role: labels['org.seedsecuritylabs.seedemu.meta.role'] || ''
                    },
                    relation: {parent: {}}
                }
            };

            nodes.push(node);
        }

        return [nodes, skippedNodes];
    }

    if (!composeData) {
        return {
            nodes: [],
            nets: []
        };
    }

    const [networks, networkNameToId] = createNetworks(composeData, projectName);
    let count = 0;
    for (const [netName, netId] of Object.entries(networkNameToId)) {
        if (count >= 5) break;
        console.log(`  ${netName} -> ${netId.substring(0, 16)}...`);
        count++;
    }
    const [nodes, skippedNodes] = createNodes(composeData, networkNameToId, projectName);

    // Build final data
    return {
        nodes: nodes,
        nets: networks
    }
}

export function dealTransitWeight(dataList: Vertex[]) {
    const groupCount: { [key: string]: number } = {};
    const dotItems: Vertex[] = [];
    const regex = /^r\d+$/;
    dataList.forEach(item => {
        if (item.shape === 'dot' && regex.test(item.object.meta.emulatorInfo.name)) {
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