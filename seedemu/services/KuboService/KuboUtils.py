import json, socket
from operator import setitem
from typing import Any, Self, Mapping, Iterable
from seedemu import *
from seedemu.core.enums import NetworkType

class DottedDict(dict):
    """A specific case of dictionary. Nested dictionaries referenced using JSON dot notation.
        NOTE: the '.' character is not allowed in keys, but may be used to separate keys in JSON dot notation.
    """
    def __init__(self, src=None, **kwargs):
        """Create an instance of a DottedDict.

        Parameters
        ----------
        src : Any, optional
            This should be a Mapping or Iterable from which a DottedDict is created, by default None
        """
        if isinstance(src, Mapping):
            for key, value in src.items():
                if type(value) == dict:
                    src[key] = DottedDict(value)
            super().__init__(src, **kwargs)
        elif isinstance(src, Iterable):
            newIterable = []
            for key, value in src:
                if type(value) == dict:
                    newIterable.append((key, DottedDict(value)))
                else:
                    newIterable.append((key, value))
            super().__init__(newIterable, **kwargs)
        else:
            super().__init__(**kwargs)
            
    
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
        """
        if not isinstance(key, str):
            raise TypeError('DottedDict expects keys of type string.')
        
        keys = key.strip().split('.')
        # print(f'{key}: {keys}')
        if len(keys) == 1:
            return super().__getitem__(keys[0])
        else:
            outerDict = self.__getitem__(keys[0])
            # print(f'{type(outerDict)}: {outerDict}')
            return outerDict.__getitem__(".".join(keys[1:]))
    
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
        """
        if not isinstance(key, str):
            raise TypeError('DottedDict expects keys of type string.')
        
        keys = key.strip().split('.')
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
        
        keys = key.strip().split('.')
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
        """
        if not isinstance(key, str):
            raise TypeError('DottedDict expects keys of type string.')
        
        keys = key.strip().split('.')
        # Standard dict, just use default implementation:
        if len(keys) == 1:
            return super().__contains__(key)
        # Should be a nested dict inside the current key, let's check:
        else:
            # If there is another mapping at the first level, check the next:
            if isinstance(self[keys[0]], Mapping):
                return self[keys[0]].__contains__(".".join(keys[1:]))
            # Otherwise, this is is not a mapping, so stop checking:
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



def setDictByDot(dict:dict, dotted_key:str, value:Any) -> None:
    """Sets a dictionary value based on JSON dot notation (used for nested dicts).

    Args:
        dict (dict): dictionary (outermost)
        dotted_key (str): dictionary key described in JSON dot notations
        value (Any): value for the given key
    """
    keys = dotted_key.strip().split('.')
    if len(keys) == 1:
        # dict[dotted_key] = value
        setitem(dict, dotted_key, value)
    else:
        setDictByDot(dict[keys[0]], ".".join(keys[1:]), value)
        

def getDictByDot(dict:dict, dotted_key:str) -> Any:
    keys = dotted_key.strip().split('.')
    if len(keys) == 1:
        return dict.get(keys[0])
    else:
        return getDictByDot(dict.get(keys[0]), ".".join(keys[1:]))
    

# def _dictFromDot(dotted_key:str, value:Any) -> dict:
#     nestedDict = {}
#     keys = dotted_key.strip().split('.')
#     if len(keys) == 1:
#         nestedDict[dotted_key] = value
#     else:
#         nestedDict[keys[0]] = _dictFromDot(".".join(keys[1:]), value)
#     return nestedDict


# def mergeNestedDicts(dict1:dict, dict2:dict) -> dict:
#     merged = dict1.copy()
    
#     for cur in [dict1, dict2]:
#         # Define other dict at current run:
#         if cur == dict1: other = dict2
#         else: other = dict1
        
#         for key, value in cur.items():
#             # If this is a nested dict in both dicts, merge those:
#             if type(value) == dict and type(other.get(key)) == dict:
#                 merged[key] = mergeNestedDicts(cur[key], other[key])
#             # If this is just a nested dict in the second dict, replace the first dict's value:
#             elif type(other.get(key)) == dict:
#                 merged[key] = other.get(key)
#             # Otherwise, just keep the value from the first dict:
#             else:
#                 merged[key] = cur.get(key)
        
#     return merged

def getIP(node:Node) -> str:
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
    try:
        socket.inet_aton(ip)
        return True
    # OSError is returned if ip is not valid (reason depends on C implementation):
    except OSError:
        return False
           
    
if __name__ == "__main__":
    newDict = {}
    d1 = _dictFromDot("Identity.PeerID", "sdjklfhuoqwjksdask'das;da0wkjklfhdsaj;sjdfasdjlhf")
    d1["test"] = 1
    d2 = _dictFromDot("Identity.PrivKey", "1231927432714718237428137421397348718394789137849712894723984071238947")
    d2['newNode'] = True
    # newDict.update(_dictFromDot("Addresses.API.Test", "[1.1.1.1, 2.2.2.2]"))
    # newDict.update(_dictFromDot("Addresses.API", "0.0.0.0"))
    # newDict.update(_dictFromDot("Identity.PeerID", "sdjklfhuoqwjksdask'das;da0wkjklfhdsaj;sjdfasdjlhf"))
    # newDict = _mergeNestedDicts(newDict, _dictFromDot("Identity.PeerID", "sdjklfhuoqwjksdask'das;da0wkjklfhdsaj;sjdfasdjlhf"))
    # newDict.update(_dictFromDot("Identity.PrivKey", "1231927432714718237428137421397348718394789137849712894723984071238947"))
    # newDict = _mergeNestedDicts(newDict, _dictFromDot("Identity.PrivKey", "1231927432714718237428137421397348718394789137849712894723984071238947"))
    newDict = mergeNestedDicts(d1, d2)
    print(json.dumps(newDict, indent=2))
    setDictByDot(newDict, "test", 5)
    print(json.dumps(newDict, indent=2))
    setDictByDot(newDict, "Identity.PrivKey", 'hehehehehhehe')
    print(json.dumps(newDict, indent=2))
    print(getDictByDot(newDict, "newNode"))
    print(getDictByDot(newDict, "Identity.PeerID"))
    print(getDictByDot(newDict, "Identity"))
    
    print(f'{"Testing DottedDict":=^100}')
    ddict = DottedDict()
    ddict['test'] = 1
    print(ddict)
    ddict['a.b.c'] = [1, 2, 3]
    print(ddict)
    print('a' in ddict)
    print('a.b' in ddict)
    ddict.pop('a.b')
    print(ddict)