import request from '@/utils/request'

export const URL = {
    ACCOUNTS_URL: '/get_accounts',
    TXS_URL: '/tx',
    Web3Url_URL: '/get_web3_url',
    ETHERSCAN_URL: '/etherscan',
    TX_FEES_URL: '/tx/fees',
    TOTAL_ETH_URL: '/get_web3_total_eth',
    RESTORE_ACCOUNTS_URL: '/restore_accounts',
    SEND_TX_URL: '/sendTX',
}

const headers = {
    headers: {
        'Content-Type': 'multipart/form-data'
    }
}

export const reqGetAccounts = () => {
    return request.get(
        URL.ACCOUNTS_URL,
    )
}

export const reqRestoreAccounts = (params: {}) => {
    return request.get(
        URL.RESTORE_ACCOUNTS_URL,
        {params}
    )
}


export const reqGetTXs = (params: {}) => {
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

export const reqGetTotalETH = () => {
    return request.get(
        URL.TOTAL_ETH_URL,
    )
}

export const reqSendTX = (data: {}) => {
    return request.post(
        URL.SEND_TX_URL,
        data,
        headers
    )
}