# Visualization

In this example, we demonstrate how to set the meta data for 
the elements in the emulation. The meta data will be displayed
by the visualization software. 

Each node in the emulation has a name, but the name may not be 
very meaningful. To help visualizing the emulation, we can
provide meta data for these nodes. The following 
examples use `setDisplayName()` and `setDisplayName` to 
set meta data. 

```
as151 = base.getAutonomousSystem(151)
as151.getRouter('router0').setDisplayName('AS151 Core Router')
as151.getHost('web').setDisplayName('example.com')

ix100_lan = base.getInternetExchange(100).getPeeringLan()
ix100_lan.setDisplayName('Seattle').setDescription('The Seattle Internet Exchange')

ix101_lan = base.getInternetExchange(101).getPeeringLan()
ix101_lan.setDisplayName('New York')
```
