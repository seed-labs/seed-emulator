# Run bootstrapper on all ethereum nodes
# All nodes need to be aware of the bootnodes
start=1
end=$(docker ps | grep Ethereum | wc -l)
for (( node=$start; node<=$end; node++ ))
do
	container=$(docker ps | grep "Ethereum-$node-" | awk '{print $1}')
	docker exec -t -w /tmp $container bash eth-bootstrapper
	sleep 1
	echo "Bootstrapper executed on node $node in container $container"
	docker exec $container ls /tmp | grep eth-node-urls
done
