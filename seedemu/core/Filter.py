from typing import Callable
from .Node import Node
from .Printable import Printable

class Filter(Printable):
    """!
    @brief the Filter class.

    The filter class is used to define some conditions to narrow down candidates
    for a binding.
    """

    asn: int
    nodeName: str
    ip: str
    prefix: str
    allowBound: bool
    custom: Callable[[str, Node], bool]

    def __init__(
        self, asn: int = None, nodeName: str = None, ip: str = None,
        prefix: str = None, custom: Callable[[str, Node], bool] = None,
        allowBound: bool = False
    ):
        """!
        @brief create new filter.
        
        If no options are given, the filter matches all nodes in the emulation.
        If more then one options are given, the options are joined with "and"
        operation - meaning the node must match all given options to be
        selected.

        @param asn (optional) asn of node. Default to None (any ASN).
        @param nodeName (optional) name of node. Default to None (any name).
        @param ip (optional) IP address of node (w/o mask). Default to None (any
        IP).
        @param prefix (optional) Prefix range of node's IP address (CIDR).
        Default to None (any prefix).
        @param custom (optional) custom test function. Must accepts
        (virtual_node_name, physical_node_object) as input and returns a bool.
        Default to None (always allow).
        @param allowBound (optional) allow re-use bound nodes. Default to false.
        """

        ## asn of node
        self.asn = asn

        ## name of node
        self.nodeName = nodeName

        ## ip address of node (w/o mask)
        self.ip = ip

        ## prefix range of node's IP address
        self.prefix = prefix

        ## custom test function
        self.custom = custom

        ## allow re-use already bound nodes
        self.allowBound = allowBound