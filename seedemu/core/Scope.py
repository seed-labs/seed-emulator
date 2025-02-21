from enum import Enum, IntEnum
from typing import Tuple


# could be replaced by @total_order
class ComparableEnum(Enum):
    def __lt__(self, other):
        if self.__class__ is other.__class__:
            return self.value < other.value
        return NotImplemented

    def __gt__(self, other):
        if self.__class__ is other.__class__:
            return self.value > other.value
        return NotImplemented

    def __le__(self, other):
        if self.__class__ is other.__class__:
            return self.value <= other.value
        return NotImplemented

    def __ge__(self, other):
        if self.__class__ is other.__class__:
            return self.value >= other.value
        return NotImplemented


class ScopeTier(ComparableEnum):
    """!
    @brief the domain or extent(kind) of a scope
    """

    "global(simulation wide setting for all containers)"
    Global = 3
    # ISD
    # "AS level setting(all containers of an AS)"
    AS = 2
    # "individual node setting(per container)"
    Node = 1


# TODO: we could just use NodeRole itself, but SEED folks are afraid of touching it, so we don't ..
class ScopeType(IntEnum):
    """Defines the type of entity affected by the scope."""

    NONE = 0  # only for checks that intersection is empty
    ANY = 15  # No specific type -> matches everything
    RNODE = 1
    HNODE = 2
    CSNODE = 4
    BRDNODE = 8
    RSNODE = 16

    @staticmethod
    def from_node(node: "Node"):
        from .enums import NodeRole

        match node.getRole():
            case NodeRole.Host:
                return ScopeType.HNODE
            case NodeRole.Router:
                return ScopeType.RNODE
            case NodeRole.BorderRouter:
                return ScopeType.BRDNODE
            case NodeRole.ControlService:
                return ScopeType.CSNODE
            case NodeRole.RouteServer:
                return ScopeType.RSNODE


class Scope:
    """!
    @brief strong type for the hierarchical scope of configuration settings.
            i.e. ''(global/simulation wide), '150' (AS level) or '150_brdnode_br0' (individual node  override)
    @note Scopes are immutable after construction and serve as a multi-level key or index into a set of options.
        Scopes implement <> comparison to readily determine when options are overriden by more specific scopes.
        However they do not form a total order (i.e. ScopeTypes like rnode, hnode within the same AS or Globally cannot be compared )
        Also Scope does not cater for multihomed ASes where nodes can be in more than one AS at the same time.
    """

    # NOTE ISD scope could be added here
    # TODO: it should be possible to support sets of ASNs and NodeIDs within the same scope object (aggregation)
    # just as is the case with NodeTypes
    # But this complicates the code ... It would in fact be easier to disaggregate Type into an ordenary Enum,
    # at the cost of having to set an Option multiple times, once for each NodeType that is to be included
    def __init__(
        self,
        tier: ScopeTier,
        node_type: ScopeType = ScopeType.ANY,
        node_id: str = None,
        as_id: int = None,
    ):
        """
        Ideally, each AS number should be globally unique
        (partly to facilitate the comparison and transition from BGP),
        but the actual requirement is only that each AS number be unique within an ISD.
        Since an AS can be part of several ISDs,
        picking a globally unique AS number also facilitates joining new ISDs.[TheCompleteGuideToSCION]
        """
        if tier == ScopeTier.AS:
            assert as_id != None, "Invalid Input"
            assert node_id == None, "Invalid Input"
        if tier == ScopeTier.Global:
            assert node_id == None
            assert as_id == None
        if tier == ScopeTier.Node:
            assert node_id != None
            assert as_id != None

        self._tier = tier
        self._node_type = node_type
        self._node_id = node_id  # Only set for per-node scopes
        self._as_id = as_id  # Only set for per-AS scopes

    '''
    def __hash__(self):
        """Allows Scope instances to be used as dictionary keys."""
        return hash((self.tier, self.node_type, self.node_id, self.as_id))
    '''

    @property
    def tier(self) -> ScopeTier:
        return self._tier

    @property
    def type(self) -> ScopeType:
        return self._node_type

    @property
    def node(self) -> str:
        return self._node_id

    @property
    def asn(self) -> int:
        return self._as_id

    def _intersection(self, other: "Scope") -> "Scope":
        """!
        @brief return a new scope which represents the intersection of both scopes
        """
        pass

    def _comparable(self, other: "Scope") -> Tuple[bool, bool]:
        """returns a two bools indicating wheter the scopes are:
        lt/gt comparable or identical"""

        same_type = True if self.type == other.type else False
        common_type = self.type & other.type
        otherTypeInSelf = (self.type & other.type) == other.type
        selfTypeInOther = (other.type & self.type) == self.type
        contained_type = selfTypeInOther or otherTypeInSelf
        same_type = self.type == other.type
        same_asn = self.asn == other.asn
        same_node = same_asn and self.node == other.node  # and same_type ?!

        if self.tier == other.tier:
            match self.tier:
                case ScopeTier.Global:  # asn, nodeID irrelevant
                    if same_type:
                        return False, True
                    else:
                        return False, False

                case ScopeTier.AS:  # nodeID irrelevant
                    if same_asn:
                        if same_type:
                            return False, True
                        else:
                            return False, False
                    else:
                        return False, False

                case ScopeTier.Node:  # type should be irrelevant (i.e. redundant ) here
                    if same_asn:
                        if same_node:
                            return False, True
                        else:
                            return False, False
                    else:
                        return False, False
        else:
            match self.tier:
                case ScopeTier.Global:
                    # other.tier must be AS or Node
                    match other.tier:
                        case ScopeTier.AS:
                            if same_type:
                                # other AS scope is subset of self
                                return True, False
                            elif otherTypeInSelf:
                                # other AS scope is a subset of self
                                return True, False
                            else:
                                # types conflict and prevent inclusion
                                return False, False
                        case ScopeTier.Node:
                            if same_type:
                                return True, False
                            elif otherTypeInSelf:
                                return True, False
                            else:
                                return False, False

                case ScopeTier.AS:

                    match other.tier:
                        case ScopeTier.Global:
                            if same_type:  # self is subset of other
                                return True, False
                            elif selfTypeInOther:
                                return True, False
                            else:
                                # both scopes make statements about different types of scopes
                                return False, False
                        case ScopeTier.Node:
                            if same_asn:
                                if same_type:
                                    return True, False
                                elif otherTypeInSelf:
                                    return True, False
                                else:
                                    return False, False
                            else:
                                return False, False

                case ScopeTier.Node:

                    match other.tier:
                        case ScopeTier.AS:
                            if same_asn:
                                if same_type:
                                    return True, False
                                elif selfTypeInOther:
                                    return True, False
                                else:
                                    return False, False
                            else:
                                return False, False

                        case ScopeTier.Global:
                            if same_type:
                                return True, False
                            elif selfTypeInOther:
                                return True, False
                            else:
                                return False, False

    def __eq__(self, other):
        """Compares two Scope objects for equality."""
        assert isinstance(other, Scope)
        _, eq2 = self._comparable(other)
        return eq2

    def __gt__(self, other):
        """!@brief defines scope hierarchy comparison i.e. broader more general(less specific) > more specific).
        i.e. LHS supserset RHS
        """
        if not isinstance(other, Scope):
            return NotImplemented

        same_type = True if self.type == other.type else False
        common_type = self.type & other.type
        otherTypeInSelf = (self.type & other.type) == other.type
        selfTypeInOther = (other.type & self.type) == self.type
        contained_type = selfTypeInOther or otherTypeInSelf
        same_type = self.type == other.type
        same_asn = self.asn == other.asn
        same_node = same_asn and self.node == other.node  # and same_type ?!

        if self.tier == other.tier:
            match self.tier:
                case ScopeTier.Global:  # asn, nodeID irrelevant
                    if same_type:
                        return False  # they are equal not gt
                    elif otherTypeInSelf:
                        return True
                    else:
                        return NotImplemented

                case ScopeTier.AS:  # nodeID irrelevant
                    if same_asn:
                        if same_type:
                            return False  # they are equal not gt
                        elif otherTypeInSelf:
                            return True
                        else:
                            return NotImplemented
                    else:
                        # scopes of different ASes are disjoint
                        return NotImplemented

                case ScopeTier.Node:  # type should be irrelevant (i.e. redundant ) here
                    if same_asn:
                        if same_node:
                            return False  # equal and not gt
                        else:
                            return NotImplemented
                    else:
                        return NotImplemented
        else:
            match self.tier:
                case ScopeTier.Global:
                    # other.tier must be AS or Node
                    match other.tier:
                        case ScopeTier.AS:
                            if same_type:
                                # other AS scope is subset of self (gt)
                                return True
                            elif otherTypeInSelf:
                                # other AS scope is a subset of self (gt)
                                return True
                            else:
                                return False
                        case ScopeTier.Node:
                            if same_type:
                                # other is subset of self (gt)
                                return True
                            elif otherTypeInSelf:
                                # other is subset of self (gt)
                                return True
                            else:
                                return False

                case ScopeTier.AS:

                    match other.tier:
                        case ScopeTier.Global:

                            return False
                        case ScopeTier.Node:
                            if same_asn:
                                if same_type:
                                    return True
                                elif otherTypeInSelf:
                                    return True
                                else:
                                    return False
                            else:
                                return False

                case ScopeTier.Node:

                    match other.tier:
                        case ScopeTier.AS:

                            return False

                        case ScopeTier.Global:
                            return False

    def lt_old(self, other):
        if self._tier != other._tier:
            return self._tier < other._tier  # Higher tier value means broader scope
        if self._node_type != other._node_type:  # More specific node type wins
            if selfTypeInOther := (((other.type & self.type) == self.type)):
                return True
            else:
                return False
        if self._node_id or other._node_id:
            return bool(self._node_id) and not bool(
                other._node_id
            )  # Node scope is most specific
        return False

    def __lt__(self, other):
        """!@brie fDefines scope hierarchy comparison (more specific < broader).
        i.e. LHS subset RHS
        """
        if not isinstance(other, Scope):
            return NotImplemented

        same_type = True if self.type == other.type else False
        common_type = self.type & other.type
        otherTypeInSelf = (self.type & other.type) == other.type
        selfTypeInOther = (other.type & self.type) == self.type
        contained_type = selfTypeInOther or otherTypeInSelf
        same_type = self.type == other.type
        same_asn = self.asn == other.asn
        same_node = same_asn and self.node == other.node  # and same_type ?!

        if self.tier == other.tier:
            match self.tier:
                case ScopeTier.Global:  # asn, nodeID irrelevant
                    if same_type:
                        return False  # they are equal not lt
                    elif selfTypeInOther:
                        return True
                    else:
                        return NotImplemented

                case ScopeTier.AS:  # nodeID irrelevant
                    if same_asn:
                        if same_type:
                            return False  # they are equal not lt
                        elif selfTypeInOther:
                            return True
                        else:
                            return NotImplemented
                    else:
                        # scopes of different ASes are disjoint
                        return NotImplemented

                case ScopeTier.Node:  # type should be irrelevant (i.e. redundant ) here
                    if same_asn:
                        if same_node:
                            return False  # equal and not lt
                        else:
                            return NotImplemented
                    else:
                        return NotImplemented
        else:
            match self.tier:
                case ScopeTier.Global:
                    # other.tier must be AS or Node
                    match other.tier:
                        case ScopeTier.AS:
                            if same_type:
                                # other AS scope is subset of self (gt)
                                return False
                            elif otherTypeInSelf:
                                # other AS scope is a subset of self (gt)
                                return False
                            else:
                                return False
                        case ScopeTier.Node:
                            if same_type:
                                # other is subset of self (gt)
                                return False
                            elif otherTypeInSelf:
                                # other is subset of self (gt)
                                return False
                            else:
                                return False

                case ScopeTier.AS:

                    match other.tier:
                        case ScopeTier.Global:
                            if same_type:  # self is subset of other
                                return True
                            elif selfTypeInOther:
                                return True
                            else:
                                # both scopes make statements about different types of scopes
                                return False
                        case ScopeTier.Node:
                            if same_asn:
                                if same_type:
                                    return False
                                elif otherTypeInSelf:
                                    return False
                                else:
                                    return False
                            else:
                                return False

                case ScopeTier.Node:

                    match other.tier:
                        case ScopeTier.AS:
                            if same_asn:
                                if same_type:
                                    return True
                                elif selfTypeInOther:
                                    return True
                                else:
                                    return False
                            else:
                                return False

                        case ScopeTier.Global:
                            if same_type:
                                return True
                            elif selfTypeInOther:
                                return True
                            else:
                                return False

    def __repr__(self):
        """String representation for debugging."""
        details = []
        if self._as_id is not None:
            details.append(f"AS={self._as_id}")
        if self._node_type != ScopeType.ANY:
            details.append(f"Type={self._node_type.name}")
        if self._node_id:
            details.append(f"Node={self._node_id}")
        return f"Scope({', '.join(details) or 'Global'})"

    # for use with functools.cmp_to_key( Scope.collate )
    @staticmethod
    def collate(a: "Scope", b: "Scope") -> int:
        # c,_= a._comparable(b)
        try:
            if a < b:
                return -1
            elif b < a:
                return 1
        except (
            TypeError
        ):  # This happens if Python encounters NotImplemented in both cases
            pass
        return 0  # Fallback: Treat as equal or use another sorting logic
