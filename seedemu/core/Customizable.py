from typing import List
from functools import cmp_to_key
from typing import Optional, Dict, Tuple
from seedemu.core.Scope import *
from seedemu.core.Option import BaseOption, OptionMode, OptionDomain

class Customizable(object):

    """!
    @brief something that can be configured by Options
    """
    _config: Dict[str,Tuple[BaseOption,NodeScope]]

    def __init__(self):  # scope param. actually only for debug/tests  , scope: Scope = None        
        super().__init__()
        self._config = {}
        self._scope = None
    
    def scope(self, domain: OptionDomain = None)-> NodeScope:
        """!@brief returns a scope that includes only this very customizable instance ,nothing else
        @param domain depending on what you need the scope object for
                (i.e. for which kind of Option you want to specify the scope for)
                you might need a different kind of scope
        """
        # it's only natural for a customizable to know its place in the hierarchy
        if not self._scope: return NodeScope(NodeScopeTier.Global) # maybe introduce a ScopeTier.NONE for this...
        else: return self._scope
            

    def getScopedOption(self, key: str, scope: NodeScope = None, prefix: str = None) -> Optional[Tuple[BaseOption, NodeScope]]:
        """! @brief retrieves an option along with the most specific Scope in which it was set.
        """
        from seedemu.core.OptionRegistry import OptionRegistry
        if not scope:  scope = self.scope(domain=OptionRegistry().getDomain(key, prefix))

        keys = [key]

        if key == '*':
            keys = self._config.keys()
        elif key not in self._config:
            if prefix!=None and (k:=f'{prefix}_{key}') in self._config:
                key = k
            else:
                return None
        
        # fetch the most specific option setting to the requested scope
        for ps in filter(None, Customizable._possible_scopes(scope)):
            for k in keys:
                if prefix != None and key != '*': k = prefix + '_' + k
                elif prefix != None and key == '*':
                    if not k.startswith(prefix):  continue
               

                for (opt, s) in self._config[k]:            
                    try:
                        # scope has equality-relation on all elements
                        if s == ps: # exact match for this specific scope
                            return opt, s
                        elif ps < s: # but this might not be implemented.. and throw
                            # return fst test scope that is included in a setting
                            return opt, s

                    except :
                        pass
            
        return None

    def getOption(self, key: str, scope: NodeScope = None, prefix: str = None ) -> Optional[BaseOption]:
        """!@brief Retrieves an option(if set) based on the precedence rules (scoping).
                If not specified the option value for the scope most specific to 'this' customizable 
                will be returned.
                However by explicitly asking for a more general scope, all parent 'handDowns' up to the Global settings
                can be retrieved from any customizable regardless of its scope.
            @note actually each layer that provides options should at least provide global defaults.
            So None will be rare if layer implementation is correct and inherits all settings to all nodes.
        """
        optn = self.getScopedOption(key, scope, prefix)
        if optn:
            return optn[0]
        else:
            return None

    def _possible_scopes(scope: NodeScope) -> List[NodeScope]:
        if isinstance(scope, NodeScope):
            possible_scopes = [
                NodeScope(NodeScopeTier.Node, scope._node_type, 
                      as_id=scope.asn, node_id=scope._node_id) if scope._node_id and scope._as_id and scope._node_type else None,   # Node-specific + type
                NodeScope(NodeScopeTier.Node,node_id=scope._node_id, as_id=scope._as_id) if scope._node_id and scope._as_id else None,   # Node-specific
                NodeScope(NodeScopeTier.AS, scope._node_type, as_id=scope._as_id) if scope._as_id and scope._node_type else None,   # AS & Type
                NodeScope(NodeScopeTier.AS, NodeScopeType.ANY, as_id=scope._as_id) if scope._as_id else None,    # AS-wide
                NodeScope(NodeScopeTier.Global, scope._node_type),   # Global & Type
                NodeScope(NodeScopeTier.Global)                     # Global (fallback)
            ]
        if isinstance(scope, NetScope):
            possible_scopes = [
                NetScope(NetScopeTier.Individual,net_type=scope.type, scope_id=scope.scope, net_id=scope.net ) 
                if scope.scope and scope.net and scope.type else None, # Net specific + type
                NetScope(NetScopeTier.Individual, scope_id=scope.scope, net_id=scope.net ) 
                if scope.scope and scope.net else None, # Net specific

                NetScope(NetScopeTier.Scoped, scope.type, scope_id=scope.scope) 
                if scope.scope and scope.type else None,   # scope & Type
                NetScope(NetScopeTier.Scoped, NetScopeType.ANY, scope_id=scope.scope)
                if scope.scope else None,    # scope-wide

                NetScope(NetScopeTier.Global, net_type=scope.type),
                NetScope(NetScopeTier.Global)
            ]

        return possible_scopes

    def _getKeys(self) -> List[str]:
        
        return list( self._config.keys())
        
    # Tuple[ BaseOption, Scope ]  or List[ScopedOption] where ScopedOption is just a wrapper around Tuple[BaseOption, Scope]
    def getOptions(self, scope: NodeScope = None )  -> List[BaseOption]:
        """! @brief return all options included by the given scope.
        """
        return [ self.getOption(k, scope) for k in self._getKeys() ]
    
    def getScopedOptions(self, scope: NodeScope = None, prefix: str = None )  -> List[Tuple[BaseOption,NodeScope]]:
        """! @brief return all options included by the given scope.
        """
        return [ self.getScopedOption(k, scope) for k in self._getKeys() if (prefix != None and k.startswith(prefix)) or prefix==None ]    
    
    # this method confines all the scope-related uglyness and spares us to expose get/setOptions() methods
    def handDown(self, child: 'Customizable'):
        """! @brief some Customizables are aggregates and own other Customizables.
            i.e. ASes are a collection of Nodes.
            This methods performs the inheritance of options from parent to child.
        """
        from .Network import Network
        from .Node import Node
        dom = OptionDomain.NET if type(child)== Network else OptionDomain.NODE
        s1=self.scope(dom)
        s2=child.scope(dom)

       
        assert not s1 < s2, 'logic error - cannot inherit options from more general scopes'

        for k, val in self._config.items():
            for (op, s) in val:
                if self.valid_down(op,child):
                    child.setOption(op, s)

    @staticmethod
    def valid_down(op, child):
            from .Network import Network
            from .Node import Node
            # enforce option-domains only at the lowest granularity (customizable hierarchy): Nodes and Networks
            # Any aggregates of higher levels i.e. ASes, ISDs (that don't inherit neither Node nor Network)
            #  can have Options of mixed domains
            return not ((op.optiondomain() == OptionDomain.NET and issubclass(type(child), Node)) or 
                        (issubclass( type(child), Network) and op.optiondomain()==OptionDomain.NODE ) )

    def setOption(self, op: BaseOption, scope: NodeScope = None ):
        """! @brief set option within the given scope.
            If unspecified the option will be overridden only for "this" Customizable i.e. AS
        """
        # TODO should we add a check here, that scope is of same or higher Tier ?!
        # Everything else would be counterintuitive i.e. setting individual node overrides through the 
        # API of the AS , rather than the respective node's itself

        assert self.valid_down(op, self), 'input error'

        if not scope:  scope = self.scope()

        opname = op.name
        # TODO: replace with op.fullname()
        if (p:=op.prefix()) != None:
                opname = f'{p}_{opname}'

        if not opname in self._config: # fst encounter of this option -> no conflict EASY 
            
            self._config[opname] = [(op,scope)]
            return
        else: # conflict / or override for another scope

            # keep the list of (scope, opt-val) sorted  ascending (from narrow to broad) by scope
                
            def find_index(lst, key):
            
                for i, element in enumerate(lst):
                    try:
                        if element == key:
                            return i
                    except TypeError:
                        pass  # Skip elements that are truly incomparable
                return -1  # Not found


            def cmp_snd(a, b):
                """Custom comparator for sorting based on the second tuple element."""
                try:
                    if a[1] < b[1]:
                        return -1
                    elif a[1] > b[1]:
                        return 1
                    else:
                        return 0
                except TypeError:
                    return 0 


            # settings for this scope already exist
            if (i:=find_index( [s for _,s in self._config[opname]], scope)) !=-1:
                # update the option value (change of mind)
                self._config[opname][i] = (op,scope)
            else: # add the setting for the new scope
                self._config[opname].append((op,scope))
                res= sorted(self._config[opname], key=cmp_to_key(cmp_snd) )
                            # key=cmp_to_key(Scope.collate),reverse=True)
                self._config[opname]  = res
            

    def getRuntimeOptions(self, scope: NodeScope = None) -> List[BaseOption]:
        return [ o for o in self.getOptions(scope) if o.mode==OptionMode.RUN_TIME]
    
    def getScopedRuntimeOptions(self, scope: NodeScope = None) -> List[Tuple[BaseOption,NodeScope]]:
        scopts = self.getScopedOptions(scope)
        return [ (o,s) for o,s in scopts if o.mode==OptionMode.RUN_TIME]
