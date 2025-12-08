// axios 二次封装
import axios from "axios"
import {ElMessage} from "element-plus"


let request = axios.create({
    baseURL: import.meta.env.VITE_SERVER_URL_PREFIX,
    timeout: import.meta.env.VITE_SERVER_TIMEOUT,
})

request.interceptors.request.use((config: any) => {
    return config
})

request.interceptors.response.use((response: any) => {
    return response.data
}, (error: any) => {
    ElMessage({
        type: 'error',
        message: error,
    })
    return Promise.reject(error)
})

export default request