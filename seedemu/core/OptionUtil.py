from enum import IntEnum
from enum import Flag, auto

class OptionDomain(IntEnum):
    """!@ defines the types of entities that a given Option 
        can apply or refer to
        Attempting to set an option on an entity to which it does not apply is meaningless.
        i.e. Latency or MTU can only pertain to Networks, not Nodes
    """
    NODE = 0
    NET = 4
    ''' these lastly exist only during build time really,
        and are only aggregates of either NODES or NETS depending on the context
    AS = 1
    ISD = 2
    IX = 3
    '''

class OptionMode(Flag):
    """!@brief characteristics of an option,
        during which time it might be changed or set
    """
    # static/hardcoded (require re-compile + image-rebuild to change)
    BUILD_TIME = auto()
    # i.e. envsubst (require only docker compose stop/start )
    RUN_TIME = auto()