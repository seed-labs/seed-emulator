from __future__ import annotations
from typing import Dict
from seedemu.core import Emulator
from seedemu.layers import Base


class PartitionDataExtractor:
    """!
    @brief Extract topology data from a rendered Emulator for multi-machine partition solver.
    
    This class is responsible for extracting the following information from seedemu Emulator objects:
    - AS list with resource consumption
    - IXP list
    - IX-AS connection relationships (which ASs are connected to each IX)
    """
    
    # Resource consumption constants for different node types
    NODE_RESOURCES = {
        'host': 1,      # Resource consumption per host node
        'router': 1     # Resource consumption per router node
    }
    
    def __init__(self, emulator: Emulator):
        """!
        @brief Initialize the data extractor.
        
        @param emulator Rendered Emulator object.
        @throws AssertionError if emulator is not rendered.
        """
        assert emulator.rendered(), "emulator is not rendered."
        self.__emulator = emulator
        self.__base: Base = emulator.getLayer('Base')
    
    def extract(self) -> Dict:
        """!
        @brief Extract topology data.
        
        @returns Dictionary in solver input format, containing:
            - asns: List[Tuple[int, int]] - AS list with resources [(asn, resource), ...]
            - ixps: List[int] - IXP ID list
            - ix_as_connections: Dict[int, List[int]] - IX-AS connections, key is IX ID, value is list of connected AS IDs
        """
        # 1. Get basic lists
        all_asns = sorted(self.__base.getAsns())
        all_ixps = self.__base.getInternetExchangeIds()
        
        # 2. Calculate resource consumption for each AS using Emulator API
        as_resources = {}
        for asn in all_asns:
            as_resources[asn] = self.__emulator.calculateAsResource(asn, self.NODE_RESOURCES)
        
        # 3. Extract IX-AS connection relationships using Emulator API
        ix_as_connections = self.__emulator.getIxAsConnections()
        
        # 4. Build output dictionary
        result = {
            'asns': [(asn, as_resources[asn]) for asn in all_asns],
            'ixps': all_ixps,
            'ix_as_connections': {ix_id: sorted(list(as_set)) for ix_id, as_set in ix_as_connections.items()},
        }
        
        return result

