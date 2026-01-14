import type {ApiResponse} from "@/api/index.ts"
import {showNotification} from "@/utils/tools.ts"

export const executeApiCall = async <T>(
    apiCall: () => Promise<ApiResponse<T>>,
): Promise<ApiResponse<T> | null> => {
    try {
        const res = await apiCall()
        if (!res.ok) {
            throw new Error(res.result as string)
        }
        return res
    } catch (error) {
        const err = error instanceof Error ? error.message : String(error)
        showNotification('error', err)
        return {ok: false, result: err as string}
    }
}