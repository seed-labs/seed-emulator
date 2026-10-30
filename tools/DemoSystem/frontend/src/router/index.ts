import {createRouter, createWebHistory, type RouteRecordRaw} from 'vue-router'
import {RouterToListItem} from "@/utils/tools.ts"
import type {NewRouteRecord, RouteRecord} from "@/types/index.ts"


export const defaultRouters: RouteRecord[] = [
    {
        path: '/',
        component: () => import('@/views/layout/index.vue'),
        redirect: {name: "dashboard", params: {dashboardName: "home"}},
        name: 'layout',
        meta: {
            title: "总览",
        },
        children: [
            {
                path: '/dashboard/:dashboardName/',
                component: () => import('@/views/common/dashboard/index.vue'),
                name: 'dashboard',
                meta: {
                    title: "面板",
                    icon: 'HomeFilled',
                    componentName: 'Dashboard',
                },
                props: true,
            },
            {
                path: '/dashboard/:dashboardName/simulation/:simulateName/',
                component: () => import('@/views/common/simulation/index.vue'),
                name: 'simulation',
                meta: {
                    title: "仿真",
                    icon: 'HomeFilled',
                    componentName: 'Simulation',
                },
                props: true
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