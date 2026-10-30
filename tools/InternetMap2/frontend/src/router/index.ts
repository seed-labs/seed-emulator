import {createRouter, createWebHistory, type RouteRecordRaw} from 'vue-router'
import {RouterToListItem} from "@/utils/tools.ts"
import type {NewRouteRecord, RouteRecord} from "@/types/index.ts"


export const defaultRouters: RouteRecord[] = [
    {
        path: '/',
        component: () => import('@/view/layout/index.vue'),
        redirect: {name: "home"},
        name: 'layout',
        children: [
            {
                path: '/home',
                component: () => import('@/view/home/index.vue'),
                name: 'home',
                meta: {
                    title: "Home",
                    icon: 'HomeFilled',
                    componentName: 'Home',
                },
            },
            {
                path: '/dashboard',
                component: () => import('@/view/dashboard/index.vue'),
                name: 'dashboard',
                meta: {
                    title: "Dashboard",
                    icon: 'HomeFilled',
                    componentName: 'Dashboard',
                },
            },
            {
                path: '/plugin',
                component: () => import('@/view/plugin/index.vue'),
                name: 'plugin',
                meta: {
                    title: "Plugin",
                    icon: 'HomeFilled',
                    componentName: 'Plugin',
                },
            },
        ]
    },
    {
        path: '/mapIndex',
        component: () => import('@/view/map/index.vue'),
        redirect: {name: "map"},
        name: 'mapIndex',
        children: [
            {
                path: '/map',
                component: () => import('@/view/map/map/map.vue'),
                name: 'map',
                meta: {
                    title: "Map",
                    icon: 'HomeFilled',
                    componentName: 'Map',
                },
            },
            {
                path: '/uploadMap',
                component: () => import('@/view/map/uploadMap/uploadMap.vue'),
                name: 'uploadMap',
                meta: {
                    title: "UploadMap",
                    icon: 'HomeFilled',
                    componentName: 'UploadMap',
                },
            },
            {
                path: '/ixMap',
                component: () => import('@/view/map/ixMap/ixMap.vue'),
                name: 'ixMap',
                meta: {
                    title: "IXMap",
                    icon: 'HomeFilled',
                    componentName: 'IXMap',
                },
            },
            {
                path: '/transitMap',
                component: () => import('@/view/map/transitMap/transitMap.vue'),
                name: 'transitMap',
                meta: {
                    title: "TransitMap",
                    icon: 'HomeFilled',
                    componentName: 'TransitMap',
                },
            },
            // {
            //     path: '/testMap',
            //     component: () => import('@/view/map/test/testMap.vue'),
            //     name: 'testMap',
            //     meta: {
            //         title: "testMap",
            //         icon: 'HomeFilled',
            //         componentName: 'testMap',
            //     },
            // },
        ]
    },
    {
        path: '/console',
        component: () => import('@/view/console/index.vue'),
        name: 'console',
        meta: {
            title: "Console",
            icon: 'HomeFilled',
            componentName: 'Console',
        },
    },
    {
        path: '/:pathMatch(.*)*',
        component: () => import('@/view/404/index.vue'),
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