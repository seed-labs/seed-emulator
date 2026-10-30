import request from '@/utils/request'
import type {AxiosRequestConfig, AxiosResponse} from "axios";

const headers = {'Content-Type': 'application/json;charset=UTF-8'}
export const URL = {
    INSTALL_URL: '/install',
    UNINSTALL_URL: '/uninstall',
} as const

export interface pluginType{
    id: string,
    name: string,
    entryPoint?: string,
    version?: string,
}
export interface ApiRespond<pluginType> {
    ok: boolean;
    result: pluginType;
}

export const reqGetInstallList = (params: {}): Promise<ApiRespond<ResultType>> => {
    return request.get(
        URL.INSTALL_URL,
        {params}
    )
}

export const reqUninstall = (data: pluginType): Promise<ApiRespond<ResultType>> => {
    return request.post(
        URL.UNINSTALL_URL,
        data,
        headers
    )
}

export const reqInstall = (data: pluginType): Promise<ApiRespond<ResultType>> => {
    return request.post(
        URL.INSTALL_URL,
        data,
        headers
    )
}
