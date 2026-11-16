# Core-Layer Component Demo

In this demo, we show how to build an emulator, and then save it 
as a component. We can 

## Creating and saving the component (`core-dump.py`)

We directly took the code from the `01-transit-as` example. We only replaced
the `emu.render()` with the following (we also removed the compilation
part, as there is no need for it). 

```python
emu.dump('component-dump.bin')
```

## Loading a pre-built component (`core-load.py`)

In another emulator-building program, we can load this pre-built component.
All the layers from the component will be loaded. If the current emulator
already has layers, merging will be conducted if needed. 


```python
emu = Emulator()
emu.load('component-dump.bin')
```


## Adding a new autonomous system

To demonstrate how to add new elements to this core components, we create another 
autonomous system (`AS153`) and peer it with `AS150` and `AS151` at `IX100`.

```python
ebgp.addPrivatePeering(100, 150, 153, abRelationship = PeerRelationship.Provider)
ebgp.addPrivatePeering(100, 151, 153, abRelationship = PeerRelationship.Peer)
```

## Adding hosts to an existing autonomous system

We add a host to `AS-151`'s network `net0`. We also add a virtual node to the 
web layer, and then bind this virtual node to the newly created web host.

```python
as151 = base.getAutonomousSystem(151)
as151.createHost('web-2').joinNetwork('net0')
web.install('web151-2')
emu.addBinding(Binding('web151-2', filter = Filter(nodeName = 'web-2', asn = 151)))
```

## Rendering and compiling

After everything is done, we can render and compile the emulation. This part is the 
same as the other examples. 

```
emu.render()
emu.compile(Docker(), './output')
```
