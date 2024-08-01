import os, sys, time
import json 
import requests
import logging

class FaucetHelper: 
    """!
    @brief Faucet helper class

    """

    _chain_id: int
    _faucet_url: str

    def __init__(self, faucet_url):
        """!
        @brief constructor.
        """
        self._faucet_url = faucet_url

        return 


    def wait_for_server_ready (self, timeout=-1): 
        """!
        @brief Check if the faucet server is running
        @param timeout -1 means wait forever
        @returns Return 1 if the server is running; 0 otherwise
        """

        start_time = time.time()
        while True:
            try:
              response = requests.get(self._faucet_url)
              if response.status_code == 200:
                  logging.info("faucet server connection succeed.")
                  return 1
    
            except Exception as e:
              print("Exception: " + str(e))

            logging.info("faucet server connection failed, retrying ...")
            if timeout < 0:  # Wait forever 
               pass
            else:
               if time.time() - start_time > timeout:
                  logging.info("faucet server connection failed.")
                  return 0
    
            time.sleep(10)  # wait for 10 seconds before retrying


    def send_fundme_request(self, account_address, amount):
        """!
        @brief Send a request to the Faucet to find an account
        @returns Return 1 if the request is successful; 0 otherwise
        """

        data = dict()
        data['address'] = account_address
        data['amount']  = amount
    
        try:
           response = requests.post(self._faucet_url + "/fundme",
                         headers={"Content-Type": "application/json"},
                         data=json.dumps(data))
           logging.info(response)
    
           if response.status_code == 200:
              api_response = response.json()
              message = api_response['message']
              if message:
                 print("Success: "+ message)
                 return 1
              else:
                 logging.error("Funds request was successful, " +
                               "but the response format is unexpected.")
           else:
              api_response = response.json()
              message = api_response['message']
              logging.error("Failed to request funds from faucet server. " +
                            "Status code: " + response.status_code +
                            "Message: " + message)
           return 0 

        except Exception as e:
            logging.error("An error occurred: "+ str(e))
            exit()
    
