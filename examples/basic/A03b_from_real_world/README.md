# From The Real World

This example demonstrates real-world machines coming into the emulator with
OpenVPN remote access. It intentionally does not include a real-world AS router.

The topology has:

- `AS2`: transit AS between `IX100` and `IX101`.
- `AS151`: stub AS at `IX100`, with OpenVPN remote access enabled on `net0`.
- `AS152`: stub AS at `IX101`, with OpenVPN remote access enabled on `net0`.

## OpenVPN Remote Access

The OpenVPN remote access provider is created with:

```python
ovpn = OpenVpnRemoteAccessProvider()
```

Remote access is enabled on selected networks:

```python
as151.createNetwork("net0").enableRemoteAccess(ovpn)
as152.createNetwork("net0").enableRemoteAccess(ovpn)
```

For details on how to connect to the OpenVPN server with the built-in
CA/certificate/key, see:

```text
misc/openvpn-remote-access
```

## Standard Arguments

```sh
python examples/basic/A03b_from_real_world/from_real_world.py amd
python examples/basic/A03b_from_real_world/from_real_world.py --platform amd --output examples/basic/A03b_from_real_world/output
python examples/basic/A03b_from_real_world/from_real_world.py --dumpfile examples/basic/A03b_from_real_world/from_real_world.bin
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
python seedemu/testing/cli.py all examples/basic/A03b_from_real_world/example.yaml --artifact-dir ci-artifacts/a03b
```

The automatic tests check emulated reachability and verify that OpenVPN bridge
nodes are generated. Manual lab activities can additionally connect an external
OpenVPN client into AS151 or AS152 and access the web hosts from outside the
emulator.
