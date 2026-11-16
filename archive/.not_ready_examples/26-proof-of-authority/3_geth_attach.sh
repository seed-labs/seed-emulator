# Run geth on all containers
start=1
end=$(docker ps | grep Ethereum | wc -l)
for (( node=$start; node<=$end; node++ ))
do
	container=$(docker ps | grep "Ethereum-$node-" | awk '{print $1}')
	(docker exec -td -w /tmp $container bash run.sh) &
	echo "Geth executed on node $node in container $container"
done

echo "Done running ethereum nodes"
