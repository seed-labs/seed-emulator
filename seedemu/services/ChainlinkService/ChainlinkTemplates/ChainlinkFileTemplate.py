from typing import Dict
import os

def get_file_content(filename):
    """!
    @brief Get the content of a file
    @param filename the file name (relative path)
    @return the content of the file
    """
    real_filename = os.path.dirname(os.path.realpath(__file__)) + "/" + filename
    with open(real_filename, "r") as file:
        return file.read()


def get_file_path(filename):
    """!
    @brief Get the real path of a file 
    @return the path
    """
    return os.path.dirname(os.path.realpath(__file__)) + "/" + filename


# Library files
BlockchainLibrary: Dict[str, str] = {
    'ethereum_helper':       get_file_path('library/EthereumHelper.py'),
    'faucet_helper':         get_file_path('library/FaucetHelper.py'),
    'utility_server_helper': get_file_path('library/UtilityServerHelper.py')
}


# Files for user node
ChainlinkUserTemplate: Dict[str, str] = {
    'setup_script':            get_file_content("files_user/chainlink_user_setup.sh"), 
    'user_contract_abi':       get_file_content("files_user/user_contract.abi"),
    'user_contract_bin':       get_file_content("files_user/user_contract.bin"),
    'request_eth_price':       get_file_content("files_user/request_eth_price.py"),
    'fund_user_contract':      get_file_content("files_user/fund_user_contract.py"),
    'get_oracle_addresses':    get_file_content("files_user/get_oracle_addresses.py"),
    'deploy_user_contract':    get_file_content("files_user/deploy_user_contract.py"),
    'set_contract_addresses':  get_file_content("files_user/set_contract_addresses.py")
}

# Link Token Contract files
# This contract is deployed by the utility server
LinkTokenFileTemplate: Dict[str, str] = {
    'link_contract_name':   'link_token_contract',
    'link_contract_abi':    get_file_content("files/contract/link_contract.abi"),
    'link_contract_bin':    get_file_content("files/contract/link_contract.bin")
}

# Oracle files
# This contract is deployed by Chainlink node
OracleContractDeploymentTemplate: Dict[str, str] = {
    'deploy_oracle_contract': get_file_content("files/deploy_oracle_contract.py"),
    'oracle_contract_abi':    get_file_content("files/contract/oracle_contract.abi"),
    'oracle_contract_bin':    get_file_content("files/contract/oracle_contract.bin")
}


# Chainlink script files 
ChainlinkFileTemplate: Dict[str, str] = {
    'setup_script':           get_file_content("files/chainlink_setup.sh"), 
    'get_auth_sender':        get_file_content("files/get_auth_sender.sh"), 
    'fund_auth_sender':       get_file_content("files/fund_auth_sender.py"), 
    'deploy_oracle_contract': get_file_content("files/deploy_oracle_contract.py"),
    'register_contract':      get_file_content("files/register_contract.py"),
    'create_jobs':            get_file_content("files/create_jobs.sh")
}


ChainlinkFileTemplate['start_commands'] = """\
service postgresql restart
su - postgres -c "psql -c \\"ALTER USER postgres WITH PASSWORD 'mysecretpassword';\\""
nohup chainlink node -config /chainlink/config.toml -secrets /chainlink/db_secrets.toml start -api /chainlink/password.txt > /chainlink/chainlink_logs.txt 2>&1 &
"""

ChainlinkFileTemplate['config'] = """\
[Log]
Level = 'info'

[WebServer]
AllowOrigins = '*'
SecureCookies = false

[WebServer.TLS]
HTTPSPort = 0

[[EVM]]
ChainID = '{chain_id}'

[[EVM.Nodes]]
Name = 'SEED Emulator'
WSURL = 'ws://{eth_server_ip}:{eth_server_ws_port}'
HTTPURL = 'http://{eth_server_ip}:{eth_server_http_port}'
"""

ChainlinkFileTemplate['secrets'] = """\
[Password]
Keystore = 'mysecretpassword'
[Database]
URL = 'postgresql://postgres:mysecretpassword@localhost:5432/postgres?sslmode=disable'
"""

ChainlinkFileTemplate['api'] = """\
{username}
{password}
"""


ChainlinkFileTemplate['nginx_site'] = """\
server {{
    listen {port};
    root /var/www/html;
    index index.html;
    server_name _;

    location / {{
        try_files $uri $uri/ @proxy_to_app;
    }}

    location @proxy_to_app {{
        proxy_pass http://localhost:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }}
}}
"""


