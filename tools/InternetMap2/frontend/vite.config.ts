import path from 'path'
import vue from '@vitejs/plugin-vue'
import {loadEnv, defineConfig} from 'vite'
import AutoImport from 'unplugin-auto-import/vite'
import Components from 'unplugin-vue-components/vite'
import {ElementPlusResolver} from 'unplugin-vue-components/resolvers'

const envDir = 'env'
export default defineConfig(({mode}) => {
    const env = loadEnv(mode, envDir)
    return {
        preflight: false,
        lintOnSave: false,
        envDir: envDir,
        plugins: [
            vue(),
            Components({
                resolvers: [ElementPlusResolver()],
            }),
            AutoImport({
                resolvers: [ElementPlusResolver()],
                imports: ['vue', 'vue-router'],
            }),
        ],
        resolve: {
            alias: {
                "@": path.resolve(__dirname, "./src"),
            }
        },
        css: {
            preprocessorOptions: {
                scss: {
                    silenceDeprecations: ['legacy-js-api'],
                    javascriptEnables: true,
                }
            }
        },
        server: {
            cors: true,
            strictPort: true,
            port: Number(env.VITE_FRONTEND_PORT) || 5173,
            open: env.VITE_FRONTEND_OPEN === 'true',
            host: env.VITE_FRONTEND_HOST,
            proxy: {
                [env.VITE_SERVER_URL_PREFIX]: {
                    target: env.VITE_PROXY_ADDRESS,
                    changeOrigin: true,
                    // rewrite: (path) => path.replace(new RegExp(env.VITE_APP_BASE_URL), ''),
                },
            },
        },
        build: {
            outDir: env.VITE_BUILD_OUTPUT_PATH,
            assetsDir: 'assets',
            rollupOptions: {
                output: {
                    chunkFileNames: 'assets/js/[name]-[hash].js',
                    entryFileNames: 'assets/js/[name]-[hash].js',
                    assetFileNames: ({name}) => {
                        const fileName = name || 'asset'
                        const extType = fileName.split('.').pop()?.toLowerCase() || ''

                        if (extType.match(/png|jpe?g|svg|gif|tiff|bmp|ico/)) {
                            return 'assets/images/[name]-[hash][extname]'
                        }
                        if (extType === 'css') {
                            return 'assets/css/[name]-[hash][extname]'
                        }
                        return 'assets/[name]-[hash][extname]'
                    }
                }
            }
        },
        base: env.VITE_BUILD_ASSET_PREFIX,
    }
})