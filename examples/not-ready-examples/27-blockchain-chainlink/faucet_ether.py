from http.server import BaseHTTPRequestHandler, HTTPServer
import json
from web3 import Web3
import time
import sys
rpc_url = 'http://10.164.0.71:8545'
web3 = Web3(Web3.HTTPProvider(rpc_url))

private_key = '72c28c0d980b5e26435fc7eb8afaa27a5a117359669d73284f69ed8a401c6a85'
account_address = Web3.toChecksumAddress('0xF5406927254d2dA7F7c28A61191e3Ff1f2400fe9')
account = web3.eth.account.privateKeyToAccount(private_key)

addresses = set()

class S(BaseHTTPRequestHandler):
    def _set_response(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()

    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        try:
            data = json.loads(post_data.decode('utf-8'))

            def find_eth_addresses(obj):
                if isinstance(obj, dict):
                    for k, v in obj.items():
                        find_eth_addresses(v)
                elif isinstance(obj, list):
                    for item in obj:
                        find_eth_addresses(item)
                elif isinstance(obj, str) and Web3.isAddress(obj):
                    addresses.add(obj)
                    print(f"Added Ethereum address to set: {obj}")

            find_eth_addresses(data)

        except json.JSONDecodeError:
            print("Could not decode the request body as JSON")

        if addresses:
            send_ethereum()

        self._set_response()
        self.wfile.write("POST request processed".encode('utf-8'))

def send_ethereum():
    for address in list(addresses):
        try:
            if web3.eth.get_balance(account_address) >= web3.toWei(5, 'ether'):
                tx = {
                    'chainId': 1337,
                    'to': address,
                    'value': web3.toWei(20, 'ether'),
                    'gas': 2000000,
                    'gasPrice': web3.toWei('50', 'gwei'),
                    'nonce': web3.eth.getTransactionCount(account_address),
                }
                signed_tx = web3.eth.account.sign_transaction(tx, private_key)
                tx_hash = web3.eth.send_raw_transaction(signed_tx.rawTransaction)
                web3.eth.wait_for_transaction_receipt(tx_hash)
                print(f"Sent 5 Ether to {address}, transaction hash: {tx_hash.hex()}")
                addresses.remove(address)
            else:
                print("Insufficient funds to send 5 Ether.")
        except Exception as e:
            print(f"An error occurred: {e}")

def run(server_class=HTTPServer, handler_class=S, port=12345):
    server_address = ('', port)
    httpd = server_class(server_address, handler_class)
    print(f"Starting httpd server on port {port}...")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    httpd.server_close()
    print("Server stopped.")

if __name__ == '__main__':
    if len(sys.argv) == 2:
        try:
            port = int(sys.argv[1])
            if 1024 <= port <= 65535:
                run(port=port)
            else:
                print("Port number must be between 1024 and 65535.")
        except ValueError:
            print("Invalid port number.")
    else:
        print("Usage: python3 faucet_ether.py <port>")
        print("Example: python3 faucet_ether.py 3000")