from enum import Enum

class NetworkType(Enum):
    """!
    @brief Network types enum.
    """
    InternetExchange = "Internet Exchange Network"
    Local = "Local Network"

class NodeType(Enum):
    """!
    @brief Node types enum.
    """
    Host = "Host"
    Router = "Router"