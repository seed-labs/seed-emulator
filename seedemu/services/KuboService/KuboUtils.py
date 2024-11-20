from __future__ import annotations
import socket, re
from ipaddress import IPv4Address
from typing import Any, Mapping, Tuple
from seedemu import *
from seedemu.core.enums import NetworkType

class DottedDict(dict):
    """A specific case of dictionary. Nested dictionaries referenced using JSON dot notation.
       This introduces additional key requirements: 
          - The '.' character is not allowed in keys, but may be used to separate keys in JSON dot notation.
          - The empty string is not a valid key.
    """
    def __init__(self, src=None, **kwargs):
        """Create an instance of a DottedDict.

        Parameters
        ----------
        src : Any, optional
            This should be a Mapping or Iterable from which a DottedDict is created, by default None
        """
        # Check if we should initialize empty DottedDict:
        if src is None:
            super().__init__(**kwargs)
        # If this is already a dict-like structure, ensure nested dicts become DottedDicts:
        elif isinstance(src, Mapping):
            newMapping = {}
            for key, value in src.items():
                if type(value) is dict:
                    newMapping[key] = DottedDict(value)
                else:
                    newMapping[key] = value
            super().__init__(newMapping, **kwargs)
        # Otherwise this must be an iterable (superset of Mapping), or superclass TypeError is raised:
        else:
            newIterable = []
            for key, value in src:
                if type(value) is dict:
                    newIterable.append((key, DottedDict(value)))
                else:
                    newIterable.append((key, value))
            super().__init__(newIterable, **kwargs)
            
    
    def __getitem__(self, key: str) -> Any:
        """Overrides the default implementation to allow retrieval in JSON dot notation.

        Parameters
        ----------
        key : str
            A string representing a key in JSON dot notation.

        Returns
        -------
        Any
            The corresponding value.

        Raises
        ------
        TypeError
            The key in a DottedDict must be of type string.
        KeyError
            The key does not exist in this DottedDict instance.
        """
        if not isinstance(key, str):
            raise TypeError('DottedDict expects keys of type string.')
        if key not in self:
            raise KeyError(key)
        
        keys = key.split('.')
        
        # If one key, just use super's:
        if len(keys) == 1:
            return super().__getitem__(keys[0])
        # Otherwise, return the value of the child given the remaining keys:
        else:
            childItem = self.__getitem__(keys[0])
            # Ensure child is dict-like before getting item recursively:
            if not isinstance(childItem, Mapping): raise KeyError(key)
            return childItem.__getitem__(".".join(keys[1:]))
    
    def __setitem__(self, key: str, value: Any) -> None:
        """Overrides the default implementation to allow setting a value using a key in JSON dot notation.

        Parameters
        ----------
        key : str
            The key represented as a string in JSON dot notation.
        value : Any
            The corresponding value.

        Raises
        ------
        TypeError
            Raised if the key is not a string, and so is not in JSON dot notation.
        KeyError
            Rasied if key is invalid (leading/trailing dots and empty string keys).
        """
        if not isinstance(key, str):
            raise TypeError('DottedDict expects keys of type string.')
        
        keys = key.split('.')
        # Catch key errors from multiple dots in a row or leading/trailing dots:
        if '' in keys: raise KeyError(key)
        
        if len(keys) == 1:
            super().__setitem__(key, value)
        # If first key refers to a dict-like object, continue to that object:
        elif keys[0] in self and isinstance(self[keys[0]], Mapping):
            self[keys[0]].__setitem__(".".join(keys[1:]), value)
        # Otherwise, make it a dict-like object and continue.
        else:
            self[keys[0]] = DottedDict()
            self[keys[0]].__setitem__(".".join(keys[1:]), value)
                    
                
    def __delitem__(self, key: str) -> None:
        """Overrides default implementation to allow deleting a value based on a key in JSON dot notation.

        Parameters
        ----------
        key : str
            The key represented as a string in JSON dot notation.

        Raises
        ------
        TypeError
            Raised if the key is not a string, and therefore not valid JSON dot notation.
        KeyError
            Raised if the key does not exist in this DottedDict instance.
        """
        if not isinstance(key, str):
            raise TypeError('DottedDict expects keys of type string.')
        if key not in self:
            raise KeyError(key)
        
        keys = key.split('.')
        if len(keys) == 1:
            super().__delitem__(key)
        else:
            self[keys[0]].__delitem__(".".join(keys[1:]))
                
    def __contains__(self, key: object) -> bool:
        """Overrides the default implementation to allow checking if a key exists as specified in JSON dot notation.

        Parameters
        ----------
        key : str
            The key represented as a string in JSON dot notation.

        Returns
        -------
        bool
            True if the key exists, False otherwise.

        Raises
        ------
        TypeError
            Raised if the key is not a string, and therefore not valid JSON dot notation.
        KeyError
            Rasied if key is invalid (leading/trailing dots and empty string keys).
        """
        if not isinstance(key, str):
            raise TypeError('DottedDict expects keys of type string.')
        
        keys = key.split('.')
        # Catch key errors from multiple dots in a row or leading/trailing dots:
        if '' in keys: raise KeyError(key)
        
        # Standard dict, just use default implementation:
        if len(keys) == 1:
            return super().__contains__(key)
        # Should be a nested dict inside the current key, let's check:
        else:
            if super().__contains__(keys[0]) and isinstance(self[keys[0]], Mapping):
                return self[keys[0]].__contains__(".".join(keys[1:]))
            # Otherwise, this key does not exist or its value isn't a mapping, so the next won't exist:
            else:
                return False
            
    def copy(self) -> Self:
        """Overrides the superclass shallow copy to return a shallow copy of type DottedDict.

        Returns
        -------
        Self
            Returns an instance of the DottedDict class with the same contents as this instance.
        """
        return DottedDict(super().copy())
 
    def merge(self, other:Mapping) -> None:
        """Merges another dict-like object into the current DottedDict (in-place).

        Parameters
        ----------
        other : Mapping
            Another dict-like object to be merged into this DottedDict instance.
        """
        for key, value in other.items():
            # Conflict and values of both are dict-like, so merge those:
            if key in self and isinstance(self[key], Mapping) and isinstance(value, Mapping):
                try:
                    self[key].merge(value)
                except AttributeError:
                    self[key] = DottedDict(self[key])
                    self[key].merge(value)
            # Always take non-dict-like values from the other:
            else:
                # Transform dict-like value to DottedDict:
                if isinstance(value, Mapping):
                    self[key] = DottedDict(value)
                else:
                    self[key] = value
                    
    def empty(self) -> bool:
        """Check whether the DottedDict instance is empty or not.

        Returns
        -------
        bool
            True if the DottedDict instance is empty, False otherwise.
        """
        return len(self) == 0
    
    def dottedItems(self) -> list[Tuple[str, Any]]:
        """Like the standard dict::items(), but returns a list of key-value pairs where keys are JSON dot notation for deepest values.

        Returns
        -------
        list[Tuple[str, Any]]
            A list of key-value pairs for every item in the DottedDict.
        """
        deepestItems = []
        for key in self:
            newItem = self.__dfsHelper(key, set())
            if newItem is not None: deepestItems.extend(newItem)
        return deepestItems
        
    def __dfsHelper(self, curKey:str, visited:set) -> list[Tuple[str, Any]]:
        """A private helper function to perform depth first search (DFS) on the DottedDict for the dottedItems() method.

        Parameters
        ----------
        curKey : str
            The current key being traversed.
        visited : set
            The set of keys that have already been visited.

        Returns
        -------
        list[Tuple[str, Any]]
            A list of key-value pairs, where the value is the deepest ('leaf') value in the DottedDict, starting from the specified key.
        """
        if curKey not in visited:
            visited.add(curKey)
            if isinstance(self[curKey], Mapping):
                childItems = []
                for childKey in self[curKey]:
                    childItems.extend(self.__dfsHelper(f'{curKey}.{childKey}', visited))
                return childItems
            else:
                return [(curKey, self[curKey])]


def getIP(node:Node) -> IPv4Address:
    """Find the first local IPv4 address for a given node.

    Parameters
    ----------
    node : Node
        A physical node in the emulator.

    Returns
    -------
    str
        A string representing an IPv4 address.
    """
    ifaces = node.getInterfaces()
    assert len(ifaces) > 0, f'Node {node.getName()} has no IP address.'
    for iface in ifaces:
        net = iface.getNet()
        if net.getType() == NetworkType.Local:
            return iface.getAddress()
    return None

def isIPv4(ip:str) -> bool:
    """Evaluates whether a string is a valid IPv4 address.

    Parameters
    ----------
    ip : str
        The string to be tested.

    Returns
    -------
    bool
        True if the given string represents a valid IPv4 address.
    """
    # Preliminary check with RegEx:
    ipv4_regex = '^((25[0-5]|(2[0-4]|1[0-9]|[1-9]|)[0-9])(\.(?!$)|$)){4}$'
    re_match = re.match(ipv4_regex, ip)
    
    # On RegEx match, check with internal library:
    if re_match:
        try:
            s = socket.inet_aton(ip)
            return True
        # OSError is returned if ip is not valid (exact reason depends on C implementation):
        except OSError:
            return False
    else:
        return False