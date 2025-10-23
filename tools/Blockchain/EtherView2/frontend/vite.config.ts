import {loadEnv, defineConfig} from 'vite'
import vue from '@vitejs/plugin-vue'
import {resolve} from 'path'
import AutoImport from 'unplugin-auto-import/vite'
import Components from 'unplugin-vue-components/vite'
import {ElementPlusResolver} from 'unplugin-vue-components/resolvers'

const envDir = '.env'
export default defineConfig(({mode}) => {
    const env = loadEnv(mode, envDir)
    return {
        plugins: [
            vue(),
            // 自动按需导入 Element Plus 组件
            Components({
                resolvers: [ElementPlusResolver()],
            }),
            AutoImport({
                resolvers: [ElementPlusResolver()],
                // 也可以自动导入 Vue 的常用 API
                imports: ['vue', 'vue-router'],
            }),
        ],
        css: {
            preprocessorOptions: {
                scss: {
                    // 无需在组件中导入全局scss变量，可直接使用
                    additionalData: `@use "@/style/element/index.scss" as *;`,
                },
            },
        },
        resolve: {
            alias: {
                '@': resolve(__dirname, 'src')
            }
        },
        // 构建配置
        build: {
            outDir: '../server/static/frontend',
            // 构建前自动清空 outDir（默认在根目录下时为 true）
            emptyOutDir: true,
            assetsDir: 'assets',
            rollupOptions: {
                output: {
                    chunkFileNames: 'assets/js/[name]-[hash].js',
                    entryFileNames: 'assets/js/[name]-[hash].js',
                    assetFileNames: (assetInfo) => {
                        const extType = assetInfo.name.split('.')[1]
                        if (/png|jpe?g|svg|gif|tiff|bmp|ico/i.test(extType)) {
                            return 'assets/images/[name]-[hash][extname]'
                        }
                        if (/css/i.test(extType)) {
                            return 'assets/css/[name]-[hash][extname]'
                        }
                        return 'assets/[name]-[hash][extname]'
                    }
                }
            }
        },
        // 开发服务器配置（用于开发阶段）
        server: {
            cors: true,
            strictPort: true, // 端口被占用时直接报错，不会自动切换
            port: Number(env.VITE_APP_PORT) || 5173,
            open: env.VITE_OPEN === 'true',
            host: env.VITE_APP_HOST,
            proxy: {
                [env.VITE_APP_BASE_URL]: {
                    target: env.VITE_APP_SERVER,
                    // 是否开启跨域
                    changeOrigin: true,
                },
            },
        },
        // 静态资源的基础路径配置
        // base: env.VITE_STATIC_ASSET_PREFIX
        // base: env.NODE_ENV === 'production' ? '/frontend' : '/'
        // base: process.env.NODE_ENV === 'production' ? '/static/frontend/' : '/'
    }
})