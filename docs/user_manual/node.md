# User Manual: Node and Its Customization

We often need to customize nodes. This manual shows how to do that. 
Customization can be done directly on a physical node. In the examples, 
we will use the following node. 

```python
as152 = base.createAutonomousSystem(152)
as152.createNetwork('net0')
node = as152.createHost('newhost').joinNetwork('net0')
```

If we want to customize an existing node, we can get 
an instance of this node using the following APIs:

```python
as152 = base.getAutonomousSystem(152)
node  = as152.getHost('newhost')
```


## Install software via `apt-get`

If we need to install additional software on a node, 
and the software can be installed via the `apt-get` command, 
we can use the `addSoftware()` API. 
The provided software will be added to the software list 
in the `apt-get install` command in Dockerfile.

```python
node.addSoftware("python3")
```


## Install software via `RUN` command 

Some of the software may have to be installed using some ad hoc
commands, like `curl`, `wget`, etc. We can add the installation commands
using the `addBuildCommand()` API. 

```python
node.addBuildCommand("curl http://example.com")
```

This API will lead to the addition of a
`RUN` command in Dockerfile. When the container is built, the command
will be executed. 

```
RUN curl http://example.com
```

## Import and create file 

We may also install our own program on a node, or just simply
set up a file. To do that, we can use several APIs. 
See the following example:  

```
# Create a file on the node; file content come from hostpath
node.importFile(hostpath="/home/seed/example.py",
                containerpath="/example.py")

# Create a file on the node; file content is the provided string
node.setFile(path="/file.txt", content="hello world")
```

For the `importFile()` API, the `hostpat` is the file on the host machine
(should have an absolute path), while the `containerpath` is the 
target location and file name in the container.
Both APIs will lead to the additional a `COPY` command in the Dockerfile. 



## Execute command during the node startup

If we want to run some commands when a container starts, we can
add our commands to the `start.sh` script, which will be 
executed automatically when a container in the emulator starts. 

```
node.insertStartCommand("ping 1.2.3.4")
node.appendStartCommand("python /myserver.py", fork=True) 
```

It should be noted that the command should not be a blocking command,
because other commands will be added to `start.sh` by the emulator. 
Running a blocking command will prevent those commands from being executed. 
To run a blocking command, set the `fork` argument to True, this will
run the command in the background. 



## Add entries to /etc/hosts 

We can assign a hostname to a node. A mapping from this hostname to the
node's IP address will be added to the `/etc/hosts` file on every node. 

```python
node.addHostName('example.com')
```

It should be noted that adding the hostname-to-IP mappings
to the `/etc/hosts` is done by the `EtcHosts` layer, so we need to add
this layer to the emulator; otherwise, the mappings will not be added. 


```python
emu.addLayer(EtcHosts())
```


