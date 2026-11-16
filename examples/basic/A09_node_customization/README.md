# Node customization

This example shows how to customize a physical `Node` before rendering and
compilation.

The example covers:

- selecting a runtime system with `setBaseSystem()`;
- installing software;
- adding Dockerfile build commands;
- importing and creating files;
- adding node start commands.

## Selecting a runtime system

Every node has a `SystemProfile`. By default, hosts use
`BaseSystem.DEFAULT`, which currently refers to `BaseSystem.SEEDEMU_BASE`.
Use `setBaseSystem()` when a node explicitly requires a different runtime
system:

```python
node.setBaseSystem(BaseSystem.SEEDEMU_ROUTER)
```

`Node` stores only the compiler-neutral profile. The selected compiler decides
how to realize that profile for its target platform.

Profiles may contain a less specialized profile according to the runtime
inheritance chain:

```text
ubuntu20.04
    └── seedemu-base
          └── seedemu-router
```

The relationship can be queried directly through `SystemProfile.contains()`:

```python
BaseSystem.SEEDEMU_ROUTER.contains(BaseSystem.SEEDEMU_BASE)
```

This returns `True`. Binding and service configuration use the relationship to
keep the more specialized compatible profile.

Extensions define their own `SystemProfile` values and may set `subset` to a
profile supplied by SeedEmu. SeedEmu does not need to contain the extension
profile or know how another compiler realizes it.

## Running the example

```bash
python node_customization.py --platform amd --output output
```

For ARM64:

```bash
python node_customization.py --platform arm --output output
```
