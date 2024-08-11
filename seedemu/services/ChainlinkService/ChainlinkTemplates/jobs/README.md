# Chainlink Jobs

This directory contains the Chainlink job templates that are used to create Chainlink jobs for the Chainlink node. Chainlink jobs are crucial for facilitating the interaction between smart contracts and external data sources. They allow smart contracts on various blockchain platforms to securely and reliably receive and process data from the outside world. 

## Tasks in Chainlink Jobs

1. **decode_log**
    - Description: This task decodes the Ethereum log data using the specified ABI (Application Binary Interface). It extracts information from the log data emitted by the smart contract, such as the request ID, payment, callback address, callback function ID, expiration time, and the actual data payload.

2. **decode_cbor**
    - Description: This task parses the CBOR (Concise Binary Object Representation) data extracted from the log. CBOR is a data format that is efficient in both encoding and decoding, and this task converts the CBOR data into a format that can be used for further processing.

3. **fetch**
    - Description: This task makes an HTTP GET request to the URL specified in the decoded CBOR data. It retrieves data from an external API endpoint, which will be processed and returned to the smart contract.

4. **parse**
    - Description: This task parses the JSON data retrieved from the external API. It extracts the specific value from the JSON response using the JSON path specified in the decoded CBOR data.

5. **multiply**
    - Description: This task multiplies the parsed value by a factor specified in the decoded CBOR data. This is useful for adjusting the scale or converting units of the retrieved data before returning it to the smart contract.

6. **encode_data**
    - Description: This task encodes the multiplied value into the appropriate ABI format. This prepares the data to be sent back to the smart contract in a format that it can understand and process.

7. **encode_tx**
    - Description: This task encodes the entire transaction data needed to fulfill the oracle request. It includes the request ID, payment, callback address, callback function ID, expiration time, and the encoded data. This prepares the transaction to be submitted to the blockchain.

8. **submit_tx**
    - Description: This task submits the encoded transaction to the specified smart contract address. It sends the processed data back to the smart contract, fulfilling the oracle request.

## Example Jobs
1. **[Get > Uint256](./getUint256.toml)**
    - Description: This job retrieves the latest price of an asset from an external API and returns it to the smart contract as a `uint256` value.
    - Tasks: `decode_log`, `decode_cbor`, `fetch`, `parse`, `multiply`, `encode_data`, `encode_tx`, `submit_tx`
    - Parameters: This job requires the following parameters to be specified while sending the oracle request:
        - `get`: internet-facing URL from where the integer is retrieved
        - `path`: comma-separated JSON path used to extract the integer value
        - `multiply`: factor using to deal with precision and rounding errors
     - Example:
       - `get`: https://min-api.cryptocompare.com/data/pricemultifull?fsyms=ETH&tsyms=USD
       - `path`: `RAW,ETH,USD,PRICE`
       - `multiply`: `100`

        This will retrieve the json data in the following format:
        ```json
        {
            "RAW": {
                "ETH": {
                    "USD": {
                        "PRICE": 2000.36
                    }
                }
            }
        }
        ```
        And the final value returned to the smart contract will be `200036`.

2. **[Get > Bool](./getBool.toml)**
    - Description: This job retrieves the latest status of a service from an external API and returns it to the smart contract as a `bool` value.
    - Tasks: `decode_log`, `decode_cbor`, `fetch`, `parse`, `encode_data`, `encode_tx`, `submit_tx`
    - Parameters: This job requires the following parameters to be specified while sending the oracle request:
        - `get`: internet-facing URL from where the boolean value is retrieved
        - `path`: comma-separated JSON path used to extract the boolean value
     - Example:
       - `get`: https://raw.githubusercontent.com/amanvelani/seed-emulator/ethereum-improvement/seedemu/services/ChainlinkService/ChainlinkTemplates/jobs/status.json
       - `path`: `values,seed`

        This will retrieve the json data in the following format:
        ```json
        {
            "values": {
                "seed": true,
                "dees": false
            }
        }
        ```
        And the final value returned to the smart contract will be `true`.

If you want to learn more about Chainlink jobs and how to create custom jobs, you can refer to the official Chainlink documentation [here](https://docs.chain.link/docs/jobs/).