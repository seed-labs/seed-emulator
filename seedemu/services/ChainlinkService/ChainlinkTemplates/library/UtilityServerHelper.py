import os, sys, time, json
import requests
import logging


class UtilityServerHelper:

    _server_url: str

    def __init__(self, server_url):

        self._server_url = server_url

        return


    def wait_for_server_ready (self, timeout=-1):
        """!
        @brief Check if the server is running
        @param timeout -1 means wait forever
        @returns Return 1 if the server is running; 0 otherwise
        """

        start_time = time.time()
        while True:
            try:
              response = requests.get(self._server_url)
              if response.status_code == 200:
                  logging.info("Utility server is connected.")
                  return 1

            except Exception as e:
              print("Exception: " + str(e))

            logging.info("Utility server connection failed, retrying ...")
            if timeout < 0:  # Wait forever
               pass
            else:
               if time.time() - start_time > timeout:
                  logging.info("Utility server connection failed.")
                  return 0

            time.sleep(10)  # wait for 10 seconds before retrying


    def get_contract_address(self, contract_name):
        """!
        @brief Get the address of a specified contract name 
        @param contract_name The name of the contract
        @returns Return the contract address 
        """
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

    def register_info(self, data):
        """!
        @brief Register a contract address with the server
        @param data JSON format, containing 'contract_name' and 'contract_address'
        """
        url = self._server_url + "/register_contract"

        while (True):
           try: 
               response = requests.post(url, json=data)
               if response and response.status_code == 200:
                   logging.info("Information registered successfully.")
                   break
               else: 
                  logging.warning("Failed to register information. Retrying...")
  
           except Exception as e:
                 logging.error(f"An error occurred: {e}")

           # Wait before retrying
           time.sleep(10)

