// axios 二次封装
import axios from "axios"
import {ElMessage} from "element-plus"


let request = axios.create({
    baseURL: "/api",
    // baseURL: import.meta.env.VITE_APP_BASE_URL,
    timeout: 10000,
})

request.interceptors.request.use((config) => {
    return config
})

request.interceptors.response.use((response) => {
    return response.data
}, (error) => {
    ElMessage({
        type: 'error',
        message: error.response.status,
    })
    return Promise.reject(error)
})

export default request