from seedsim.core import Printable, Node
from enum import Enum
from typing import List, Callable

class Action(Enum):
    RANDOM = 0
    FIRST = 1
    LAST = 2

class Filter(Printable):
    asn: int
    nodeName: str
    ip: str
    prefix: str
    anyService: List[str]
    allServices: List[str]
    notServices: List[str]

    custom: Callable[[Node], bool]

    def __init__(
        self, asn: int = None, nodeName: str = None, ip: str = None,
        prefix: str = None, anyService: List[str] = [], allServices: List[str] = [],
        notServices: List[str] = [], custom: Callable[[Node], bool] = None
    ):
        self.asn = asn
        self.nodeName = nodeName
        self.ip = ip
        self.prefix = prefix
        self.anyService = anyService
        self.allServices = allServices
        self.notServices = notServices
        self.custom = custom

class Binding(Printable):

    souce: str
    action: Action
    filter: Filter

    def __init__(self, source, action = Action.RANDOM, filter = Filter()):
        self.souce = source
        self.action = action
        self.filter = filter


