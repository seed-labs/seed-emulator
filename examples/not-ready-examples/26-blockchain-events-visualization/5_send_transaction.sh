# In component-blockchain.py, i am using mod 3
# These are the same commands for both proof of work and proof of authority
start=1
end=$(docker ps | grep Ethereum | wc -l)

echo "Unlocking sealers ..."
for (( node=$start; node<=$end; node++ ))
do
	if  (($node % 3)); then
		container=$(docker ps | grep "Ethereum-$node-" | awk '{print $1}')
		docker exec -t $container geth attach --exec "eth.sendTransaction({from:eth.coinbase, to:eth.accounts[1], value:1})"
		echo "Sending transaction inside node $node"
	fi
done
