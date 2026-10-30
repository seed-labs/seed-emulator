import type {AxiosRequestConfig} from "axios";
import request from "@/utils/request.ts";
import type {Response} from "@/utils/types.ts";

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
            const response: Response = await request(config);
            if (response.ok) {
                return response;
            } else {
                throw response;
            }
        } catch (error: any) {
            if (error?.response) {
                return Promise.reject({
                    ok: false,
                    result: 'non-200 response from API.',
                });
            } else if (error?.request) {
                return Promise.reject({
                    ok: false,
                    result: 'axios request failed.',
                });
            } else {
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