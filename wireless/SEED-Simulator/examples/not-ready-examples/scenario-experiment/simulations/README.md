# Topologies
## 1. Linear Mobility Model


https://github.com/seed-labs/seed-blockchain/assets/19922651/db6da467-2e88-4982-853a-e8154d4aca0a

```python
for i, node in enumerate(nodes):
    # Linear
    mobility = LinearMobilityModel(nodeId=i, nodeTotal=NODE_TOTAL, length=1000, maxLength=2000)
        
    mobility.setMobilityBuildingInfo()
    mobility.setBoundary(Box(0,200, 0, 200, 0, 100), isBouncy=True)

    nodes[i].setMobility(mobility)

```

## 2. Circular Mobility Model


https://github.com/seed-labs/seed-blockchain/assets/19922651/93302a56-76b4-482c-bf1e-45ac6aec3229

```python
for i, node in enumerate(nodes):
    # Circular
    if i==22 or i==29:
        mobility = CircularMobilityModel(nodeId=i, nodeTotal=NODE_TOTAL, centerX=100, centerY=100, radius=100, maxRadius=300)
    else:
        mobility = CircularMobilityModel(nodeId=i, nodeTotal=NODE_TOTAL, centerX=100, centerY=100, radius=200)

    mobility.setMobilityBuildingInfo()
    mobility.setBoundary(Box(0,200, 0, 200, 0, 100), isBouncy=True)
 
    nodes[i].setMobility(mobility)
```

## 3. Star Mobility Model



https://github.com/seed-labs/seed-blockchain/assets/19922651/767eb5ca-908d-4490-ad5a-bd4e43f339a1

```python
for i, node in enumerate(nodes):
    # Star
    mobility = StarMobilityModel(nodeId=i, nodeTotal=NODE_TOTAL, centerX=100, centerY=100, radius=50, maxRadius=100)
   
    mobility.setMobilityBuildingInfo()
    mobility.setBoundary(Box(0,200, 0, 200, 0, 100), isBouncy=True)

    nodes[i].setMobility(mobility)
```

## 4. Grid Mobilitiy Model


https://github.com/seed-labs/seed-blockchain/assets/19922651/fe16984b-5147-4534-9c00-7c8a8db95e0b


```python
for i, node in enumerate(nodes):
    # Grid
    if i==22 or i==29:
        mobility = GridMobilityModel(nodeId=i, nodeTotal=NODE_TOTAL, colTotal=10, dist=10, paused=False)
    else:
        mobility = GridMobilityModel(nodeId=i, nodeTotal=NODE_TOTAL, colTotal=10, dist=10, paused=True)
        
    mobility.setMobilityBuildingInfo()
    mobility.setBoundary(Box(0,200, 0, 200, 0, 100), isBouncy=True)
    
    nodes[i].setMobility(mobility)
```

# Experiment Scenario 1

From the static topology model, move one node and see the change of routes.

## 1. LogDistanceProgationLossModel

Frequency : 28.0e9

### 1-1. Circle topology

![circle topology with log distance propagation model](./img/circle_log_distance.jpg)
expected result : loss will be changed to 100% from 0% when the distance between 2 nodes is over threshold.
experiment result : when the distance is 51.65m, the loss becomes 100%.

### 1-2. Line topology


