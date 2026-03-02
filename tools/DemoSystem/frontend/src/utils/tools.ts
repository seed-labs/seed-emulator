import {useRouter} from "vue-router";
import type {RouteRecord, NewRouteRecord} from "@/types/index.ts";
import {ElLoading, ElNotification} from "element-plus";
import {executeApiCall} from "@/hook";
import {
    reqHostExec,
    reqDockerExec,
    reqDockerExecCp,
    reqDockerComposeExec,
} from "@/api/docker";
import type {HostExec, DockerExec, DockerExecCp, DockerComposeExec} from "@/api/docker";

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

export interface MenuMeta {
    title: string
    img?: string
    description?: string
    video?: {
        src: string
        title: string
        description: string
    }
}

export interface MenuItem {
    name: string
    path: string
    meta: MenuMeta
    children?: MenuItem[]
}

export const findMenuByName = (
    menus: MenuItem[],
    name: string
): MenuItem | undefined => {
    for (const menu of menus) {
        if (menu.name === name) {
            return menu
        }

        if (menu.children?.length) {
            const found = findMenuByName(menu.children, name)
            if (found) return found
        }
    }

    return undefined
}
export const showNotification = (type: 'success' | 'warning' | 'info' | 'error' | '', message: string, title?: string) => {
    ElNotification({
        type,
        message,
        title
    })
}
export const AllLoading = () => {
    return ElLoading.service({
        lock: true,
        text: 'Loading…',
        background: 'rgba(0,0,0,0.3)',
        fullscreen: true
    })
}
export const sleep = (ms: number) => new Promise(resolve => setTimeout(resolve, ms));
export const dockerExec = async (params: { [key: string]: any }) => {
    const action = params.action || "exec"
    delete params.action;
    let ret
    switch (action) {
        case 'docker_cp':
            ret = await executeApiCall(() =>
                reqDockerExecCp(params as DockerExecCp)
            )
            break
        case 'docker_exec':
            ret = await executeApiCall(() =>
                reqDockerExec(params as DockerExec)
            )
            break
        case 'docker_compose':
            ret = await executeApiCall(() =>
                reqDockerComposeExec(params as DockerComposeExec)
            )
            break
        case 'host_exec':
            ret = await executeApiCall(() =>
                reqHostExec(params as HostExec)
            )
            break
        case 'terminal_exec':
            const msg = {
                type: "DEMO_SYSTEM_CTRL",
                cmd: params.cmd || "pwd",
                name: params.containerName
            }
            params.terminalIframeElement?.contentWindow?.postMessage(
                msg,
                '*'
            )
            ret = {ok: true, result: "ok"}
            break
        default:
            ret = {ok: false, result: `不支持的action: ${action}`}
    }

    return ret
}
export const getBirdConfigContent = (targetIPs: string[]) => {
    const base = `protocol static {
  ipv4 { table t_bgp;  };
`

    const routes = targetIPs
        .map((ip) => {
            const tIPs = splitCIDRInTwo(ip)

            return `
  route ${tIPs[0]} blackhole {
      bgp_large_community.add(LOCAL_COMM);
  };
  route ${tIPs[1]} blackhole {
      bgp_large_community.add(LOCAL_COMM);
  };`;
        })
        .join('');

    return `${base}${routes}
}`
}
export const splitCIDRInTwo = (cidr: string): [string, string] => {
    const [ip, prefixStr] = cidr.split('/');
    const prefix = parseInt(prefixStr!);

    if (prefix >= 32) {
        throw new Error(`Cannot split CIDR ${cidr}: prefix length must be less than 32`);
    }

    // 将 IP 地址转换为 32 位整数
    const ipToInt = (ip: string): number => {
        return ip.split('.')
            .reduce((acc, octet, idx) => acc + (parseInt(octet) << (24 - 8 * idx)), 0);
    };

    // 将整数转换为 IP 地址
    const intToIp = (n: number): string => {
        return [
            (n >>> 24) & 0xFF,
            (n >>> 16) & 0xFF,
            (n >>> 8) & 0xFF,
            n & 0xFF
        ].join('.');
    };

    const ipInt = ipToInt(ip!);
    const newPrefix = prefix + 1;
    const subnetSize = 1 << (32 - newPrefix); // 每个子网的大小

    // 第一个子网：原始网络地址
    const firstSubnet = `${intToIp(ipInt)}/${newPrefix}`;

    // 第二个子网：第一个子网地址 + 子网大小
    const secondSubnet = `${intToIp(ipInt + subnetSize)}/${newPrefix}`;

    return [firstSubnet, secondSubnet];
}