from enum import Enum, IntEnum
from typing import Tuple, Optional
from abc import ABC, abstractmethod

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
    pass

class NodeScopeTier(ScopeTier):
    """!
    @brief the domain or extent(kind) of a scope
    """
    "global(simulation wide setting for all containers)"
    Global=3
    #ISD
    #"AS level setting(all containers of an AS)"
    AS=2
    #"individual node setting(per container)"
    Node=1



class ScopeType(IntEnum):
    pass



#TODO: we could just use NodeRole itself, but SEED folks are afraid of touching it, so we don't ..
class NodeScopeType(ScopeType):
    """Defines the type of entity affected by the scope."""
    NONE = 0       # only for checks that intersection is empty
    ANY = 15       # No specific type -> matches everything 
    RNODE = 1
    HNODE = 2
    CSNODE = 4
    BRDNODE = 8
    RSNODE = 16
    @staticmethod
    def from_node(node: 'Node'):
        from .enums import NodeRole
        
        match node.getRole():
            case NodeRole.Host:
                return NodeScopeType.HNODE
            case NodeRole.Router:
                return NodeScopeType.RNODE
            case NodeRole.BorderRouter:
                return NodeScopeType.BRDNODE
            case NodeRole.ControlService:
                return NodeScopeType.CSNODE
            case NodeRole.RouteServer:
                return NodeScopeType.RSNODE



class Scope(ABC):
    @property
    @abstractmethod
    def tier(self) -> ScopeTier:
        pass

    @property
    @abstractmethod
    def type(self)-> ScopeType:
        pass

    def __eq__(self, other: 'Scope') -> bool:
        """Compares two Scope objects for equality."""
        assert isinstance(other, Scope)
        _, eq2= self._comparable(other)
        return eq2
    
    @abstractmethod
    def _comparable(self, other: 'Scope') -> Tuple[bool,bool]:
        pass

    @abstractmethod
    def __lt__(self, other: 'Scope'):
        pass
    @abstractmethod
    def __gt__(self, other: 'Scope'):
        pass

    @abstractmethod
    def _intersection(self, other: 'Scope') -> 'Scope':
        pass
    # for use with functools.cmp_to_key( Scope.collate )
    @staticmethod
    def collate(a: 'Scope', b: 'Scope') -> int:
        #c,_= a._comparable(b)
        try:
            if a < b:
                return -1
            elif b < a:
                return 1
        except TypeError:  # This happens if Python encounters NotImplemented in both cases
            pass
        return 0  # Fallback: Treat as equal or use another sorting logic


class NodeScope:
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
    def __init__(self,
                  tier: NodeScopeTier,
                  node_type: NodeScopeType = NodeScopeType.ANY,
                  node_id: str = None,
                  as_id: int = None):
        '''
        Ideally, each AS number should be globally unique 
        (partly to facilitate the comparison and transition from BGP),
        but the actual requirement is only that each AS number be unique within an ISD.
        Since an AS can be part of several ISDs, 
        picking a globally unique AS number also facilitates joining new ISDs.[TheCompleteGuideToSCION]
        '''
        if tier==NodeScopeTier.AS:
            assert as_id!=None, 'Invalid Input'
            assert node_id==None, 'Invalid Input'
        if tier==NodeScopeTier.Global:
            assert node_id==None
            assert as_id==None
        if tier==NodeScopeTier.Node:
            assert node_id!=None
            assert as_id!=None

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
    def tier(self) -> NodeScopeTier:
        return self._tier
    
    @property
    def type(self)-> NodeScopeType:
        return self._node_type
    
    @property
    def node(self) -> Optional[str]:
        return self._node_id
    
    @property
    def asn(self) -> Optional[int]:
        return self._as_id

    def _intersection(self, other: 'Scope') -> 'Scope':
        """!
        @brief return a new scope which represents the intersection of both scopes
        """
        pass

    def _comparable(self, other: Scope) -> Tuple[bool,bool]:
        """ returns a two bools indicating wheter the scopes are:
          lt/gt comparable or identical"""

        if not isinstance(other, NodeScope): return (False, False)

        same_type = True if self.type == other.type else False
        common_type = self.type & other.type
        otherTypeInSelf = ( (self.type & other.type) == other.type )
        selfTypeInOther = ( ( (other.type & self.type)==self.type ) )
        contained_type = selfTypeInOther or otherTypeInSelf
        same_type = self.type == other.type
        same_asn = self.asn == other.asn
        same_node = same_asn and self.node == other.node # and same_type ?!

        if self.tier==other.tier:
            match self.tier:
                case NodeScopeTier.Global:  # asn, nodeID irrelevant
                    if same_type:
                        return False, True
                    else:
                        return False, False

                case NodeScopeTier.AS: # nodeID irrelevant
                    if same_asn:
                        if same_type:
                            return False, True
                        else:
                            return False, False
                    else:
                        return False, False
                    
                case NodeScopeTier.Node: # type should be irrelevant (i.e. redundant ) here
                    if same_asn:
                        if same_node:
                            return False,True
                        else:
                            return False, False
                    else:
                        return False, False
        else:
            match self.tier:
                case NodeScopeTier.Global:
                    # other.tier must be AS or Node
                    match other.tier:
                        case NodeScopeTier.AS:
                            if same_type:
                                # other AS scope is subset of self
                                return True, False
                            elif otherTypeInSelf:
                            # other AS scope is a subset of self
                                return True, False
                            else:
                                # types conflict and prevent inclusion
                                return False, False
                        case NodeScopeTier.Node:
                            if same_type:
                                return True, False
                            elif otherTypeInSelf: 
                                return True, False
                            else:
                                return False, False
                    
                case NodeScopeTier.AS:
                    
                    match  other.tier:
                        case NodeScopeTier.Global:
                            if same_type: # self is subset of other
                                return True, False
                            elif selfTypeInOther:
                                return True, False
                            else:
                                # both scopes make statements about different types of scopes
                                return False, False
                        case NodeScopeTier.Node:
                            if same_asn:
                                if same_type:
                                    return True, False
                                elif otherTypeInSelf:
                                    return True, False
                                else:
                                    return False, False
                            else:
                                return False, False
                    
                case NodeScopeTier.Node:

                    match other.tier:
                        case NodeScopeTier.AS:
                            if same_asn:
                                if same_type:
                                    return True, False
                                elif selfTypeInOther:
                                    return True, False
                                else:
                                    return False, False
                            else:
                                return False, False

                        case NodeScopeTier.Global:
                            if same_type:
                                return True, False
                            elif selfTypeInOther:
                                return True, False
                            else:
                                return False, False
                    




    def __gt__(self, other: Scope):        
        """!@brief defines scope hierarchy comparison i.e. broader more general(less specific) > more specific).
            i.e. LHS supserset RHS
        """
        if not isinstance(other, NodeScope):
            return NotImplemented
        # TODO what is correct ?! NotImpl or False
        #if not isinstance(other, NodeScope): return False

        same_type = True if self.type == other.type else False
        common_type = self.type & other.type
        otherTypeInSelf = ( (self.type & other.type) == other.type )
        selfTypeInOther = ( ( (other.type & self.type)==self.type ) )
        contained_type = selfTypeInOther or otherTypeInSelf
        same_type = self.type == other.type
        same_asn = self.asn == other.asn
        same_node = same_asn and self.node == other.node # and same_type ?!

        if self.tier==other.tier:
            match self.tier:
                case NodeScopeTier.Global:  # asn, nodeID irrelevant
                    if same_type:
                        return False # they are equal not gt
                    elif otherTypeInSelf:
                        return True
                    else:
                        return NotImplemented

                case NodeScopeTier.AS: # nodeID irrelevant
                    if same_asn:
                        if same_type:
                            return False # they are equal not gt
                        elif otherTypeInSelf:
                            return True
                        else:
                            return NotImplemented
                    else:
                        # scopes of different ASes are disjoint
                        return NotImplemented
                    
                case NodeScopeTier.Node: # type should be irrelevant (i.e. redundant ) here
                    if same_asn:
                        if same_node:
                            return False # equal and not gt
                        else:
                            return NotImplemented
                    else:
                        return NotImplemented
        else:
            match self.tier:
                case NodeScopeTier.Global:
                    # other.tier must be AS or Node
                    match other.tier:
                        case NodeScopeTier.AS:
                            if same_type:
                                # other AS scope is subset of self (gt)
                                return True
                            elif otherTypeInSelf:
                                # other AS scope is a subset of self (gt)
                                return True
                            else:                                
                                return False
                        case NodeScopeTier.Node:
                            if same_type:
                                # other is subset of self (gt)
                                return True
                            elif otherTypeInSelf: 
                                # other is subset of self (gt)
                                return True
                            else:
                                return False
                    
                case NodeScopeTier.AS:
                    
                    match  other.tier:
                        case NodeScopeTier.Global:
                            
                                return False
                        case NodeScopeTier.Node:
                            if same_asn:
                                if same_type:
                                    return True
                                elif otherTypeInSelf:
                                    return True
                                else:
                                    return False
                            else:
                                return False
                    
                case NodeScopeTier.Node:

                    match other.tier:
                        case NodeScopeTier.AS:
                            
                            return False

                        case NodeScopeTier.Global:
                            return False        
       

    def lt_old(self, other):
        if self._tier != other._tier:
            return self._tier < other._tier  # Higher tier value means broader scope
        if self._node_type != other._node_type:   # More specific node type wins
            if   selfTypeInOther := ( ( (other.type & self.type)==self.type ) ):
                return True
            else:
                return False
        if self._node_id or other._node_id:
            return bool(self._node_id) and not bool(other._node_id)  # Node scope is most specific
        return False

    def __lt__(self, other: Scope):
        """!@brie fDefines scope hierarchy comparison (more specific < broader).
            i.e. LHS subset RHS
        """
        if not isinstance(other, NodeScope):
            return NotImplemented
        
        same_type = True if self.type == other.type else False
        common_type = self.type & other.type
        otherTypeInSelf = ( (self.type & other.type) == other.type )
        selfTypeInOther = ( ( (other.type & self.type)==self.type ) )
        contained_type = selfTypeInOther or otherTypeInSelf
        same_type = self.type == other.type
        same_asn = self.asn == other.asn
        same_node = same_asn and self.node == other.node # and same_type ?!

        if self.tier==other.tier:
            match self.tier:
                case NodeScopeTier.Global:  # asn, nodeID irrelevant
                    if same_type:
                        return False # they are equal not lt
                    elif selfTypeInOther:
                        return True
                    else:
                        return NotImplemented

                case NodeScopeTier.AS: # nodeID irrelevant
                    if same_asn:
                        if same_type:
                            return False # they are equal not lt
                        elif selfTypeInOther:
                            return True
                        else:
                            return NotImplemented
                    else:
                        # scopes of different ASes are disjoint
                        return NotImplemented
                    
                case NodeScopeTier.Node: # type should be irrelevant (i.e. redundant ) here
                    if same_asn:
                        if same_node:
                            return False # equal and not lt
                        else:
                            return NotImplemented
                    else:
                        return NotImplemented
        else:
            match self.tier:
                case NodeScopeTier.Global:
                    # other.tier must be AS or Node
                    match other.tier:
                        case NodeScopeTier.AS:
                            if same_type:
                                # other AS scope is subset of self (gt)
                                return False
                            elif otherTypeInSelf:
                                # other AS scope is a subset of self (gt)
                                return False
                            else:                                
                                return False
                        case NodeScopeTier.Node:
                            if same_type:
                                # other is subset of self (gt)
                                return False
                            elif otherTypeInSelf: 
                                # other is subset of self (gt)
                                return False
                            else:
                                return False
                    
                case NodeScopeTier.AS:
                    
                    match  other.tier:
                        case NodeScopeTier.Global:
                            if same_type: # self is subset of other
                                return True
                            elif selfTypeInOther:
                                return True
                            else:
                                # both scopes make statements about different types of scopes
                                return False
                        case NodeScopeTier.Node:
                            if same_asn:
                                if same_type:
                                    return False
                                elif otherTypeInSelf:
                                    return False
                                else:
                                    return False
                            else:
                                return False
                    
                case NodeScopeTier.Node:

                    match other.tier:
                        case NodeScopeTier.AS:
                            if same_asn:
                                if same_type:
                                    return True
                                elif selfTypeInOther:
                                    return True
                                else:
                                    return False
                            else:
                                return False

                        case NodeScopeTier.Global:
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
        if self._node_type != NodeScopeType.ANY:
            details.append(f"Type={self._node_type.name}")
        if self._node_id:
            details.append(f"Node={self._node_id}")
        return f"NodeScope({', '.join(details) or 'Global'})"
    




class NetScopeTier(ScopeTier):
    Global = 3
    Scoped =  2 # by IX, ASN scope Nr
    Individual = 1 # specific Network instance
class NetScopeType(ScopeType):
    NONE = 0
    ANY  = 9
    LOCAL = 1 # LocalNetwork
    XC = 2 # CrossConnect
    IX = 4 # InternetExchange
    BRIDGE = 8 # Bridge
    @staticmethod
    def from_net(net: 'Network') -> 'NetScopeType':
        from .enums import NetworkType
        match net.getType():
            case NetworkType.InternetExchange:
                return NetScopeType.IX
            case NetworkType.Local:
                return NetScopeType.LOCAL
            case NetworkType.CrossConnect:
                return NetScopeType.XC
            case NetworkType.Bridge:
                return NetScopeType.BRIDGE


class NetScope:
    """!
    @brief strong type for the hierarchical scope of configuration settings.
   
    @note Scopes are immutable after construction and serve as a multi-level key or index into a set of options.
        Scopes implement <> comparison to readily determine when options are overriden by more specific scopes.
        However they do not form a total order (i.e. ScopeTypes like rnode, hnode within the same AS or Globally cannot be compared )
        Also Scope does not cater for multihomed ASes where nodes can be in more than one AS at the same time.
    """
    
    # NOTE ISD scope could be added here

  
    def __init__(self,
                  tier: NetScopeTier,
                  net_type: NetScopeType = NetScopeType.ANY,
                  net_id: str = None,
                  scope_id: int = None):
        '''
        @param scope_id  an IX or ASN number
        @param net_id    name of a specific Network
        '''
        if tier==NetScopeTier.Scoped:
            assert scope_id!=None, 'Invalid Input'
            assert net_id==None, 'Invalid Input'
        if tier==NetScopeTier.Global:
            assert net_id==None, 'invalid input'
            assert scope_id==None, 'invalid input'
        if tier==NetScopeTier.Node:
            assert net_id!=None, 'invalid input'
            assert scope_id!=None, 'invalid input'

        self._tier = tier
        self._net_type = net_type
        self._net_id = net_id  # Only set for per-node scopes
        self._scope_id = scope_id  # Only set for per-AS scopes
    '''
    def __hash__(self):
        """Allows Scope instances to be used as dictionary keys."""
        return hash((self.tier, self.node_type, self.node_id, self.as_id))
    '''
    @property
    def tier(self) -> NetScopeTier:
        return self._tier
    
    @property
    def type(self)-> NetScopeType:
        return self._net_type
    
    @property
    def net(self) -> Optional[str]:
        return self._net_id
    
    @property
    def scope(self) -> Optional[int]:
        return self._scope_id

    def _intersection(self, other: 'Scope') -> 'Scope':
        """!
        @brief return a new scope which represents the intersection of both scopes
        """
        pass

    def _comparable(self, other: Scope) -> Tuple[bool,bool]:
        """ returns a two bools indicating wheter the scopes are:
          lt/gt comparable or identical"""

        if not isinstance(other, NetScope): return (False, False)

        same_type = True if self.type == other.type else False
        common_type = self.type & other.type
        otherTypeInSelf = ( (self.type & other.type) == other.type )
        selfTypeInOther = ( ( (other.type & self.type)==self.type ) )
        contained_type = selfTypeInOther or otherTypeInSelf
        same_type = self.type == other.type
        same_scope = self._scope_id == other._scope_id
        same_node = same_scope and self._net_id == other._net_id # and same_type ?!

        if self.tier==other.tier:
            match self.tier:
                case NetScopeTier.Global:  # asn, nodeID irrelevant
                    if same_type:
                        return False, True
                    else:
                        return False, False

                case NetScopeTier.Scoped: # nodeID irrelevant
                    if same_scope:
                        if same_type:
                            return False, True
                        else:
                            return False, False
                    else:
                        return False, False
                    
                case NetScopeTier.Individual: # type should be irrelevant (i.e. redundant ) here
                    if same_scope:
                        if same_node:
                            return False,True
                        else:
                            return False, False
                    else:
                        return False, False
        else:
            match self.tier:
                case NetScopeTier.Global:
                    # other.tier must be AS or Node
                    match other.tier:
                        case NetScopeTier.AS:
                            if same_type:
                                # other AS scope is subset of self
                                return True, False
                            elif otherTypeInSelf:
                            # other AS scope is a subset of self
                                return True, False
                            else:
                                # types conflict and prevent inclusion
                                return False, False
                        case NetScopeTier.Node:
                            if same_type:
                                return True, False
                            elif otherTypeInSelf: 
                                return True, False
                            else:
                                return False, False
                    
                case NetScopeTier.AS:
                    
                    match  other.tier:
                        case NetScopeTier.Global:
                            if same_type: # self is subset of other
                                return True, False
                            elif selfTypeInOther:
                                return True, False
                            else:
                                # both scopes make statements about different types of scopes
                                return False, False
                        case NetScopeTier.Node:
                            if same_scope:
                                if same_type:
                                    return True, False
                                elif otherTypeInSelf:
                                    return True, False
                                else:
                                    return False, False
                            else:
                                return False, False
                    
                case NetScopeTier.Node:

                    match other.tier:
                        case NetScopeTier.AS:
                            if same_scope:
                                if same_type:
                                    return True, False
                                elif selfTypeInOther:
                                    return True, False
                                else:
                                    return False, False
                            else:
                                return False, False

                        case NetScopeTier.Global:
                            if same_type:
                                return True, False
                            elif selfTypeInOther:
                                return True, False
                            else:
                                return False, False
                    




    def __gt__(self, other: Scope):        
        """!@brief defines scope hierarchy comparison i.e. broader more general(less specific) > more specific).
            i.e. LHS supserset RHS
        """
        if not isinstance(other, NetScope):
            return NotImplemented
        # TODO what is correct ?! NotImpl or False
        #if not isinstance(other, NodeScope): return False

        same_type = True if self.type == other.type else False
        common_type = self.type & other.type
        otherTypeInSelf = ( (self.type & other.type) == other.type )
        selfTypeInOther = ( ( (other.type & self.type)==self.type ) )
        contained_type = selfTypeInOther or otherTypeInSelf
        same_type = self.type == other.type
        same_asn = self.scope == other.scope
        same_node = same_asn and self.net == other.net # and same_type ?!

        if self.tier==other.tier:
            match self.tier:
                case NetScopeTier.Global:  # asn, nodeID irrelevant
                    if same_type:
                        return False # they are equal not gt
                    elif otherTypeInSelf:
                        return True
                    else:
                        return NotImplemented

                case NetScopeTier.Scoped: # nodeID irrelevant
                    if same_asn:
                        if same_type:
                            return False # they are equal not gt
                        elif otherTypeInSelf:
                            return True
                        else:
                            return NotImplemented
                    else:
                        # scopes of different ASes are disjoint
                        return NotImplemented
                    
                case NetScopeTier.Node: # type should be irrelevant (i.e. redundant ) here
                    if same_asn:
                        if same_node:
                            return False # equal and not gt
                        else:
                            return NotImplemented
                    else:
                        return NotImplemented
        else:
            match self.tier:
                case NetScopeTier.Global:
                    # other.tier must be AS or Node
                    match other.tier:
                        case NetScopeTier.Scoped:
                            if same_type:
                                # other AS scope is subset of self (gt)
                                return True
                            elif otherTypeInSelf:
                                # other AS scope is a subset of self (gt)
                                return True
                            else:                                
                                return False
                        case NetScopeTier.Individual:
                            if same_type:
                                # other is subset of self (gt)
                                return True
                            elif otherTypeInSelf: 
                                # other is subset of self (gt)
                                return True
                            else:
                                return False
                    
                case NetScopeTier.AS:
                    
                    match  other.tier:
                        case NetScopeTier.Global:
                            
                                return False
                        case NetScopeTier.Node:
                            if same_asn:
                                if same_type:
                                    return True
                                elif otherTypeInSelf:
                                    return True
                                else:
                                    return False
                            else:
                                return False
                    
                case NetScopeTier.Node:

                    match other.tier:
                        case NetScopeTier.Scoped:                            
                            return False

                        case NetScopeTier.Global:
                            return False        
       

    def __lt__(self, other: Scope):
        """!@brie fDefines scope hierarchy comparison (more specific < broader).
            i.e. LHS subset RHS
        """
        if not isinstance(other, NetScope):
            return NotImplemented
        
        same_type = True if self.type == other.type else False
        common_type = self.type & other.type
        otherTypeInSelf = ( (self.type & other.type) == other.type )
        selfTypeInOther = ( ( (other.type & self.type)==self.type ) )
        contained_type = selfTypeInOther or otherTypeInSelf
        same_type = self.type == other.type
        same_scope = self.scope == other.scope
        same_net = same_scope and self.net == other.net # and same_type ?!

        if self.tier==other.tier:
            match self.tier:
                case NetScopeTier.Global:  # asn, nodeID irrelevant
                    if same_type:
                        return False # they are equal not lt
                    elif selfTypeInOther:
                        return True
                    else:
                        return NotImplemented

                case NetScopeTier.AS: # nodeID irrelevant
                    if same_scope:
                        if same_type:
                            return False # they are equal not lt
                        elif selfTypeInOther:
                            return True
                        else:
                            return NotImplemented
                    else:
                        # scopes of different ASes are disjoint
                        return NotImplemented
                    
                case NetScopeTier.Individual: # type should be irrelevant (i.e. redundant ) here
                    if same_scope:
                        if same_net:
                            return False # equal and not lt
                        else:
                            return NotImplemented
                    else:
                        return NotImplemented
        else:
            match self.tier:
                case NetScopeTier.Global:
                    # other.tier must be AS or Node
                    match other.tier:
                        case NetScopeTier.Scoped:
                            if same_type:
                                # other AS scope is subset of self (gt)
                                return False
                            elif otherTypeInSelf:
                                # other AS scope is a subset of self (gt)
                                return False
                            else:                                
                                return False
                        case NetScopeTier.Individual:
                            if same_type:
                                # other is subset of self (gt)
                                return False
                            elif otherTypeInSelf: 
                                # other is subset of self (gt)
                                return False
                            else:
                                return False
                    
                case NetScopeTier.Scoped:
                    
                    match  other.tier:
                        case NetScopeTier.Global:
                            if same_type: # self is subset of other
                                return True
                            elif selfTypeInOther:
                                return True
                            else:
                                # both scopes make statements about different types of scopes
                                return False
                        case NetScopeTier.Individual:
                            if same_scope:
                                if same_type:
                                    return False
                                elif otherTypeInSelf:
                                    return False
                                else:
                                    return False
                            else:
                                return False
                    
                case NetScopeTier.Individual:

                    match other.tier:
                        case NetScopeTier.Scoped:
                            if same_scope:
                                if same_type:
                                    return True
                                elif selfTypeInOther:
                                    return True
                                else:
                                    return False
                            else:
                                return False

                        case NetScopeTier.Global:
                            if same_type:
                                return True
                            elif selfTypeInOther:
                                return True
                            else:
                                return False

    def __repr__(self):
        """String representation for debugging."""
        details = []
        if self._scope_id is not None:
            details.append(f"scope={self._scope_id}")
        if self._net_type != NetScopeType.ANY:
            details.append(f"Type={self._net_type.name}")
        if self._net_id:
            details.append(f"Net={self._net_id}")
        return f"NetScope({', '.join(details) or 'Global'})"
    
