import os, sys, time
import json
import requests
import logging

class UtilityServerHelper:

    _server_url: str

    def __init__(self, server_url):

        self._server_url = server_url

        return


    def get_contract_address(self, contract_name):
         url = self._server_url + "/contracts_info?name=" + contract_name
         while (True):
            try:
                response = requests.get(url)
                if response and response.status_code == 200:
                    address = response.text.strip().strip('"')
                    break
                else:
                    logging.warning("Failed to fetch data from server. Retrying...")
    
            except Exception as e:
                   logging.error(f"An error occurred: {e}")
    
            # Wait 10 seconds before retrying
            time.sleep(10)
    
         return address


