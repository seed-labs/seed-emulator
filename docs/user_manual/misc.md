# Miscellaneous


<a name="registry"></a>
## Registry

There is a global class, Registry, which keep tracks of every important objects
created in the emulation (nodes, layers, networks, files, etc.). In fact, what
compiles do is just takes the node and network objects out from the Registry
and convert them to dockerfiles.

### Inspecting objects

Most of the objects created in the emulator are derived from the `Printable`
class. As the name suggested, they can be printed. To see what classes are
printable, check the API documentation. `Registry` is also a printable object,
we can print it to check almost all objects created in the emulation:

```python
print(emu.getRegistry())
```
