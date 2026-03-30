import request from '@/utils/request'

export const URL = {
    IP_URL: '/ip',
    RUN_URL: '/run',
} as const

export interface ApiResponse<ResultType = any> {
    ok: boolean;
    result: ResultType;
}

export const reqGetIP = (): Promise<ApiResponse<any>> => {
    return request.get(
        URL.IP_URL
    )
}

export const reqRun = (data: { cmd: string }): Promise<ApiResponse<any>> => {
    return request.post(
        URL.RUN_URL,
        data,
    )
}
