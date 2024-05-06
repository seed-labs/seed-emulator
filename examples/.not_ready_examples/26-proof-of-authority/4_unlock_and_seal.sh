# Only unlock and run the miners/sealers
# In component-blockchain.py, i am using mod 3
# These are the same commands for both proof of work and proof of authority
start=1
end=$(docker ps | grep Ethereum | wc -l)

echo "Unlocking sealers ..."
for (( node=$start; node<=$end; node++ ))
do
	if  (($node % 3)); then
		container=$(docker ps | grep "Ethereum-$node-" | awk '{print $1}')
		docker exec -t $container geth attach --exec "personal.unlockAccount(eth.coinbase, 'admin', 0)"
		docker exec -t $container geth attach --exec "miner.start(1)"
		echo "Unlocked sealer in node $node and started sealing"
	fi
done
