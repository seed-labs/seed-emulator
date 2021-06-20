from .DataProvider import DataProvider
from typing import List, Dict, Any
import requests

RIPE_API = 'https://stat.ripe.net/data'
PEERINGDB_API = 'https://www.peeringdb.com/api'

class Ris(DataProvider):
    """!
    @brief data provider based on PeeringDB and RIPE RIS API.
    """

    __cache: Dict[str, Dict[str, Any]]

    def __init__(self):
        """!
        @brief Create a new RIS data provider.
        """
        self.__cache = {}
        self.__cache['prefixes'] = {}
        self.__cache['peers'] = {}
        self.__cache['exchanges'] = {}
        self.__cache['exchange_details'] = {}
        super().__init__()

    def __ripe(self, verb: str, params: Any) -> Any:
        """!
        @brief invoke RIPE API.

        @param verb API action.
        @param params requst params.

        @returns API respond.
        """
        rslt = requests.get('{}/{}/data.json'.format(RIPE_API, verb), params)

        assert rslt.status_code == 200, 'RIPEstat data API returned non-200'

        json = rslt.json()
        assert json['status'] == 'ok', 'RIPEstat API returned not-OK'

        return json['data']
    
    def __peeringdb(self, path: str, params: Any) -> Any:
        """!
        @brief invoke PeeringDB API.

        @param path API path.
        @param params requst params.

        @returns API respond.
        """
        rslt = requests.get('{}/{}'.format(PEERINGDB_API, path), params)

        assert rslt.status_code == 200, 'PeeringDB data API returned non-200'

        json = rslt.json()
        return json['data']

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
        if asn in self.__cache['exchanges']:
            self._log('exchange list of AS{} in cache.'.format(asn))
            return self.__cache['exchanges'][asn]
        
        self._log('exchange list of AS{} not in cache, loading from PeeringDB...'.format(asn))

        exchanges = []

        data = self.__peeringdb('net', {
            'asn': asn,
            'depth': 1
        })

        if len(data) > 0: exchanges = data[0]['netixlan_set']
        
        if len(exchanges) == 0: self._log('note: AS{} does not have any public exchanges on record.'.format(asn))
        
        self.__cache['exchanges'][asn] = exchanges

        return exchanges

    def getInternetExchangeMembers(self, id: int) -> Dict[int, str]:
        if id in self.__cache['exchange_details']:
            self._log('exchange details of IX{} in cache.'.format(id))
            return self.__cache['exchange_details'][id]['']
        
        self._log('exchange details of IX{} not in cache, loading from PeeringDB...'.format(id))

    def getInternetExchangePrefix(self, id: int) -> str:
        return
    