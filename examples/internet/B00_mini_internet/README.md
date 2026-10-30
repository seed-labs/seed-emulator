# Mini Internet

This is a comprehensive example. It creates 6 Internet exchanges,
5 transit ASes, and 12 stub ASes. One of the ASes (`AS-99999`) is a real-world
autonomous system, which announces the real-work network prefixes 
to the emulator. Packets to these prefixes will be routed out to the 
real Internet. Another AS (`AS-152`) allows machines from the outside
to join the emulation (via VPN), so they can interact with the machines
inside the emulator.

The emulator generated from this example is saved to a component file, 
and be used by several other examples as the basis.

The public Python entrypoint is still:

```python
from examples.internet.B00_mini_internet import mini_internet

mini_internet.run(dumpfile='./base_internet.bin')
mini_internet.run(dumpfile='./base_internet.bin', hosts_per_as=2)
```

Other examples use this API to build their underlying network topology, so the
`run(dumpfile=None, hosts_per_as=2, ...)` signature is kept compatible.


## Using Utility Functions

We have created a few utility functions to help make it easy
to create autonomous systems. 
The following example creates a transit AS (`AS-2`), which
has a presence at 3 Internet exchanges (`ix-100`, `ix-101`,
and `ix-102`). It also creates two internal networks to 
connect the 3 BGP routers of this AS.

```
Makers.makeTransitAs(base, 2, [100, 101, 102],
       [(100, 101), (101, 102)]
)
```

The following example creates a stub AS (`AS-153`), 
which has a presence at `ix-101`. Three hosts will be 
created for this AS, one running a web service, and the other 
two not running any service. 

```
Makers.makeStubAs(emu, base, 153, 101, [web, None, None])
```

## Standard Arguments

The example accepts both the legacy platform argument and the newer named
arguments:

```sh
python examples/internet/B00_mini_internet/mini_internet.py amd
python examples/internet/B00_mini_internet/mini_internet.py --platform amd --output examples/internet/B00_mini_internet/output
python examples/internet/B00_mini_internet/mini_internet.py --dumpfile examples/internet/B00_mini_internet/base_internet.bin
```

Supported arguments:

- `amd|arm`: optional legacy platform argument.
- `--platform amd|arm`: named platform argument.
- `--output PATH`: output folder for Docker compiler results.
- `--dumpfile PATH`: save a serialized emulator instead of compiling Docker output.
- `--hosts-per-as N`: number of hosts created in each stub AS.
- `--override` / `--no-override`: control whether existing output is replaced.
- `--skip-render`: compile without calling `emu.render()` first.

## TestRunner Lifecycle

This example includes an `example.yaml` manifest for `seedemu.testing`. Run
these commands from the repository root:

```sh
python seedemu/testing/cli.py clean examples/internet/B00_mini_internet/example.yaml
python seedemu/testing/cli.py compile examples/internet/B00_mini_internet/example.yaml --artifact-dir ci-artifacts/b00
python seedemu/testing/cli.py build examples/internet/B00_mini_internet/example.yaml --artifact-dir ci-artifacts/b00
python seedemu/testing/cli.py up examples/internet/B00_mini_internet/example.yaml --artifact-dir ci-artifacts/b00
python seedemu/testing/cli.py probe examples/internet/B00_mini_internet/example.yaml --artifact-dir ci-artifacts/b00
python seedemu/testing/cli.py test examples/internet/B00_mini_internet/example.yaml --artifact-dir ci-artifacts/b00
python seedemu/testing/cli.py down examples/internet/B00_mini_internet/example.yaml --artifact-dir ci-artifacts/b00
```

The full lifecycle can also be run with:

```sh
python seedemu/testing/cli.py all examples/internet/B00_mini_internet/example.yaml --artifact-dir ci-artifacts/b00
```

The manifest declares `runner: internet` because it uses Internet-style probes.
The readiness stage checks representative transit routers, stub routers, and
stub hosts. The probe stage checks cross-AS reachability across different parts
of the mini Internet. The `test_runtime.py` program demonstrates custom runtime
validation, including a check for the AS154 host with the customized IP address.

