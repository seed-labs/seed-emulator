from typing import List
from functools import cmp_to_key
from typing import Optional, Dict, Tuple
from seedemu.core.Scope import *
from seedemu.core.Option import BaseOption, OptionMode

class Customizable(object):

    """!
    @brief something that can be configured by Options
    """
    _config: Dict[str,Tuple[BaseOption,Scope]]

    def __init__(self):  # scope param. actually only for debug/tests  , scope: Scope = None        
        super().__init__()
        self._config = {}
        self._scope = None
    
    def scope(self)-> Scope:
        """!@brief returns a scope that includes only this very customizable instance ,nothing else"""
        # it's only natural for a customizable to know its place in the hierarchy
        if not self._scope: return Scope(ScopeTier.Global) # maybe introduce a ScopeTier.NONE for this...
        else: return self._scope
            

    def getScopedOption(self, key: str, scope: Scope = None) -> Optional[Tuple[BaseOption, Scope]]:
        """! @brief retrieves an option along with the most specific Scope in which it was set.
        """
        if not scope:  scope = self.scope()
        
        if key not in self._config: return None
        
        # fetch the most specific option setting to the requested scope
        for ps in filter(None, Customizable._possible_scopes(scope)):
            for (opt,s ) in self._config[key]:            
                try:
                    # scope has equality-relation on all elements
                    if s==ps: # exact match for this specific scope
                        return opt, s
                    elif ps< s: # but this might not be implemented.. and throw
                        # return fst test scope that is included in a setting
                        return opt,s

                except :
                    pass
            
        return None

    def getOption(self, key: str, scope: Scope = None ) -> Optional[BaseOption]:
        """!@brief Retrieves an option(if set) based on the precedence rules (scoping).
                If not specified the option value for the scope most specific to 'this' customizable 
                will be returned.
                However by explicitly asking for a more general scope, all parent 'handDowns' up to the Global settings
                can be retrieved from any customizable regardless of its scope.
            @note actually each layer that provides options should at least provide global defaults.
            So None will be rare if layer implementation is correct and inherits all settings to all nodes.
        """
        optn = self.getScopedOption(key, scope)
        if optn:
            return optn[0]
        else:
            return None

    def _possible_scopes(scope: Scope) -> List[Scope]:
        possible_scopes = [
            Scope(ScopeTier.Node, scope._node_type, 
                  as_id=scope.asn, node_id=scope._node_id) if scope._node_id and scope._as_id and scope._node_type else None,   # Node-specific + type
            Scope(ScopeTier.Node,node_id=scope._node_id, as_id=scope._as_id) if scope._node_id and scope._as_id else None,   # Node-specific
            Scope(ScopeTier.AS, scope._node_type, as_id=scope._as_id) if scope._as_id and scope._node_type else None,   # AS & Type
            Scope(ScopeTier.AS, ScopeType.ANY, as_id=scope._as_id) if scope._as_id else None,    # AS-wide
            Scope(ScopeTier.Global, scope._node_type),   # Global & Type
            Scope(ScopeTier.Global)                     # Global (fallback)
        ]
        return possible_scopes

    def _getKeys(self) -> List[str]:
        
        return list( self._config.keys())
        
    # Tuple[ BaseOption, Scope ]  or List[ScopedOption] where ScopedOption is just a wrapper around Tuple[BaseOption, Scope]
    def getOptions(self, scope: Scope = None )  -> List[BaseOption]:
        """! @brief return all options included by the given scope.
        """
        return [ self.getOption(k, scope) for k in self._getKeys() ]
    
    def getScopedOptions(self, scope: Scope = None )  -> List[Tuple[BaseOption,Scope]]:
        """! @brief return all options included by the given scope.
        """
        return [ self.getScopedOption(k, scope) for k in self._getKeys() ]    
    
    # this method confines all the scope-related uglyness and spares us to expose get/setOptions() methods
    def handDown(self, child: 'Customizable'):
        """! @brief some Customizables are aggregates and own other Customizables.
            i.e. ASes are a collection of Nodes.
            This methods performs the inheritance of options from parent to child.
        """
        
        try: # scopes could be incomparable
            assert self.scope()>child.scope(), 'logic error - cannot inherit options from more general scopes'
        except :
            pass

        for k, val in self._config.items():
            for (op, s) in val:
                child.setOption(op, s)

    def setOption(self, op: BaseOption, scope: Scope = None ):
        """! @brief set option within the given scope.
            If unspecified the option will be overridden only for "this" Customizable i.e. AS
        """
        # TODO should we add a check here, that scope is of same or higher Tier ?!
        # Everything else would be counterintuitive i.e. setting individual node overrides through the 
        # API of the AS , rather than the respective node's itself

        if not scope:  scope = self.scope()

        if not op.name in self._config: # fst encounter of this option -> no conflict EASY 
            self._config[op.name] = [(op,scope)]
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
            if (i:=find_index( [s for _,s in self._config[op.name]], scope)) !=-1:
                # update the option value (change of mind)
                self._config[op.name][i] = (op,scope)
            else: # add the setting for the new scope
                self._config[op.name].append((op,scope))
                res= sorted(self._config[op.name], key=cmp_to_key(cmp_snd) )
                            # key=cmp_to_key(Scope.collate),reverse=True)
                self._config[op.name]  = res
            

    def getRuntimeOptions(self, scope: Scope = None) -> List[BaseOption]:
        return [ o for o in self.getOptions(scope) if o.mode==OptionMode.RUN_TIME]
    
    def getScopedRuntimeOptions(self, scope: Scope = None) -> List[Tuple[BaseOption,Scope]]:
        scopts = self.getScopedOptions(scope)
        return [ (o,s) for o,s in scopts if o.mode==OptionMode.RUN_TIME]
