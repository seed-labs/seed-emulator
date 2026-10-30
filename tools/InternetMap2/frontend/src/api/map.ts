import request from '@/utils/request'

export interface containerType{
    id: string,
    name: string,
    entryPoint?: string,
    version?: string,
}

export interface networkType{
    id: string,
    name: string,
    entryPoint?: string,
    version?: string,
}
export const URL = {
    CONTAINER_URL: '/container',
    NETWORK_URL: '/network',
} as const

export interface ApiRespond<ResultType> {
    ok: boolean;
    result: ResultType;
}

export const reqGetContainersList = (params: {}): Promise<ApiRespond<any>> => {
    return request.get(
        URL.CONTAINER_URL,
        {params}
    )
}

export const reqGetNetworksList = (params: {}): Promise<ApiRespond<any>> => {
    return request.get(
        URL.NETWORK_URL,
        {params}
    )
}
