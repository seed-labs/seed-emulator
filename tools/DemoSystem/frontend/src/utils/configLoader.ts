// 配置类型定义
export interface ConfigModule {
    default?: any

    [key: string]: any
}

export interface LoadConfigOptions {
    // 是否启用缓存
    cache?: boolean
    // 缓存过期时间（毫秒）
    cacheExpiry?: number
    // 失败时重试次数
    retryCount?: number
    // 重试延迟（毫秒）
    retryDelay?: number
}

// 配置缓存接口
interface ConfigCacheItem {
    data: any
    timestamp: number
    expiry: number
}

// 使用 import.meta.glob 获取所有配置文件
// 这会自动扫描 src/extensions 目录下所有子目录中的 index.ts 文件
const configModules = import.meta.glob('@/extensions/**/index.ts', {
    eager: false,
    // import: 'default'  // 默认导入 default 导出
})

// 配置缓存
const configCache = new Map<string, ConfigCacheItem>()
const defaultCacheExpiry = 5 * 60 * 1000 // 5分钟

/**
 * 清理过期的缓存
 */
const cleanupExpiredCache = (): void => {
    const now = Date.now()
    for (const [key, item] of configCache.entries()) {
        if (now - item.timestamp > item.expiry) {
            configCache.delete(key)
        }
    }
}

/**
 * 从缓存获取配置
 */
const getFromCache = (key: string): any | null => {
    const item = configCache.get(key)
    if (!item) return null

    const now = Date.now()
    if (now - item.timestamp > item.expiry) {
        configCache.delete(key)
        return null
    }

    return item.data
}

/**
 * 设置缓存
 */
const setToCache = (key: string, data: any, expiry: number = defaultCacheExpiry): void => {
    configCache.set(key, {
        data,
        timestamp: Date.now(),
        expiry
    })

    // 定期清理缓存
    if (configCache.size > 100) {
        cleanupExpiredCache()
    }
}

/**
 * 标准化配置路径
 * 支持多种格式的路径输入：
 * - /yesterday_once_more/bgp
 * - yesterday_once_more/bgp
 * - yesterday_once_more/bgp/
 */
const normalizeConfigPath = (path: string): string => {
    // 移除开头和结尾的斜杠
    let normalized = path.replace(/^\/+|\/+$/g, '')

    // 移除 index.ts 后缀（如果存在）
    normalized = normalized.replace(/\/index\.ts$/, '')

    return normalized
}

/**
 * 查找匹配的模块路径
 */
const findMatchingModulePath = (configPath: string): string | null => {
    const normalizedPath = normalizeConfigPath(configPath)

    // 获取所有可能的模块路径
    const modulePaths = Object.keys(configModules)

    // 方法1：精确匹配
    for (const modulePath of modulePaths) {
        // 移除 @/extensions/ 前缀和 /index.ts 后缀
        const relativePath = modulePath
            .replace('@/extensions/', '')
            .replace('/index.ts', '')

        if (relativePath === normalizedPath) {
            return modulePath
        }
    }

    // 方法2：包含匹配（支持模糊匹配）
    for (const modulePath of modulePaths) {
        if (modulePath.includes(normalizedPath)) {
            return modulePath
        }
    }

    // 方法3：处理多层路径（如 bgp/subconfig）
    const parts = normalizedPath.split('/')
    if (parts.length > 1) {
        const lastPart = parts[parts.length - 1]
        for (const modulePath of modulePaths) {
            if (modulePath.includes(lastPart)) {
                return modulePath
            }
        }
    }

    return null
}

/**
 * 主函数：根据路径动态加载配置
 * @param configPath 配置路径
 * @returns 配置对象
 */
export const loadConfigByGlob = async (configPath: string): Promise<any> => {

    // 验证输入
    if (!configPath) {
        throw new Error('配置路径不能为空')
    }

    try {
        // 查找匹配的模块路径
        const modulePath = findMatchingModulePath(configPath)

        if (!modulePath) {
            console.warn(`未找到配置文件: ${configPath}`)
            console.debug('可用的配置路径:',
                Object.keys(configModules).map(p =>
                    p.replace('@/extensions/', '').replace('/index.ts', '')
                )
            )
            return null
        }

        console.debug(`开始加载配置: ${configPath}, 模块路径: ${modulePath}`)

        // 获取导入函数
        const importFn = configModules[modulePath]
        if (!importFn) {
            throw new Error(`未找到导入函数: ${modulePath}`)
        }

        // 执行导入
        const module = await importFn()

        // 处理导入结果
        let configData = {
            default: module.default,    // 默认导出
            ...module                   // 所有命名导出
        }
        if (module && typeof module === 'object' && 'default' in module) {
            // configData = module.default
            configData = module
        }

        console.debug(`成功加载配置: ${configPath}`)
        return configData

    } catch (error) {
        console.error(`加载配置失败: ${configPath}`, error)
        throw error
    }
}

/**
 * 批量加载多个配置
 */
export const loadMultipleConfigs = async (
    configPaths: string[],
): Promise<Record<string, any>> => {
    const results: Record<string, any> = {}
    const errors: Record<string, Error> = {}

    await Promise.all(
        configPaths.map(async (path) => {
            try {
                const config = await loadConfigByGlob(path)
                if (config) {
                    const key = path.replace(/^\/+|\/+$/g, '').replace(/\//g, '-')
                    results[key] = config
                }
            } catch (error) {
                errors[path] = error as Error
                console.error(`加载配置 ${path} 失败:`, error)
            }
        })
    )

    if (Object.keys(errors).length > 0) {
        console.warn('批量加载中有失败的配置:', errors)
    }

    return results
}

/**
 * 获取所有可用的配置路径
 */
export const getAvailableConfigPaths = (): string[] => {
    return Object.keys(configModules).map(modulePath =>
        modulePath
            .replace('@/extensions/', '')
            .replace('/index.ts', '')
    )
}

/**
 * 预加载所有配置（可用于优化首次加载）
 */
export const preloadAllConfigs = async (): Promise<void> => {
    console.debug('开始预加载所有配置...')

    const promises = Object.keys(configModules).map(async (modulePath) => {
        try {
            const importFn = configModules[modulePath]
            await importFn()
            console.debug(`预加载成功: ${modulePath}`)
        } catch (error) {
            console.warn(`预加载失败: ${modulePath}`, error)
        }
    })

    await Promise.all(promises)
    console.debug('所有配置预加载完成')
}

/**
 * 清除所有配置缓存
 */
export const clearAllCache = (): void => {
    configCache.clear()
    console.debug('已清除所有配置缓存')
}

/**
 * 获取缓存统计信息
 */
export const getCacheStats = (): {
    size: number
    keys: string[]
} => {
    return {
        size: configCache.size,
        keys: Array.from(configCache.keys())
    }
}