from enum import Enum

class NetworkType(Enum):
    """!
    @brief Network types enum.
    """

    ## Public internet exchange network
    InternetExchange = "Internet Exchange Network"

    ## Private links netwroks. OSPF routers and IBGP runs on this type of
    #  networks.
    Local = "Local Network"

    ## Bridge networks. This type of network eanble access to the real world.
    Bridge = "Bridge Network"

    ## XC network. This type of network connects two nodes directly.
    CrossConnect = "Cross Connect"

class NodeRole(Enum):
    """!
    @brief Node roles enum.
    """

    ## Host node.
    Host = "Host"

    ## Router node.
    Router = "Router"

    ## Route served node.
    RouteServer = "Route Server"