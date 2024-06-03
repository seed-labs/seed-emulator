# Kubo Service
This includes development notes on the technical implementation of the IPFS Kubo service.
Additionally, this includes notes on possibilities for future work.

## Future Work
- [ ] Visualization
- [ ] Architecture Propogation
- [ ] Educational Lab Development
- [ ] Custom Per-Node Bootstrap IPs

### Visualization
Each IPFS Kubo node is bundled with its own instance of the [IPFS Kubo Web UI](https://github.com/ipfs/ipfs-webui)
which is automatically launched alongside the Kubo daemon. This provides a GUI with information
about the Kubo node that it is hosted on, as well as a way to traverse the contents of the
local IPFS network. However, there are a few difficulties here:
- Each instance of the Web UI only provides information for the node that it is hosted on, and
access to the IPFS network.
- The Web UI requires access to the **IPFS HTTP Gateway** which is also bundled with Kubo, and
makes IPFS data available over HTTP on port 8080 (there does not seem to be an easy way to change this). *This conflicts with the default exposed port for the emulator's Internet Map.*
- The Web UI requires access to the **IPFS RPC API** which is also bundled with Kubo, and makes it possible to gather information about the local node and make configuration changes.
The RPC API runs over port 5001 by default (can be configured easily), which is also the port
over which the Web UI is hosted.

The ideal solution would be to find a way to proxy access to each of the Kubo nodes in the emulator, and provide the user with an easy way to access this Web UI for each host (e.g. through) the Internet Map.

### Architecture Propogation
When Kubo is installed on a node, it is installed from the IPFS developer repository. Many
different combinations of architectures and distributions are available, so the `KuboService`
allows the user to change these parameters. However, these values depend on emulation settings
and should be derived from there instead of set manually.
- `Architecture` is used by the compiler to allow the user to run emulations on both AMD and
  ARM systems. Rather than implementing this separately in each component of the Emulator,
  this should be a parameter that is configured on the Emulator as a whole and accessible by
  each component.
- `Distribution` is used by Kubo to download the correct version for the specified operating
  system and distribution. This depends on the base system as specified in the server class,
  and should be derived from here if possible.

### Educational Lab
This would be based on the [Kubo dApp](/examples/not-ready-examples/28-kubo-dapp/README.md) example. It should combine IPFS Kubo with Ethereum smart contracts to show how to deploy a simple dApp and illustrate the basic functionality of both IPFS, and smart contracts.

Below, you will find a possible outline for the structure of this lab:
1. Intro to IPFS
   - What is IPFS?
   - How to interact with IPFS using the Kubo CLI. Have student:
      - View bootstrap nodes
      - View peers
      - Add file
      - Access the data from another node
2. Intro to Ethereum & Smart Contracts
   - What is Ethereum (brief)?
   - What is a smart contract?
   - How to create a basic smart contract, have student:
     - Fill in code skeleton for simple hello world contract.
     - Compile using Remix
     - Deploy in Emulator
     - Test
3. IPFS For dApp Data Storage
   - What is a dApp?
   - Student fill in smart contract code skeleton.
   - Student will compile & deploy contract unguided.
   - Student must demonstrate that the dApp works.

### Custom Per-Node Boot IPs
In the current implementation, when you set a node as a bootstrap node, all other nodes
will bootstrap to that node during initialization (it is implemented at the service
level).

As a minor addition for a future version, it would be nice to implement functionality
at the server level to allow users to specify additional bootstrap nodes for a
particular server, or to override the bootstrap nodes from the service level.

This would involve adding a parameter or setter method in the `KuboServer` class, and
likely relocating the bootstrap script generation process from the `KuboService` class
to the `KuboServer` class. A helper method `KuboUtils.isIPv4()` would be helpful here
to validate user-provided IPv4 addresses.

## Technical Implementation
The following includes some technical notes on the implementation, including aspects which might be improved or expanded on in the future.

### KuboService
- `self._distro` and `self._arch` are implemented at the service level, so will be the same for all nodes.
    - `self._distro` depends on `KuboServer._base_system` and should change dynamically based on that.
    - `self._arch` must be the same as the architecture given to the compiler, Kubo should determine dynamically based on compiler arch.
- `self._tmp_dir` is the location in which temporary setup files may be placed, right now just the bootstrap script.
    - Change `TEMPORARY_DIR` in `KuboService` to modify this.
- `self._first_installed` may be used to expose a single node's Web UI to the host VM. We should find a better way to expose all nodes' Web UIs without individual port forwarding (which also conflicts with Internet Map default port 8080).
- `self._doInstall(node:Node, server:KuboServer)` does all service-level installation (port bindings and bootstrapping), and then begins server-level installation for the given node.
    - Bootstrap list and bootstrap script are generated once when this method is first called, and reused for all other method calls.
- `self._getBootstrapIps()` populates the service's bootstrap list using the first valid, local IPv4 address for each node.

### KuboServer
- `self.setVersion(version:str)` attempts to verify the format of the version string to ensure that it matches the expected format (using RegEx).
- `self.initConfig` is a public variable so that users are encouraged to directly modify the `DottedDict`, however, we also provide `self.replaceConfig()`.
- `self.startConfig` is a public variable so that users are encouraged to directly modify the `DottedDict`, however, we also provide `self.importConfig()` and `self.setConfig()`. Both of these are redundant and could be removed.

### KuboUtils
- `DottedDict` is a specialized subclass of the built-in Python `dict`. It restricts key values
  to nonempty string values in which the period (`.`) character is not allowed. This is
  because the `DottedDict` class allows the user to reference keys within a nested set of
  dictionaries using JSON dot notation.
    - E.g. `dottedDict1['Identity.PeerID']` allows the user to reference the value of `dottedDict1 = {'Identity': {'PeerID': 'bafybeicn7i3soqdgr7dwnrwytgq4zxy7a5jpkizrvhm5mv6bgjd32wm3q4'}}`
    - Aside from the usual `dict` operations, we implement the `merge(other:Mapping)` method
    to merge the contents of another dict-like object into the existing `DottedDict` instance.
    - We implement the `empty()` method to easily identify whether the `DottedDict` instance
    contains any items.
    - We also implement the `dottedItems()` method which functions similarly to the default `items()` method, but returns a list of key-value pairs where keys are in JSON dot notation and values are the deepest value in the nested dictionary.
    - This is used internally by the `KuboServer` class to store and modify the user-defined
      Kubo configuration file.
- We also implement a few simple utility functions to get a local IPv4 address from a given
  physical node on the Emulator, and to verify that a given string represents a valid IPv4
  address.