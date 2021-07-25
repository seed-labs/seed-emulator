# Using a Pre-built Component

In Example `A01-transit-as`, we have saved the emulator in
a file as a component. In this example, we demonstrate how 
we can load it into another emulation. 


## Loading a Pre-Built Component

We can load a pre-built component. All the layers of the component 
will be loaded. If the current emulator already has layers, 
merging will be conducted if needed.


```python
emu = Emulator()
emu.load('../01-transit-as/base-component.bin')
```

## Getting the Layer Reference

If we want to make changes to any layer, we first need to get 
the layer object. In this example, we need to make changes
to the `base`, `web`, and `ebgp` layers, so we get their references.

```
base: Base       = emu.getLayer('Base')
web:  WebService = emu.getLayer('WebService')
ebgp: Ebgp       = emu.getLayer('Ebgp')
```

## Adding Host to an Existing Autonomous System

We can also modify an existing AS from the component. We just need to 
get the reference of this AS first, and then use the standard API
to make changes. In this example, we have a new host to `AS-151`.

```python
as151 = base.getAutonomousSystem(151)
as151.createHost('web-2').joinNetwork('net0')
```

## Adding a New Autonomous System

Once we get the `base` layer, we can add new elements to the layer,
such as a new autonomous system, a new internet exchange, etc. 
The code to do this is the same as that in building an emulation
from scratch. In this example, we created a new autonomous system `AS-153`,
and then peer it with the other two ASes from the component at the
internet exchange `ix100`, which is also from the component.

```python
ebgp.addPrivatePeering(100, 150, 153, abRelationship = PeerRelationship.Provider)
ebgp.addPrivatePeering(100, 151, 153, abRelationship = PeerRelationship.Peer)
```

## Adding a New Internet Exchange 

In the example, we also show how to create an new internet exchange, and then 
peer two ASes in this IX. We do need to create a new BGP router for an AS
and place it inside this IX, if the AS wants to peer with others in this IX.


```
base.createInternetExchange(102)
```


