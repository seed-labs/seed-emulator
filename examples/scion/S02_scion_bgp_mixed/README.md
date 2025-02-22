# SCION and BGP Coexistence

SCION can operate independently from but alongside BGP. This example demonstrates a more complex topology with both SCION and BGP routing.
Moreover it serves as a demo of how to use the option system.

## Step 1: Create layers

```pythonfrom seedemu.compiler import Docker, Graphviz
from seedemu.core import Emulator, OptionMode, Scope, ScopeTier, ScopeType
from seedemu.layers import (
    ScionBase, ScionRouting, ScionIsd, Scion, Ospf, Ibgp, Ebgp, PeerRelationship,
    SetupSpecification, CheckoutSpecification)
from seedemu.layers.Scion import LinkType as ScLinkType

# Initialize
emu = Emulator()
base = ScionBase()
# change global defaults here .. .
loglvl = ScionRouting.Option.loglevel('error', mode=OptionMode.RUN_TIME)

spec = SetupSpecification.LOCAL_BUILD(
        CheckoutSpecification(
            mode = "build",
            git_repo_url = "https://github.com/scionproto/scion.git",
            checkout = "v0.12.0" # could be tag, branch or commit-hash
        ))
opt_spec = ScionRouting.Option.setup_spec(spec)
routing = ScionRouting(loglevel=loglvl, setup_spec=opt_spec)

# o = ScionRouting.Option('loglevel','trace', OptionMode.RUN_TIME)
ospf = Ospf()
scion_isd = ScionIsd()
scion = Scion()
ibgp = Ibgp()
ebgp = Ebgp()
```

In addition to the SCION layers we instantiate the `Ibgp` and `Ebgp` layers for BGP as well as `Ospf` for AS-internal routing.
Note that the ScionRouting layer accepts global default values for options as constructor parameters.
 We use it here to decrease the loglevel from 'debug' to 'error' for all SCION distributables in the whole emulation if not overriden elsewhere. Also we change the mode for `LOGLEVEL` from `BUILD_TIME`(default) to `RUN_TIME` in the same statement.
 Lastly we specify (as a global default for all nodes) that we want to use a local build of the `v0.12.0` SCION stack, rather than the 'official' `.deb` packages (`SetupSpecification.PACKAGES`). The SetupSpec is just an ordinary option and be overriden for ASes or individual nodes just like any other.

## Step 2: Create isolation domains and internet exchanges

```python
base.createIsolationDomain(1)
base.createIsolationDomain(2)

base.createInternetExchange(100)
base.createInternetExchange(101)
base.createInternetExchange(102)
base.createInternetExchange(103)
base.createInternetExchange(104)
```

We have two ISDs and four internet exchanges this time.

## Step 3: Create autonomous systems

The topology we create contains the two core ASes 150 and 160. AS 150 is in ISD 1 and AS 160 is in ISD 2.
 ISD 1 has three additional non-core ASes. In ISD 2 we have one non-core AS.

### Step 3.1: Core AS of ISD 1

```python
as150 = base.createAutonomousSystem(150)
scion_isd.addIsdAs(1, 150, is_core=True)
as150.createNetwork('net0')
as150.createNetwork('net1')
as150.createNetwork('net2')
as150.createNetwork('net3')
as150.createControlService('cs1').joinNetwork('net0')
as150.createControlService('cs2').joinNetwork('net2')
as150_br0 = as150.createRouter('br0')
as150_br1 = as150.createRouter('br1')
as150_br2 = as150.createRouter('br2')
as150_br3 = as150.createRouter('br3')
as150_br0.joinNetwork('net0').joinNetwork('net1').joinNetwork('ix100')
as150_br1.joinNetwork('net1').joinNetwork('net2').joinNetwork('ix101')
as150_br2.joinNetwork('net2').joinNetwork('net3').joinNetwork('ix102')
as150_br3.joinNetwork('net3').joinNetwork('net0').joinNetwork('ix103')
```

AS 150 contains four internal network connected in a ring topology by the four border routers br0, br1, br2, and br3. There are two control services cs1 and cs2. We will use br0 to connect to the core of ISD 2 (i.e., AS 160) and the other border routers to connect to customer/child ASes 151, 152, and 153.

#### Step 3.1.1:   Option Settings for ISD-AS 1-150
```python
# override global default for AS150
as150.setOption(ScionRouting.Option.disable_bfd(mode = OptionMode.RUN_TIME),
                Scope(ScopeTier.AS,
                      as_id=as150.getAsn(),
                      node_type=ScopeType.BRDNODE))
# override AS settings for individual nodes
as150_br0.setOption(ScionRouting.Option.loglevel('debug', OptionMode.RUN_TIME))
as150_br1.setOption(ScionRouting.Option.serve_metrics('true', OptionMode.RUN_TIME))
as150_br1.addPortForwarding(30442, 30442)
```
This section overrides some global defaults:
- DISABLE_BFD option is changed from default BUILD_TIME to RUNTIME_MODE (the value is left at the default: 'true') on all SCION border routers of AS150
- LOGLEVEL is increased from global default 'error' to 'debug' only for node '150_br0' and the mode set to RUN_TIME
- SERVE_METRICS option is enabled on node '150_br1'.
    This node will serve collected Prometheus metrics of the SCION border router distributable on port 30442.
    If this behaviour is no longer desired it can turned of at RUN_TIME again, without re-compile  and container rebuild

As a result the following `.env` file will be generated next to the `docker-compose.yml` containing all instantiated `RUN_TIME` options:
```
LOGLEVEL_150_BR0=debug
DISABLE_BFD_150_BRDNODE=true
SERVE_METRICS_150_BR1=true
LOGLEVEL_150=info
LOGLEVEL=error
```
These variables are referenced from the `docker-compose.yml` file:

```
    brdnode_150_br0:
        ...
        environment:
            - LOGLEVEL=${LOGLEVEL_150_BR0}
            - DISABLE_BFD=${DISABLE_BFD_150_BRDNODE}

    brdnode_150_br1:
        ...
        environment:
            - LOGLEVEL=${LOGLEVEL_150}
            - SERVE_METRICS=${SERVE_METRICS_150_BR1}
            - DISABLE_BFD=${DISABLE_BFD_150_BRDNODE}

    brdnode_150_br2|3:
        ...
        environment:
            - LOGLEVEL=${LOGLEVEL_150}
            - DISABLE_BFD=${DISABLE_BFD_150_BRDNODE}
    csnode_150_cs1:
        ...
        environment:
            - LOGLEVEL=${LOGLEVEL_150}

      brdnode_151_br0:
        ...
        environment:
            - LOGLEVEL=${LOGLEVEL}
```
Note that each service has in its `environment:` section (only) the runtime variables that apply to it (that is: match its ASN, NodeType or NodeIdentity).

### Step 3.2 Non-Core ASes of ISD 1

```python
asn_ix = {
    151: 101,
    152: 102,
    153: 103,
}
for asn, ix in asn_ix.items():
    as_ = base.createAutonomousSystem(asn)
    scion_isd.addIsdAs(1, asn, is_core=False)
    scion_isd.setCertIssuer((1, asn), issuer=150)
    as_.createNetwork('net0')
    as_.createControlService('cs1').joinNetwork('net0')
    as_.createRouter('br0').joinNetwork('net0').joinNetwork(f'ix{ix}')
```

ISD 1 contains three non-core ASes that connect back to the core on ix101, ix102, and ix103, respectively.

### Step 3.3: ISD 2

AS 160 is the second ISD's core. It contains two border routers.

```python
as160 = base.createAutonomousSystem(160)
scion_isd.addIsdAs(2, 160, is_core=True)
as160.createNetwork('net0')
as160.createControlService('cs1').joinNetwork('net0')
as160.createRouter('br0').joinNetwork('net0').joinNetwork('ix100')
as160.createRouter('br1').joinNetwork('net0').joinNetwork('ix104')
```

Furthermore, there is the non-core AS 161 in ISD 2.

```python
as161 = base.createAutonomousSystem(161)
scion_isd.addIsdAs(2, 161, is_core=False)
scion_isd.setCertIssuer((2, 161), issuer=160)
as161.createNetwork('net0')
as161.createControlService('cs1').joinNetwork('net0')
as161.createRouter('br0').joinNetwork('net0').joinNetwork('ix104')
```

### Step 4: SCION links

```python
scion.addIxLink(100, (1, 150), (2, 160), ScLinkType.Core)
scion.addIxLink(101, (1, 150), (1, 151), ScLinkType.Transit)
scion.addIxLink(102, (1, 150), (1, 152), ScLinkType.Transit)
scion.addIxLink(103, (1, 150), (1, 153), ScLinkType.Transit)
scion.addIxLink(104, (2, 160), (2, 161), ScLinkType.Transit)
```

We connect the two core ASes with a core link. The non-core ASes are connected to the ISD cores by transit links.

### Step 5: BGP peering

```python
ebgp.addPrivatePeering(100, 150, 160, abRelationship=PeerRelationship.Peer)
ebgp.addPrivatePeering(101, 150, 151, abRelationship=PeerRelationship.Provider)
ebgp.addPrivatePeering(102, 150, 152, abRelationship=PeerRelationship.Provider)
ebgp.addPrivatePeering(103, 150, 153, abRelationship=PeerRelationship.Provider)
ebgp.addPrivatePeering(104, 160, 161, abRelationship=PeerRelationship.Provider)
```

For BGP, we use private peering between the pair of core ASes and between the cores and their non-core children.

### Step 6: ICMP and SCMP Ping

Once the topology has been compiled and is running, we can test BGP and SCION connectivity using the `ping` and `scion` tools, respectively.

For example, to ping a host in AS 161 we can use a command such as
```zsh
ping 10.161.0.71
```

To do the same in SCION, we can use
```zsh
scion ping 2-161,10.161.0.71
```

If both ping commands show responses then both the BGP and SCION routing are working.
