from .Printable import Printable
from .enums import InterfaceType

class Interface(Printable):
    """!
    @brief Interface class.

    This class represents a network interface card.
    """

    def getType(self) -> InterfaceType:
        """!
        @brief Get type of this interface.

        This will be used in some automation
        cases. For example, AddressAssignmentConstraint will use the node type
        to decide how to assign IP addresses to nodes.

        @returns interface type
        """
        raise NotImplementedError("getType not implemented.")