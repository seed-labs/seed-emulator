import requests

class BeaconClient:
    """!
    @brief The BeaconClient class.  
    """

    def __init__(self):
        """!
        @brief BeaconClient constructor.
        """

        self._beacon_node_url = 'http://10.151.0.71:8000'

    def getValidatorStatus(self):
        return requests.get(self._beacon_node_url+"/"+"/eth/v1/beacon/states/head/validators")['data']


class ValidatorClient:
    """!
    @brief The ValidatorClient class.
    """

    def __init__(self):
        """!
        @brief ValidatorClient constructor.
        """

        self._validator_node_url = 'http://10.151.0.71:5062'