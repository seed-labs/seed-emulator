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


EthServerFileTemplates: Dict[str, str] = {
        'bootstrapper':        get_file_content("files_ethereum/bootstrapper.sh"),
        'beacon_bootstrapper': get_file_content("files_ethereum/beacon_bootstrapper.sh")
}

UtilityServerFileTemplates: Dict[str, str] = {
        'fund_account':    get_file_content("files_utility/fund_account.py"),
        'deploy_contract': get_file_content("files_utility/deploy_contract.py"),
        'utility_server':  get_file_content("files_utility/utility_server.py"),
        'server_setup':    get_file_content("files_utility/utility_server_setup.py")
}

FaucetServerFileTemplates: Dict[str, str] = {
        'faucet_server':   get_file_content("files_faucet/faucet_server.py"),
        'fund_accounts':   get_file_content("files_faucet/fund_accounts.sh"),
        'fundme':          get_file_content("files_faucet/fundme.py"),
        'faucet_url':      "http://{address}:{port}/",
        'faucet_fund_url': "http://{address}:{port}/fundme",
        'fund_curl': "curl -X POST -d 'address={recipient}&amount={amount}' http://{address}:{port}/fundme"
}

