from enum import Enum

class ConsensusMechanism(Enum):
    """!
    @brief Consensus Mechanism Enum.
    """

    # POA for Proof of Authority
    POA = 'POA'
    # POW for Proof of Work
    POW = 'POW'
    POS = 'POS'

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

class EthUnit(Enum):
    """!
    @brief ethereum unit type enum
    """
    WEI = 1
    GWEI = pow(10, 9)
    ETHER = pow(10, 18)
