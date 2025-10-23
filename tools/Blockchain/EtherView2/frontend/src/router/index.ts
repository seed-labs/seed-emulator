import {createRouter, createWebHistory} from 'vue-router'
import {useGlobalStore} from "@/store"
import {ElNotification} from "element-plus";

const routes = [
    {
        path: '/',
        redirect: {name: 'Home'},
        children: [
            {
                path: '/home',
                name: 'Home',
                component: () => import('@/views/HomeView.vue'),
                meta: {
                    title: 'Home'
                }
            },
            {
                path: '/blockchain',
                name: 'blockchain',
                children: [
                    {
                        path: '/blockchain/tx',
                        name: 'transactions',
                        component: () => import('@/views/blockchain/TXView.vue')
                    },
                    {
                        path: '/blockchain/ptx',
                        name: 'pending transactions',
                        component: () => import('@/views/blockchain/PTXView.vue')
                    },
                    {
                        path: '/blockchain/citx',
                        name: 'contract internal transactions',
                        component: () => import('@/views/blockchain/CITXView.vue')
                    },
                    {
                        path: '/blockchain/blocks',
                        name: 'blocks',
                        component: () => import('@/views/blockchain/BlocksView.vue')
                    },
                    {
                        path: '/blockchain/accounts',
                        name: 'accounts',
                        component: () => import('@/views/blockchain/AccountsView.vue')
                    },
                    {
                        path: '/blockchain/block/:id',
                        name: 'blockInfo',
                        component: () => import('@/views/blockchain/BlockInfoView.vue')
                    },
                ]
            }
        ]
    },
    {
        path: '/:pathMatch(.*)*',
        component: () => import('@/views/NotFoundView.vue'),
        name: '404',
        meta: {
            title: '404',
            icon: 'Failed'
        }
    }
]

const router = createRouter({
    history: createWebHistory(process.env.NODE_ENV === 'production' ? '/frontend' : '/'), //url的基础路径
    // history: createWebHistory(),
    // history: createWebHistory(import.meta.env.VITE_URL_PREFIX), //url的基础路径
    routes
})

// router.beforeEach(async (to, from, next) => {
//     let globalStore = useGlobalStore()
//     document.title = to.meta.title || 'EtherView'
//
//     if (globalStore.web3Url) {
//         next()
//     } else {
//         try {
//             await globalStore.getWeb3Url()
//         } catch (err) {
//             setTimeout(() => {
//                 ElNotification({
//                     type: 'error',
//                     message: 'getWeb3Url error'
//                 } as any)
//             }, 1000)
//         } finally {
//             next({...to, replace: true})
//         }
//     }
// })

export default router