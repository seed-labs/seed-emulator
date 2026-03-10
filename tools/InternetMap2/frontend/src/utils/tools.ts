import {useRouter} from "vue-router";
import {ElLoading} from "element-plus";
import type {RouteRecord, NewRouteRecord} from "@/types/index.ts";
import type {EmulatorNetwork, EmulatorNode} from "@/utils/types.ts";

// 按path 查找路由对象
export const getRouteByPath = (path: string) => {
    const router = useRouter()
    const routes = router.getRoutes()
    return routes.find(route => route.path === path)
}
// 将路由的所有最底层item插入到同一个列表
export const RouterToListItem = (routes: RouteRecord[]) => {
    const result: NewRouteRecord[] = [];

    const walk = (list: RouteRecord[]) => {
        for (const item of list) {
            // 先把当前节点加入结果（如果不想保留父节点可以自行过滤）
            result.push({
                title: item.meta?.title,
                name: item.path,
                content: item.meta?.componentName as string,
                icon: item.meta?.icon,
                type: 'element',
            });
            // 若存在 children，递归处理
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
            // 标准化路径比较（处理开头斜杠）
            const normalizedRoutePath = route.path.startsWith('/') ? route.path : `/${route.path}`
            const normalizedTargetPath = currentPath.startsWith('/') ? currentPath : `/${currentPath}`

            // 检查是否匹配当前路由
            if (normalizedRoutePath === normalizedTargetPath) {
                result.push(...parents, route)
                return true
            }

            // 如果有子路由，递归查找
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
// 读取环境变量
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
        // 转换为16进制字符串，并确保长度为64字符（类似SHA-256）
        const hashHex = Math.abs(hash).toString(16).padStart(8, '0');
        // 重复几次以达到类似SHA-256的长度
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
            console.log("警告: compose文件中没有网络定义");
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

            // 保存映射关系
            networkNameToId[fullNetName] = netId;

            // Extract emulator info from labels
            const emulatorInfo = {
                name: labels['org.seedsecuritylabs.seedemu.meta.name'] || '',
                prefix: labels['org.seedsecuritylabs.seedemu.meta.prefix'] || subnet,
                scope: labels['org.seedsecuritylabs.seedemu.meta.scope'] || '',
                type: labels['org.seedsecuritylabs.seedemu.meta.type'] || 'local'
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
     * 检查节点是否有效
     * 要求：meta.emulatorInfo.name 存在且不是空字符串
     */
    function isValidNode(labels: Record<string, any>): boolean {
        // 检查 nodename 是否存在且不是空字符串
        const nodeName = labels['org.seedsecuritylabs.seedemu.meta.nodename'];

        // 如果是 undefined 或者 null，返回 false
        if (nodeName === undefined || nodeName === null) {
            return false;
        }

        // 去除空白字符后检查是否为空
        if (typeof nodeName === 'string' && nodeName.trim() === '') {
            return false;
        }

        // 检查是否有网络配置
        let hasNetwork = false;
        for (const key in labels) {
            if (key.startsWith('org.seedsecuritylabs.seedemu.meta.net.')) {
                hasNetwork = true;
                break;
            }
        }

        // 必须有名称，至少有一个网络配置
        return Boolean(nodeName) && hasNetwork;
    }

    /**
     * 获取节点名称，返回去除空白字符后的值
     */
    function getNodeName(labels: Record<string, any>): string {
        const nodeName = labels['org.seedsecuritylabs.seedemu.meta.nodename'] || '';
        if (typeof nodeName === 'string') {
            return nodeName.trim();
        }
        return String(nodeName);
    }

    /**
     * Create node entries from compose data，只保留有效的节点
     */
    function createNodes(
        composeData: ComposeData,
        networkNameToId: NetworkNameToId,
        project: string = "demo_output"
    ): [EmulatorNode[], SkippedNode[]] {
        const nodes: EmulatorNode[] = [];
        const skippedNodes: SkippedNode[] = [];

        if (!composeData.services) {
            console.log("警告: compose文件中没有服务定义");
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

            // 获取标签
            const labels = svcConfig.labels || {};

            // 获取节点名称用于检查
            const nodeName = getNodeName(labels);
            const containerName = svcConfig.container_name || svcName;

            // 检查节点是否有效
            if (!isValidNode(labels)) {
                let skipReason = '';
                if (!nodeName) {
                    skipReason = 'meta.emulatorInfo.name为空';
                } else if (nodeName.trim() === '') {
                    skipReason = 'meta.emulatorInfo.name为空字符串';
                } else {
                    skipReason = '没有网络配置';
                }
                skippedNodes.push({
                    name: containerName,
                    node_name: nodeName,
                    reason: skipReason
                });
                continue;
            }

            // 生成节点ID
            const nodeId = generateId(`${project}_${svcName}_${containerName}`);

            // 获取镜像名称
            const image = svcConfig.image || svcName;

            // 构建Names数组 - 格式为 ["/容器名称"]
            const names: string[] = [];
            if (containerName) {
                names.push(`/${containerName}`);
            }

            // 构建网络设置
            const netSettings: { Networks: Record<string, any> } = {Networks: {}};
            let networkMode = "";

            if (svcConfig.networks) {
                for (const [netName, netCfg] of Object.entries(svcConfig.networks)) {
                    const fullNetName = `${project}_${netName}`;

                    // 获取IP地址
                    let ip = '';
                    if (typeof netCfg === 'object' && netCfg !== null) {
                        ip = (netCfg as any).ipv4_address || '';
                    }

                    // 获取网络ID - 确保不为空
                    let networkId = networkNameToId[fullNetName];
                    if (!networkId) {
                        console.log(`警告: 网络 ${fullNetName} 的ID未找到，将生成新的ID`);
                        networkId = generateId(fullNetName);
                    }

                    // 设置网络模式为第一个网络
                    if (!networkMode) {
                        networkMode = fullNetName;
                    }

                    // 计算网关地址
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

            // 从标签中提取网络信息
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

            // 构建节点对象
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