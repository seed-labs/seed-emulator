# Merging Two Emulations

This example demonstrates how we can merge two emulations.
These two emulations can come from pre-built emulations. In this 
example, we first build the emulations A and B separately,
and then we merge them.

```
emu_merged = emuA.merge(emuB, DEFAULT_MERGERS)
```

## Standard Arguments

```sh
python examples/basic/A06_merge_emulation/merge_emulation.py amd
python examples/basic/A06_merge_emulation/merge_emulation.py --platform amd --output examples/basic/A06_merge_emulation/output
python examples/basic/A06_merge_emulation/merge_emulation.py --dumpfile examples/basic/A06_merge_emulation/merge_emulation.bin
```

Supported arguments:

- `amd|arm`: optional legacy platform argument.
- `--platform amd|arm`: named platform argument.
- `--output PATH`: output folder for Docker compiler results.
- `--dumpfile PATH`: save a serialized emulator instead of compiling Docker output.
- `--override` / `--no-override`: control whether existing output is replaced.
- `--skip-render`: compile without calling `emu.render()` first.

## TestRunner Lifecycle

```sh
python seedemu/testing/cli.py all examples/basic/A06_merge_emulation/example.yaml --artifact-dir ci-artifacts/a06
```

The runtime test verifies that the merged AS150 and AS151 nodes are generated
and can reach each other through the merged IX100 topology.
