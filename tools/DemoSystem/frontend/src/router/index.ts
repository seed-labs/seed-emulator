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

export default router