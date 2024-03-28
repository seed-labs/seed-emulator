# Linear Topology

https://github.com/seed-labs/seed-blockchain/assets/19922651/db6da467-2e88-4982-853a-e8154d4aca0a

The Linear Mobility Model positions nodes in a linear arrangement. For example, the following code places all nodes on a horizontal line, with each node positioned at equal intervals, and the distance between the first and last nodes set to the specified length:

```python
for i, node in enumerate(nodes):
    # Linear 
    mobility = LinearMobilityModel(nodeId=i, nodeTotal=30, length=1000, maxLength=2000)
    nodes[i].setMobility(mobility)
```
In this example, if maxLength is provided, the length will increase at a rate of 5m per second until it reaches maxLength or until the iterations (time steps) are completed.