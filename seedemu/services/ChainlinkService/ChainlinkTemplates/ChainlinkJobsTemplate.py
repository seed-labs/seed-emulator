from typing import Dict

# Templates for chainlink jobs

ChainlinkJobsTemplate: Dict[str, str] = {}

ChainlinkJobsTemplate['getBool'] = '''\
type = "directrequest"
schemaVersion = 1
name = "Get > Bool"
maxTaskDuration = "0s"
allowUnrestrictedNetworkAccess="true"
contractAddress = "oracle_contract_address"
externalJobID = "a75ebb6e-5a7b-492f-bfb6-7ab240100a95"
minIncomingConfirmations = 0
minContractPaymentLinkJuels = 1360000000000000000
observationSource = """
    decode_log   [type="ethabidecodelog"
                  abi="OracleRequest(bytes32 indexed specId, address requester, bytes32 requestId, uint256 payment, address callbackAddr, bytes4 callbackFunctionId, uint256 cancelExpiration, uint256 dataVersion, bytes data)"
                  data="$(jobRun.logData)"
                  topics="$(jobRun.logTopics)"]

    decode_cbor  [type="cborparse" data="$(decode_log.data)"]
    fetch        [type="http" method=GET url="$(decode_cbor.get)"]
    parse        [type="jsonparse" path="$(decode_cbor.path)" data="$(fetch)"]
    encode_data  [type="ethabiencode" abi="(bool value)" data="{ \\\\"value\\\\": $(parse) }"]
    encode_tx    [type="ethabiencode"
                  abi="fulfillOracleRequest(bytes32 requestId, uint256 payment, address callbackAddress, bytes4 callbackFunctionId, uint256 expiration, bytes32 data)"
                  data="{\\\\"requestId\\\\": $(decode_log.requestId), \\\\"payment\\\\": $(decode_log.payment), \\\\"callbackAddress\\\\": $(decode_log.callbackAddr), \\\\"callbackFunctionId\\\\": $(decode_log.callbackFunctionId), \\\\"expiration\\\\": $(decode_log.cancelExpiration), \\\\"data\\\\": $(encode_data)}"]
    submit_tx    [type="ethtx" to="oracle_contract_address" data="$(encode_tx)"]

    decode_log -> decode_cbor -> fetch -> parse -> encode_data -> encode_tx -> submit_tx
"""
'''


ChainlinkJobsTemplate['getUint256Uint256'] = '''\
type = "directrequest"
schemaVersion = 1
name = "Get > Uint256,Uint256"
allowUnrestrictedNetworkAccess = "true"
maxTaskDuration = "0s"
externalJobID = "437d298d-210c-4fff-935d-cedb97ea8011"
contractAddress = "oracle_contract_address"
minIncomingConfirmations = 0
minContractPaymentLinkJuels = 1360000000000000000
observationSource = """
    decode_log   [type="ethabidecodelog"
                  abi="OracleRequest(bytes32 indexed specId, address requester, bytes32 requestId, uint256 payment, address callbackAddr, bytes4 callbackFunctionId, uint256 cancelExpiration, uint256 dataVersion, bytes data)"
                  data="$(jobRun.logData)"
                  topics="$(jobRun.logTopics)"]

    decode_cbor     [type="cborparse" data="$(decode_log.data)"]
    fetch           [type="http" method=GET url="$(decode_cbor.get)"]
    parseVal1       [type="jsonparse" path="$(decode_cbor.path1)" data="$(fetch)"]
    parseVal2       [type="jsonparse" path="$(decode_cbor.path2)" data="$(fetch)"]
    multiplyVal1   [type="multiply" input="$(parseVal1)" times="$(decode_cbor.multiply)"]
    multiplyVal2   [type="multiply" input="$(parseVal2)" times="$(decode_cbor.multiply)"]
    encode_data     [type="ethabiencode" abi="(bytes32 requestId, uint256 val1, uint256 val2)" data="{ \\\\"requestId\\\\": $(decode_log.requestId), \\\\"val1\\\\": $(multiplyVal1), \\\\"val2\\\\": $(multiplyVal2)}"]
    encode_tx       [type="ethabiencode"
                      abi="fulfillOracleRequest2(bytes32 requestId, uint256 payment, address callbackAddress, bytes4 callbackFunctionId, uint256 expiration, bytes calldata data)"
                      data="{\\\\"requestId\\\\": $(decode_log.requestId), \\\\"payment\\\\": $(decode_log.payment), \\\\"callbackAddress\\\\": $(decode_log.callbackAddr), \\\\"callbackFunctionId\\\\": $(decode_log.callbackFunctionId), \\\\"expiration\\\\": $(decode_log.cancelExpiration), \\\\"data\\\\": $(encode_data)}"
                    ]
    submit_tx    [type="ethtx" to="oracle_contract_address" data="$(encode_tx)"]

    decode_log -> decode_cbor -> fetch -> parseVal1 -> multiplyVal1 -> parseVal2 -> multiplyVal2 -> encode_data -> encode_tx -> submit_tx
"""
'''

ChainlinkJobsTemplate['getUint256'] = '''\
type = "directrequest"
schemaVersion = 1
name = "Get > Uint256"
allowUnrestrictedNetworkAccess = "true"
externalJobID = "7599d3c8-f31e-4ce7-8ad2-b790cbcfc673"
maxTaskDuration = "0s"
contractAddress = "oracle_contract_address"
minIncomingConfirmations = 0
minContractPaymentLinkJuels = 1350000000000000000
observationSource = """
    decode_log   [type="ethabidecodelog"
                  abi="OracleRequest(bytes32 indexed specId, address requester, bytes32 requestId, uint256 payment, address callbackAddr, bytes4 callbackFunctionId, uint256 cancelExpiration, uint256 dataVersion, bytes data)"
                  data="$(jobRun.logData)"
                  topics="$(jobRun.logTopics)"]

    decode_cbor  [type="cborparse" data="$(decode_log.data)"]
    fetch        [type="http" method=GET url="$(decode_cbor.get)"]
    parse        [type="jsonparse" path="$(decode_cbor.path)" data="$(fetch)"]
    multiply     [type="multiply" input="$(parse)" times="$(decode_cbor.multiply)"]
    encode_data  [type="ethabiencode" abi="(uint256 value)" data="{ \\\\"value\\\\": $(multiply) }"]
    encode_tx    [type="ethabiencode"
                  abi="fulfillOracleRequest(bytes32 requestId, uint256 payment, address callbackAddress, bytes4 callbackFunctionId, uint256 expiration, bytes32 data)"
                  data="{\\\\"requestId\\\\": $(decode_log.requestId), \\\\"payment\\\\": $(decode_log.payment), \\\\"callbackAddress\\\\": $(decode_log.callbackAddr), \\\\"callbackFunctionId\\\\": $(decode_log.callbackFunctionId), \\\\"expiration\\\\": $(decode_log.cancelExpiration), \\\\"data\\\\": $(encode_data)}"
                 ]
    submit_tx    [type="ethtx" to="oracle_contract_address" data="$(encode_tx)"]

    decode_log -> decode_cbor -> fetch -> parse -> multiply -> encode_data -> encode_tx -> submit_tx
"""
'''

