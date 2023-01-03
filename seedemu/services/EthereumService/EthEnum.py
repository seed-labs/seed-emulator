from enum import Enum

class ConsensusMechanism(Enum):
    """!
    @brief Consensus Mechanism Enum.
    """

    # POA for Proof of Authority
    POA = 'POA'
    # POW for Proof of Work
    POW = 'POW'

class Syncmode(Enum):
    """!
    @brief geth syncmode Enum.
    """
    SNAP = 'snap'
    FULL = 'full'
    LIGHT = 'light'

class EthereumServerTypes(Enum):
    """!
    @brief ethereum server type enum.
    """
    ETH_NODE = 'eth_node'
    BEACON_SETUP_NODE = 'beacon_setup_node'

