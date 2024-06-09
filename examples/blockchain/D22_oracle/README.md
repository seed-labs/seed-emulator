# Oracle

This example demonstrates how a blockchain can 
access data from the world outside. Blockchain
programs (i.e., smart contract) cannot directly 
access external data. It has to be done using
a special mechanism called oracle,
which is a means for smart contracts to access data from 
the world outside the blockchain. It typically involves 
a smart contract (running inside the blockchain) and 
an external node running outside of the blockchain. 
The external node take data from the outside world and 
put it into the blockchain.  

This example is created to demonstrate how oracle works.
We have created two new nodes, one for running the oracle node (getting
data from external sources) and the other for running the 
user program (getting data from the oracle). 


## Oracle Node

The main purpose of this node is to fetch external data and save
the data to the blockchain. When the emulator starts, 
this node will automatically carry out
the following tasks: 

- Create an account, and fund it using Faucet
- Deploy the oracle contract
- Register the oracle address with the utility server
- Start the server to listen to the update-price message, and do the 
  following once such a message is received: 

    - Fetch the data from outside. In this example, for the sake of 
      simplicity, we just randomly generate a price value. In practice,
      the data is obtained from an external data source 
    - Write the price data to the oracle contract by invoking the `setPrice`
      function. This will trigger a transaction 


## User Node

This node demonstrates how oracle is used. Typically, a user contract
would interact with the oracle contract to get the external data. 
For the simplicity, we directly interact with the oracle contract 
using a Python program. The program is already installed on 
the user node, and we need to go to this container, 
manually run this program: `user_get_price.py`. The program will
do the followings:

- Get the oracle contract address from the Utility server
- Invoke the oracle contract' `updatePrice` function. This will trigger 
  a transaction
- Sleep for a few seconds, then invoke the oracle contract's
  `getPrice` function, and print out the price. 
  This is just a local call.  
- The program will repeat the whole updatePrice-getPrice process. 
```
root@8631f635cd20 /oracle # python3 user_get_price.py
== EthereumHelper: Successfully connected to http://10.150.0.74:8545
... - INFO - Utility server is connected.
... - INFO - Successfully invoke updatePrice().
Price 30
Price 30
Price 43
Price 43
Price 43
... - INFO - Successfully invoke updatePrice().
Price 43
Price 43
Price 59
Price 59
```

## The Oracle Contract

The oracle contract in this example is very simple. It mainly has
the following three functions:

```
function getPrice() public view returns (uint) {
    return price;
}

event UpdatePriceMessage(address indexed _from);

function updatePrice() public payable {
    emit UpdatePriceMessage(msg.sender);
}

function setPrice(uint p) public {
    price = p;
}
```

When the user needs to get the most recent price data, 
it invokes the `updatePrice` function. This will emit
a `UpdatePriceMessage`, which informs the oracle node
to go fetch the data. The oracle node then
writes the price data to the oracle contract by invoking
`setPrice`. After the data is stored on the blockchain,
the user can use a local call `getPrice` to read the 
price value. 



