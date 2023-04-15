# SCION Internet Architecture

SCION (Scalability, Control, and Isolation On Next-generation networks) is a new secure and reliable inter-domain routing protocol. SCION offers inter-domain path control with explicit trust by grouping ASes in Isolation Domains (ISDs) and embedding the cryptographically secured AS-level path into packet headers.

This example demonstrates how to create a small SCION Internet topology in the SEED emulator.

## Step 0: Install SCION PKI tool
We rely on an external tool called `scion-pki` to generate the cryptographic material necessary for SCION. You can install `scion-pki` in a number of ways:

### Install SCION Packages
[deb packages](https://docs.scionlab.org/content/install/pkg.html) are available for Debian and Ubuntu (x86, x86-64, arm32, and arm64).

Example installation on Ubuntu:
```bash
sudo apt-get install apt-transport-https ca-certificates
echo "deb [trusted=yes] https://packages.netsec.inf.ethz.ch/debian all main" | sudo tee /etc/apt/sources.list.d/scionlab.list
sudo apt-get update
sudo apt-get install scion-tools
```

### Compile from source
To compile from source you need an up-to-date version of the [Go programming language](https://go.dev/doc/install). The SCION source code is available on GitHub: https://github.com/scionproto/scion.
[Detailed build instructions](https://docs.scion.org/en/latest/build/setup.html) are available, but on Ubuntu systems it is usually enough to run the following commands.
```bash
git clone https://github.com/scionproto/scion.git
cd scion
go build -o bin ./scion-pki/cmd/scion-pki
```

Once you have installed a copy of `scion-pki` make sure to add it to the `PATH` environment variable before you continue.

## Step 1: Import emulator components for SCION

```python
from seedemu.compiler import Docker
from seedemu.core import Emulator
from seedemu.layers import ScionBase, ScionRouting, ScionIsd, Scion
from seedemu.layers.Scion import LinkType as ScLinkType
```

SCION support in the emulator relies on four emulation layers:
- The `ScionBase` layer extends the `Base` layer by adding Isolation Domains (ISDs). We will use the base layer to declare ISDs.
- The `ScionRouting` layer extends the `Routing` layer with support for SCION inter-AS routing. It installs and configures the SCION routing daemons on routers and control service hosts (see Step 3 below). Additionally, it installs the SCION host stack on all hosts.
- The `ScionIsd` layer manages the trust relationships between ASes. Each AS must be assigned to an ISD and given a role of either core or regular non-core AS. The `ScionIsd` layer invokes the `scion-pki` tool to generate the secret keys and certificates necessary for the SCION control plane.
- The `Scion` layer is the equivalent to the `Ebgp` layer for a BGP-based Internet. We use it to define links between ASes within and across ISDs.

Initialization is as usual:
```python
emu = Emulator()
base = ScionBase()
routing = ScionRouting()
scion_isd = ScionIsd()
scion = Scion()
```

## Step 2: Create isolation domains

```python
base.createIsolationDomain(1)
```

Each SCION AS is member of an isolation domain (ISD). ISDs manage the trust relationship between ASes. ASes in the same ISD have to trust each other to a higher degree than they would trust an AS from a foreign ISD. An ISD is identified by a globally unique numerical 16-bit ID. In this example we create a single ISD with identifier 1. In the emulator ISDs may optionally have a descriptive label as well.

## Step 3: Create autonomous systems

```python
as150 = base.createAutonomousSystem(150)
```

SCION ASes are created in the same way as BGP ASes. The `ScionBase` layer automatically returns SCION-enabled ASes. Within the emulator we use ASNs from the 32-bit BGP ASN namespace.

### Step 3.1: Add the AS to an ISD

```python
scion_isd.addIsdAs(1, 150, is_core=True)
```

We use the `ScionIsd` layer to assign AS 150 to the ISD we have created. By specifying `is_core=True` we make AS 150 a core AS of its ISD. Every ISD must have at least one core AS. Please note that it is currently not possible to assign an AS to multiple ISDs at the same time as the semantics of multi-ISD ASes have not been finalized yet in SCION.

For non-core ASes must additionally specify which core AS is signing the non-core AS's certificates with a call to `scion_isd.setCertIssuer()`.

### Step 3.2: Create the internal network and border routers

```python
as150.createNetwork('net0')
as150_router = as150.createRouter('br0')
as150_router.joinNetwork('net0').joinNetwork('ix100')
```

The `ScionRouting` layer upgrades all routers to SCION border routers, so we can add routers as usual. In this example, border router `br0` connects to three networks: (1) the internal network `net0`, (2) the internet exchange `ix100`, and (3) a cross-connect network to AS 153.

In addition to the border routers each SCION AS has at least one control service. The control service contains the beacon, certificate, and path servers necessary for SCION control plane operations. AS 150 as one control service called `cs1`.

```python
as150.createControlService('cs1').joinNetwork('net0')
```

## Step 4: Set up inter-AS routing

```python
scion.addIxLink(100, (1, 150), (1, 151), ScLinkType.Core)
scion.addIxLink(100, (1, 151), (1, 152), ScLinkType.Core)
scion.addIxLink(100, (1, 152), (1, 150), ScLinkType.Core)
scion.addXcLink((1, 150), (1, 153), ScLinkType.Transit)
```

Inter-AS routing in SCION is based on fixed "links" which are combined during the beaconing process to form end-to-end paths. SCION links are roughly equivalent to BGP peering sessions.

The `Scion` layer exposes two methods `addIxLink()` and `addXcLink()` for setting up SCION links over an IX and via direct cross-connect links, respectively. In both methods, we must specify the two endpoints of the link as pairs of ISD and ASN. The order of endpoints matters as SCION transit links are directional (for beaconing purposes, packets are still forwarded in both directions) from `a` to `b`. The reason we must name ASes by ASN and ISD is that only the pair of ISD and ASN uniquely identifies a SCION AS, i.e., a link from (1, 150) to (1, 151) is completely different from a hypothetical link between (2, 150) and (2, 151).

Besides the endpoints every SCION link has a type. Currently there are three types:
- `Core` links connect core ASes of the same or different ISDs. The core ASes of every ISD must all be reachable by one another via core links. The BGP analogy to core links is peering between Tier 1 ASes.
- `Transit` links connect core ASes to non-core ASes in the same ISD. They model Internet transit as sold from a provider AS to a customer AS.
- `Peering` links are used for any other type of peering between two ASes of the same or different ISDs.

In our example topology we have three core ASes with fully-meshed core-peering and an additional non-core AS 153 that obtains transit through AS 150.

## Step 5: Render and compile

```python
emu.addLayer(base)
emu.addLayer(routing)
emu.addLayer(scion_isd)
emu.addLayer(scion)

emu.render()

emu.compile(Docker(), './output')
```

Rendering and compiling the topology for Docker works as usual. Graphing the SCION links is supported as well.
