# Star Mobility Model



https://github.com/seed-labs/seed-blockchain/assets/19922651/767eb5ca-908d-4490-ad5a-bd4e43f339a1

```python
for i, node in enumerate(nodes):
    # Star
    mobility = StarMobilityModel(nodeId=i, nodeTotal=NODE_TOTAL, centerX=100, centerY=100, radius=50, maxRadius=100)
   
    mobility.setMobilityBuildingInfo()
    mobility.setBoundary(Box(0,200, 0, 200, 0, 100), isBouncy=True)

    nodes[i].setMobility(mobility)
```