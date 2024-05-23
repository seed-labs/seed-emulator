# Scion with link properties

In this example we show how one can specify link properties.

We have three ASes 110,111 and 112. 110 is a core AS and is connected to the other two ASes through a cross connects.

## Setting Cross connect link properties

Setting cross connect link properties works as shown in this exampls:

`as_110_br2.crossConnect(112,'br1','10.3.0.10/29',latency=30,bandwidth=500,packetDrop=0.1,MTU=1100)`


`as110.createNetwork('net0').setDefaultLinkProperties(latency=10, bandwidth=1000, packetDrop=0.1).setMtu(1400)`

Latency, and Bandwidth will be included in the Scion beacons if specified here. If no properties are specified, they will be omitted in the beacons

## Specify border routers for scion routing

If there is more than one link between a pair of ASes one can specify how to set the routes as follows:

`scion.addXcLink((1,110),(1,111),ScLinkType.Transit,a_router='br1',b_router='br1')`
`scion.addXcLink((1,110),(1,111),ScLinkType.Transit,a_router='br2',b_router='br1')`

## Set additional Border Router / AS properties

One can also specify additional information for the Scion-ASes and the border routers. Geolocation, and AS note will also be included in the beacons during the beaconing process   

`as110.setNote('This is a core AS')`

`as_110_br1 = as110.createRouter('br1').joinNetwork('net0').setGeo(Lat=37.7749, Long=-122.4194,Address="San Francisco, CA, USA").setNote("This is a border router")`

## Including link properties in beacons

By default, available link properties, Geolocation, Hops and AS-Notes will not be included in the `staticInfoConfig.json` file on the control Service nodes. To turn this on one can set the `generateStaticInfoConfig` flag to true as follows:

```python
as110.setGenerateStaticInfoConfig(True)
```