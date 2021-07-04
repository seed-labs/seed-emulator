# Compiler

The emulator provides a few other compilers for running the emulation in
different environments. It also includes a graphing system for visualizing
various topologies. 


## Docker compiler

This compiler generates the docker files that can run
on a single host. 

```python
emu.compile(Docker(), './output/regular-docker')
```

## Distributed Docker (`DistributedDocker`) compiler

```python
emu.compile(DistributedDocker(), './output/distributed-docker')
```

Instead of compiling all nodes into one set of containers, the
`DistributedDocker` compiler compiles nodes into multiple sets of containers.
Each autonomous system will be in its own set, and each will have its own
`docker-compose.yml`. 

This works by making all internet exchange networks overlay network. To run the
emulation distributed, create a docker swarm, and start the internet exchange
container sets on manager nodes. The rest of the autonomous systems can be
started on either worker or manager nodes.


## GCP (Google Cloud Platform) Distributed Docker (`GcpDistributedDocker`) compiler

```python
emu.compile(GcpDistributedDocker(), './output/gcp-distributed-docker')
```

Instead of creating a docker swarm manually and host the autonomous systems one
by one, we can use the GCP Distributed Docker compiler to compile the emulation
to a terraform plan; the plan will automatically create virtual machines for
the swarm, configure the swarm, and deploy the autonomous systems on them.

It uses the `DistributedDocker` to generate the containers and will generate an
additional terraform plan for deploying it on GCP. To deploy, run `terraform
apply` and follow the instructions.



## Graph compiler

```python
emu.compile(Graphviz(), './output/graphs')
```

Instead of generating the emulation files, 
this compiler gathers all graphable objects, creates the graphs, 
and generates the files that can be visualized using the 
`Graphviz` software. 

All classes derived from `Graphable` can output one or more graphs of their
topology. Currently, the `Graphable` classes and the graph they produce are as
follow:

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

The `getGraphs` call returns a `dict` of type `<str, Graph>`. The key is the
name of the graph, and the value is the generated graph object. All graphs have
a `toGraphviz` method, to convert the graph into graphviz dot file.
