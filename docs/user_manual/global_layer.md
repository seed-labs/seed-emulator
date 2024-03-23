# Global Layer

The global layer is a special layer that is used to manage configurations that apply to all the nodes in the emulator.

## Example Usage for setting the recursive DNS server for all nodes in the emulator

```python
# We use `world` here because `global` is a reserved keyword in Python
world = Global()
ldns = DomainNameCachingService()
# At the AS level
world.apply(lambda node: ldns.setNameServers(node, ['10.152.0.53']), Filter(asn=160))
world.apply(lambda node: ldns.setNameServers(node, ['10.152.0.53']), Filter(asn=170))

# At the emulator level
world.apply(lambda node: ldns.setNameServers(node, ['10.153.0.53']))

# At the node level (not included in the example)
ldns.setNameServers(node, ['10.152.0.53'], override=True)

emu.addLayer(world)
```

## The `apply` method

It will apply a function to nodes that matches the filter.
Calling the `apply` method multiple times will apply the configurations
in the order they are called.

### Parameter `func`

Parameter func is the function to be applied. It takes a node as its argument.
If you want to add a function that takes more than one argument,
you can use a lambda function to wrap it.

```python
# Multiple arguments
def setNameServers(node, servers):
    # Add the Name servers to the node
    pass
world.apply(lambda node: setNameServers(node, ["1.14.5.14"]))

# Single argument
def installGit(node):
    node.addSoftware("git")
world.apply(installGit)
```

The function passed to the `apply` method is recommended to be idempotent.
All side effects that will manipulate nodes are recommended to be done in each
layer/service's configure stage.

If side effects that will manipulate nodes are done in layer/service's configure stage,
you need to add Global layer as the dependency of that layer/service. So that the
Global layer will be executed before that layer/service.

```python
class MyLayer(Layer):
    def __init__(self):
        super().__init__()
        #                          reverse, optional
        self.addDependency('Global', False, True)
```

### Parameter `filter`

Parameter filter is the filter to filter nodes that satisfy the requirement.
If None, apply to all nodes.

The filter here accepts a `Filter` object. Since the filter logic is implemented inside
the `Global` layer rather than the `Filter` object, the `Filter` object might perform
differently in the `Global` layer than in other parts.

For example, the allowBound filter is not supported in the global layer.

Moreover, inside the `Global` layer, the prefix filter is implemented in a portable way that
supports both IPv4 and IPv6 via IPv4-mapped IPv6 addresses. This might not be the case in other
parts.


