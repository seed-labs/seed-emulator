
## Simulator Class

The simulator class stores the following objects
```
networks = {}
hosts    = {}
routers  = {}
ASes     = {}
IXPs     = {}
```
Each of them is a dictionary data structure. The key is the name. In the simulator, each entity has a unique name. The naming convention is encoded in the ```SimConstants``` class. The value part is the object. Given the name, we can easily retrieve its corresponding object.


## AS/IXP, Host, BGPRouter, RouteServer classes

The relationships among the different entity in the model are captured inside each class. For example, the BGPRouter has a ```peers``` element, which stores a list of peers of this BGPRouter. We only use names in those data structures, instead of using the actual object. We use the set data structure, so we don't need to worry about adding duplicate entries.

Some of the classes also has an ```interfaces``` element. This one is a list, because the order is important (e.g. for BGP routers, eth0 is for the internal network, and eth1 is for the IX network). In the future, if we can control the name of each interface, we will change it to a dictionary data structure, so we don't make assumption on the order.


## File: ases.csv

Store the ASes information. Here is the type information. Right now 
we didn't do anythind different for TR and ST types. 

```
TR: Transit AS 
ST: Stub AS
IX: Internet Exchange
```

**Future work:**  We can add tags in each row, to indicate that we want to run on hosts, for example,
```
3,    TR,    10.@.0.0/24, DNS,Web,
4,    TR,    10.@.0.0/24, Web,
```

## File: peering.csv

Each line has 10 peerings. If this is not enough, we can
use another row. The program can handle this. 
```
150@100: means peering with AS150 at IX100.
rs@100:  means peering with the route server at IX100
```

There is no need to repeat the peering: if AS2 and AS3 is already peered in AS2's record, there is no need to do it in AS3's record. However, if a peering is duplicated, it does not do any harm.

**Future work:** the program can generate a new csv file, which provides the complete peering information. 

