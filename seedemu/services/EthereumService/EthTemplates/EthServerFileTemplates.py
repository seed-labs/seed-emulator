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

EthServerFileTemplates: Dict[str, str] = {}

EthServerFileTemplates['bootstrapper'] = \
         get_file_content("files_ethereum/bootstrapper.sh")

EthServerFileTemplates['beacon_bootstrapper'] = \
         get_file_content("files_ethereum/beacon_bootstrapper.sh")

