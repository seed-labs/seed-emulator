# Kubo Example
This is designed to be a very simple example depicting how to install IPFS Kubo on many nodes.
It uses the [mini-internet](../../B00-mini-internet/README.md) topology and configuration as its base layer, and builds Kubo on top of that.

## Building the Emulation
1. Create an instance of the emulator.
    ```python
    emu = Emulator()
    ```

2. Load the pre-built emulation from the [mini-internet example](../06-mini-internet/README.md) as the base layer for this emulation.
    ```python
    emu.load('./base_component.bin')
    ```
    This works because we have a slightly modified version of the mini-internet Python script
    which dumps the emulation to a binary file, rather than compiling it for Docker (see the
    last line of [base-component.py](base-component.py)). *If you wanted to build a topology
    yourself, you could do that at this point instead of loading from a pre-built emulation.*

3. Initialize the Kubo service. The defaults should be fine, but you may specify additional
parameters for the instance here.
    ```python
    ipfs = KuboService()
    ```

4. Install IPFS Kubo on each host in the base layer. This requires us to iterate through each
stub autonomous system (AS) in the base layer, and each host within that AS. Once we have
installed and configured Kubo on a particular node, we must bind this virtual representation
of a node to a physical node in the Emulator. One way to do all of this is as follows:
    ```python
    numHosts = 3   # Number of hosts in the stub AS to install Kubo on
    i = 0   # Used as index for physical node name
    for asNum in range(150, 172):
        try:
            curAS = emu.getLayer('Base').getAutonomousSystem(asNum)
        except:
            print(f'AS {asNum} does\'t appear to exist.')
        else:
            # This AS exists, so install Kubo on each host:
            for h in range(numHosts):
                vnode = f'kubo-{i}'
                displayName = f'Kubo-{i}_'  # Make display name more descriptive
                cur = ipfs.install(vnode)
                # Make a few nodes boot nodes:
                if i % 5 == 0:
                    cur.setBootNode()
                    displayName += 'Boot'
                else:
                    displayName += 'Peer'
                
                # Modify display name and bind virtual node to physical node:
                emu.getVirtualNode(vnode).setDisplayName(displayName)
                emu.addBinding(Binding(vnode, filter=Filter(asn=asNum, nodeName=f'host_{h}')))
    ```
    As you can see, the only additional configuration that we do relating to Kubo, is to set
    a few nodes as boot nodes. In Kubo, boot nodes or bootstrap nodes are just Kubo nodes that
    are well-connected and will be used by new nodes to learn about other nodes on the
    network. You should have at least one boot node configured for Kubo to work correctly.

5. Once you have completed the installation and configuration of all Kubo nodes in the emulation, you are ready to add the Kubo service layer to the emulation.
    ```python
    emu.addLayer(ipfs)
    ```

6. Now, you are ready to render and compile the emulation. We'll do this for Docker.
    ```python
    docker = Docker(internetMapEnabled = True)
    emu.render()
    emu.compile(docker, OUTPUDIR, override = True)
    ```
    Here, we additionally enable the *Internet Map*, an emulator functionality that displays a
    visualization of the emulation in your browser at http://localhost:8080/map.html. We also enable override for our compiler, so that it will overwrite previous compiles each time we
    run this script.

7. Finally, go ahead and run the emulation script, in this case, `kubo.py`. This will compile
the emulation for Docker, and generate this in the `./output/` directory.


## Running the Emulation
Within the output directory, use the appropriate Docker compose CLI tool to build and run
the emulation.
```bash
./output$ docker compose build
./output$ docker compose up
```

- Now that the emulation is running, you can view the network topology and access each host
via the Internet Map at http://localhost:8080/map.html. Alternatively, you can use the `docker
exec` command to attach a CLI session to a given Docker container.
- The best way to interact with IPFS here, is to use the Kubo CLI on any host that has Kubo
installed.

## Interacting with IPFS
The best way to interact with IPFS is to use the Kubo CLI on any host that has Kubo installed.
You can do this by opening a terminal window on a specific device through the Internet Map, or
by using the `docker exec` tool to attach a CLI to a particular container.

For a full command reference, please see the Kubo CLI reference [here](https://docs.ipfs.tech/reference/kubo/cli/#ipfs).
Below, you will find a brief description of a few CLI commands that you may use to test your
emulation.

### `ipfs bootstrap list`
With this command, you are able to view the list of bootstrap nodes used by the current Kubo
node. This should contain each Kubo node that we set to be a boot node during the installation
of Kubo in the emulator.

### `ipfs swarm peers`
With this command, you are able to view all of the peering relationships that Kubo has made.
This should include all bootstrap nodes, all adjacent Kubo nodes, as well as nodes learned
about via the bootstrap process. This means that the output of this command should include all
Kubo nodes on the network, for this simulation.

### `ipfs add <filename>`
This command allows you to upload a given local file to IPFS. Take note of the long string of
letters and numbers that are returned by this command - this is the file's CID, or content
identifier. IPFS is a content-addressed file system, and so you will need this ID to access
your file again later.
```
root@0402d8fca4df / # ipfs add test.txt
added QmTE9Xp76E67vkYeygbKJrsVj8W2LLcyUifuMHMEkyRfUL test.txt
 13 B / 13 B [===============================================================] 100.00%
root@0402d8fca4df / # 
```

### `ipfs cat <cid>`
This command allows you to view the contents of a given file on IPFS, from any node in the
IPFS network. Rather than a filename, this command takes the data's CID as its only argument.
This is because IPFS is a content-addressed file system.
```
root@1bb8278a2cab / # ipfs cat QmTE9Xp76E67vkYeygbKJrsVj8W2LLcyUifuMHMEkyRfUL
Hello, World
root@1bb8278a2cab / # 
```