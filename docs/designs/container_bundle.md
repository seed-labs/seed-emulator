# Add a group of containers to emulator

Created: October 8, 2026 

### Design Assumptions

- Default network: All the containers in the bundle are attached to the isolated external network created for this bundle. This network is not reachable by the nodes in the emulator.
- Emulator networks: If a container needs to communicate with the nodes in the emulator, it also needs to attach to a network internal to the emulator. Which network to use is up to the bundle.
- Limited customization needs: Most part of the container’s Dockerfile and compose entries are already prepared, so there is no need to provide many unnecessary customization APIs.
- /etc/hosts:  The name-ip mappings are only needed by the containers in this bundle; other containers in the emulator do not need the mappings.
- Compose’s extra_hosts entry: provide name-ip mappings to the containers inside the emulator.

### ContainerBundle (Similar to Service)

- init(emulator, suffix):
    - Call `_createContainer(local_name, suffix)` to create the containers in this bundle.
    - Each container has a local name, which is decided by the bundle. The hostname of a container = local name + suffix
- _createContainer(local_name,  suffix):  internal method to create Container.
- setDefaultNetwork(name, prefix, [ip address list]):  This network is an isolated network reserved for this bundle. All the containers will be attached to this network by default. Containers on this network cannot reach the hosts on the emulator, and vice versa. The host machine can reach these containers. A network entry will be created in the compose file.
    - If users do not set this, default values will be used
- setPorts(list):  Allocate a list of ports for the containers; they can use these ports for port forwarding. Port selection is up to the bundle
- configure(): Configure the containers in this group.  When this is called, all the information needed by a container is already decided, so we can generate the final content for all the files of the container.
    - Attach all the containers to the default network:  PrepairedContainer :: joinExternalNetwork(network, hostname, ip_address)
    - Attach containers to a selected emulator network, if needed. The selection method is implemented here (see the notes below). Set the network information for each container.   PrepairedContainer :: joinInternalNetwork(network, hostname, ip_address, default_router)
    - Select ports for each container. These ports are for port forwarding. Container’s local ports are decided locally by the bundle.
    - Construct the final Dockerfile, compose entry, etchosts file, and other files.  Store the final results in the Container object. Construction is based on the prepared format strings defined in this object (or file).
- install():  Call `PreparedContainer::install()`for each container. This API returns the followings:
    - The compose entry strings for all the containers in this bundle.
- File templates:  the file templates is stored in the same file using a dictionary: key —> content
- Attributes
    - __internal_hostname_ip_mappings: record the the hostname-ip mappings for those hosts attached to the internal network. These mappings will be added to the compose entry for all the emulator nodes (using the extra_hosts entry). This is to supplement the /etc/hosts content set by the EtcHosts layer, because we cannot use this layer anymore after the rendering phase. Docker will append these mappings to /etc/hosts when creating containers.
    - __external_hostname_ip_mappings: this is for the /etc/hosts file of all the containers in this bundle.
- **Notes**:
    - If a container needs to communicate with the nodes inside the emulator, it needs to be attached to a network inside the emulator. The Bundle class can use the Emulator object to select networks, reserve IP addresses (each network object has an IP assignment method), and get the default routes on these networks. The selection can be based on ASN, network name, or hostname. The selection is entirely up to the bundle.

### PreparedContainer

Most of the part of this container is already fixed, but a small part of it needs to be decided during the construction time. Eventually, docker compiler creates a folder for each container, and add corresponding entries to docker-compose.yml. 

- init(name, suffix, etchosts_file=”etchosts”):  Set the name of the container.
- install():  Create a folder for the container, and set its content. Use the hostname (local name + suffix) as the folder name. Return the followings:
    - The docker compose service entry for this container.
    - The hostname-ip mappings for the
- joinInternalNetwork(network, hostname, ip_address, default_router): Attach the container to an internal network inside the emulator.
    - Typically, a container should join just one internal network (if it needs to communicate with the nodes inside the emulator). If indeed, it is attached to multiple internal networks, only the first network’s following information is used:  hostname-ip mapping, default router.
    - The IP address should pick from the reserved range, so it does not use the ones that are already allocated.
    - The default router information can be obtained from the network object.
- joinExternalNetwork(network, hostname, ip_address): Attach the container to a network external to the emulator.
- setComposeContent(content: str): Set the docker compose entry for this container. Set __compose_content.
- setDockerfile(content: str):  Set the content of the Dockerfile, use self.__files[”Dockerfile”]
- setEtcHosts(content: str): Set the content of the /etc/hosts file, use self.__files[_etchosts_file]
- setFile(filename, content): Set the content of the other files. Each file set via this API will appear in the output container folder
- Attributes:
    - __emulator: the emulator object
    - __name: str,  __suffix: str
    - __internal_networks:  a list of network (network_name, hostname, ip_address,  default_router)
    - __external_network:  only one (network_name, hostname, ip_address)
    - __files:  Dict[name, content]:   each entry will become a file in the final image folder.
    - __etchosts_file
    - __compose_content


### Notes (future work)

- For each network, reserve a block of IPs for external containers, i.e., for containers added later by the docker compiler.


### Code Example

```python
# VisualizationSystem
class VisualizationSystem(ContainerBundle)

# Example
docker = Docker()

...
emu.render()

# After the rendering 
# Customize and configure the containers in the entire group
bundle = VisualizationSystem(emu, "map.seed")
bundle.setDefaultNetwork("visualization_network", "172.19.0.0/16", [f"172.18.0.{i}" for i in range(5, 11)])
bundle.setPorts(list(range(8090, 8099))

# Docker first invokes bundle.configure() which will configure all the containers;
# Docker then invokes bundle.install() to create a folder for each container, and add entries to docker-compose.yml
docker.addContainerBundle(bundle) 

# Dockerfile of each container image
From baseimage

COPY {etchosts} /tmp/etc-hosts
RUN cat /tmp/etc-hosts >> /etc/hosts



# Add extra_hosts 
services:
  frontend:
    image: ubuntu:24.04
    extra_hosts:
      backend.visual.seed: "10.150.0.10"
      database.visual.seed: "10.150.0.11"

```