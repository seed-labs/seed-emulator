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

FaucetServerFileTemplates: Dict[str, str] = {}
FaucetServerFileTemplates['faucet_fund_url'] = "http://{address}:{port}/fundme"
FaucetServerFileTemplates['faucet_url']      = "http://{address}:{port}/"

FaucetServerFileTemplates['fund_curl'] = \
    "curl -X POST -d 'address={recipient}&amount={amount}' http://{address}:{port}/fundme"

FaucetServerFileTemplates['fund_script'] = \
        get_file_content("files_faucet/fund_script.sh")

FaucetServerFileTemplates['faucet_server'] = \
        get_file_content("files_faucet/faucet_server.py")

FaucetServerFileTemplates['fund_user_script'] = \
        get_file_content("files_faucet/fund_script_for_user.sh")
