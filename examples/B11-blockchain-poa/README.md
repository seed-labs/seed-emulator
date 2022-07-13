# Blockchain - POA (Proof of Authority)

In this example, we deploy 100 ethereum nodes inside the SEED Emulator.
We use `go ethereum:geth` software to run ethereum blockchain and use
`clique` option to deploy blockchain based on `POA: Proof of Authority` 
consensus mechanism. 

## Test Environment Settings
**PC Environment Settings**
- Virtual Machine (Virtualbox)
- CPU : 4 processors
- Memory: 8GB

**SEED Emulator Environment Settings**
- Internet Exchange : 5
- Transit AS : 4
- Stub AS : 10
- Hosts : 100

**Ethereum Service Settings**
- Total Node : 100
- Sealer Node: 40
- Boot Node : 10
- saveState : False
- geth snapshot option : False
- geth syncmode : Full
- creating a block per 15 seconds


## Resource Consumption
htop shows that `/usr/libexec/gvfs-udisks2-volume-monitor` consumes most of CPU. 
To maximize efficiency, you can disable gvfs-udisk2-volume-monitor by the command below.
`systemctl --user stop gvfs-udisks2-volume-monitor.service`

When you reboot your computer, it will run again as we only `stop` the service. 
If you want to disable the service permantly, you can use `disable` instead. 

### Sending transactions per sec
#### **without stopping gvfs-udisk2-volume-monitor.service**
- Max Transaction Counts : 3328
- Running Time : about 80 minutes

![](images/sending_trx.mp4)

