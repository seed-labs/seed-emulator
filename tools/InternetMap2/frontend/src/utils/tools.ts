import {useRouter} from "vue-router";
import {ElLoading} from "element-plus";
import type {RouteRecord, NewRouteRecord} from "@/types/index.ts";

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

export const geoToXY = (lat: number, lon: number) => {
    const WIDTH = 2400
    const HEIGHT = 1200
    return {
        x: ((lon + 180) / 360) * WIDTH - WIDTH / 2,
        y: ((90 - lat) / 180) * HEIGHT - HEIGHT / 2
    }
}