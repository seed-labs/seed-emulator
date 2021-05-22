# seedsim: miscellaneous

The emulator provides a few other compilers for running the emulation in different environments. It also includes a graphing system for visualizing various topologies. We will go over them in this example. 

The topology used in this example is the exact same as the MPLS transit example. We won't go over the setup again here.

## Graphing

All classes derived from `Graphable` can output one or more graphs of their topology. Currently, the `Graphable` classes and the graph they produce are as follow:

- `AutonomousSystem` offers the following graphs:
    - Layer 2 connections of the current AS.
- `Base` offers the following graphs:
    - Layer 2 connections of all AS, on one graph.
- `Ebgp` offers the following graphs:
    - eBGP peering (One each AS).
    - eBGP peering (All AS on one graph)
- `Ibgp` offers the following graphs:
    - iBGP peering (One each AS).
- `Mpls` offers the following graphs:
    - MPLS topology (One each AS).

To get graphs from graphable classes, first, render the emulation, then call `graphable.createGraphs()`. Once done, they will be available via `graphable.getGraphs()`. For example:

```python
r.render()

# ...

ebgp.createGraphs()
for graph in ebgp.getGraphs().values():
    print(graph)
    print(graph.toGraphviz())
```

The `getGraphs` call returns a `dict` of type `<str, Graph>`. The key is the name of the graph, and the value is the generated graph object. All graphs have a `toGraphviz` method, to convert the graph into graphviz dot file.

## Registry

There is a global class, Registry, which keep tracks of every important objects created in the emulation (nodes, layers, networks, files, etc.). In fact, what compiles do is just takes the node and network objects out from the Registry and convert them to dockerfiles.

### Inspecting objects

Most of the objects created in the emulator are derived from the `Printable` class. As the name suggested, they can be printed. To see what classes are printable, check the API documentation. `Registry` is also a printable object, we can print it to check almost all objects created in the emulation:

```python
print(Registry())
```

## Other compiling options

```python
docker_compiler.compile('./seedsim-misc/regular-docker')
```

In the examples, we have only used the single-host docker compiler. The emulator, however, does offer various other options to run the emulation distributly.

### Distributed Docker (`DistributedDocker`) compiler

```python
dist_compiler.compile('./seedsim-misc/distributed-docker')
```

Instead of compiling all nodes into one set of containers, the `DistributedDocker` compiler compiles nodes into multiple sets of containers. Each autonomous system will be in its own set, and each will have its own `docker-compose.yml`. 

This works by making all internet exchange networks overlay network. To run the emulation distributed, create a docker swarm, and start the internet exchange container sets on manager nodes. The rest of the autonomous systems can be started on either worker or manager nodes.

### GCP (Google Cloud Platform) Distributed Docker (`GcpDistributedDocker`) compiler

```python
gcp_dist_compiler.compile('./seedsim-misc/gcp-distributed-docker')
```

Instead of creating a docker swarm manually and host the autonomous systems one by one, we can use the GCP Distributed Docker compiler to compile the emulation to a terraform plan; the plan will automatically create virtual machines for the swarm, configure the swarm, and deploy the autonomous systems on them.

It uses the `DistributedDocker` to generate the containers and will generate an additional terraform plan for deploying it on GCP. To deploy, run `terraform apply` and follow the instructions.

### Graphs

```python
graphviz_compiler.compile('./seedsim-misc/graphs')
```

This is not a real compiler. Instead of comping nodes, the compiler gathers all graphable objects, create the graphs, and dump h Graphviz files.