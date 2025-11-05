import {createPinia, defineStore} from 'pinia'
import {reqGetWeb3Url} from '@/api/index';


export const useGlobalStore = defineStore('Global', {
    state: () => {
        return {
            web3Url: localStorage.getItem('web3Url')
        }
    },
    actions: {
        async getWeb3Url() {
            let res = await reqGetWeb3Url()
            if (res.status) {
                this.web3Url = res.data
                localStorage.setItem('web3Url', res.data)
            } else {
                return Promise.reject(new Error(res.message))
            }
        },
    },
    getters: {}
})

let pinia = createPinia()
export default pinia