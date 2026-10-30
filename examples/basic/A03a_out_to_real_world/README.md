# Out To The Real World

This example demonstrates traffic going from the emulator out to the real
world. It intentionally does not include OpenVPN remote access.

The topology has:

- `AS2`: transit AS between `IX100` and `IX101`.
- `AS151`: stub AS at `IX100` with a web host.
- `AS152`: stub AS at `IX101` with a web host.
- `AS20940`: Akamai real-world AS at `IX101`.

`example.com` is commonly served from Akamai infrastructure, so this example
uses Akamai to demonstrate real-world prefix injection. By default, the example
uses a deterministic Akamai prefix:

```text
23.192.228.0/24
```

Pass `--live-prefixes` to fetch live AS20940 prefixes instead.

## Standard Arguments

```sh
python examples/basic/A03a_out_to_real_world/out_to_real_world.py amd
python examples/basic/A03a_out_to_real_world/out_to_real_world.py --platform amd --output examples/basic/A03a_out_to_real_world/output
python examples/basic/A03a_out_to_real_world/out_to_real_world.py --dumpfile examples/basic/A03a_out_to_real_world/out_to_real_world.bin
python examples/basic/A03a_out_to_real_world/out_to_real_world.py --live-prefixes
```

Supported arguments:

- `amd|arm`: optional legacy platform argument.
- `--platform amd|arm`: named platform argument.
- `--output PATH`: output folder for Docker compiler results.
- `--dumpfile PATH`: save a serialized emulator instead of compiling Docker output.
- `--live-prefixes`: fetch live AS20940 prefixes.
- `--override` / `--no-override`: control whether existing output is replaced.
- `--skip-render`: compile without calling `emu.render()` first.

## TestRunner Lifecycle

```sh
python seedemu/testing/cli.py all examples/basic/A03a_out_to_real_world/example.yaml --artifact-dir ci-artifacts/a03a
```

The automatic tests avoid depending on live Internet availability. They check
emulated reachability, Akamai real-world router configuration, and that OpenVPN
remote access is not part of this example.

## Manual Real-World Reachability Test

The automatic CI tests do not require live Internet access. To manually verify
that an emulated host can reach the outside world, start the compiled emulation,
go to this example folder, and run:

```sh
sh test_real_world_reachability.sh
```

The script runs one command from `hnode_151_web`: ping `23.192.228.80` over
IPv4. This address is inside the deterministic Akamai prefix used by this
example, so the check does not depend on DNS or a web server. If the command
succeeds, the emulator can reach the real world from inside.
