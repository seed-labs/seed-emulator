import type {AxiosRequestConfig} from "axios";
import request from "@/utils/request.ts";

/**
 * console network manager.
 */
export class ConsoleNetwork {
    private readonly _id: string;

    constructor(id: string) {
        this._id = id;
    }

    /**
     * get the container details
     *
     * @returns container details.
     */
    async getContainer(): Promise<any> {
        const config: AxiosRequestConfig = {
            method: 'GET',
            url: `/container/${this._id}`,
        };
        try {
            const response = await request(config);
            if (response.ok) {
                return response;
            } else {
                throw response;
            }
        } catch (error: any) {
            if (error?.response) {
                // 服务器有响应但状态码非 2xx
                return Promise.reject({
                    ok: false,
                    result: 'non-200 response from API.',
                });
            } else if (error?.request) {
                // 请求已发出，但没有收到响应
                return Promise.reject({
                    ok: false,
                    result: 'axios request failed.',
                });
            } else {
                // 其它错误（例如代码错误、JSON 解析错误等）
                return Promise.reject({
                    ok: false,
                    result: error?.message ?? 'unknown error',
                });
            }
        }
    }

    /**
     * get the websocket.
     *
     * @param protocol (optional) websocket protocol (ws/wss), default to ws.
     * @returns websocket.
     */
    getSocket(protocol: string = 'ws'): WebSocket {
        const host = import.meta.env.MODE === 'development' ? import.meta.env.VITE_PROXY_ADDRESS.replace(/^https?:\/\//, '') : location.host
        return new WebSocket(`${protocol}://${host}${import.meta.env.VITE_SERVER_URL_PREFIX}/console/${this._id}`);
    }
}