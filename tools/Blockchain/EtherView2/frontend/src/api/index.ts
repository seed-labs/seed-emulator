import request from '@/utils/request'

export enum URL {
    ACCOUNTS_URL = '/get_accounts',
    TXS_URL = '/tx',
    Web3Url_URL = '/get_web3_url',
    ETHERSCAN_URL = '/etherscan',
    TX_FEES_URL = '/tx/fees',
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

export const reqGetEtherScan = () => {
    return request.get(
        URL.ETHERSCAN_URL,
    )
}

export const reqGetTxFees = () => {
    return request.get(
        URL.TX_FEES_URL,
    )
}