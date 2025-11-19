import {createPinia, defineStore} from 'pinia'
import {reqGetWeb3Url} from '@/api/index';


export const useGlobalStore = defineStore('Global', {
    state: () => {
        return {
            web3Url: sessionStorage.getItem('web3Url'),
            restoreAccountsList: JSON.parse(sessionStorage.getItem('restoreAccountsList') || "[]")
        }
    },
    actions: {
        async getWeb3Url() {
            let res = await reqGetWeb3Url()
            if (res.status) {
                this.web3Url = res.data
                sessionStorage.setItem('web3Url', res.data)
            } else {
                return Promise.reject(new Error(res.message))
            }
        },
        setRestoreAccountsList(restoreAccountsList:[]) {
            this.restoreAccountsList = restoreAccountsList
            sessionStorage.setItem('restoreAccountsList', JSON.stringify(restoreAccountsList))
        }
    },
    getters: {}
})

let pinia = createPinia()
export default pinia