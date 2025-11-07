该示例尚未成熟，启动成功后需要执行如下命令，Etherview才能完全正常工作
- ip route del default 删除默认路由
- ip route add default via 10.152.0.1 dev eth0 新增默认路由 
- for i in $(seq 150 165); do ip route add 10.$i.0.0/24 via 10.152.0.254 dev eth0; done 新增路由

注：
    具体路由请根据实际情况而定，
    此处示例asn=152，新增的默认路由则为`10.152.0.1`，
    `10.152.0.254`是`emu.getDefaultRouterByAsnAndNetwork(152, 'net0')`的值
    `asns = [150, 151, 152, 153, 154, 160, 161, 162, 163, 164]`, 故循环`$(seq 150 165)`

