# Merging Two Emulations

This example demonstrates how we can merge two emulations.
These two emulations can come from pre-built emulations. In this 
example, we first build the emulations A and B separately,
and then we merge them.

```
emu_merged = emuA.merge(emuB, DEFAULT_MERGERS)
```
