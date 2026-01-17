import {createRouter, createWebHistory, type RouteRecordRaw} from 'vue-router'
import {RouterToListItem} from "@/utils/tools.ts"
import type {NewRouteRecord, RouteRecord} from "@/types/index.ts"


export const defaultRouters: RouteRecord[] = [
    {
        path: '/',
        component: () => import('@/views/layout/index.vue'),
        redirect: {name: "home"},
        name: 'layout',
        meta: {
            title: "总览",
        },
        children: [
            {
                path: '/home',
                component: () => import('@/views/home/index.vue'),
                name: 'home',
                meta: {
                    title: "首页",
                    icon: 'HomeFilled',
                    componentName: 'Home',
                },
            },
            {
                path: '/common',
                component: () => import('@/views/common/index.vue'),
                name: 'common',
                meta: {
                    title: "通用",
                    icon: 'HomeFilled',
                    componentName: 'Common',
                },
                // 添加 props 函数
                props: (route) => ({
                    name: route.query.name || "bgp",
                })
            },
            // {
            //     path: '/large-scale-internet-simulation',
            //     component: () => import('@/views/largeScaleInternetSimulation/index.vue'),
            //     name: 'large-scale-internet-simulation',
            //     meta: {
            //         title: "大规模互联网仿真演示",
            //         icon: 'HomeFilled',
            //         componentName: 'LargeScaleInternetSimulation',
            //     },
            // },
            // {
            //     path: '/large-scale-blockchain-simulation',
            //     component: () => import('@/views/largeScaleBlockchainSimulation/index.vue'),
            //     name: 'large-scale-blockchain-simulation',
            //     meta: {
            //         title: "大规模区块链仿真演示",
            //         icon: 'HomeFilled',
            //         componentName: 'LargeScaleBlockchainSimulation',
            //     },
            // },
            // {
            //     path: '/yesterday_once_more',
            //     component: () => import('@/views/yesterdayReenacted/index.vue'),
            //     name: 'yesterday_once_more',
            //     meta: {
            //         title: "昨日重现",
            //         icon: 'HomeFilled',
            //         componentName: 'YesterdayReenacted',
            //     },
            // },
            // {
            //     path: '/yesterday_once_more/bgp',
            //     component: () => import('@/views/yesterdayReenacted/bgpExploration/index.vue'),
            //     name: 'bgp-exploration',
            //     meta: {
            //         title: "BGP 劫持攻击",
            //         icon: 'HomeFilled',
            //         componentName: 'BgpExploration',
            //     },
            // },
            // {
            //     path: '/auto-CTF',
            //     component: () => import('@/views/autoCTFRange/index.vue'),
            //     name: 'auto-CTF',
            //     meta: {
            //         title: "自动 CTF 靶场",
            //         icon: 'HomeFilled',
            //         componentName: 'AutoCTFRange',
            //     },
            // },
        ]
    },
    {
        path: '/:pathMatch(.*)*',
        component: () => import('@/views/404/index.vue'),
        name: '404',
        meta: {
            title: '404',
            componentName: 'NotFound',
        }
    }
]

export const routerList: NewRouteRecord[] = RouterToListItem(defaultRouters)


let router = createRouter({
    history: createWebHistory(import.meta.env.VITE_FRONTEND_URL_PREFIX),
    routes: defaultRouters as RouteRecordRaw[],
    scrollBehavior() {
        return {
            left: 0,
            top: 0
        }
    }
})

// router.beforeEach(async (to, from, next) => {
//     let userStore = useUserStore()
//     if (to.meta.title) {
//         document.title = `${settings.title} - ${to.meta.title}`
//     } else {
//         document.title = settings.title
//     }
//     // 进度条开始
//     NProgress.start()
//     // 登录判断
//     if (userStore.token) {
//         if (to.name === 'login') {
//             next({name: 'home'})
//         } else {
//             let userInfo = userStore.userInfo
//             if (Object.keys(userInfo).length) {
//                 next()
//             } else {
//                 try {
//                     await userStore.getSelfInfo()
//                     // await userStore.getMenuTree()
//                     // 确保addRoute()时动态添加的路由已经完全被加载上
//                     // replace: true只是一个设置信息，告诉VUE本次操作后，不能通过浏览器后退按钮，返回前一个路由
//                     // to不能找到对应的路由的话，就再执行一次beforeEach((to, from, next)直到其中的next({ ...to})能找到对应的路由为止
//                     // 切记 any路由也要采用动态注册方式，否则此处会经常匹配到any路由 ！！！
//                     // 切记 any路由也要采用动态注册方式，否则此处会经常匹配到any路由 ！！！
//                     // 切记 any路由也要采用动态注册方式，否则此处会经常匹配到any路由 ！！！
//                     next({...to, replace: true})
//                 } catch (err) {
//                     setTimeout(() => {
//                         ElNotification({
//                             type: 'error',
//                             message: '获取基础信息失败，退出登录'
//                         })
//                     }, 1000)
//                     // token过期, 清空所有用户数据
//                     userStore.resetState()
//                     // 跳转到登录页
//                     next({name: 'login', query: {redirect: to.path}})
//                 }
//             }
//         }
//     } else {
//         // 切勿直接用 next({name: 'login', query: {redirect: to.path}}) 代替下面判断
//         if (to.name === 'login') {
//             next()
//         } else {
//             next({name: 'login', query: {redirect: to.path}})
//         }
//     }
// })

export default router