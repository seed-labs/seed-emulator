import {ElLoading} from "element-plus";

export const AllLoading = () => {
    return ElLoading.service({
        lock: true,
        text: 'Loading…',
        background: 'rgba(0,0,0,0.3)',
        fullscreen: true
    })
}