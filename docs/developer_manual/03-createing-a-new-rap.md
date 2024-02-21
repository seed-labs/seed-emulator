# Creating a new remote access provider (RAP)

A remote access provider contains the logic to enable remote access to a network. The way a remote access provider work is that the emulator will provide the remote access provider with:

- The network to enable remote access on. 
- A for-service bridging network: this network is not a part of the emulation. Instead, it was used by special services like this to communicate with the emulator host.
- A bridging node: this node is not a part of emulation. It is a special node that will have access to both the for-service bridging network and the network to enable remote access on.

Then, what a remote access provider usually do is:

- Start a VPN server, listen for incoming connections on the for-service bridge network, so the emulator host can port-forward to the VPN server and allow hosts in the real world to connect.
- Add the VPN server interface and the network to enable remote access on to the same bridge so that clients can access the network.

However, note that a remote access provider does not necessarily create a VPN server - they can also be a VPN client that connects to another emulator or just a regular Linux bridge, to connect to, say, a network created by some other virtualization software.

To create a new remote access provider, one will need to implement the `RemoteAccessProvider` interface. The `RemoteAccessProvider` has the following methods:

## `RemoteAccessProvider::getName`

The `getName` call takes nothing, and return the name of the remote access provider.

## `RemoteAccessProvider::configureRemoteAccess`

The `configureRemoteAccess` contains the actual logic. Four parameters will be passed to `configureRemoteAccess`.

The first is a reference to the current emulator instance, in case the access provider needs to access other objects in the emulator. Note that remote access providers are invoked during the configuration stage by the `Base` layer. Since autonomous systems are configured one by one, objects in other autonomous systems may not be available in the emulator yet. 

The second is a reference to the network instance of the network to be bridged to - in other words, the goal is to provide remote access to this network.

The third is a reference to a service node. A service node is not part of the emulation. This node can be used to run software (like VPN server) for remote access. This node will be under the same scope as the network passed as the second parameter. The node will be an empty node - no networks connected, no software installed. The regular APIs like `joinNetwork` and `addSoftware` works. 

The last is a reference to the for-service network. The for service network has a name that begins with `000`; therefore it ensures that whatever nodes joined this network will have this network as their default gateway if compiled by the `Docker` compiler. This will ensure the default gateway works even if the user uses the `selfManagedNetwork` option. If compiled by the `Docker` compiler, this network will have NAT access to the internet.