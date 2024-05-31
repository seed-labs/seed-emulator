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
    'check_link_contract':  get_file_content("files/check_link_contract.sh"), 
    'register_contract':    get_file_content("files/register_contract.sh"),
    'create_jobs':          get_file_content("files/create_jobs.sh"),
    'request_fund':         get_file_content("files/request_fund.sh")
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
WSURL = 'ws://{rpc_ip}:{rpc_ws_port}'
HTTPURL = 'http://{rpc_ip}:{rpc_port}'
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


