import request from '@/utils/request'

export enum URL {
    ACCOUNTS_URL = '/get_accounts',
    TXS_URL = '/tx',
    Web3Url_URL = '/get_web3_url',
}

export const reqGetAccounts = () => {
    return request.get(
        URL.ACCOUNTS_URL,
    )
}


export const reqGetTXs = (params) => {
    return request.get(
        URL.TXS_URL,
        {params}
    )
}

export const reqGetWeb3Url = () => {
    return request.get(
        URL.Web3Url_URL,
    )
}