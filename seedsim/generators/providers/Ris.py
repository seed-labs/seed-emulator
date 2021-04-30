from .DataProvider import DataProvider
from typing import List, Dict, Any
import requests

RIPE_API = 'https://stat.ripe.net/data'
PEERINGDB_API = ''

class Ris(DataProvider):

    __cache: Dict[str, Dict[str, Any]]

    def __init__(self) -> None:
        self.__cache = {}
        self.__cache['prefixes'] = {}
        self.__cache['peers'] = {}
        self.__cache['exchanges'] = {}
        super().__init__()

    def __ripe(self, verb: str, params: Any) -> Any:
        rslt = requests.get('{}/{}/data.json'.format(RIPE_API, verb), params)

        assert rslt.status_code == 200, 'RIPEstat data API returned non-200'

        json = rslt.json()
        assert json['status'] == 'ok', 'RIPEstat API returned not-OK'

        return json['data']
    
    def __peeringdb(self, path: str, arg: str) -> Any:
        pass

    def getName(self) -> str:
        return 'Ris'

    def getPrefixes(self, asn: int) -> List[str]:
        if asn in self.__cache['prefixes']:
            self._log('prefix list of AS{} in cache.'.format(asn))
            return self.__cache['prefixes'][asn]

        self._log('prefix list of AS{} not in cache, loading from RIPE RIS...'.format(asn))
        
        data = self.__ripe('announced-prefixes', { 'resource': asn })

        prefixes = [p['prefix'] for p in data['prefixes'] if ':' not in p['prefix']]
        self.__cache['prefixes'][asn] = prefixes

    def getPeers(self, asn: int) -> Dict[int, str]:
        if asn in self.__cache['peers']:
            self._log('peer list of AS{} in cache.'.format(asn))
            return self.__cache['peers'][asn]

        self._log('peer list of AS{} not in cache, loading from RIPE RIS...'.format(asn))

        data = self.__ripe('asn-neighbours', { 'resource': asn })

        peers = {}
        for peer in data['neighbours']:
            peers[peer] = peer['type']

        self.__cache['peers'][asn] = peers
        
        return peers
    
    def getInternetExchanges(self, asn: int) -> List[int]:
        return

    def getInternetExchangeMembers(self, id: int) -> Dict[int, str]:
        return

    def getInternetExchangePrefix(self, id: int) -> str:
        return
    