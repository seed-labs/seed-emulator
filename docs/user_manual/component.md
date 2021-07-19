# User Manual: Emulator Component

Put the manual regarding component here. 


<a name="virtual-node-binding"></a>
## Virtual node binding & filtering

The constructor of a binding looks like this:

```python
def __init__(self, source, action = Action.RANDOM, filter = Filter()):
```

- `source` is a regex string to match virtual node names. For example, if we want to match all nodes starts with "web," we can use `"web.*"`.
- `action` is the action to take after a list of candidates is selected by the filter. It can be `RANDOM`, which select a random node from the list, `FIRST`, which use the first node from the list, or `LAST`, which use the last node from the list. It defaults to `RANDOM`.
- `filter` points to a filter object. Filters will be discussed in detail later. It defaults to an empty filter with no rules set, which will select all physical nodes without binding as candidates.

The constructor of a filter looks like this:

```python
def __init__(
    self, asn: int = None, nodeName: str = None, ip: str = None,
    prefix: str = None, custom: Callable[[str, Node], bool] = None,
    allowBound: bool = False
)
```

All constructor parameters are one of the constraints. If more than one constraint is set, a physical node must meet all constraints to be selected as a candidate. 

- `asn` allows one to limit the AS number of physical nodes. When this is set, only physical nodes from the given AS will be selected.
- `nodeName` allows one to define the name of the physical node to be selected. Note that physical nodes from different ASes can have the same name. 
- `ip` allows one to define the IP of the physical node to be selected.
- `prefix` allows one to define the prefix of IP address on the physical node to be selected. Note that the prefix does not have to match the exact prefix attach to the interface of the physical node; as long as the IP address on the interface falls into the range of the prefix given, the physical node will be selected.
- `custom` allows one to use a custom function to select nodes. The function should take two parameters, the first is a string, the virtual node name, and the second is a Node object, the physical node. Then function should then return `True` if a node should be selected, or `False` otherwise.
- `allowBound` allows physical nodes that are already selected by other binding to be selected again.

