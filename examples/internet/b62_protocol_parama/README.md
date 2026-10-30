# Protocol Parameter Tuning

This example is based on `B00_mini_internet`, but it keeps protocol timer
configuration explicit so users can see and adjust the new APIs.

The topology is the same mini Internet shape as B00: transit ASes, route-server
peerings, private peerings, and stub ASes. The difference is in
`protocol_parama.py`:

```python
ebgp = Ebgp().setTimers(holdTime=36000, keepaliveTime=60)
ibgp = Ibgp().setTimers(holdTime=36000, keepaliveTime=60)
ospf = Ospf().setTimers(tick=1, hello=1, dead=4)
```

## Protocol Parameters

`Ospf().setTimers(tick=..., hello=..., dead=...)`

- `tick`: BIRD OSPF scheduler tick interval, in seconds.
- `hello`: OSPF hello interval, in seconds.
- `dead`: OSPF dead interval, in seconds.
- Default values in SeedEMU are `tick=1`, `hello=1`, and `dead=4`.
- For BIRD, all three values are rendered. For FRR, `hello` and `dead` are
  rendered because FRR does not expose a matching OSPF `tick` command.

`Ebgp().setTimers(holdTime=..., keepaliveTime=...)`

- `holdTime`: BGP hold time, in seconds.
- `keepaliveTime`: BGP keepalive interval, in seconds.
- Default values in SeedEMU are `holdTime=36000` and `keepaliveTime=60`.

`Ibgp().setTimers(holdTime=..., keepaliveTime=...)`

- Controls the same BGP hold and keepalive timers for iBGP sessions.
- Default values in SeedEMU are `holdTime=36000` and `keepaliveTime=60`.

If these APIs are not called, SeedEMU uses the defaults above. Invalid timer
values, such as non-positive values or `keepaliveTime >= holdTime`, raise an
error during rendering.

## Build And Run

From the repository root:

```sh
python3 seedemu/testing/cli.py clean examples/internet/b62_protocol_parama/example.yaml --artifact-dir ci-artifacts/b62
python3 seedemu/testing/cli.py compile examples/internet/b62_protocol_parama/example.yaml --artifact-dir ci-artifacts/b62
python3 seedemu/testing/cli.py build examples/internet/b62_protocol_parama/example.yaml --artifact-dir ci-artifacts/b62
python3 seedemu/testing/cli.py up examples/internet/b62_protocol_parama/example.yaml --artifact-dir ci-artifacts/b62
python3 seedemu/testing/cli.py probe examples/internet/b62_protocol_parama/example.yaml --artifact-dir ci-artifacts/b62
python3 seedemu/testing/cli.py test examples/internet/b62_protocol_parama/example.yaml --artifact-dir ci-artifacts/b62
python3 seedemu/testing/cli.py down examples/internet/b62_protocol_parama/example.yaml --artifact-dir ci-artifacts/b62
```

The full lifecycle can also be run with:

```sh
python3 seedemu/testing/cli.py all examples/internet/b62_protocol_parama/example.yaml --artifact-dir ci-artifacts/b62
```

## Failure And Recovery Control

After the emulation is running, use `fault_control.py` to stop or recover one
or more services by Docker Compose service name.

Stop multiple containers:

```sh
python3 examples/internet/b62_protocol_parama/fault_control.py down --container brdnode_2_r100,brdnode_2_r101
```

The same command also accepts space-separated names:

```sh
python3 examples/internet/b62_protocol_parama/fault_control.py down --container brdnode_2_r100 brdnode_2_r101
```

Recover them:

```sh
python3 examples/internet/b62_protocol_parama/fault_control.py up --container brdnode_2_r100,brdnode_2_r101
```

List generated Compose services:

```sh
python3 examples/internet/b62_protocol_parama/fault_control.py list
```

By default, the script uses `output/docker-compose.yml` inside this example
directory. Use `--compose PATH` to point it at another Compose file.
