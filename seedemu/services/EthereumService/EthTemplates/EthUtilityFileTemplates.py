
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


EthUtilityFileTemplates: Dict[str, str] = {}

EthUtilityFileTemplates['fund_account'] = \
        get_file_content("files_utility/fund_account.py")

EthUtilityFileTemplates['deploy_contract'] = \
        get_file_content("files_utility/deploy_contract.py")

EthUtilityFileTemplates['info_server'] = \
        get_file_content("files_utility/info_server.py")
